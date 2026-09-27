"""Parse a Claude Code transcript JSONL and summarise the LAST turn.

A "turn" is everything after the last real user prompt; the ``Stop`` hook fires
when that turn ends. Raw text (prompt, tool arguments, outputs) is only held in
memory for local classification and is never copied into the summary fields
that end up in a record, except the prompt text, which ``record.py`` hands to
the local classifier and then drops.

The transcript format is not a stable public API; the parser is defensive and
skips anything it does not recognise.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SUBAGENT_TOOLS = {"Agent", "Task"}

# Test runners commonly invoked from Bash. Matched against the command string locally.
TEST_CMD_RE = re.compile(
    r"(?:^|[\s;&|(])(?:"
    r"pytest|py\.test|python3?\s+-m\s+(?:pytest|unittest)|tox|nox"
    r"|(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?test\b|npx\s+(?:jest|vitest)|jest|vitest|deno\s+test"
    r"|go\s+test|cargo\s+test|mvn\s+(?:-\S+\s+)*test|(?:\./)?gradlew?\s+\S*test\S*|gbuild\s+\S*test\S*"
    r"|make\s+(?:check|test)|ctest|rspec|phpunit|dotnet\s+test|swift\s+test|mix\s+test"
    r")",
    re.IGNORECASE,
)
GIT_COMMIT_RE = re.compile(r"(?:^|[\s;&|(])git(?:\s+-[cC]\s+\S+)*\s+commit\b")
INTERRUPT_MARKER = "[Request interrupted by user"


@dataclass
class ToolCall:
    name: str
    command: str | None = None  # Bash only; local use
    file_path: str | None = None  # edit tools only; local use
    is_error: bool | None = None


@dataclass
class TurnSummary:
    prompt_text: str = ""  # LOCAL ONLY: used for classification, never serialised
    prior_prompts: int = 0
    models: Counter = field(default_factory=Counter)  # model id -> output tokens
    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    context_tokens: int | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    client_version: str | None = None
    effort: str | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    interrupted: bool = False
    api_error: bool = False

    # ---- derived evidence -------------------------------------------------
    @property
    def tools_used(self) -> list[str]:
        names = set()
        for call in self.tool_calls:
            # MCP tool names can reveal private server names; collapse them.
            names.add("mcp" if call.name.startswith("mcp__") else call.name)
        return sorted(names)

    @property
    def files_touched(self) -> int:
        return len({c.file_path for c in self.tool_calls if c.name in EDIT_TOOLS and c.file_path})

    @property
    def test_calls(self) -> list[ToolCall]:
        return [c for c in self.tool_calls if c.name == "Bash" and c.command and TEST_CMD_RE.search(c.command)]

    @property
    def tests_passed(self) -> bool | None:
        runs = self.test_calls
        if not runs or runs[-1].is_error is None:
            return None
        return not runs[-1].is_error

    @property
    def committed(self) -> bool:
        return any(
            c.name == "Bash" and c.command and GIT_COMMIT_RE.search(c.command) and c.is_error is False
            for c in self.tool_calls
        )

    @property
    def tool_error_count(self) -> int:
        return sum(1 for c in self.tool_calls if c.is_error)

    @property
    def latency_ms(self) -> int | None:
        if self.duration_ms is not None:
            return self.duration_ms
        if self.started_at and self.ended_at and self.ended_at >= self.started_at:
            return int((self.ended_at - self.started_at).total_seconds() * 1000)
        return None


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _content_blocks(entry: dict) -> list:
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return []
    content = msg.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _prompt_text(entry: dict) -> str | None:
    """Return the text if this entry is a real (human) user prompt, else None."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    blocks = _content_blocks(entry)
    if not blocks or any(b.get("type") == "tool_result" for b in blocks):
        return None
    text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    if not text.strip() or text.lstrip().startswith("<local-command"):
        return None
    return text


def _read_entries(lines: Iterable[str]) -> Iterable[dict]:
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def summarize_last_turn(lines: Iterable[str]) -> TurnSummary:
    """Stream the transcript, keeping only entries of the last turn in memory."""
    turn: list[dict] = []
    prompt = ""
    prompts_seen = 0
    for entry in _read_entries(lines):
        text = _prompt_text(entry)
        if text is not None and not text.startswith(INTERRUPT_MARKER):
            prompts_seen += 1
            prompt = text
            turn = [entry]
        else:
            turn.append(entry)

    s = TurnSummary(prompt_text=prompt, prior_prompts=max(prompts_seen - 1, 0))
    per_message: dict[str, dict] = {}  # message.id -> best usage/model seen
    calls: dict[str, ToolCall] = {}
    order: list[str] = []

    for entry in turn:
        ts = _parse_ts(entry.get("timestamp"))
        if ts:
            s.started_at = s.started_at or ts
            s.ended_at = ts
        if isinstance(entry.get("version"), str):
            s.client_version = entry["version"]
        if entry.get("isSidechain"):
            continue  # subagent internals live in their own transcripts
        etype = entry.get("type")

        if etype == "system" and entry.get("subtype") == "turn_duration":
            if isinstance(entry.get("durationMs"), (int, float)):
                s.duration_ms = int(entry["durationMs"])
            continue

        if etype == "assistant":
            msg = entry.get("message") or {}
            if isinstance(entry.get("effort"), str):
                s.effort = entry["effort"]
            if entry.get("isApiErrorMessage"):
                s.api_error = True
            mid = msg.get("id") or entry.get("uuid") or f"anon-{len(per_message)}"
            usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
            prev = per_message.get(mid)
            # Streaming splits one API message into several lines that repeat usage;
            # keep the most complete copy (highest output_tokens).
            if prev is None or (usage.get("output_tokens") or 0) >= (prev["usage"].get("output_tokens") or 0):
                per_message[mid] = {"usage": usage, "model": msg.get("model")}
            for block in _content_blocks(entry):
                if block.get("type") == "tool_use" and isinstance(block.get("name"), str):
                    inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                    call = ToolCall(
                        name=block["name"],
                        command=inp.get("command") if isinstance(inp.get("command"), str) else None,
                        file_path=inp.get("file_path") or inp.get("notebook_path"),
                    )
                    tid = block.get("id") or f"anon-tool-{len(order)}"
                    calls[tid] = call
                    order.append(tid)
            continue

        if etype == "user":
            for block in _content_blocks(entry):
                if block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                    err = block.get("is_error")
                    calls[block["tool_use_id"]].is_error = err if isinstance(err, bool) else None
                if block.get("type") == "text" and str(block.get("text", "")).startswith(INTERRUPT_MARKER):
                    s.interrupted = True
            tur = entry.get("toolUseResult")
            if isinstance(tur, dict) and tur.get("interrupted") is True:
                s.interrupted = True

    first = True
    for info in per_message.values():
        model, usage = info["model"], info["usage"]
        if not model or model == "<synthetic>":
            if model == "<synthetic>":
                s.api_error = True
            continue
        s.api_calls += 1
        inp = int(usage.get("input_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        cr = int(usage.get("cache_read_input_tokens") or 0)
        cw = int(usage.get("cache_creation_input_tokens") or 0)
        s.input_tokens += inp
        s.output_tokens += out
        s.cache_read_tokens += cr
        s.cache_write_tokens += cw
        s.models[model] += out
        if first:
            s.context_tokens = inp + cr + cw
            first = False

    s.tool_calls = [calls[t] for t in order]
    return s


def summarize_file(path: str) -> TurnSummary:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return summarize_last_turn(fh)
