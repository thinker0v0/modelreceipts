"""Claude Code ``Stop`` hook entry point — DRY RUN ONLY.

Reads the hook payload (JSON) from stdin, parses ``transcript_path``, builds a
record, validates it and shows a local preview. This module performs no
network I/O and never imports ``submit`` (the separate, opt-in send command).

Hook safety: in ``--hook`` mode the command always exits 0 and never writes
hook-control JSON to stdout, so it cannot block or alter the agent's session.

Next-prompt retry signal: with ``--preview-dir``, the hook remembers (in
``<preview-dir>/.state/``, keyed by a hash of the transcript path) which preview
belongs to the latest turn. When the NEXT turn of the same session ends, the
new prompt is checked locally with ``retry-rules-v1`` and the previous preview's
``user_retry_next_prompt`` / ``retry_detector`` are filled in. Only the boolean
is written; no text is stored. Submit a preview after the next turn has ended
(or accept ``null`` for the last turn of a session).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from . import RETRY_DETECTOR_ID
from .record import build_record
from .signals import detect_retry
from .transcript import TurnSummary, summarize_file
from .validate import load_validator

BANNER = "[modelreceipts] DRY RUN — preview only, nothing was sent anywhere."


def build(payload: dict, env: dict | None = None) -> tuple[dict, list[str], TurnSummary]:
    """Return (record, validation_errors, summary) for a Stop-hook payload."""
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not Path(transcript_path).is_file():
        raise ValueError("payload.transcript_path is missing or not a readable file")
    summary = summarize_file(transcript_path)
    record = build_record(payload, summary, env=env if env is not None else dict(os.environ))
    return record, load_validator().errors(record), summary


def run(payload: dict, env: dict | None = None) -> tuple[dict, list[str]]:
    """Return (record, validation_errors) for a Stop-hook payload."""
    record, errors, _summary = build(payload, env)
    return record, errors


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _state_path(preview_dir: Path, transcript_path: str) -> Path:
    key = hashlib.sha256(transcript_path.encode("utf-8")).hexdigest()[:32]
    return preview_dir / ".state" / f"{key}.json"


def backfill_previous(preview_dir: Path, transcript_path: str, summary: TurnSummary) -> str | None:
    """Fill the previous turn's next-prompt retry signal. Returns its record id if updated."""
    state_file = _state_path(preview_dir, transcript_path)
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        prev_id, prev_count = str(state["record_id"]), int(state["prompt_count"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    # Only the turn IMMEDIATELY before this prompt; a re-fired Stop for the same turn is ignored.
    if prev_count != summary.prior_prompts or "/" in prev_id or prev_id.startswith("."):
        return None
    target = preview_dir / f"{prev_id}.json"
    try:
        prev = json.loads(target.read_text(encoding="utf-8"))
        evidence = prev["outcome"]["evidence"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if prev.get("schema_version") != "0.2.0" or evidence.get("user_retry_next_prompt") is not None:
        return None
    evidence["user_retry_next_prompt"] = detect_retry(summary.prompt_text, summary.previous_prompt_text)
    evidence["retry_detector"] = RETRY_DETECTOR_ID
    if load_validator().errors(prev):
        return None
    _write_atomic(target, json.dumps(prev, ensure_ascii=False, indent=2) + "\n")
    return prev_id


def remember_turn(preview_dir: Path, transcript_path: str, record: dict, summary: TurnSummary) -> None:
    state_file = _state_path(preview_dir, transcript_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(state_file, json.dumps({"record_id": record["record_id"],
                                          "prompt_count": summary.prior_prompts + 1}) + "\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="modelreceipts hook",
        description="Build a ModelReceipts record from a Claude Code Stop-hook payload (dry run).",
    )
    parser.add_argument("--payload", type=Path, help="read the payload from a file instead of stdin")
    parser.add_argument(
        "--preview-dir", type=Path,
        help="write <record_id>.json into this directory instead of printing to stdout",
    )
    parser.add_argument(
        "--hook", action="store_true",
        help="running inside Claude Code: always exit 0, keep stdout empty, report problems on stderr",
    )
    args = parser.parse_args(argv)

    try:
        raw = args.payload.read_text(encoding="utf-8") if args.payload else sys.stdin.read()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")
        record, errors, summary = build(payload)
    except (OSError, ValueError) as exc:
        print(f"[modelreceipts] skipped: {exc}", file=sys.stderr)
        return 0 if args.hook else 2

    if errors:
        print("[modelreceipts] record failed schema validation:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)

    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = payload["transcript_path"]
        updated = backfill_previous(args.preview_dir, transcript_path, summary)
        out = args.preview_dir / f"{record['record_id']}.json"
        out.write_text(text + "\n", encoding="utf-8")
        remember_turn(args.preview_dir, transcript_path, record, summary)
        print(f"{BANNER} Wrote {out}", file=sys.stderr)
        if updated:
            print(f"[modelreceipts] filled next-prompt retry signal in {updated}.json", file=sys.stderr)
    elif args.hook:
        # stdout of a Stop hook may be parsed by Claude Code as hook-control JSON.
        print(BANNER, file=sys.stderr)
        print(text, file=sys.stderr)
    else:
        print(BANNER, file=sys.stderr)
        print(text)

    if args.hook:
        return 0
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
