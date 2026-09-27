"""Claude Code ``Stop`` hook entry point — DRY RUN ONLY.

Reads the hook payload (JSON) from stdin, parses ``transcript_path``, builds a
record, validates it and shows a local preview. This module performs no
network I/O and never imports ``submit`` (the separate, opt-in send command).

Hook safety: in ``--hook`` mode the command always exits 0 and never writes
hook-control JSON to stdout, so it cannot block or alter the agent's session.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .record import build_record
from .transcript import summarize_file
from .validate import load_validator

BANNER = "[modelreceipts] DRY RUN — preview only, nothing was sent anywhere."


def run(payload: dict, env: dict | None = None) -> tuple[dict, list[str]]:
    """Return (record, validation_errors) for a Stop-hook payload."""
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not Path(transcript_path).is_file():
        raise ValueError("payload.transcript_path is missing or not a readable file")
    summary = summarize_file(transcript_path)
    record = build_record(payload, summary, env=env if env is not None else dict(os.environ))
    return record, load_validator().errors(record)


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
        record, errors = run(payload)
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
        out = args.preview_dir / f"{record['record_id']}.json"
        out.write_text(text + "\n", encoding="utf-8")
        print(f"{BANNER} Wrote {out}", file=sys.stderr)
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
