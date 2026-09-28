"""Classifier eval set + harness. Run from repo root: python3 -m unittest discover -s collector/tests"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

COLLECTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COLLECTOR))

from modelreceipts import DEFAULT_SCHEMA_PATH  # noqa: E402
from modelreceipts.classify import CLASSIFIERS  # noqa: E402
from modelreceipts.evaluate import evaluate, load_examples, summary_for  # noqa: E402


class EvalSetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = load_examples()
        schema = json.loads(Path(DEFAULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        cls.l1 = set(schema["$defs"]["l1"]["enum"])
        cls.l2 = set(schema["$defs"]["l2_coding"]["enum"])

    def test_well_formed_and_labels_are_closed_codes(self):
        ids = [e["id"] for e in self.examples]
        self.assertEqual(len(ids), len(set(ids)))
        for e in self.examples:
            self.assertIn(e["split"], {"dev", "test"})
            self.assertIn(e["l1"], self.l1)
            if e["l1"] == "coding":
                self.assertIn(e["l2"], self.l2)
            else:
                self.assertIsNone(e["l2"])

    def test_every_class_is_in_both_splits(self):
        for split in ("dev", "test"):
            labels = {e["l2"] or e["l1"] for e in self.examples if e["split"] == split}
            self.assertEqual(labels, self.l2 | (self.l1 - {"coding"}), split)

    def test_summary_reconstructs_activity(self):
        ex = {"prompt": "x", "files_touched": 2, "test_calls": 1, "tools": ["Read", "mcp"]}
        s = summary_for(ex)
        self.assertEqual(s.files_touched, 2)
        self.assertEqual(len(s.test_calls), 1)
        self.assertIn("mcp", s.tools_used)

    def test_metrics_are_consistent(self):
        for name in CLASSIFIERS:
            r = evaluate(self.examples, name)
            self.assertEqual(r["n"], len(self.examples))
            self.assertEqual(sum(v["support"] for v in r["per_class"].values()), r["n"])
            self.assertEqual(sum(v["predicted"] for v in r["per_class"].values()), r["n"])
            self.assertAlmostEqual(r["accuracy"], sum(v["tp"] for v in r["per_class"].values()) / r["n"])
            self.assertGreaterEqual(r["l1_accuracy"], r["accuracy"])

    def test_old_classifier_versions_stay_registered(self):
        self.assertIn("rules-v0", CLASSIFIERS)

    def test_results_file_is_up_to_date(self):
        import io
        from contextlib import redirect_stdout
        from modelreceipts.evaluate import main
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--markdown"])
        committed = (COLLECTOR / "eval" / "RESULTS.md").read_text(encoding="utf-8")
        self.assertEqual(buf.getvalue(), committed, "regenerate collector/eval/RESULTS.md")


if __name__ == "__main__":
    unittest.main()
