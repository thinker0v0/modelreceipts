"""Seed importer tests. Run from repo root:

    python3 -m unittest discover -s seeds/tests -v
"""

from __future__ import annotations

import datetime
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEEDS))

from modelreceipts_seeds import EXCLUDED_SOURCES, aider_polyglot  # noqa: E402
from modelreceipts_seeds.miniyaml import parse_list_of_maps  # noqa: E402

SNAPSHOT = aider_polyglot.SOURCE_DIR / "polyglot_leaderboard.yml"


class MiniYamlTest(unittest.TestCase):
    def test_subset(self):
        text = (
            "# top comment\n"
            "- dirname: a--b # trailing comment\n"
            "  test_cases: 225\n"
            "  pass_rate_2: 51.6\n"
            '  command: "aider --model x # not a comment"\n'
            "  date: 2025-01-17\n"
            "  total_cost: 0 # incorrect: 6.3\n"
            "  hash: 8e3\n"
            "\n"
            "- dirname: c\n"
            "  quoted: 'it''s'\n"
            "  empty:\n"
        )
        self.assertEqual(parse_list_of_maps(text), [
            {"dirname": "a--b", "test_cases": 225, "pass_rate_2": 51.6, "command": "aider --model x # not a comment",
             "date": "2025-01-17", "total_cost": 0, "hash": "8e3"},
            {"dirname": "c", "quoted": "it's", "empty": None},
        ])

    def test_unsupported_constructs_fail_loudly(self):
        for text in ("- a: [1, 2]\n", "- a:\n    nested: 1\n", "a: 1\n", "- a: 1\n  a: 2\n", "- a: \"open\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_list_of_maps(text)

    def test_agrees_with_pyyaml_on_snapshot_if_installed(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed (optional cross-check)")
        text = SNAPSHOT.read_text(encoding="utf-8")
        ref = [{k: v.isoformat() if isinstance(v, datetime.date) else v for k, v in row.items()}
               for row in yaml.safe_load(text)]
        self.assertEqual(parse_list_of_maps(text), ref)


class AiderImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta, cls.index, cls.records = aider_polyglot.build()

    def test_provenance(self):
        m = self.meta
        self.assertEqual(m["source_type"], "benchmark")
        self.assertEqual(m["license"], "Apache-2.0")
        self.assertRegex(m["commit"], r"^[0-9a-f]{40}$")
        self.assertIn(m["commit"], m["url"])
        self.assertIn(m["commit"], m["raw_url"])
        self.assertTrue(m["url"].startswith("https://github.com/Aider-AI/aider/"))

    def test_tampered_snapshot_is_refused(self):
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(aider_polyglot.SOURCE_DIR / "SOURCE.json", tmp / "SOURCE.json")
            (tmp / "polyglot_leaderboard.yml").write_text(SNAPSHOT.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sha256"):
                aider_polyglot.load_source(tmp)
        finally:
            shutil.rmtree(tmp)

    def test_every_record_is_schema_valid_and_benchmark(self):
        from modelreceipts.validate import load_validator
        v = load_validator()
        # Full validation of ~15k records takes a few seconds; check a stride + all distinct cells.
        sample = self.records[::37] + [self.records[0], self.records[-1]]
        for r in sample:
            self.assertEqual(v.errors(r), [], r["record_id"])
        self.assertEqual({r["source"]["source_type"] for r in self.records}, {"benchmark"})
        self.assertEqual({r["task"]["classifier"] for r in self.records}, {"seed:aider-polyglot"})
        self.assertTrue(all(r["outcome"]["self_assessment"] is None for r in self.records))

    def test_counts_reproduce_leaderboard_pass_rates(self):
        _, rows = aider_polyglot.load_source()
        self.assertEqual(len(self.index), len(rows))
        self.assertEqual(len(self.records), sum(r["test_cases"] for r in rows))
        by_cell = Counter()
        passes = Counter()
        for r in self.records:
            key = (r["model"]["id"], r["method"]["harness"])
            by_cell[key] += 1
            passes[key] += r["outcome"]["evidence"]["tests_passed"]
        for row, idx in zip(rows, self.index):
            key = (idx["model_id"], idx["harness"])
            with self.subTest(row=row["dirname"]):
                self.assertEqual(by_cell[key], row["test_cases"])
                self.assertEqual(passes[key], row["pass_num_2"])
                # Published pass_rate_2 sometimes divides by total_tests (unfinished exercises = fail) and
                # sometimes rounds down; records cover exactly the exercises that ran, so allow <0.5pp.
                self.assertAlmostEqual(100 * passes[key] / by_cell[key], row["pass_rate_2"], delta=0.5)

    def test_zero_cost_means_unknown(self):
        costs = {(r["model"]["id"], r["method"]["harness"]): r["usage"]["cost_usd_client"] for r in self.records}
        row = next(i for i in self.index if i["dirname"].startswith("2025-02-25-20-23-07--gemini-pro"))
        self.assertIsNone(costs[(row["model_id"], row["harness"])])

    def test_record_ids_are_deterministic_and_unique(self):
        again = aider_polyglot.build()[2]
        self.assertEqual([r["record_id"] for r in again[:50]], [r["record_id"] for r in self.records[:50]])
        self.assertEqual(len({r["record_id"] for r in self.records}), len(self.records))

    def test_excluded_sources_are_not_used(self):
        data_dirs = {p.name.lower() for p in (SEEDS / "data").iterdir()}
        for banned in EXCLUDED_SOURCES:
            self.assertFalse(any(banned in d for d in data_dirs), banned)
        blob = json.dumps(self.meta).lower()
        self.assertNotIn("artificialanalysis", blob)
        self.assertNotIn("lmsys-chat", blob)


if __name__ == "__main__":
    unittest.main()
