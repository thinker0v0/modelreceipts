"""Server tests (stdlib only). Run from repo root:

    python3 -m unittest discover -s server/tests -v
"""

from __future__ import annotations

import copy
import json
import sqlite3
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from modelreceipts_server import REPO_ROOT  # noqa: E402
from modelreceipts_server.aggregate import Thresholds, aggregate, wilson  # noqa: E402
from modelreceipts_server.app import NotLoopback, Policy, make_server  # noqa: E402
from modelreceipts_server.store import DuplicateRecord, InvalidRecord, Store  # noqa: E402

EXAMPLE = json.loads((REPO_ROOT / "schema" / "examples" / "01-stop-hook-bugfix-tests-passed.json").read_text(encoding="utf-8"))


def record(i: int, *, model="example-model-a", harness="claude-code", l2="coding.bugfix", passed=True, self_score=None) -> dict:
    r = copy.deepcopy(EXAMPLE)
    r["record_id"] = f"00000000-0000-4000-8000-{i:012d}"
    r["model"]["id"] = model
    r["method"]["harness"] = harness
    r["task"]["l2"] = l2
    r["outcome"]["evidence"]["tests_passed"] = passed
    r["outcome"]["self_assessment"] = None if self_score is None else {"score": self_score, "rater": "self_llm", "judge_model": None, "extractor": None}
    return r


