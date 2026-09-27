"""Build a schema v0.1 record from a Stop-hook payload and a turn summary.

Whitelist design: the record is constructed field by field from derived
values. Nothing from the payload (session id, cwd, paths, messages) is copied.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from . import CLASSIFIER_ID, SCHEMA_VERSION, TAXONOMY_VERSION
from .classify import classify
from .transcript import SUBAGENT_TOOLS, TurnSummary

_EFFORT_RE = re.compile(r"^[a-z]{1,16}$")
_VERSION_RE = re.compile(r"^[0-9A-Za-z.+-]{1,32}$")


def detect_route(env: Mapping[str, str]) -> str:
    """Infer the serving path from environment variable NAMES/flags only."""
    if env.get("CLAUDE_CODE_USE_BEDROCK") in {"1", "true"}:
        return "bedrock"
    if env.get("CLAUDE_CODE_USE_VERTEX") in {"1", "true"}:
        return "vertex"
    base = env.get("ANTHROPIC_BASE_URL", "")
    if "openrouter" in base:
        return "openrouter"
    if base:
        return "proxy"
    return "direct"


def _clean_model_id(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._:/@-]", "", raw).lstrip("._:/@-")[:128]
    return cleaned or "unknown"


def _provider(model_id: str) -> str:
    if model_id.startswith("claude"):
        return "anthropic"
    return "unknown"


def _workflow_tags(summary: TurnSummary, payload: Mapping[str, Any]) -> list[str]:
    tools = {c.name for c in summary.tool_calls}
    tags = set()
    if payload.get("permission_mode") == "plan" or "ExitPlanMode" in tools:
        tags.add("plan-mode")
    if tools & SUBAGENT_TOOLS:
        tags.add("subagents")
    if "Skill" in tools:
        tags.add("skills")
    if any(t.startswith("mcp__") for t in tools):
        tags.add("mcp")
    if tools & {"WebSearch", "WebFetch"}:
        tags.add("web")
    return sorted(tags)


def _status(summary: TurnSummary) -> str:
    if summary.interrupted:
        return "aborted"
    if summary.api_error and summary.api_calls == 0:
        return "error"
    return "completed"


def build_record(
    payload: Mapping[str, Any],
    summary: TurnSummary,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    record_id: str | None = None,
) -> dict:
    env = env or {}
    now = now or datetime.now(timezone.utc)
    l1, l2 = classify(summary)

    ranked = list(dict.fromkeys(_clean_model_id(m) for m, _ in summary.models.most_common()))
    model_id = ranked[0] if ranked else "unknown"
    effort = payload.get("effort") if isinstance(payload.get("effort"), str) else summary.effort
    effort = effort if isinstance(effort, str) and _EFFORT_RE.match(effort) else None
    version = summary.client_version if summary.client_version and _VERSION_RE.match(summary.client_version) else None

    if summary.tool_calls:
        interaction = "agentic"
    elif summary.prior_prompts:
        interaction = "multi_turn"
    else:
        interaction = "single_turn"

    model: dict[str, Any] = {
        "provider": _provider(model_id),
        "id": model_id,
        "route": detect_route(env),
        "effort": effort,
    }
    if len(ranked) > 1:
        model["other_ids"] = ranked[1:9]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id or str(uuid.uuid4()),
        "submitted_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "source_type": "field_report",
            "client": "claude-code",
            "client_version": version,
            "collector": "stop-hook",
            "submit_mode": "all_runs",
            "install_key_sig": None,
        },
        "task": {
            "l1": l1,
            "l2": l2,
            "taxonomy_version": TAXONOMY_VERSION,
            "classifier": CLASSIFIER_ID,
            "interaction_type": interaction,
            "difficulty_prior": {
                "files_touched": summary.files_touched,
                "context_tokens": summary.context_tokens,
            },
        },
        "model": model,
        "method": {
            "harness": "claude-code",
            "workflow_tags": _workflow_tags(summary, payload),
            "tools_used": summary.tools_used[:64],
        },
        "usage": {
            "input_tokens": summary.input_tokens,
            "output_tokens": summary.output_tokens,
            "cache_read_tokens": summary.cache_read_tokens,
            "cache_write_tokens": summary.cache_write_tokens,
            "cost_usd_client": None,  # not present in transcripts; OTel enrichment is a later step
            "cost_usd_server": None,  # recomputed server-side from a price table (not in v0.1)
            "latency_ms": summary.latency_ms,
            "turns": summary.api_calls,
        },
        "outcome": {
            "status": _status(summary),
            "evidence": {
                "test_cmd_detected": bool(summary.test_calls),
                "test_runs": len(summary.test_calls),
                "tests_passed": summary.tests_passed,
                "committed": summary.committed,
                "tool_error_count": summary.tool_error_count,
                "reverted_within_7d": None,
                "user_retry_next_prompt": None,
            },
            # The collector never asks a model to grade itself.
            "self_assessment": None,
        },
        "pairing": {"pair_id": None},
        "privacy": {"content_included": False, "identifiers_included": False},
    }
