"""Per-cell aggregates with k-contributor / n-record disclosure thresholds.

A cell is ``(source_type, l1, l2, model, method)``; ``method`` is ``method.harness``
in v0.1. Seed layers and field reports are never pooled: ``source_type`` is part
of the cell key and every threshold is set per source type.

Disclosure rule (feasibility report, "20% MVP"): a cell is published only when it
has at least ``k`` distinct contributors AND at least ``n`` records. Suppressed
cells are listed by key only, without any counts.

Default thresholds:

* ``field_report``: k=5, n=30 (the report's initial proposal).
* seed layers (``benchmark``/``preference``/``usage``): k=1, n=30. Seed data is
  already public and has a single publisher, so k protects nobody there; n still
  guards against tiny samples.

Ranking signal = evidence. ``self_assessment`` is reported beside it with
``excluded_from_ranking: true`` and is never used for ordering.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Mapping

SOURCE_TYPES = ("field_report", "benchmark", "preference", "usage")


@dataclass(frozen=True)
class Threshold:
    min_contributors: int
    min_records: int


@dataclass
class Thresholds:
    by_source: dict = field(default_factory=lambda: {
        "field_report": Threshold(5, 30),
        "benchmark": Threshold(1, 30),
        "preference": Threshold(1, 30),
        "usage": Threshold(1, 30),
    })

    @classmethod
    def build(cls, k: int = 5, n: int = 30, seed_k: int = 1, seed_n: int = 30) -> "Thresholds":
        if min(k, n, seed_k, seed_n) < 1:
            raise ValueError("thresholds must be >= 1")
        seed = Threshold(seed_k, seed_n)
        return cls({"field_report": Threshold(k, n), "benchmark": seed, "preference": seed, "usage": seed})

    def for_source(self, source_type: str) -> Threshold:
        return self.by_source[source_type]

    def as_json(self) -> dict:
        return {st: {"min_contributors": t.min_contributors, "min_records": t.min_records}
                for st, t in self.by_source.items()}


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


def _cell_stats(source_type: str, rows: list[Mapping]) -> dict:
    tested = [r["tests_passed"] for r in rows if r["tests_passed"] is not None]
    passed = sum(1 for t in tested if t)
    cost = _mean([r["cost_usd_client"] for r in rows])
    pass_rate = round(passed / len(tested), 4) if tested else None
    stats = {
        "tests": {
            "tested": len(tested),
            "passed": passed,
            "pass_rate": pass_rate,
            "ci95": wilson(passed, len(tested)),
            "tested_share": round(len(tested) / len(rows), 4),
        },
        "cost_usd_per_task": {
            "client_mean": cost,
            "server_mean": _mean([r["cost_usd_server"] for r in rows]),
            "reported": sum(1 for r in rows if r["cost_usd_client"] is not None),
        },
        "cost_usd_per_success": round(cost / pass_rate, 6) if cost is not None and pass_rate else None,
        "latency_ms_median": _median([r["latency_ms"] for r in rows]),
    }
    if source_type == "field_report":
        self_scores = [r["self_score"] for r in rows if r["self_score"] is not None]
        stats["commit_rate"] = round(sum(r["committed"] for r in rows) / len(rows), 4)
        stats["tool_errors_mean"] = _mean([r["tool_error_count"] for r in rows])
        stats["self_assessment"] = {
            "n": len(self_scores),
            "mean": _mean(self_scores),
            "excluded_from_ranking": True,
        }
    else:
        # Seed rows carry placeholder values for fields the source does not report.
        stats["commit_rate"] = None
        stats["tool_errors_mean"] = None
        stats["self_assessment"] = None
    return stats


def aggregate(
    rows: Iterable[Mapping],
    thresholds: Thresholds,
    *,
    level: str = "l2",
    source_type: str | None = None,
    l1: str | None = None,
    l2: str | None = None,
    seed_sources: list[dict] | None = None,
    now: datetime | None = None,
) -> dict:
    if level not in {"l1", "l2"}:
        raise ValueError("level must be 'l1' or 'l2'")
    groups: dict[tuple, list] = defaultdict(list)
    totals: dict[str, int] = defaultdict(int)
    for r in rows:
        totals[r["source_type"]] += 1
        if source_type and r["source_type"] != source_type:
            continue
        if l1 and r["l1"] != l1:
            continue
        if l2 and r["l2"] != l2:
            continue
        key = (r["source_type"], r["l1"], r["l2"] if level == "l2" else None, r["model_id"], r["harness"])
        groups[key].append(r)

    cells, suppressed = [], []
    for key in sorted(groups, key=lambda k: tuple("" if v is None else v for v in k)):
        st, c_l1, c_l2, model, method = key
        members = groups[key]
        th = thresholds.for_source(st)
        k = len({m["contributor"] for m in members})
        head = {"source_type": st, "l1": c_l1, "l2": c_l2, "model": model, "method": method}
        if k < th.min_contributors or len(members) < th.min_records:
            suppressed.append({**head, "reason": "below_threshold"})
            continue
        cells.append({**head, "n": len(members), "k": k, **_cell_stats(st, members)})

    now = now or datetime.now(timezone.utc)
    return {
        "api": "modelreceipts.aggregates/v0.1",
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "filters": {"source_type": source_type, "l1": l1, "l2": l2},
        "thresholds": thresholds.as_json(),
        "method_dimension": "method.harness",
        "ranking_signal": "outcome.evidence (tests.pass_rate); self_assessment is excluded_from_ranking",
        "totals": {"records_by_source_type": {st: totals.get(st, 0) for st in SOURCE_TYPES}},
        "sources": seed_sources or [],
        "cells": cells,
        "suppressed": suppressed,
    }