class ValidationTest(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def tearDown(self):
        self.store.close()

    def test_valid_record_is_stored(self):
        self.store.add_field_report(record(1), install_id="install-1")
        self.assertEqual(self.store.count(), 1)

    def test_invalid_records_are_rejected_with_reasons(self):
        bad_cases = {
            "prompt text smuggled in": lambda r: r.__setitem__("prompt", "fix my login bug"),
            "content_included true": lambda r: r["privacy"].__setitem__("content_included", True),
            "missing evidence": lambda r: r["outcome"].pop("evidence"),
            "unknown l2": lambda r: r["task"].__setitem__("l2", "coding.vibes"),
        }
        for label, mutate in bad_cases.items():
            with self.subTest(label):
                r = record(2)
                mutate(r)
                with self.assertRaises(InvalidRecord) as ctx:
                    self.store.add_field_report(r)
                self.assertTrue(ctx.exception.errors)
        self.assertEqual(self.store.count(), 0)

    def test_seed_source_types_are_not_accepted_as_field_reports(self):
        r = record(3)
        r["source"]["source_type"] = "benchmark"
        with self.assertRaises(InvalidRecord):
            self.store.add_field_report(r)

    def test_non_object_is_rejected(self):
        with self.assertRaises(InvalidRecord):
            self.store.add_field_report([1, 2, 3])  # type: ignore[arg-type]


class AppendOnlyTest(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        self.store.add_field_report(record(1), install_id="a")
        seed = record(2)
        seed["source"]["source_type"] = "benchmark"
        self.store.import_seed({"source_id": "s", "source_type": "benchmark", "name": "s",
                                "url": "https://example.invalid", "license": "CC0-1.0"}, [seed])

    def tearDown(self):
        self.store.close()

    def test_duplicate_record_id_is_refused_not_overwritten(self):
        changed = record(1, model="example-model-z")
        with self.assertRaises(DuplicateRecord):
            self.store.add_field_report(changed, install_id="b")
        body = self.store.raw_connection().execute(
            "SELECT model_id FROM records WHERE record_id = ?", (changed["record_id"],)).fetchall()
        self.assertEqual(body, [("example-model-a",)])

    def test_sql_update_and_delete_are_blocked_by_triggers(self):
        db = self.store.raw_connection()
        for sql in ("UPDATE records SET model_id = 'x'", "DELETE FROM records",
                    "UPDATE seed_sources SET name = 'x'", "DELETE FROM seed_sources"):
            with self.subTest(sql=sql):
                with self.assertRaisesRegex(sqlite3.DatabaseError, "append-only"):
                    db.execute(sql)
        self.assertEqual(self.store.count(), 2)

    def test_contributor_is_salted_hash_not_raw_install_id(self):
        row = self.store.raw_connection().execute(
            "SELECT contributor FROM records WHERE source_type = 'field_report'").fetchone()[0]
        self.assertRegex(row, r"^c:[0-9a-f]{24}$")  # salted hash, raw install id is not stored
        other = Store(":memory:")  # different salt -> different key
        self.assertNotEqual(other.contributor_key("a"), self.store.contributor_key("a"))
        self.assertEqual(self.store.contributor_key(None), "anonymous")
        other.close()


class ThresholdTest(unittest.TestCase):
    def _store(self, n: int, contributors: int, **kw) -> Store:
        s = Store(":memory:")
        for i in range(n):
            s.add_field_report(record(i, **kw), install_id=f"install-{i % contributors}")
        return s

    def test_cell_hidden_below_k_even_with_many_records(self):
        s = self._store(40, contributors=4)
        out = aggregate(s.rows(), Thresholds())
        self.assertEqual(out["cells"], [])
        self.assertEqual(len(out["suppressed"]), 1)
        self.assertNotIn("n", out["suppressed"][0])  # no counts leak for suppressed cells
        self.assertNotIn("k", out["suppressed"][0])

    def test_cell_hidden_below_n_even_with_many_contributors(self):
        s = self._store(29, contributors=29)
        self.assertEqual(aggregate(s.rows(), Thresholds())["cells"], [])

    def test_cell_visible_at_threshold(self):
        s = self._store(30, contributors=5)
        cells = aggregate(s.rows(), Thresholds())["cells"]
        self.assertEqual(len(cells), 1)
        self.assertEqual((cells[0]["n"], cells[0]["k"]), (30, 5))

    def test_anonymous_records_count_as_one_contributor(self):
        s = Store(":memory:")
        for i in range(40):
            s.add_field_report(record(i), install_id=None)
        out = aggregate(s.rows(), Thresholds.build(k=2, n=1))
        self.assertEqual(out["cells"], [])

    def test_thresholds_are_configurable(self):
        s = self._store(6, contributors=2)
        self.assertEqual(len(aggregate(s.rows(), Thresholds.build(k=2, n=6))["cells"]), 1)
        self.assertEqual(aggregate(s.rows(), Thresholds.build(k=3, n=6))["cells"], [])
        with self.assertRaises(ValueError):
            Thresholds.build(k=0)

    def test_source_types_are_separate_cells_with_their_own_thresholds(self):
        s = self._store(30, contributors=5, model="gpt-x", harness="aider-diff", l2="coding.feature")
        seed = [record(1000 + i, model="gpt-x", harness="aider-diff", l2="coding.feature", passed=i % 2 == 0) for i in range(30)]
        for r in seed:
            r["source"]["source_type"] = "benchmark"
            r["source"]["collector"] = "seed-import"
        meta = {"source_id": "test-seed", "source_type": "benchmark", "name": "t", "url": "https://example.invalid", "license": "CC0-1.0"}
        self.assertEqual(s.import_seed(meta, seed), (30, 0))
        self.assertEqual(s.import_seed(meta, seed), (0, 30))  # idempotent re-import
        out = aggregate(s.rows(), Thresholds())
        by_type = {c["source_type"]: c for c in out["cells"]}
        self.assertEqual(set(by_type), {"field_report", "benchmark"})  # never pooled
        self.assertEqual(by_type["benchmark"]["k"], 1)  # seed layer: k=1 allowed by default
        self.assertEqual(by_type["benchmark"]["tests"]["pass_rate"], 0.5)
        self.assertIsNone(by_type["benchmark"]["commit_rate"])  # placeholder fields ignored for seeds
        self.assertEqual(by_type["field_report"]["tests"]["pass_rate"], 1.0)
        only_seed = aggregate(s.rows(), Thresholds(), source_type="benchmark")
        self.assertEqual([c["source_type"] for c in only_seed["cells"]], ["benchmark"])
        # stricter seed threshold hides it
        self.assertEqual(aggregate(s.rows(), Thresholds.build(seed_n=31), source_type="benchmark")["cells"], [])

    def test_self_assessment_is_reported_but_never_the_ranking_signal(self):
        s = Store(":memory:")
        for i in range(30):
            s.add_field_report(record(i, passed=i < 12, self_score=0.95), install_id=f"i{i % 5}")
        cell = aggregate(s.rows(), Thresholds())["cells"][0]
        self.assertEqual(cell["tests"]["pass_rate"], 0.4)
        self.assertEqual(cell["self_assessment"]["mean"], 0.95)
        self.assertTrue(cell["self_assessment"]["excluded_from_ranking"])

    def test_l1_level_rollup(self):
        s = Store(":memory:")
        for i in range(30):
            s.add_field_report(record(i, l2="coding.bugfix" if i % 2 else "coding.test"), install_id=f"i{i % 5}")
        self.assertEqual(aggregate(s.rows(), Thresholds())["cells"], [])  # each L2 has only 15
        l1 = aggregate(s.rows(), Thresholds(), level="l1")["cells"]
        self.assertEqual((len(l1), l1[0]["l2"], l1[0]["n"]), (1, None, 30))

    def test_wilson(self):
        self.assertEqual(wilson(0, 0), None)
        lo, hi = wilson(50, 100)
        self.assertAlmostEqual(lo, 0.4038, places=3)
        self.assertAlmostEqual(hi, 0.5962, places=3)


class HttpApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        # Legacy mode: unsigned submissions allowed, detail view open (local development).
        cls.httpd = make_server(cls.store, "127.0.0.1", 0, Thresholds.build(k=2, n=2, max_share=1.0), quiet=True,
                                policy=Policy(signatures="optional", gate=False))
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.store.close()

    def call(self, method, path, body=None, headers=None):
        data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
        h = {"Content-Type": "application/json"} if data is not None else {}
        h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), err.read()

    def test_post_validate_store_and_aggregate(self):
        status, _, body = self.call("POST", "/v1/records", record(501), {"X-ModelReceipts-Install": "i-1"})
        self.assertEqual(status, 201, body)
        self.assertEqual(self.call("POST", "/v1/records", record(502), {"X-ModelReceipts-Install": "i-2"})[0], 201)
        status, headers, _ = self.call("POST", "/v1/records", record(501))
        self.assertEqual(status, 409)
        bad = record(503)
        bad["prompt"] = "secret"
        status, _, body = self.call("POST", "/v1/records", bad)
        self.assertEqual(status, 400)
        self.assertIn("unexpected property 'prompt'", body.decode())
        status, headers, body = self.call("GET", "/v1/aggregates/detail?source_type=field_report")
        self.assertEqual(status, 200)
        agg = json.loads(body)
        self.assertEqual(agg["thresholds"]["field_report"],
                         {"min_contributors": 2, "min_records": 2, "max_contributor_share": 1.0})
        self.assertEqual([(c["model"], c["n"], c["k"]) for c in agg["cells"]], [("example-model-a", 2, 2)])
        status, headers, body = self.call("GET", "/v1/overview")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(json.loads(body)["view"], "overview")

    def test_rejects_bad_transport(self):
        self.assertEqual(self.call("POST", "/v1/records", b"{not json")[0], 400)
        self.assertEqual(self.call("POST", "/v1/records", b"{}", {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.call("POST", "/v1/records", b" " * (64 * 1024 + 1))[0], 413)
        self.assertEqual(self.call("GET", "/v1/aggregates/detail?source_type=nope")[0], 400)

    def test_no_update_or_delete_routes(self):
        for method in ("PUT", "DELETE", "PATCH"):
            with self.subTest(method=method):
                status, headers, _ = self.call(method, "/v1/records", record(600))
                self.assertEqual(status, 405)
                self.assertEqual(headers.get("Allow"), "POST")
        self.assertEqual(self.call("POST", "/v1/aggregates", {})[0], 405)

    def test_dashboard_static_and_traversal(self):
        status, headers, body = self.call("GET", "/dashboard/index.html")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertEqual(self.call("GET", "/dashboard/../server/modelreceipts_server/store.py")[0], 404)
        self.assertEqual(self.call("GET", "/dashboard/%2e%2e/LICENSE")[0], 404)
        self.assertEqual(self.call("GET", "/healthz")[0], 200)


class BindTest(unittest.TestCase):
    def test_refuses_non_loopback_hosts(self):
        s = Store(":memory:")
        for host in ("0.0.0.0", "::", "192.168.1.10", ""):
            with self.subTest(host=host), self.assertRaises(NotLoopback):
                make_server(s, host, 0)
        s.close()


if __name__ == "__main__":
    unittest.main()
