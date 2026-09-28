"""v1.0 server features: signatures, contributor gate, rate limits, per-cell cap,
server-side cost, separated self-assessment, dominance cap, pair mode, seed cells,
database migration. All data is SYNTHETIC. Run from repo root:

    python3 -m unittest discover -s server/tests
"""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from modelreceipts_server import REPO_ROOT  # noqa: E402
from modelreceipts_server.aggregate import Thresholds, aggregate, overview, pairwise, self_vs_evidence  # noqa: E402
from modelreceipts_server.app import Policy, make_server  # noqa: E402
from modelreceipts_server.prices import PriceTable  # noqa: E402
from modelreceipts_server.ratelimit import RateLimits, TokenBucket  # noqa: E402
from modelreceipts_server.store import LegacyDatabase, Store, migrate_database  # noqa: E402

from modelreceipts.signing import generate_key, sign_request  # noqa: E402

EXAMPLES = REPO_ROOT / "schema" / "examples"
EXAMPLE = json.loads((EXAMPLES / "01-stop-hook-bugfix-tests-passed.json").read_text(encoding="utf-8"))
NS = uuid.UUID("7d0c3f5e-1a2b-5c3d-9e4f-5a6b7c8d9e0f")


def record(i, *, model="example-model-a", harness="claude-code", l2="coding.bugfix", passed=True,
           self_score=None, pair_id=None, route="unknown", retry=None) -> dict:
    r = copy.deepcopy(EXAMPLE)
    r["record_id"] = str(uuid.uuid5(NS, str(i)))
    r["model"]["id"] = model
    r["model"]["route"] = route
    r["method"]["harness"] = harness
    r["task"]["l2"] = l2
    r["outcome"]["evidence"]["tests_passed"] = passed
    r["outcome"]["evidence"]["user_retry_next_prompt"] = retry
    r["outcome"]["evidence"]["retry_detector"] = None if retry is None else "retry-rules-v1"
    r["outcome"]["self_assessment"] = (None if self_score is None else
                                       {"score": self_score, "rater": "self_claim", "judge_model": None,
                                        "extractor": "claim-rules-v1"})
    r["pairing"]["pair_id"] = pair_id
    return r


class _Http(unittest.TestCase):
    policy = Policy()
    thresholds = Thresholds.build(k=2, n=2, max_share=1.0)

    def setUp(self):
        self.store = Store(":memory:")
        self.httpd = make_server(self.store, "127.0.0.1", 0, self.thresholds, quiet=True, policy=self.policy)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.store.close()

    def call(self, method, path, body=None, key=None, headers=None, sign_body=None):
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        h = {"Content-Type": "application/json"} if data is not None else {}
        if key is not None:
            h.update(sign_request(key, method, path, (data or b"") if sign_body is None else sign_body))
        h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, dict(resp.headers), json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), json.loads(err.read() or b"{}")


class SignatureTest(_Http):
    def test_signed_accepted_unsigned_and_forged_refused(self):
        key = generate_key()
        status, _, body = self.call("POST", "/v1/records", record(1), key=key)
        self.assertEqual(status, 201, body)
        self.assertTrue(body["signed"])
        contributor, verified = self.store.raw_connection().execute(
            "SELECT contributor, key_verified FROM records").fetchone()
        self.assertRegex(contributor, r"^k:[0-9a-f]{24}$")
        self.assertEqual(verified, 1)
        self.assertEqual(self.call("POST", "/v1/records", record(2))[0], 401)  # unsigned
        self.assertEqual(self.call("POST", "/v1/records", record(2), headers={"X-ModelReceipts-Install": "x"})[0], 401)
        status, _, body = self.call("POST", "/v1/records", record(3), key=key, sign_body=b"{}")  # body swapped
        self.assertEqual((status, body["error"]), (401, "bad_signature"))
        self.assertEqual(self.store.count(), 1)

    def test_same_key_is_one_contributor_different_keys_are_two(self):
        k1, k2 = generate_key(), generate_key()
        for i, key in enumerate((k1, k1, k2)):
            self.assertEqual(self.call("POST", "/v1/records", record(10 + i), key=key)[0], 201)
        rows = self.store.raw_connection().execute("SELECT DISTINCT contributor FROM records").fetchall()
        self.assertEqual(len(rows), 2)


