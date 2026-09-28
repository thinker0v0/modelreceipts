"""Arena / OpenRouter seed-cell importers and the Aider v0.2 nulls. Run from repo root:

    python3 -m unittest discover -s seeds/tests
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEEDS))

from modelreceipts_seeds import aider_polyglot, arena, openrouter  # noqa: E402


def _csv(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["id", "model_a", "model_b", "prompt", "response_a", "response_b",
                                        "winner_model_a", "winner_model_b", "winner_tie"])
    w.writeheader()
    for i, (a, b, prompt, result) in enumerate(rows):
        w.writerow({"id": i, "model_a": a, "model_b": b, "prompt": json.dumps([prompt]),
                    "response_a": json.dumps(["SECRET-RESPONSE-A"]), "response_b": json.dumps(["SECRET-RESPONSE-B"]),
                    "winner_model_a": int(result == "a"), "winner_model_b": int(result == "b"),
                    "winner_tie": int(result == "tie")})
    return buf.getvalue()


# SYNTHETIC battles (made-up prompts; not from the dataset)
BATTLES = [
    ("model-x", "model-y", "Fix the TypeError in utils.py when parsing dates", "a"),
    ("model-x", "model-y", "Fix the KeyError in parser.py on empty input", "b"),
    ("model-y", "model-z", "Write a haiku about autumn", "tie"),
    ("model-x", "model-z", "Write a haiku about winter", "a"),
    ("model-x", "model-x", "self battle is skipped", "a"),
]


class ArenaAggregateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        text = _csv(BATTLES)
        (self.tmp / "train.csv").write_text(text, encoding="utf-8")
        meta = {"source_id": "arena-test@synthetic", "raw_sha256": hashlib.sha256(text.encode()).hexdigest()}
        (self.tmp / "SOURCE.json").write_text(json.dumps(meta), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_counts_rollups_and_no_text(self):
        cells = arena.rebuild_from_csv(self.tmp / "train.csv", self.tmp)
        by = {(c["task"]["l1"], c["task"]["l2"], c["model"]["id"]): c["metrics"] for c in cells}
        allx = by[(None, None, "model-x")]
        self.assertEqual((allx["battles"], allx["wins"], allx["losses"], allx["ties"]), (3, 2, 1, 0))
        self.assertEqual(allx["win_rate"], round(2 / 3, 4))
        self.assertEqual(by[(None, None, "model-z")]["ties"], 1)
        coding = {k: v for k, v in by.items() if k[0] == "coding" and k[1] is None}
        self.assertEqual(coding[("coding", None, "model-x")]["battles"], 2)
        # every L2 cell is also counted in its L1 rollup and in the all-task rollup
        total_all = sum(v["battles"] for k, v in by.items() if k[0] is None)
        total_l1 = sum(v["battles"] for k, v in by.items() if k[0] is not None and k[1] is None)
        self.assertEqual(total_all, total_l1)
        self.assertEqual(total_all, 2 * 4)  # 4 valid battles, two models each
        blob = json.dumps(cells)
        for leaked in ("SECRET", "haiku", "TypeError", "utils.py"):
            self.assertNotIn(leaked, blob)

    def test_raw_sha_mismatch_is_refused(self):
        with open(self.tmp / "train.csv", "a", encoding="utf-8") as fh:
            fh.write("tampered\n")
        with self.assertRaisesRegex(ValueError, "sha256"):
            arena.rebuild_from_csv(self.tmp / "train.csv", self.tmp)

    def test_malformed_labels_are_skipped(self):
        rows = [{"model_a": "a", "model_b": "b", "prompt": "[\"x\"]", "winner_model_a": "1", "winner_model_b": "1",
                 "winner_tie": "0"}]
        self.assertEqual(dict(arena.aggregate_battles(rows)), {})


class ArenaCommittedCellsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta, cls.cells = arena.build()

    def test_provenance(self):
        m = self.meta
        self.assertEqual((m["license"], m["source_type"], m["raw_redistributed"]), ("Apache-2.0", "preference", False))
        self.assertRegex(m["revision"], r"^[0-9a-f]{40}$")
        self.assertIn(m["revision"], m["url"])
        self.assertIn(m["revision"], m["fetch_command"])
        self.assertRegex(m["raw_sha256"], r"^[0-9a-f]{64}$")

    def test_cells_are_valid_counts_only(self):
        from modelreceipts.validate import AutoValidator
        v = AutoValidator(allow_seed_cells=True)
        for c in self.cells[::25] + self.cells[-3:]:
            self.assertEqual(v.errors(c), [], c["cell_id"])
        for c in self.cells:
            m = c["metrics"]
            self.assertEqual(m["wins"] + m["losses"] + m["ties"], m["battles"])
            self.assertEqual(set(c), {"schema_version", "kind", "cell_id", "source", "task", "model", "method",
                                      "period", "metrics", "privacy"})
        self.assertEqual(len({c["cell_id"] for c in self.cells}), len(self.cells))
        total = sum(c["metrics"]["battles"] for c in self.cells if c["task"]["l1"] is None)
        self.assertEqual(total % 2, 0)  # two models per battle

    def test_tampered_cells_are_refused(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(arena.SOURCE_DIR / "SOURCE.json", tmp / "SOURCE.json")
            text = (arena.SOURCE_DIR / "cells.jsonl").read_text(encoding="utf-8")
            (tmp / "cells.jsonl").write_text(text.replace('"wins":', '"wins": ', 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sha256"):
                arena.build(tmp)
        finally:
            shutil.rmtree(tmp)


class OpenRouterTest(unittest.TestCase):
    def test_fixture_is_synthetic_and_shares_add_up(self):
        meta, cells = openrouter.build()
        self.assertTrue(meta["synthetic"])
        self.assertEqual([c["metrics"]["rank"] for c in cells], list(range(1, len(cells) + 1)))
        a = cells[0]
        self.assertEqual((a["model"]["provider"], a["model"]["id"]), ("example-vendor", "example-vendor/example-model-a"))
        self.assertEqual(a["metrics"]["tokens"], 1_000_000_000)  # two rows summed
        total = 1_000_000_000 + 640_000_000 + 410_000_000 + 205_000_000 + 120_000_000 + 300_000_000
        self.assertAlmostEqual(a["metrics"]["share"], round(1e9 / total, 6))
        self.assertLess(sum(c["metrics"]["share"] for c in cells), 1.0)  # "other" keeps its share, no cell
        self.assertNotIn("other", [c["model"]["id"] for c in cells])

    def test_operator_export_gets_content_addressed_id(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            p = tmp / "export.json"
            p.write_text(json.dumps({"period": None, "rows": [{"model": "v/m", "tokens": 5}]}), encoding="utf-8")
            meta, cells = openrouter.build(p)
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(meta["source_id"], f"openrouter-usage@{digest[:12]}")
            self.assertFalse(meta["synthetic"])
            self.assertEqual(cells[0]["metrics"], {"kind": "usage", "tokens": 5, "share": 1.0, "rank": 1})
        finally:
            shutil.rmtree(tmp)

    def test_bad_exports_fail_loudly(self):
        for export in ({"rows": [{"model": "a", "tokens": -1}]}, {"rows": [{"model": "a", "tokens": True}]},
                       {"rows": [{"model": "other", "tokens": 0}]},
                       {"period": {"start": "2026-9-1", "end": "x"}, "rows": [{"model": "a", "tokens": 1}]}):
            with self.subTest(export=export), self.assertRaises(ValueError):
                openrouter.cells_from_export(export, "t")


class AiderV02Test(unittest.TestCase):
    def test_unknown_fields_are_null_not_placeholders(self):
        _, _, records = aider_polyglot.build()
        r = records[0]
        self.assertEqual(r["schema_version"], "0.2.0")
        ev = r["outcome"]["evidence"]
        self.assertIsNone(ev["committed"])
        self.assertIsNone(ev["tool_error_count"])
        self.assertIsNone(ev["retry_detector"])
        self.assertIsNone(r["usage"]["turns"])


class CliTest(unittest.TestCase):
    def test_openrouter_cli_writes_valid_jsonl(self):
        from modelreceipts_seeds.__main__ import main
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / "cells.jsonl"
            self.assertEqual(main(["openrouter", "--out", str(out)]), 0)
            lines = out.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 5)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
