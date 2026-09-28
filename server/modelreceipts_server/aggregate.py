"""Aggregates with k-contributor / n-record disclosure thresholds.

Two views (feasibility report, "게이트 = 공개 개요 + 기여자 전용 세분 조회"):

* ``overview()`` — PUBLIC. Field reports are rolled up to ``(L1, model)``
  (L2 and harness collapsed) and carry only n, k, pass rate and median
  latency; no confidence intervals, costs, retry or self-assessment detail.
  Seed layers (already public data) are shown as-is.
* ``detail()`` — CONTRIBUTORS ONLY (the server checks a signed request from a
  key that contributed in the last 90 days). Cells ``(source_type, L1, L2,
  model, harness)`` with Wilson 95% CIs, cost per task and per success
  (client and server values side by side), commit/retry rates, the isolated
  self-assessment, pair-mode head-to-head results and the "self-assessment
  ranking vs evidence ranking" comparison.

Disclosure rule, per source type: a cell is published only with at least ``k``
distinct contributors AND at least ``n`` records AND no single contributor
above ``max_share`` of its records. Suppressed cells are listed by key only.

Defaults: field_report k=5, n=30, max_share=0.5; seed layers k=1, n=30 (public
data with one publisher, so k protects nobody; n still guards tiny samples).
Pairs: at least ``pair_min_pairs`` pairs from ``pair_min_contributors``.

Ranking signal = evidence. ``self_assessment`` is reported beside it with
``excluded_from_ranking: true`` and never used for ordering.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Iterator, Mapping

SOURCE_TYPES = ("field_report", "benchmark", "preference", "usage")
SEED_TYPES = ("benchmark", "preference", "usage")


@dataclass(frozen=True)
class Threshold:
    min_contributors: int
    min_records: int
    max_share: float = 1.0


@dataclass
class Thresholds:
    by_source: dict = field(default_factory=lambda: {
        "field_report": Threshold(5, 30, 0.5),
        "benchmark": Threshold(1, 30),
        "preference": Threshold(1, 30),
        "usage": Threshold(1, 1),
    })
    pair_min_pairs: int = 10
    pair_min_contributors: int = 3

    @classmethod
    def build(cls, k: int = 5, n: int = 30, seed_k: int = 1, seed_n: int = 30, max_share: float = 0.5,
              pair_min_pairs: int = 10, pair_min_contributors: int = 3) -> "Thresholds":
        if min(k, n, seed_k, seed_n, pair_min_pairs, pair_min_contributors) < 1:
            raise ValueError("thresholds must be >= 1")
        if not 0 < max_share <= 1:
            raise ValueError("max_share must be in (0, 1]")
        seed = Threshold(seed_k, seed_n)
        return cls({"field_report": Threshold(k, n, max_share), "benchmark": seed, "preference": seed,
                    "usage": Threshold(seed_k, 1)}, pair_min_pairs, pair_min_contributors)

    def for_source(self, source_type: str) -> Threshold:
        return self.by_source[source_type]

    def as_json(self) -> dict:
        out = {st: {"min_contributors": t.min_contributors, "min_records": t.min_records,
                    "max_contributor_share": t.max_share} for st, t in self.by_source.items()}
        out["pairs"] = {"min_pairs": self.pair_min_pairs, "min_contributors": self.pair_min_contributors}
        return out


def wilson(successes: int, n: int, z: float = 1.96) -> list[float] | None:
    if n <= 0:
        return None
    p = successes / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (c - s) / d), 4), round(min(1.0, (c + s) / d), 4)]


def _mean(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(statistics.fmean(vals), 6) if vals else None


def _median(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def _get(row: Mapping, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _suppression(members: list, th: Threshold) -> str | None:
    counts: dict[str, int] = defaultdict(int)
    for m in members:
        counts[m["contributor"]] += 1
    if len(counts) < th.min_contributors or len(members) < th.min_records:
        return "below_threshold"
    if max(counts.values()) / len(members) > th.max_share:
        return "dominated_by_one_contributor"
    return None


def _pass_stats(rows: list[Mapping]) -> dict:
    tested = [r["tests_passed"] for r in rows if r["tests_passed"] is not None]
    passed = sum(1 for t in tested if t)
    return {"tested": len(tested), "passed": passed,
            "pass_rate": round(passed / len(tested), 4) if tested else None,
            "ci95": wilson(passed, len(tested)),
            "tested_share": round(len(tested) / len(rows), 4)}


def _cell_stats(source_type: str, rows: list[Mapping]) -> dict:
    tests = _pass_stats(rows)
    cost = _mean([r["cost_usd_client"] for r in rows])
    server_cost = _mean([r["cost_usd_server"] for r in rows])
    pr = tests["pass_rate"]
    stats = {
        "tests": tests,
        "cost_usd_per_task": {
            "client_mean": cost,
            "server_mean": server_cost,
            "reported": sum(1 for r in rows if r["cost_usd_client"] is not None),
            "server_computed": sum(1 for r in rows if r["cost_usd_server"] is not None),
        },
        "cost_usd_per_success": round(cost / pr, 6) if cost is not None and pr else None,
        "server_cost_usd_per_success": round(server_cost / pr, 6) if server_cost is not None and pr else None,
        "latency_ms_median": _median([r["latency_ms"] for r in rows]),
    }
    if source_type == "field_report":
        self_scores = [r["self_score"] for r in rows if r["self_score"] is not None]
        retries = [_get(r, "retry_next") for r in rows if _get(r, "retry_next") is not None]
        stats["commit_rate"] = round(sum(1 for r in rows if r["committed"]) / len(rows), 4)
        stats["tool_errors_mean"] = _mean([r["tool_error_count"] for r in rows])
        stats["retry_next_prompt"] = {"observed": len(retries),
                                      "rate": round(sum(retries) / len(retries), 4) if retries else None}
        stats["self_assessment"] = {"n": len(self_scores), "mean": _mean(self_scores), "excluded_from_ranking": True}
    else:
        # Seed rows do not report these; v0.1 seed rows carried placeholders.
        stats["commit_rate"] = None
        stats["tool_errors_mean"] = None
        stats["retry_next_prompt"] = None
        stats["self_assessment"] = None
    return stats


def _filter(rows: Iterable[Mapping], source_type: str | None, l1: str | None, l2: str | None) -> Iterator[Mapping]:
    for r in rows:
        if source_type and r["source_type"] != source_type:
            continue
        if l1 and r["l1"] != l1:
            continue
        if l2 and r["l2"] != l2:
            continue
        yield r


def _cells(rows: list, thresholds: Thresholds, key_fn: Callable[[Mapping], tuple],
           stats_fn: Callable[..., dict]) -> tuple[list[dict], list[dict]]:
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        groups[key_fn(r)].append(r)
    cells, suppressed = [], []
    for key in sorted(groups, key=lambda k: tuple("" if v is None else v for v in k)):
        st, c_l1, c_l2, model, method = key
        members = groups[key]
        head = {"source_type": st, "l1": c_l1, "l2": c_l2, "model": model, "method": method}
        reason = _suppression(members, thresholds.for_source(st))
        if reason:
            suppressed.append({**head, "reason": reason})
            continue
        k = len({m["contributor"] for m in members})
        cells.append({**head, "n": len(members), "k": k, **stats_fn(st, members)})
    return cells, suppressed


def pairwise(rows: Iterable[Mapping], thresholds: Thresholds, l2: str | None = None) -> dict:
    """Head-to-head results of pair-mode runs (same task, two models).

    A pair is decisive when exactly one arm's last test run passed; both passed
    or both failed is a tie; pairs where either arm has no test result are
    counted as ``undecided`` and excluded from the win rate.
    """
    by_pair: dict[str, list] = defaultdict(list)
    for r in rows:
        pid = _get(r, "pair_id")
        if pid and r["source_type"] == "field_report" and (not l2 or r["l2"] == l2):
            by_pair[pid].append(r)
    groups: dict[tuple, dict] = {}
    for members in by_pair.values():
        if len(members) != 2 or members[0]["model_id"] == members[1]["model_id"]:
            continue
        a, b = sorted(members, key=lambda m: m["model_id"])
        if (a["l1"], a["l2"]) != (b["l1"], b["l2"]):
            continue
        g = groups.setdefault((a["l1"], a["l2"], a["model_id"], b["model_id"]),
                              {"pairs": 0, "a_wins": 0, "b_wins": 0, "ties": 0, "undecided": 0, "contributors": set()})
        g["pairs"] += 1
        g["contributors"].update({a["contributor"], b["contributor"]})
        ta, tb = a["tests_passed"], b["tests_passed"]
        if ta is None or tb is None:
            g["undecided"] += 1
        elif ta == tb:
            g["ties"] += 1
        elif ta:
            g["a_wins"] += 1
        else:
            g["b_wins"] += 1
    published, suppressed = [], []
    for (c_l1, c_l2, ma, mb), g in sorted(groups.items(), key=lambda kv: tuple("" if v is None else v for v in kv[0])):
        head = {"l1": c_l1, "l2": c_l2, "model_a": ma, "model_b": mb}
        if g["pairs"] < thresholds.pair_min_pairs or len(g["contributors"]) < thresholds.pair_min_contributors:
            suppressed.append({**head, "reason": "below_threshold"})
            continue
        decided = g["a_wins"] + g["b_wins"] + g["ties"]
        published.append({**head, "pairs": g["pairs"], "k": len(g["contributors"]),
                          "a_wins": g["a_wins"], "b_wins": g["b_wins"], "ties": g["ties"], "undecided": g["undecided"],
                          "a_score": round((g["a_wins"] + g["ties"] / 2) / decided, 4) if decided else None,
                          "a_score_ci95": wilson(round(g["a_wins"] + g["ties"] / 2), decided) if decided else None})
    return {"method": "evidence: last test run of each arm; tie = both passed or both failed",
            "results": published, "suppressed": suppressed}


def self_vs_evidence(cells: list[dict]) -> list[dict]:
    """Per L2: rank models by mean self-assessment and by evidence pass rate (published field cells only)."""
    per_l2: dict[str, dict[str, dict]] = defaultdict(dict)
    for c in cells:
        sa = c.get("self_assessment")
        if c["source_type"] != "field_report" or not sa or not sa["n"] or not c["tests"]["tested"]:
            continue
        m = per_l2[c["l2"] or c["l1"]].setdefault(c["model"], {"self": 0.0, "self_n": 0, "passed": 0, "tested": 0})
        m["self"] += sa["mean"] * sa["n"]
        m["self_n"] += sa["n"]
        m["passed"] += c["tests"]["passed"]
        m["tested"] += c["tests"]["tested"]
    out = []
    for task, models in sorted(per_l2.items()):
        if len(models) < 2:
            continue
        rows = [{"model": name, "self_mean": round(v["self"] / v["self_n"], 4),
                 "pass_rate": round(v["passed"] / v["tested"], 4), "tested": v["tested"]}
                for name, v in models.items()]
        by_self = sorted(rows, key=lambda r: (-r["self_mean"], r["model"]))
        by_ev = sorted(rows, key=lambda r: (-r["pass_rate"], r["model"]))
        for r in rows:
            r["rank_by_self"] = by_self.index(r) + 1
            r["rank_by_evidence"] = by_ev.index(r) + 1
        out.append({"task": task, "models": sorted(rows, key=lambda r: r["rank_by_evidence"]),
                    "rank_changes": sum(1 for r in rows if r["rank_by_self"] != r["rank_by_evidence"]),
                    "top_differs": by_self[0]["model"] != by_ev[0]["model"]})
    return out


def seed_cell_view(seed_cells: Iterable[Mapping], thresholds: Thresholds) -> dict:
    published, suppressed = [], []
    for c in sorted(seed_cells, key=lambda c: (c["source_id"], c["kind"], c["l1"] or "", c["l2"] or "", c["model_id"])):
        head = {"source_id": c["source_id"], "source_type": c["source_type"], "l1": c["l1"], "l2": c["l2"],
                "model": c["model_id"], "provider": c["provider"], "method": c["harness"], "kind": c["kind"]}
        if c["kind"] == "preference":
            if c["battles"] < thresholds.for_source("preference").min_records:
                suppressed.append({**head, "reason": "below_threshold"})
                continue
            decided = c["battles"]
            published.append({**head, "battles": c["battles"], "wins": c["wins"], "losses": c["losses"],
                              "ties": c["ties"], "win_rate": c["win_rate"],
                              "win_rate_ci95": wilson(round(c["win_rate"] * decided), decided)})
        else:
            published.append({**head, "tokens": c["tokens"], "share": c["share"], "rank": c["rank"]})
    return {"note": "Seed layers are never pooled with field reports. preference = human pairwise votes (not outcome "
                    "evidence); usage = adoption share (no quality signal).",
            "cells": published, "suppressed": suppressed}


def _envelope(api: str, view: str, level: str, thresholds: Thresholds, filters: dict, totals: dict,
              seed_sources: list[dict] | None, now: datetime | None, method_dim: str | None) -> dict:
    now = now or datetime.now(timezone.utc)
    return {
        "api": api,
        "view": view,
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "filters": filters,
        "thresholds": thresholds.as_json(),
        "method_dimension": method_dim,
        "ranking_signal": "outcome.evidence (tests.pass_rate); self_assessment is excluded_from_ranking",
        "totals": {"records_by_source_type": {st: totals.get(st, 0) for st in SOURCE_TYPES}},
        "sources": seed_sources or [],
    }


def _cell_totals(seed_cells: Iterable[Mapping]) -> dict:
    t: dict[str, int] = defaultdict(int)
    for c in seed_cells:
        t[c["source_type"]] += 1
    return dict(sorted(t.items()))


def _totals(rows: Iterable[Mapping]) -> dict:
    t: dict[str, int] = defaultdict(int)
    for r in rows:
        t[r["source_type"]] += 1
    return t


def aggregate(rows: Iterable[Mapping], thresholds: Thresholds, *, level: str = "l2", source_type: str | None = None,
              l1: str | None = None, l2: str | None = None, seed_sources: list[dict] | None = None,
              seed_cells: Iterable[Mapping] | None = None, prices: dict | None = None,
              now: datetime | None = None) -> dict:
    """The contributor-only DETAILED view."""
    if level not in {"l1", "l2"}:
        raise ValueError("level must be 'l1' or 'l2'")
    rows = list(rows)
    selected = list(_filter(rows, source_type, l1, l2))
    cells, suppressed = _cells(
        selected, thresholds,
        lambda r: (r["source_type"], r["l1"], r["l2"] if level == "l2" else None, r["model_id"], r["harness"]),
        _cell_stats)
    out = _envelope("modelreceipts.aggregates/v1", "detail", level, thresholds,
                    {"source_type": source_type, "l1": l1, "l2": l2}, _totals(rows), seed_sources, now, "method.harness")
    out["price_table"] = prices
    out["cells"] = cells
    out["suppressed"] = suppressed
    out["pairwise"] = pairwise(selected, thresholds)
    out["self_vs_evidence"] = self_vs_evidence(cells)
    seed_cells = list(seed_cells or [])
    out["totals"]["seed_cells_by_source_type"] = _cell_totals(seed_cells)
    out["seed_cells"] = seed_cell_view(
        [c for c in seed_cells if (not source_type or c["source_type"] == source_type)], thresholds)
    return out


def _overview_stats(source_type: str, rows: list[Mapping]) -> dict:
    tests = _pass_stats(rows)
    return {"tests": {"tested": tests["tested"], "pass_rate": tests["pass_rate"]},
            "latency_ms_median": _median([r["latency_ms"] for r in rows])}


def overview(rows: Iterable[Mapping], thresholds: Thresholds, *, seed_sources: list[dict] | None = None,
             seed_cells: Iterable[Mapping] | None = None, now: datetime | None = None) -> dict:
    """The PUBLIC view: field reports at (L1, model); seed layers as published by their sources."""
    rows = list(rows)
    field = [r for r in rows if r["source_type"] == "field_report"]
    seeds = [r for r in rows if r["source_type"] != "field_report"]
    f_cells, f_supp = _cells(field, thresholds, lambda r: (r["source_type"], r["l1"], None, r["model_id"], None),
                             _overview_stats)
    s_cells, s_supp = _cells(seeds, thresholds, lambda r: (r["source_type"], r["l1"], r["l2"], r["model_id"], r["harness"]),
                             _cell_stats)
    out = _envelope("modelreceipts.overview/v1", "overview", "l1", thresholds, {}, _totals(rows), seed_sources, now,
                    "field_report: collapsed; seeds: method.harness")
    out["cells"] = f_cells + s_cells
    out["suppressed"] = f_supp + s_supp
    seed_cells = list(seed_cells or [])
    out["totals"]["seed_cells_by_source_type"] = _cell_totals(seed_cells)
    out["seed_cells"] = seed_cell_view(seed_cells, thresholds)
    out["gate"] = {
        "detail_endpoint": "/v1/aggregates/detail",
        "who": "contributors: a signed request from an install key that submitted a field report in the last 90 days",
        "adds": ["L2 x harness cells", "Wilson 95% CIs", "cost per task / per success (client and server)",
                 "commit, retry and tool-error rates", "self-assessment vs evidence", "pair-mode head-to-head"],
    }
    return out