class GateTest(_Http):
    def test_overview_is_public_and_coarse(self):
        key = generate_key()
        for i in range(4):
            self.call("POST", "/v1/records", record(i, l2="coding.bugfix" if i % 2 else "coding.docs"),
                      key=key if i < 2 else generate_key())
        status, headers, body = self.call("GET", "/v1/overview")
        self.assertEqual(status, 200)
        self.assertEqual(body["view"], "overview")
        field = [c for c in body["cells"] if c["source_type"] == "field_report"]
        self.assertEqual(len(field), 1)
        cell = field[0]
        self.assertEqual((cell["l2"], cell["method"], cell["n"]), (None, None, 4))
        self.assertNotIn("ci95", cell["tests"])
        for hidden in ("cost_usd_per_task", "self_assessment", "retry_next_prompt", "commit_rate"):
            self.assertNotIn(hidden, cell)
        self.assertEqual(body["gate"]["detail_endpoint"], "/v1/aggregates/detail")
        self.assertEqual(self.call("GET", "/v1/aggregates")[2]["view"], "overview")  # alias

    def test_detail_requires_a_recent_contributor_key(self):
        path = "/v1/aggregates/detail?source_type=field_report"
        status, _, body = self.call("GET", path)
        self.assertEqual((status, body["error"]), (401, "contributors_only"))
        stranger = generate_key()
        status, _, body = self.call("GET", path, key=stranger)
        self.assertEqual((status, body["error"]), (403, "contributors_only"))
        contributor = generate_key()
        self.assertEqual(self.call("POST", "/v1/records", record(1), key=contributor)[0], 201)
        self.assertEqual(self.call("POST", "/v1/records", record(2), key=generate_key())[0], 201)
        status, _, body = self.call("GET", path, key=contributor)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["view"], "detail")
        self.assertIn("ci95", body["cells"][0]["tests"])
        self.assertIn("pairwise", body)
        # a signature for another query string does not open this one
        h = sign_request(contributor, "GET", "/v1/aggregates/detail")
        self.assertEqual(self.call("GET", path, headers=h)[0], 401)


class RateLimitTest(_Http):
    policy = Policy(limits=RateLimits(per_hour=1, burst=3, cell_daily_cap=50))

    def test_burst_then_429_with_retry_after(self):
        key = generate_key()
        codes = [self.call("POST", "/v1/records", record(i), key=key)[0] for i in range(4)]
        self.assertEqual(codes, [201, 201, 201, 429])
        status, headers, body = self.call("POST", "/v1/records", record(9), key=key)
        self.assertEqual((status, body["error"]), (429, "rate_limited"))
        self.assertGreater(int(headers["Retry-After"]), 0)
        self.assertEqual(self.call("POST", "/v1/records", record(10), key=generate_key())[0], 201)  # other key

    def test_token_bucket_refills(self):
        now = [0.0]
        b = TokenBucket(per_hour=3600, burst=2, clock=lambda: now[0])
        self.assertEqual([b.take("k")[0] for _ in range(3)], [True, True, False])
        now[0] += 1.0
        self.assertTrue(b.take("k")[0])


class CellCapTest(_Http):
    policy = Policy(limits=RateLimits(per_hour=1000, burst=100, cell_daily_cap=2))

    def test_one_key_cannot_fill_a_cell(self):
        key = generate_key()
        codes = [self.call("POST", "/v1/records", record(i), key=key)[0] for i in range(3)]
        self.assertEqual(codes, [201, 201, 429])
        self.assertEqual(self.call("POST", "/v1/records", record(3), key=key)[2]["error"], "cell_daily_cap")
        self.assertEqual(self.call("POST", "/v1/records", record(4, l2="coding.docs"), key=key)[0], 201)


