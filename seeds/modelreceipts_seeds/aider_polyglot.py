"""Aider polyglot leaderboard -> schema v0.2 seed records (``source_type=benchmark``).

Input: the pinned snapshot in ``seeds/data/aider-polyglot/`` (see SOURCE.json for
URL, commit, sha256 and license). The importer never touches the network.

Mapping (one leaderboard row = one benchmark run over ``test_cases`` exercises):

* Each exercise becomes one record, so aggregates count exercises the same way
  they count field runs. Outcomes come from the row's own counters:
  ``pass_num_1`` records passed on the 1st try (``test_runs=1``),
  ``pass_num_2 - pass_num_1`` passed on the 2nd try (``test_runs=2``),
  the rest failed after 2 tries. Which exercise passed is unknown and irrelevant
  for aggregates. Record ids are deterministic (uuid5), so re-imports are idempotent.
  Resulting pass rate = pass_num_2 / test_cases; the published ``pass_rate_2``
  sometimes divides by ``total_tests`` instead (differences up to ~0.4pp).
* ``model.id`` = slug of the leaderboard's display name (keeps variants such as
  "(32k thinking)" distinct). ``method.harness`` = ``aider-<edit_format>``.
* Cost/latency per exercise = row total / test_cases. ``total_cost: 0`` means
  "not reported" on the leaderboard and becomes ``null``.
* Task codes: ``coding`` / ``coding.feature`` (Exercism "implement to spec"),
  classifier ``seed:aider-polyglot``. This L2 mapping is an approximation.
* Fields the leaderboard does not report (``committed``, ``tool_error_count``,
  ``turns`` and, for most rows, tokens) are ``null`` (schema v0.2). Record ids
  are the same as in the earlier v0.1 import, so a v0.1 database migrated with
  ``migrate-db`` and a fresh v0.2 import describe the same exercises.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterator

from . import DATA_DIR
from .miniyaml import parse_list_of_maps

SOURCE_DIR = DATA_DIR / "aider-polyglot"
SEED_NAMESPACE = uuid.UUID("6f0c1b9e-3c53-5d1e-9a57-0b6a1f0d6c11")
CLASSIFIER = "seed:aider-polyglot"
L1, L2 = "coding", "coding.feature"

_PROVIDERS = [
    (r"claude|sonnet|opus|haiku", "anthropic"),
    (r"^(gpt|o1|o3|o4|chatgpt)", "openai"),
    (r"gemini|gemma", "google"),
    (r"deepseek", "deepseek"),
    (r"grok", "xai"),
    (r"qwen|qwq", "alibaba"),
    (r"llama", "meta"),
    (r"codestral|mistral", "mistral"),
    (r"^command", "cohere"),
    (r"kimi", "moonshotai"),
    (r"^yi-", "01-ai"),
    (r"openhands", "all-hands"),
]


def slug(text: str, max_len: int = 64) -> str:
    s = re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-._")
    s = re.sub(r"-{2,}", "-", s)
    return s[:max_len].rstrip("-._") or "unknown"


def guess_provider(display_name: str) -> str:
    name = display_name.lower()
    for pattern, provider in _PROVIDERS:
        if re.search(pattern, name):
            return provider
    return "unknown"


def guess_route(command: str) -> str:
    if "openrouter/" in command:
        return "openrouter"
    if "API_BASE=" in command or "# via" in command:
        return "proxy"
    return "unknown"


def load_source(source_dir: Path = SOURCE_DIR) -> tuple[dict, list[dict]]:
    """Return (provenance, rows). Verifies the snapshot's sha256 against SOURCE.json."""
    meta = json.loads((source_dir / "SOURCE.json").read_text(encoding="utf-8"))
    raw = (source_dir / meta["file"]).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != meta["sha256"]:
        raise ValueError(f"snapshot sha256 mismatch: {digest} != {meta['sha256']}")
    return meta, parse_list_of_maps(raw.decode("utf-8"))


