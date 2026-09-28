"""``PYTHONPATH=seeds python3 -m modelreceipts_seeds <source> [options]``

sources:
  aider-polyglot   per-exercise benchmark records from the pinned leaderboard snapshot
  arena-55k        aggregate preference cells (committed counts); --rebuild-from train.csv regenerates them
  openrouter       aggregate usage cells from the SYNTHETIC fixture, or --input EXPORT.json (operator-supplied)

Every output is validated against the v0.2 schemas. ``--out`` writes JSON Lines.
Loading into a server database: ``python3 -m modelreceipts_server import-seed <source>``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts_seeds", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", choices=["aider-polyglot", "arena-55k", "openrouter"])
    parser.add_argument("--out", type=Path, help="write records / cells as JSON Lines")
    parser.add_argument("--rebuild-from", type=Path, help="arena-55k: raw train.csv to rebuild cells.jsonl from")
    parser.add_argument("--input", type=Path, help="openrouter: an export you obtained (see seeds/README.md)")
    args = parser.parse_args(argv)

    from modelreceipts.validate import load_validator

    validator = load_validator(allow_seed_cells=True)
    if args.source == "aider-polyglot":
        from . import aider_polyglot
        meta, index, docs = aider_polyglot.build()
        print(f"rows        {len(index)}")
    elif args.source == "arena-55k":
        from . import arena
        if args.rebuild_from:
            cells = arena.rebuild_from_csv(args.rebuild_from)
            digest = arena.write_cells(cells)
            print(f"rebuilt     {len(cells)} cells -> seeds/data/arena-55k/cells.jsonl sha256={digest}")
            print("            update cells_sha256 in SOURCE.json if it changed")
            return 0
        meta, docs = arena.build()
    else:
        from . import openrouter
        meta, docs = openrouter.build(args.input)
    bad = sum(1 for d in docs if validator.errors(d))
    print(f"source      {meta['source_id']}  ({meta['license']})")
    print(f"url         {meta['url']}")
    if meta.get("synthetic"):
        print("NOTE        SYNTHETIC fixture - not real data")
    print(f"documents   {len(docs)}  (schema-invalid: {bad})")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for d in docs:
                fh.write(json.dumps(d, separators=(",", ":")) + "\n")
        print(f"wrote       {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
