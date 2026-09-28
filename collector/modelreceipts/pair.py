"""Pair mode: mark two local preview records as the SAME task run with two models.

    python3 -m modelreceipts pair A.json B.json [--apply]

Typical flow: run one task in two worktrees (or twice) with different models,
let the preview-only hook write both records, then pair them. Both records get
the same random ``pairing.pair_id`` and ``source.collector = "pair-mode"``.
Pairs control for task difficulty, so the server reports head-to-head results
for them separately (``pairwise`` in the detailed aggregates).

Checks: both are v0.2 field reports, same L1/L2, different primary models, not
already paired. Dry run unless ``--apply``; files are rewritten atomically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from .validate import load_validator


def check_pair(a: dict, b: dict) -> list[str]:
    problems = []
    for name, r in (("A", a), ("B", b)):
        if r.get("schema_version") != "0.2.0":
            problems.append(f"{name}: needs schema 0.2.0 (run `modelreceipts migrate` first)")
            continue
        if r["source"]["source_type"] != "field_report":
            problems.append(f"{name}: only field reports can be paired")
        if r["pairing"]["pair_id"] is not None:
            problems.append(f"{name}: already paired ({r['pairing']['pair_id']})")
    if problems:
        return problems
    if (a["task"]["l1"], a["task"]["l2"]) != (b["task"]["l1"], b["task"]["l2"]):
        problems.append(f"task codes differ: {a['task']['l1']}/{a['task']['l2']} vs {b['task']['l1']}/{b['task']['l2']}")
    if a["model"]["id"] == b["model"]["id"]:
        problems.append("both records use the same primary model")
    if a["record_id"] == b["record_id"]:
        problems.append("A and B are the same record")
    return problems


def make_pair(a: dict, b: dict, pair_id: str | None = None) -> tuple[dict, dict]:
    pid = pair_id or str(uuid.uuid4())
    out = []
    for r in (a, b):
        r = json.loads(json.dumps(r))
        r["pairing"]["pair_id"] = pid
        r["source"]["collector"] = "pair-mode"
        out.append(r)
    return out[0], out[1]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts pair", description=__doc__.split("\n\n")[0])
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--apply", action="store_true", help="rewrite both files (default: dry run)")
    args = parser.parse_args(argv)
    try:
        a, b = (json.loads(p.read_text(encoding="utf-8")) for p in (args.a, args.b))
        problems = check_pair(a, b)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[modelreceipts] cannot read records: {exc}", file=sys.stderr)
        return 2
    if problems:
        for msg in problems:
            print(f"[modelreceipts] not paired: {msg}", file=sys.stderr)
        return 1
    pa, pb = make_pair(a, b)
    validator = load_validator()
    errs = validator.errors(pa) + validator.errors(pb)
    if errs:
        print(f"[modelreceipts] paired records would be invalid: {errs[:3]}", file=sys.stderr)
        return 1
    print(f"pair_id {pa['pairing']['pair_id']}: {a['model']['id']} vs {b['model']['id']} on {a['task']['l2'] or a['task']['l1']}")
    if not args.apply:
        print("[modelreceipts] DRY RUN — re-run with --apply to write both files.")
        return 0
    for path, rec in ((args.a, pa), (args.b, pb)):
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    print(f"[modelreceipts] wrote {args.a} and {args.b}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