def _per_case(total: Any, n: int, as_int: bool = False) -> int | float | None:
    if not isinstance(total, (int, float)) or isinstance(total, bool) or total <= 0:
        return None
    return int(total // n) if as_int else round(total / n, 6)


def row_to_records(row: dict, source_id: str) -> Iterator[dict]:
    n = int(row["test_cases"])
    p1, p2 = int(row["pass_num_1"]), int(row["pass_num_2"])
    if not 0 <= p1 <= p2 <= n:
        raise ValueError(f"inconsistent pass counts in {row.get('dirname')}: {p1}, {p2}, {n}")
    display = str(row["model"])
    command = str(row.get("command", ""))
    effort = row.get("reasoning_effort")
    effort = effort if isinstance(effort, str) and re.fullmatch(r"[a-z]{1,16}", effort) else None
    version = str(row.get("versions", ""))
    version = version if re.fullmatch(r"[0-9A-Za-z.+-]{1,32}", version) else None
    seconds = row.get("seconds_per_case")
    latency = round(float(seconds) * 1000) if isinstance(seconds, (int, float)) and seconds > 0 else None
    tokens_in = _per_case(row.get("prompt_tokens"), n, as_int=True)
    tokens_out = _per_case(row.get("completion_tokens"), n, as_int=True)
    outcomes = [(True, 1)] * p1 + [(True, 2)] * (p2 - p1) + [(False, 2)] * (n - p2)

    for i, (passed, runs) in enumerate(outcomes):
        yield {
            "schema_version": "0.2.0",
            "record_id": str(uuid.uuid5(SEED_NAMESPACE, f"{source_id}/{row['dirname']}/{i}")),
            "submitted_at": f"{row['date']}T00:00:00Z",
            "source": {
                "source_type": "benchmark",
                "client": "aider",
                "client_version": version,
                "collector": "seed-import",
                "submit_mode": "all_runs",
                "install_key_sig": None,
            },
            "task": {
                "l1": L1,
                "l2": L2,
                "taxonomy_version": "t0.1",
                "classifier": CLASSIFIER,
                "interaction_type": "multi_turn",
                "difficulty_prior": {"files_touched": None, "context_tokens": None},
            },
            "model": {
                "provider": guess_provider(display),
                "id": slug(display, 128),
                "route": guess_route(command),
                "effort": effort,
            },
            "method": {
                "harness": f"aider-{slug(str(row['edit_format']))}",
                "workflow_tags": ["benchmark.aider-polyglot"],
                "tools_used": [],
            },
            "usage": {
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "cache_read_tokens": None,
                "cache_write_tokens": None,
                "cost_usd_client": _per_case(row.get("total_cost"), n),
                "cost_usd_server": None,
                "latency_ms": latency,
                "turns": None,
            },
            "outcome": {
                "status": "completed",
                "evidence": {
                    "test_cmd_detected": True,
                    "test_runs": runs,
                    "tests_passed": passed,
                    "committed": None,
                    "tool_error_count": None,
                    "reverted_within_7d": None,
                    "user_retry_next_prompt": None,
                    "retry_detector": None,
                },
                "self_assessment": None,
            },
            "pairing": {"pair_id": None},
            "privacy": {"content_included": False, "identifiers_included": False},
        }


def build(source_dir: Path = SOURCE_DIR) -> tuple[dict, list[dict], list[dict]]:
    """Return (provenance, row_index, records).

    ``row_index`` maps each leaderboard row to the derived model id / harness so
    the original display names stay traceable without widening the record schema.
    """
    meta, rows = load_source(source_dir)
    records: list[dict] = []
    index: list[dict] = []
    for row in rows:
        recs = list(row_to_records(row, meta["source_id"]))
        records.extend(recs)
        index.append({
            "dirname": row["dirname"],
            "display_name": row["model"],
            "model_id": recs[0]["model"]["id"],
            "harness": recs[0]["method"]["harness"],
            "date": row["date"],
            "test_cases": row["test_cases"],
            "pass_rate_2": row["pass_rate_2"],
        })
    return meta, index, records
