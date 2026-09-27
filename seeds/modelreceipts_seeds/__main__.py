"""``PYTHONPATH=seeds python3 -m modelreceipts_seeds aider-polyglot [--out FILE.jsonl]``

Builds seed records from the pinned snapshot, validates every one against
schema v0.1 and prints a summary. ``--out`` writes one record per line.
Loading into a server database: ``python3 -m modelreceipts_server import-seed aider-polyglot``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import aider_polyglot


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts_seeds")
    parser.add_argument("source", choices=["aider-polyglot"])
    parser.add_argument("--out", type=Path, help="write records as JSON Lines")
    args = parser.parse_args(argv)

    from modelreceipts.validate import load_validator

    meta, index, records = aider_polyglot.build()
    validator = load_validator()
    bad = sum(1 for r in records if validator.errors(r))
    print(f"source      {meta['source_id']}  ({meta['license']})")
    print(f"url         {meta['url']}")
    print(f"commit      {meta['commit']}  {meta['commit_date']}")
    print(f"rows        {len(index)}")
    print(f"records     {len(records)}  (schema-invalid: {bad})")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        print(f"wrote       {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
