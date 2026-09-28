"""Schema migration v0.1 -> v0.2.

``python3 -m modelreceipts migrate FILE.json|FILE.jsonl ... (--out-dir DIR | --stdout)``

What changes (see schema/README.md, "v0.1 -> v0.2"):

* ``schema_version`` 0.1.0 -> 0.2.0; ``record_id`` is kept (same run, new format).
* ``usage.cost_usd_server`` is no longer carried in the body (the server keeps its
  own recomputed value in a separate table). A non-null v0.1 value is dropped and
  reported in the notes.
* ``source.install_key_sig`` must be null (signatures travel in a header).
* ``outcome.evidence.retry_detector`` is added: ``null``, or ``"manual"`` if a
  v0.1 record already carried a non-null ``user_retry_next_prompt``.
* ``outcome.self_assessment`` gains ``extractor`` (null).
* SEED records only (``source.collector == "seed-import"``): v0.1 placeholders for
  values the source never reported become ``null`` -- ``committed=false``,
  ``tool_error_count=0``, ``turns=0`` and zero token counts. Field reports keep
  their values: for them ``false``/``0`` are real observations.

The input files are never modified.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from .validate import iter_documents, load_validator

TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


def migrate_record(record: dict) -> tuple[dict, list[str]]:
    """Return (v0.2 record, notes). v0.2 input is returned unchanged."""
    version = record.get("schema_version")
    if version == "0.2.0":
        return copy.deepcopy(record), []
    if version != "0.1.0":
        raise ValueError(f"cannot migrate schema_version {version!r}")
    r = copy.deepcopy(record)
    notes: list[str] = []
    r["schema_version"] = "0.2.0"

    src = r["source"]
    if src.get("install_key_sig") is not None:
        notes.append("dropped source.install_key_sig (signatures travel in a header in v0.2)")
    src["install_key_sig"] = None

    usage = r["usage"]
    if usage.get("cost_usd_server") is not None:
        notes.append(f"dropped usage.cost_usd_server={usage['cost_usd_server']} (server keeps its own value)")
    usage["cost_usd_server"] = None

    ev = r["outcome"]["evidence"]
    ev["retry_detector"] = "manual" if ev.get("user_retry_next_prompt") is not None else None

    sa = r["outcome"].get("self_assessment")
    if isinstance(sa, dict):
        sa.setdefault("extractor", None)

    is_seed = src.get("collector") == "seed-import" and src.get("source_type") != "field_report"
    if is_seed:
        if ev.get("committed") is False:
            ev["committed"] = None
        if ev.get("tool_error_count") == 0:
            ev["tool_error_count"] = None
        if usage.get("turns") == 0:
            usage["turns"] = None
        for k in TOKEN_FIELDS:
            if usage.get(k) == 0:
                usage[k] = None
        notes.append("seed placeholders (false/0) -> null")
    return r, notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts migrate",
                                     description="Migrate v0.1 records to schema v0.2 (inputs are not modified).")
    parser.add_argument("files", nargs="+", type=Path)
    out = parser.add_mutually_exclusive_group(required=True)
    out.add_argument("--out-dir", type=Path, help="write <name> into this directory (.jsonl stays .jsonl)")
    out.add_argument("--stdout", action="store_true", help="print migrated documents as JSON Lines")
    args = parser.parse_args(argv)

    validator = load_validator(versions=("0.2.0",))
    failed = migrated = 0
    for path in args.files:
        results = []
        for label, doc in iter_documents(path):
            try:
                new, notes = migrate_record(doc)
            except (ValueError, KeyError, TypeError) as exc:
                print(f"FAIL {label}: {exc}", file=sys.stderr)
                failed += 1
                continue
            errs = validator.errors(new)
            if errs:
                failed += 1
                print(f"FAIL {label}: migrated record is invalid: {errs[:3]}", file=sys.stderr)
                continue
            migrated += 1
            if notes:
                print(f"note {label}: {'; '.join(notes)}", file=sys.stderr)
            results.append(new)
        if args.stdout:
            for rec in results:
                print(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
        elif results:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            target = args.out_dir / path.name
            if target.resolve() == path.resolve():
                print(f"FAIL {path}: refusing to overwrite the input", file=sys.stderr)
                failed += 1
                continue
            if path.suffix == ".jsonl":
                text = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in results)
            else:
                text = json.dumps(results[0], ensure_ascii=False, indent=2) + "\n"
            target.write_text(text, encoding="utf-8")
    print(f"migrated {migrated}, failed {failed}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