class ServerCostTest(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def tearDown(self):
        self.store.close()

    def test_price_table_has_provenance(self):
        d = self.store.prices.describe()
        for field in ("url", "as_of", "retrieved_at", "retrieved_via", "verified_live"):
            self.assertIn(field, d["source"])
        self.assertEqual(d["applies_to_routes"], ["direct"])
        self.assertEqual(len(d["sha256"]), 64)

    def test_cost_is_recomputed_and_stored_separately(self):
        r = record(1, model="claude-opus-5-5", route="direct")
        r["usage"].update(input_tokens=1_000_000, output_tokens=100_000, cache_read_tokens=2_000_000,
                          cache_write_tokens=0, cost_usd_client=9.99)
        self.store.add_field_report(r, install_id="i")
        cost = self.store.server_cost(r["record_id"])
        self.assertEqual(cost, {"price_table_id": "anthropic-api@2026-06-24", "cost_usd": 6.4, "reason": "ok"})
        body = json.loads(self.store.raw_connection().execute("SELECT body FROM records").fetchone()[0])
        self.assertEqual(body["usage"]["cost_usd_client"], 9.99)  # client value untouched
        self.assertIsNone(body["usage"]["cost_usd_server"])
        row = self.store.rows()[0]
        self.assertEqual((row["cost_usd_client"], row["cost_usd_server"]), (9.99, 6.4))

    def test_uncovered_cases_get_null_with_reason(self):
        cases = [(record(2, model="claude-opus-5-5", route="bedrock"), "route_not_covered"),
                 (record(3, model="example-model-a", route="direct"), "model_not_in_table")]
        for r, reason in cases:
            self.store.add_field_report(r, install_id="i")
            self.assertEqual(self.store.server_cost(r["record_id"])["reason"], reason)
            self.assertIsNone(self.store.server_cost(r["record_id"])["cost_usd"])

    def test_longest_prefix_and_bad_tables(self):
        t = PriceTable.load()
        self.assertEqual(t.lookup("claude-opus-5-5")["input"], 4.0)
        self.assertEqual(t.lookup("claude-opus-5-20260101")["input"], 5.0)
        self.assertIsNone(t.lookup("claude-opus-50"))
        with self.assertRaises(ValueError):
            PriceTable({**t.data, "source": {"name": "x"}})

    def test_side_tables_are_append_only(self):
        self.store.add_field_report(record(4, self_score=0.9), install_id="i")
        db = self.store.raw_connection()
        for sql in ("UPDATE server_costs SET cost_usd = 0", "DELETE FROM self_assessments"):
            with self.subTest(sql=sql), self.assertRaisesRegex(sqlite3.DatabaseError, "append-only"):
                db.execute(sql)


class SelfAssessmentSeparationTest(unittest.TestCase):
    def test_self_score_lives_in_its_own_table(self):
        s = Store(":memory:")
        s.add_field_report(record(1, self_score=0.95), install_id="i")
        db = s.raw_connection()
        self.assertIsNone(db.execute("SELECT self_score FROM records").fetchone()[0])
        self.assertEqual(db.execute("SELECT score, rater, extractor FROM self_assessments").fetchone(),
                         (0.95, "self_claim", "claim-rules-v1"))
        self.assertEqual(s.rows()[0]["self_score"], 0.95)
        s.close()


class AggregationRulesTest(unittest.TestCase):
    def _store(self, specs):
        s = Store(":memory:")
        for i, (install, kw) in enumerate(specs):
            s.add_field_report(record(i, **kw), install_id=install)
        return s

    def test_dominated_cell_is_suppressed(self):
        specs = [("big", {})] * 24 + [(f"small-{i}", {}) for i in range(6)]
        s = self._store(specs)
        agg = aggregate(s.rows(), Thresholds.build(k=5, n=30, max_share=0.5))
        self.assertEqual(agg["cells"], [])
        self.assertEqual(agg["suppressed"][0]["reason"], "dominated_by_one_contributor")
        agg = aggregate(s.rows(), Thresholds.build(k=5, n=30, max_share=0.9))
        self.assertEqual(len(agg["cells"]), 1)
        s.close()

    def test_retry_rate_counts_only_observed(self):
        specs = [(f"i{i}", {"retry": [True, False, None][i % 3]}) for i in range(30)]
        s = self._store(specs)
        cell = aggregate(s.rows(), Thresholds.build(k=5, n=30))["cells"][0]
        self.assertEqual(cell["retry_next_prompt"], {"observed": 20, "rate": 0.5})
        s.close()

    def test_pairwise_head_to_head(self):
        specs = []
        outcomes = [(True, False)] * 6 + [(True, True)] * 3 + [(False, True)] * 2 + [(None, True)] * 1
        for j, (pa, pb) in enumerate(outcomes):
            pid = str(uuid.uuid5(NS, f"pair{j}"))
            specs.append((f"u{j % 4}", {"model": "example-model-a", "passed": pa, "pair_id": pid}))
            specs.append((f"u{j % 4}", {"model": "example-model-b", "passed": pb, "pair_id": pid}))
        s = self._store(specs)
        res = pairwise(s.rows(), Thresholds.build(pair_min_pairs=10, pair_min_contributors=3))
        self.assertEqual(len(res["results"]), 1)
        r = res["results"][0]
        self.assertEqual((r["pairs"], r["a_wins"], r["b_wins"], r["ties"], r["undecided"]), (12, 6, 2, 3, 1))
        self.assertAlmostEqual(r["a_score"], round((6 + 1.5) / 11, 4))
        self.assertEqual(pairwise(s.rows(), Thresholds.build(pair_min_pairs=13))["results"], [])
        s.close()

    def test_self_vs_evidence_ranks(self):
        cells = [
            {"source_type": "field_report", "l1": "coding", "l2": "coding.bugfix", "model": "m1",
             "tests": {"tested": 10, "passed": 8}, "self_assessment": {"n": 10, "mean": 0.6}},
            {"source_type": "field_report", "l1": "coding", "l2": "coding.bugfix", "model": "m2",
             "tests": {"tested": 10, "passed": 5}, "self_assessment": {"n": 10, "mean": 0.95}},
        ]
        [row] = self_vs_evidence(cells)
        ranks = {m["model"]: (m["rank_by_self"], m["rank_by_evidence"]) for m in row["models"]}
        self.assertEqual(ranks, {"m1": (2, 1), "m2": (1, 2)})
        self.assertTrue(row["top_differs"])


class SeedCellTest(unittest.TestCase):
    def test_import_is_idempotent_validated_and_thresholded(self):
        cell = json.loads((EXAMPLES / "seed-cells" / "preference-cell.json").read_text(encoding="utf-8"))
        small = copy.deepcopy(cell)
        small["cell_id"] = str(uuid.uuid5(NS, "small"))
        small["model"]["id"] = "example-model-small"
        small["metrics"].update(battles=10, wins=5, losses=5, ties=0, win_rate=0.5)
        meta = {"source_id": "example-preference@synthetic", "source_type": "preference", "name": "synthetic",
                "url": "about:synthetic", "license": "CC0-1.0"}
        s = Store(":memory:")
        self.assertEqual(s.import_seed_cells(meta, [cell, small]), (2, 0))
        self.assertEqual(s.import_seed_cells(meta, [cell, small]), (0, 2))
        bad = copy.deepcopy(cell)
        bad["prompt"] = "leak"
        with self.assertRaises(ValueError):
            s.import_seed_cells(meta, [bad])
        for sql in ("UPDATE seed_cells SET wins = 0", "DELETE FROM seed_cells"):
            with self.subTest(sql=sql), self.assertRaisesRegex(sqlite3.DatabaseError, "append-only"):
                s.raw_connection().execute(sql)
        view = aggregate(s.rows(), Thresholds(), seed_cells=s.seed_cell_rows())["seed_cells"]
        self.assertEqual([c["model"] for c in view["cells"]], ["example-model-a"])
        self.assertEqual(view["suppressed"][0]["model"], "example-model-small")
        self.assertEqual(overview(s.rows(), Thresholds(), seed_cells=s.seed_cell_rows())["totals"]
                         ["seed_cells_by_source_type"], {"preference": 2})
        s.close()


OLD_DDL = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE seed_sources (source_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, name TEXT NOT NULL, url TEXT NOT NULL,
  commit_sha TEXT, commit_date TEXT, sha256 TEXT, license TEXT NOT NULL, license_note TEXT, imported_at TEXT NOT NULL);
CREATE TABLE records (seq INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL UNIQUE, received_at TEXT NOT NULL,
  source_type TEXT NOT NULL, contributor TEXT NOT NULL, seed_source_id TEXT REFERENCES seed_sources(source_id),
  l1 TEXT NOT NULL, l2 TEXT, model_id TEXT NOT NULL, harness TEXT NOT NULL, tests_passed INTEGER,
  committed INTEGER NOT NULL, tool_error_count INTEGER NOT NULL, cost_usd_client REAL, cost_usd_server REAL,
  latency_ms INTEGER, self_score REAL, body TEXT NOT NULL);
"""


class MigrateDbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = self.tmp / "old.sqlite3"
        db = sqlite3.connect(self.old)
        db.executescript(OLD_DDL)
        db.execute("INSERT INTO meta VALUES ('contributor_salt', 'oldsalt')")
        db.execute("INSERT INTO seed_sources VALUES ('s', 'benchmark', 's', 'https://example.invalid', NULL, NULL,"
                   " NULL, 'CC0-1.0', NULL, '2026-09-27T00:00:00Z')")
        v01 = json.loads((EXAMPLES / "v0.1" / "02-self-assessment-disagrees-with-evidence.json").read_text())
        seed = json.loads((EXAMPLES / "v0.1" / "01-stop-hook-bugfix-tests-passed.json").read_text())
        seed["source"].update(source_type="benchmark", collector="seed-import")
        seed["usage"]["turns"] = 0
        for rec, contrib, src in ((v01, "c:abc", None), (seed, "seed:s", "s")):
            db.execute("INSERT INTO records (record_id, received_at, source_type, contributor, seed_source_id, l1, l2,"
                       " model_id, harness, tests_passed, committed, tool_error_count, body) VALUES"
                       " (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (rec["record_id"], "2026-09-27T00:00:00Z", rec["source"]["source_type"], contrib, src,
                        rec["task"]["l1"], rec["task"]["l2"], rec["model"]["id"], rec["method"]["harness"], 1, 0, 0,
                        json.dumps(rec)))
        db.commit()
        db.close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_copy_migration_keeps_source_and_identity(self):
        before = self.old.read_bytes()
        counts = migrate_database(self.old, self.tmp / "new.sqlite3")
        self.assertEqual(counts["records"], 2)
        self.assertEqual(counts["migrated_bodies"], 2)
        self.assertEqual(self.old.read_bytes(), before)
        new = Store(self.tmp / "new.sqlite3")
        self.assertEqual(new.salt, "oldsalt")
        rows = new.raw_connection().execute("SELECT contributor, schema_version, body FROM records ORDER BY seq").fetchall()
        self.assertEqual([r[0] for r in rows], ["c:abc", "seed:s"])
        self.assertEqual({r[1] for r in rows}, {"0.2.0"})
        self.assertIsNone(json.loads(rows[1][2])["usage"]["turns"])  # seed placeholder -> null
        self.assertEqual(new.raw_connection().execute("SELECT score FROM self_assessments").fetchone()[0], 0.95)
        new.close()
        with self.assertRaises(FileExistsError):
            migrate_database(self.old, self.tmp / "new.sqlite3")

    def test_opening_an_old_database_upgrades_it_additively(self):
        s = Store(self.old)
        cols = {r[1] for r in s.raw_connection().execute("PRAGMA table_info(records)")}
        self.assertTrue({"schema_version", "pair_id", "retry_next", "key_verified"} <= cols)
        self.assertEqual(s.count(), 2)
        s.add_field_report(record(77), install_id="new")
        self.assertEqual(s.count(), 3)
        nulls = record(78)
        nulls["outcome"]["evidence"]["committed"] = None  # v0.2 allows null; the old column does not
        with self.assertRaisesRegex(LegacyDatabase, "migrate-db"):
            s.add_field_report(nulls, install_id="new")
        self.assertEqual(s.count(), 3)
        s.close()


class SampleUpToDateTest(unittest.TestCase):
    def test_committed_samples_match_generator(self):
        from modelreceipts_server.sample import build_samples
        detail, public = build_samples()
        for name, obj in (("aggregates.sample.json", detail), ("overview.sample.json", public)):
            committed = (REPO_ROOT / "dashboard" / "data" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertEqual(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", committed,
                                 "run: PYTHONPATH=server python3 -m modelreceipts_server make-sample")
        from modelreceipts_server.figure import render
        svg = render(detail)
        self.assertIn("SYNTHETIC", svg)
        self.assertEqual(svg, (REPO_ROOT / "docs" / "figures" / "self-vs-evidence.synthetic.svg").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
