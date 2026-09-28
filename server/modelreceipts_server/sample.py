"""Build the dashboard samples ``dashboard/data/{aggregates,overview}.sample.json``.

REAL (public, pinned) seed data:
  * Aider polyglot leaderboard (benchmark records)
  * LMArena arena-human-preference-55k aggregate win counts (preference cells;
    only the all-task and coding rollups are loaded to keep the sample small)
SYNTHETIC data, labeled as such everywhere it appears:
  * field reports and pair-mode runs for made-up ``example-model-*`` models and
    ``example-harness-*`` harnesses (deterministic PRNG, fixed timestamps)
  * their self-assessments, next-prompt retry flags and token counts
  * the price table used for their server-side cost (``data/prices.synthetic.json``)
  * the OpenRouter-shaped usage fixture

The real collector never asks a model to grade itself; the synthetic
self-assessments exist so the "self-assessment ranking vs evidence ranking"
comparison can be demonstrated before real data exists.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from .aggregate import Thresholds, aggregate, overview
from .prices import DATA_DIR, PriceTable
from .store import Store

SAMPLE_NAMESPACE = uuid.UUID("0b8d1f55-2f7e-5d4c-8a3e-4c2f1a9e7b21")
FIXED_NOW = datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc)
SYNTHETIC_PRICES = DATA_DIR / "prices.synthetic.json"

# (model, skill = evidence pass tendency, bias = how much the model over-claims success, token scale)
MODELS = [
    ("example-model-a", 0.61, 0.29, 1.0),
    ("example-model-b", 0.70, 0.06, 1.3),
    ("example-model-c", 0.52, 0.36, 0.8),
    ("example-model-d", 0.66, 0.13, 1.1),
    ("example-model-e", 0.47, 0.05, 0.6),
]
HARNESSES = [("example-harness-a", 0.00, 1.0), ("example-harness-b", 0.05, 1.4)]
L2S = [("coding.bugfix", 0.00), ("coding.feature", -0.06), ("coding.refactor", 0.04), ("coding.test", 0.07)]
PAIRS = [("example-model-a", "example-model-b"), ("example-model-c", "example-model-d"),
         ("example-model-b", "example-model-d")]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _record(i: int, rnd: random.Random, l2: str, model: str, skill: float, bias: float, scale: float,
            harness: str, p: float, pair_id: str | None = None) -> dict:
    tested = rnd.random() < 0.85
    passed = rnd.random() < p if tested else None
    self_score = round(_clamp(skill + bias + rnd.uniform(-0.12, 0.12), 0.05, 1.0), 3)
    retry = rnd.random() < (0.45 if passed is False else 0.12)
    tokens_in = int(rnd.randint(2_000, 20_000) * scale)
    return {
        "schema_version": "0.2.0",
        "record_id": str(uuid.uuid5(SAMPLE_NAMESPACE, f"field/{i}")),
        "submitted_at": "2026-09-27T12:00:00Z",
        "source": {"source_type": "field_report", "client": "example-client", "client_version": None,
                   "collector": "pair-mode" if pair_id else "manual", "submit_mode": "all_runs", "install_key_sig": None},
        "task": {"l1": "coding", "l2": l2, "taxonomy_version": "t0.1", "classifier": "manual",
                 "interaction_type": "agentic",
                 "difficulty_prior": {"files_touched": rnd.randint(1, 6), "context_tokens": None}},
        "model": {"provider": "example", "id": model, "route": "unknown", "effort": None},
        "method": {"harness": harness, "workflow_tags": ["synthetic"], "tools_used": []},
        "usage": {"input_tokens": tokens_in, "output_tokens": int(rnd.randint(1_500, 12_000) * scale),
                  "cache_read_tokens": int(rnd.randint(20_000, 400_000) * scale),
                  "cache_write_tokens": int(rnd.randint(1_000, 30_000) * scale),
                  "cost_usd_client": None, "cost_usd_server": None,
                  "latency_ms": rnd.randint(20_000, 240_000), "turns": rnd.randint(2, 30)},
        "outcome": {"status": "completed",
                    "evidence": {"test_cmd_detected": tested, "test_runs": int(tested) + rnd.randint(0, 2) * int(tested),
                                 "tests_passed": passed,
                                 "committed": rnd.random() < _clamp(p - 0.08, 0, 1),
                                 "tool_error_count": rnd.randint(0, 3),
                                 "reverted_within_7d": None,
                                 "user_retry_next_prompt": retry, "retry_detector": "synthetic"},
                    "self_assessment": {"score": self_score, "rater": "self_claim", "judge_model": None,
                                        "extractor": "synthetic"}},
        "pairing": {"pair_id": pair_id},
        "privacy": {"content_included": False, "identifiers_included": False},
    }


def synthetic_field_records(seed: int = 20260927) -> Iterator[tuple[str, dict]]:
    """Yield (install_id, record) pairs: independent runs, then pair-mode runs. Deterministic."""
    rnd = random.Random(seed)
    skills = {m: (s, b, sc) for m, s, b, sc in MODELS}
    i = 0
    for l2, l2fx in L2S:
        for model, skill, bias, scale in MODELS:
            for harness, hfx, _hcost in HARNESSES:
                n = rnd.randint(14, 70)
                k = rnd.randint(2, 12)
                p = _clamp(skill + l2fx + hfx + rnd.uniform(-0.04, 0.04), 0.05, 0.95)
                for j in range(n):
                    i += 1
                    yield (f"synthetic-install-{l2}-{model}-{harness}-{j % k}",
                           _record(i, rnd, l2, model, skill, bias, scale, harness, p))
    for l2, l2fx in L2S[:2]:
        for ma, mb in PAIRS:
            for j in range(rnd.randint(12, 30)):
                pid = str(uuid.uuid5(SAMPLE_NAMESPACE, f"pair/{l2}/{ma}/{mb}/{j}"))
                install = f"synthetic-pair-install-{j % 6}"
                for model in (ma, mb):
                    skill, bias, scale = skills[model]
                    i += 1
                    p = _clamp(skill + l2fx, 0.05, 0.95)
                    yield install, _record(i, rnd, l2, model, skill, bias, scale, "example-harness-a", p, pid)


def _sample_store(thresholds: Thresholds) -> tuple[Store, int]:
    from modelreceipts_seeds import aider_polyglot, arena, openrouter

    store = Store(":memory:", prices=PriceTable.load(SYNTHETIC_PRICES), salt="sample-fixed-salt")
    meta, _index, seed_records = aider_polyglot.build()
    store.import_seed(meta, seed_records, validate=False)  # validated by the seed test-suite
    a_meta, a_cells = arena.build()
    subset = [c for c in a_cells if c["task"]["l1"] is None or (c["task"]["l1"] == "coding" and c["task"]["l2"] is None)]
    store.import_seed_cells(a_meta, subset, validate=False)
    o_meta, o_cells = openrouter.build()
    store.import_seed_cells(o_meta, o_cells, validate=False)
    field = 0
    for install_id, record in synthetic_field_records():
        store.add_field_report(record, install_id=install_id, received_at="2026-09-27T12:00:00Z")
        field += 1
    return store, field


def _label(field: int) -> dict:
    return {
        "label": ("SAMPLE — REAL public seeds: Aider polyglot leaderboard (benchmark, pinned snapshot) and LMArena "
                  "arena-human-preference-55k win counts (preference, all-task and coding rollups). SYNTHETIC: all "
                  f"{field} field_report records incl. pair-mode runs (example-model-*, example-harness-*), their "
                  "self-assessments, retry flags and server costs (synthetic price table), and the OpenRouter-shaped "
                  "usage fixture."),
        "synthetic_field_reports": True,
        "synthetic_sources": ["field_report", "openrouter-usage@synthetic-fixture", "synthetic-example@2026-09-27"],
        "generator": "PYTHONPATH=server python3 -m modelreceipts_server make-sample",
    }


def build_samples(thresholds: Thresholds | None = None) -> tuple[dict, dict]:
    thresholds = thresholds or Thresholds()
    store, field = _sample_store(thresholds)
    rows, sources, seed_cells = store.rows(), store.seed_sources(), store.seed_cell_rows()
    detail = aggregate(rows, thresholds, seed_sources=sources, seed_cells=seed_cells,
                       prices=store.prices.describe(), now=FIXED_NOW)
    public = overview(rows, thresholds, seed_sources=sources, seed_cells=seed_cells, now=FIXED_NOW)
    for obj in (detail, public):
        obj["dataset"] = _label(field)
    store.close()
    return detail, public


def build_sample(thresholds: Thresholds | None = None) -> dict:
    """Backward-compatible: the detailed sample only."""
    return build_samples(thresholds)[0]
