"""OpenRouter usage share -> aggregate USAGE seed cells.

Status: importer implemented and tested against a SYNTHETIC fixture only.
Real data is NOT fetched by this repository:

* The research notes say the rankings data is CC BY 4.0 but that the JSON
  export needs an OpenRouter API key; the exact endpoint path and field names
  were not verified against first-party documentation. Getting a key and
  confirming the terms is a human task (docs/USER_TASKS.md).
* No scraping of openrouter.ai pages, and no third-party mirrors whose
  license is unclear.

Input format this importer accepts (map the real export onto it after checking
its documentation)::

    {"period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
     "rows": [{"model": "<vendor>/<model>", "tokens": 123}, ...]}

Multiple rows for the same model (e.g. daily rows) are summed. Rows named
"other" (the long tail bucket) count toward the total but get no cell.
Output: one ``usage`` cell per model with tokens, share of all tokens and rank.
Usage is adoption, not quality: these cells are never a ranking signal.
Attribution when real data is used: "Data: OpenRouter, CC BY 4.0".
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from pathlib import Path

from . import DATA_DIR

SOURCE_DIR = DATA_DIR / "openrouter"
CELL_NAMESPACE = uuid.UUID("9d3c2b1a-6e5f-5a4b-8c7d-0e1f2a3b4c5d")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _split(model: str) -> tuple[str, str]:
    vendor, _, name = model.partition("/")
    provider = re.sub(r"[^a-z0-9._-]+", "-", vendor.lower()).strip("-._") or "unknown"
    mid = re.sub(r"[^A-Za-z0-9._:/@-]", "-", model).lstrip("._:/@-")[:128] or "unknown"
    return provider[:64], mid


def cells_from_export(export: dict, source_id: str) -> list[dict]:
    period = export.get("period")
    if period is not None and not (_DATE.match(period.get("start", "")) and _DATE.match(period.get("end", ""))):
        raise ValueError("period.start/end must be YYYY-MM-DD")
    totals: dict[str, int] = defaultdict(int)
    grand = 0
    for row in export["rows"]:
        tokens = row["tokens"]
        if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
            raise ValueError(f"bad token count for {row.get('model')!r}")
        grand += tokens
        if str(row["model"]).lower() != "other":
            totals[str(row["model"])] += tokens
    if grand == 0:
        raise ValueError("export has no tokens")
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    cells = []
    for rank, (model, tokens) in enumerate(ranked, 1):
        provider, mid = _split(model)
        cells.append({
            "schema_version": "0.2.0",
            "kind": "seed_cell",
            "cell_id": str(uuid.uuid5(CELL_NAMESPACE, f"{source_id}/{model}")),
            "source": {"source_type": "usage", "source_id": source_id},
            "task": {"l1": None, "l2": None, "taxonomy_version": "t0.1", "classifier": None},
            "model": {"provider": provider, "id": mid},
            "method": {"harness": None},
            "period": period,
            "metrics": {"kind": "usage", "tokens": tokens, "share": round(tokens / grand, 6), "rank": rank},
            "privacy": {"content_included": False, "identifiers_included": False},
        })
    return cells


def build(input_path: Path | None = None, source_dir: Path = SOURCE_DIR) -> tuple[dict, list[dict]]:
    """Default: the committed SYNTHETIC fixture (sha256-checked). ``input_path``: a real export
    the operator obtained, imported under source_id ``openrouter-usage@<sha256[:12]>``."""
    meta = json.loads((source_dir / "SOURCE.json").read_text(encoding="utf-8"))
    path = input_path or source_dir / meta["file"]
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if input_path is None:
        if digest != meta["sha256"]:
            raise ValueError(f"fixture sha256 mismatch: {digest} != {meta['sha256']}")
    else:
        meta = {**meta, "source_id": f"openrouter-usage@{digest[:12]}", "sha256": digest, "synthetic": False,
                "name": "OpenRouter usage share (operator-supplied export)",
                "license": "CC-BY-4.0",
                "license_note": "Operator-supplied export. Confirm the current OpenRouter data terms before "
                                "publishing. Attribution: 'Data: OpenRouter, CC BY 4.0'."}
    return meta, cells_from_export(json.loads(raw), meta["source_id"])
