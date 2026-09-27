"""Build ``dashboard/data/aggregates.sample.json``: real Aider seed + SYNTHETIC field reports.

The field reports are fake and deterministic (seeded PRNG, fixed timestamps).
They use made-up model ids (``example-model-*``) and harnesses
(``example-harness-*``) so nobody mistakes them for measurements of real
products. They include a synthetic ``self_assessment`` so the dashboard can
demonstrate the "self-assessment vs evidence" comparison; the real collector
never asks a model to grade itself.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from .aggregate import Thresholds, aggregate
from .store import Store

SAMPLE_NAMESPACE = uuid.UUID("0b8d1f55-2f7e-5d4c-8a3e-4c2f1a9e7b21")
FIXED_NOW = datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc)

# skill = evidence pass tendency, bias = how much the model over-claims success.
MODELS = [
    ("example-model-a", 0.61, 0.29, 1.0),
    ("example-model-b", 0.70, 0.06, 1.6),
    ("example-model-c", 0.52, 0.36, 0.5),
    ("example-model-d", 0.66, 0.13, 0.9),
    ("example-model-e", 0.47, 0.05, 0.25),
]
HARNESSES = [("example-harness-a", 0.00, 1.0), ("example-harness-b", 0.05, 1.4)]
L2S = [("coding.bugfix", 0.00), ("coding.feature", -0.06), ("coding.refactor", 0.04), ("coding.test", 0.07)]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def synthetic_field_records(seed: int = 20260927):
    """Yield (install_id, record) pairs. Deterministic for a given seed."""
    rnd = random.Random(seed)
    i = 0
    for l2, l2fx in L2S:
        for model, skill, bias, price in MODELS:
            for harness, hfx, hcost in HARNESSES:
                n = rnd.randint(14, 70)
                k = rnd.randint(2, 12)
                p = _clamp(skill + l2fx + hfx + rnd.uniform(-0.04, 0.04), 0.05, 0.95)
                for j in range(n):
                    i += 1
                    tested = rnd.random() < 0.85
                    passed = rnd.random() < p if tested else None
                    self_score = round(_clamp(skill + bias + rnd.uniform(-0.12, 0.12), 0.05, 1.0), 3)
                    record = {
                        "schema_version": "0.1.0",
                        "record_id": str(uuid.uuid5(SAMPLE_NAMESPACE, f"field/{i}")),
                        "submitted_at": "2026-09-26T12:00:00Z",
                        "source": {"source_type": "field_report", "client": "example-client", "client_version": None,
                                   "collector": "manual", "submit_mode": "all_runs", "install_key_sig": None},
                        "task": {"l1": "coding", "l2": l2, "taxonomy_version": "t0.1", "classifier": "manual",
                                 "interaction_type": "agentic",
                                 "difficulty_prior": {"files_touched": rnd.randint(1, 6), "context_tokens": None}},
                        "model": {"provider": "example", "id": model, "route": "unknown", "effort": None},
                        "method": {"harness": harness, "workflow_tags": ["synthetic"], "tools_used": []},
                        "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0,
                                  "cost_usd_client": round(0.12 * price * hcost * rnd.uniform(0.7, 1.3), 4),
                                  "cost_usd_server": None,
                                  "latency_ms": rnd.randint(20_000, 240_000), "turns": rnd.randint(2, 30)},
                        "outcome": {"status": "completed",
                                    "evidence": {"test_cmd_detected": tested, "test_runs": int(tested) + rnd.randint(0, 2) * int(tested),
                                                 "tests_passed": passed,
                                                 "committed": rnd.random() < _clamp(p - 0.08, 0, 1),
                                                 "tool_error_count": rnd.randint(0, 3),
                                                 "reverted_within_7d": None, "user_retry_next_prompt": None},
                                    "self_assessment": {"score": self_score, "rater": "self_llm", "judge_model": None}},
                        "pairing": {"pair_id": None},
                        "privacy": {"content_included": False, "identifiers_included": False},
                    }
                    yield f"synthetic-install-{l2}-{model}-{harness}-{j % k}", record


def build_sample(thresholds: Thresholds | None = None) -> dict:
    from modelreceipts_seeds import aider_polyglot

    thresholds = thresholds or Thresholds()
    store = Store(":memory:")
    meta, _index, seed_records = aider_polyglot.build()
    store.import_seed(meta, seed_records, validate=False)  # validated by the seed test-suite
    field = 0
    for install_id, record in synthetic_field_records():
        store.add_field_report(record, install_id=install_id)
        field += 1
    result = aggregate(store.rows(), thresholds, seed_sources=store.seed_sources(), now=FIXED_NOW)
    result["dataset"] = {
        "label": ("SAMPLE — benchmark cells are the real, public Aider polyglot leaderboard (pinned snapshot); "
                  f"all {field} field_report records are SYNTHETIC (example-model-*, example-harness-*)."),
        "synthetic_field_reports": True,
        "generator": "PYTHONPATH=server python3 -m modelreceipts_server make-sample",
    }
    store.close()
    return result
