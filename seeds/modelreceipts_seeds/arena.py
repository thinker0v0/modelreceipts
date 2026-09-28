"""LMArena ``arena-human-preference-55k`` -> aggregate PREFERENCE seed cells.

Source (pinned, see ``data/arena-55k/SOURCE.json``): Hugging Face dataset
``lmarena-ai/arena-human-preference-55k`` at revision 18c2983, license
Apache-2.0 (dataset card). 57,477 battles between 64 models, collected for the
2024 Kaggle "LMSYS - Chatbot Arena Human Preference Predictions" competition.

What is stored in this repository: ONLY counts. For every battle the prompt is
classified locally with the collector's ``rules-v1`` classifier (in memory);
the cell ``(L1, L2, model)`` then gets +1 battle and a win / loss / tie. No
prompt, response or battle id is written anywhere. The raw CSV (184 MB,
contains model outputs) is NOT redistributed; the maintainer rebuilds the cells
with ``--rebuild-from train.csv`` after downloading it (command in SOURCE.json).

Caveats (also on the dashboard):

* Preference is not outcome evidence. These cells are a separate layer and are
  never pooled with field reports or ranked with them.
* The models are from 2023-2024 and the battle dates are not in the file.
* ``rules-v1`` was built for agent turns with tool activity; on chat prompts it
  sees text only. Treat the L1/L2 split as approximate.
* Both "tie" and "tie (both bad)" count as ties (the file does not distinguish).
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from . import DATA_DIR
from .aider_polyglot import guess_provider, slug

SOURCE_DIR = DATA_DIR / "arena-55k"
CELL_NAMESPACE = uuid.UUID("2b7e6a90-51c4-5f0e-8d2a-7f3e9c1b4a55")
EXTRA_PROVIDERS = [("vicuna|fastchat", "lmsys"), ("mixtral|mistral", "mistral"), ("palm|bard|gemini", "google"),
                   ("wizardlm", "microsoft"), ("zephyr", "huggingface"), ("openchat", "openchat"),
                   ("koala", "berkeley"), ("alpaca", "stanford"), ("chatglm", "zhipu"), ("pplx", "perplexity"),
                   ("stripedhyena", "together"), ("dolly", "databricks"), ("dbrx", "databricks"),
                   ("mpt", "mosaicml"), ("falcon", "tii"), ("solar", "upstage"), ("nous|hermes", "nousresearch"),
                   ("tulu", "allenai"), ("openhermes", "nousresearch"), ("starling", "nexusflow"),
                   ("guanaco", "timdettmers"), ("oasst", "openassistant"), ("stablelm", "stabilityai"),
                   ("rwkv", "rwkv"), ("codellama", "meta"), ("phi-", "microsoft")]


def provider_for(model: str) -> str:
    import re
    p = guess_provider(model)
    if p != "unknown":
        return p
    for pattern, name in EXTRA_PROVIDERS:
        if re.search(pattern, model.lower()):
            return name
    return "unknown"


def _classify(prompt_field: str) -> tuple[str, str | None]:
    """Classify a battle's prompt(s) locally. The text never leaves this function."""
    from modelreceipts.classify import classify
    from modelreceipts.transcript import TurnSummary

    try:
        turns = json.loads(prompt_field)
        text = "\n".join(t for t in turns if isinstance(t, str)) if isinstance(turns, list) else str(turns)
    except (json.JSONDecodeError, TypeError):
        text = prompt_field or ""
    return classify(TurnSummary(prompt_text=text[:4000]), classifier="rules-v1")


def aggregate_battles(rows: Iterable[dict]) -> dict[tuple, dict]:
    """rows: dicts with model_a, model_b, prompt, winner_model_a, winner_model_b, winner_tie."""
    counts: dict[tuple, dict] = defaultdict(lambda: {"battles": 0, "wins": 0, "losses": 0, "ties": 0})
    for row in rows:
        a, b = row["model_a"], row["model_b"]
        wa, wb, tie = row["winner_model_a"] == "1", row["winner_model_b"] == "1", row["winner_tie"] == "1"
        if a == b or wa + wb + tie != 1:
            continue  # self-battles and malformed labels are skipped
        l1, l2 = _classify(row["prompt"])
        for task in ((l1, l2), (l1, None), (None, None)) if l2 else ((l1, None), (None, None)):
            for model, won, lost in ((a, wa, wb), (b, wb, wa)):
                c = counts[(task[0], task[1], model)]
                c["battles"] += 1
                c["wins"] += int(won)
                c["losses"] += int(lost)
                c["ties"] += int(tie)
    return counts


def cells_from_counts(counts: dict[tuple, dict], source_id: str) -> list[dict]:
    cells = []
    for (l1, l2, model) in sorted(counts, key=lambda k: (k[0] or "", k[1] or "", k[2])):
        c = counts[(l1, l2, model)]
        cells.append({
            "schema_version": "0.2.0",
            "kind": "seed_cell",
            "cell_id": str(uuid.uuid5(CELL_NAMESPACE, f"{source_id}/{l1}/{l2}/{model}")),
            "source": {"source_type": "preference", "source_id": source_id},
            "task": {"l1": l1, "l2": l2, "taxonomy_version": "t0.1", "classifier": "rules-v1" if l1 else None},
            "model": {"provider": provider_for(model), "id": slug(model, 128)},
            "method": {"harness": None},
            "period": None,
            "metrics": {"kind": "preference", "battles": c["battles"], "wins": c["wins"], "losses": c["losses"],
                        "ties": c["ties"], "win_rate": round((c["wins"] + c["ties"] / 2) / c["battles"], 4)},
            "privacy": {"content_included": False, "identifiers_included": False},
        })
    return cells


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rebuild_from_csv(csv_path: Path, source_dir: Path = SOURCE_DIR, check_sha: bool = True) -> list[dict]:
    meta = json.loads((source_dir / "SOURCE.json").read_text(encoding="utf-8"))
    if check_sha:
        digest = _sha256(csv_path)
        if digest != meta["raw_sha256"]:
            raise ValueError(f"raw CSV sha256 mismatch: {digest} != {meta['raw_sha256']}")
    csv.field_size_limit(sys.maxsize)
    with open(csv_path, encoding="utf-8", newline="") as fh:
        counts = aggregate_battles(csv.DictReader(fh))
    return cells_from_counts(counts, meta["source_id"])


def write_cells(cells: list[dict], source_dir: Path = SOURCE_DIR) -> str:
    text = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for c in cells)
    (source_dir / "cells.jsonl").write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(source_dir: Path = SOURCE_DIR) -> tuple[dict, list[dict]]:
    """Load the committed aggregate cells; verify their sha256 against SOURCE.json."""
    meta = json.loads((source_dir / "SOURCE.json").read_text(encoding="utf-8"))
    raw = (source_dir / "cells.jsonl").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != meta["cells_sha256"]:
        raise ValueError(f"cells.jsonl sha256 mismatch: {digest} != {meta['cells_sha256']}")
    cells = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return meta, cells
