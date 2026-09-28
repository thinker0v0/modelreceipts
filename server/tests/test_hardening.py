"""v1.0.0rc2 self-review: regression tests for input-handling bugs in the server,
plus cheap randomized ("property-style") checks with a FIXED seed so failures
are reproducible. All data is SYNTHETIC. Run from repo root:

    python3 -m unittest discover -s server/tests
"""

from __future__ import annotations

import copy
import io
import json
import random
import socket
import sys
import threading
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from modelreceipts_server import REPO_ROOT  # noqa: E402
from modelreceipts_server.aggregate import Thresholds  # noqa: E402
from modelreceipts_server.app import MAX_BODY, Policy, make_server  # noqa: E402
from modelreceipts_server.ratelimit import RateLimits, TokenBucket  # noqa: E402
from modelreceipts_server.store import Store  # noqa: E402

from modelreceipts.signing import generate_key, sign_request  # noqa: E402

EXAMPLE = json.loads((REPO_ROOT / "schema" / "examples" / "01-stop-hook-bugfix-tests-passed.json")
                     .read_text(encoding="utf-8"))
NS = uuid.UUID("0b7e6a52-3c1d-4f7a-9d2e-6c5b4a392817")
SEED = 20260928
KNOWN_STATUSES = {200, 201, 400, 401, 403, 404, 405, 409, 411, 413, 415, 429}


def record(i: int, **usage) -> dict:
    r = copy.deepcopy(EXAMPLE)
    r["record_id"] = str(uuid.uuid5(NS, str(i)))
    r["model"]["id"] = "example-model-a"
    r["usage"].update(usage)
    return r


class _Server(unittest.TestCase):
    policy = Policy(signatures="optional", gate=False,
                    limits=RateLimits(per_hour=100_000, burst=10_000, cell_daily_cap=10_000))
    quiet = True

    def setUp(self):
        self.store = Store(":memory:")
        self.httpd = make_server(self.store, "127.0.0.1", 0, Thresholds.build(k=1, n=1, max_share=1.0),
                                 quiet=self.quiet, policy=self.policy)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.store.close()

    def raw(self, head: bytes, body: bytes = b"", shut_write: bool = True) -> tuple[int | None, bytes]:
        """Send raw bytes; return (status or None if the server dropped the connection, body)."""
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as c:
            try:
                c.sendall(head + body)
            except OSError:
                pass  # the server may answer and close before reading everything
            if shut_write:
                try:
                    c.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
            chunks = []
            try:
                while True:
                    d = c.recv(65536)
                    if not d:
                        break
                    chunks.append(d)
            except OSError:
                pass
        data = b"".join(chunks)
        if not data.startswith(b"HTTP/1."):
            return None, data
        head_end = data.find(b"\r\n\r\n")
        return int(data.split(b" ", 2)[1]), data[head_end + 4:]

    def post(self, body: bytes, extra: bytes = b"", length: str | None = None) -> tuple[int | None, bytes]:
        cl = str(len(body)) if length is None else length
        head = (b"POST /v1/records HTTP/1.1\r\nHost: t\r\nContent-Type: application/json\r\n"
                b"Connection: close\r\nContent-Length: " + cl.encode() + b"\r\n" + extra + b"\r\n")
        return self.raw(head, body)

    def get(self, path: bytes) -> tuple[int | None, bytes]:
        return self.raw(b"GET " + path + b" HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n")


class TransportLimitsTest(_Server):
    def test_negative_content_length_is_refused_without_reading_the_body(self):
        # Bug (rc1): int("-1") passed the size check and rfile.read(-1) read to EOF,
        # bypassing MAX_BODY entirely.
        status, body = self.post(b"x" * (MAX_BODY * 3), length="-1")
        self.assertIn(status, {400, 411})
        self.assertEqual(json.loads(body)["error"], "content_length_required")
        self.assertEqual(self.store.count(), 0)

    def test_deeply_nested_json_gets_400_not_a_dropped_connection(self):
        # Bug (rc1): RecursionError escaped the handler; the client saw a reset.
        status, body = self.post(b"[" * 30000 + b"]" * 30000)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_json")

    def test_huge_integer_literal_gets_400(self):
        # Bug (rc1): int() digit-limit ValueError is not a JSONDecodeError and escaped.
        status, body = self.post(b"1" * 50000)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_json")

    def test_nan_and_infinity_literals_are_not_json(self):
        # Bug (rc1): json.loads accepted NaN/Infinity, the validator accepted them as
        # numbers, and the detail view later emitted the invalid token `Infinity`.
        for literal in (b"Infinity", b"-Infinity", b"NaN"):
            with self.subTest(literal=literal):
                raw = json.dumps(record(1)).encode().replace(b'"cost_usd_client": null',
                                                              b'"cost_usd_client": ' + literal)
                status, body = self.post(raw)
                self.assertEqual(status, 400, body)
        self.assertEqual(self.store.count(), 0)

    def test_integer_too_large_for_storage_gets_400(self):
        # Bug (rc1): latency_ms = 10**30 passed validation and SQLite raised OverflowError.
        status, body = self.post(json.dumps(record(2, latency_ms=10 ** 30)).encode())
        self.assertEqual(status, 400, body)
        self.assertEqual(json.loads(body)["error"], "schema_validation_failed")

    def test_nul_byte_in_static_path_gets_404(self):
        # Bug (rc1): Path.resolve() raised ValueError("embedded null byte") and the
        # connection was dropped.
        status, _ = self.get(b"/dashboard/index.html\x00.png")
        self.assertEqual(status, 404)

    def test_validation_errors_do_not_echo_large_input(self):
        r = record(3)
        r["model"]["id"] = "x" * 20000
        status, body = self.post(json.dumps(r).encode())
        self.assertEqual(status, 400)
        self.assertLess(len(body), 4000)


class ClientDisconnectTest(_Server):
    def test_reset_connection_is_not_logged_as_a_traceback(self):
        # Bug (rc1): a client that resets a keep-alive connection (e.g. `curl | head`)
        # made socketserver print a full traceback with file paths to stderr.
        import struct
        import time
        from contextlib import redirect_stderr
        err = io.StringIO()
        with redirect_stderr(err):
            c = socket.create_connection(("127.0.0.1", self.port), timeout=10)
            c.sendall(b"GET /healthz HTTP/1.1\r\nHost: t\r\n\r\n")
            self.assertTrue(c.recv(65536).startswith(b"HTTP/1.1 200"))
            c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))  # close with RST
            c.close()
            time.sleep(0.3)
        self.assertNotIn("Traceback", err.getvalue())


class InternalErrorTest(_Server):
    def test_unexpected_exception_is_a_generic_500(self):
        def boom():
            raise RuntimeError("/srv/secret/path.sqlite3 is locked")
        self.store.rows = boom
        status, body = self.get(b"/v1/overview")
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body), {"error": "internal_error"})
        self.assertNotIn(b"secret", body)


class LogInjectionTest(_Server):
    quiet = False

    def test_control_characters_in_paths_are_escaped_in_logs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            status, _ = self.get(b"/nope\x1b[2J\x1b[31mFAKE")
        self.assertEqual(status, 404)
        self.assertNotIn("\x1b", out.getvalue())
        self.assertIn("/nope", out.getvalue())


class NewContributorLimitTest(_Server):
    policy = Policy(limits=RateLimits(per_hour=1000, burst=100, cell_daily_cap=1000,
                                      new_contributors_per_hour=1, new_contributor_burst=3))

    def signed_post(self, i: int, key) -> int | None:
        body = json.dumps(record(i)).encode()
        hdr = "".join(f"{k}: {v}\r\n" for k, v in sign_request(key, "POST", "/v1/records", body).items())
        return self.post(body, hdr.encode())[0]

    def test_rotating_keys_does_not_bypass_rate_limits(self):
        # Bug (rc1): every fresh key got its own full bucket, so generating a key per
        # request removed the per-contributor limit completely.
        keys = [generate_key() for _ in range(5)]
        codes = [self.signed_post(i, k) for i, k in enumerate(keys)]
        self.assertEqual(codes, [201, 201, 201, 429, 429])
        # a returning contributor is not affected by the newcomer budget
        self.assertEqual(self.signed_post(99, keys[0]), 201)


class RandomizedServerTest(_Server):
    """Property: for any mutated record, the server answers with a known status and
    valid JSON, never drops the connection, and stores only schema-valid records."""

    MUTATIONS = [None, True, False, 0, -1, 1.5, 2 ** 63, -(2 ** 63), 1e308, "", "x" * 300, "a\nb", "é",
                 [], {}, [1, 2], {"k": "v"}, "../../etc/passwd", "'; DROP TABLE records; --"]

    def _paths(self, obj, prefix=()):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield prefix + (k,)
                yield from self._paths(v, prefix + (k,))

    def test_random_mutations(self):
        rng = random.Random(SEED)
        paths = list(self._paths(EXAMPLE))
        stored = 0
        for i in range(60):
            r = record(1000 + i)
            for _ in range(rng.randint(1, 3)):
                path = rng.choice(paths)
                node = r
                for part in path[:-1]:
                    node = node.get(part, {}) if isinstance(node, dict) else {}
                if isinstance(node, dict):
                    if rng.random() < 0.1:
                        node.pop(path[-1], None)
                    else:
                        node[path[-1]] = rng.choice(self.MUTATIONS)
            status, body = self.post(json.dumps(r).encode())
            with self.subTest(i=i):
                self.assertIn(status, KNOWN_STATUSES, body[:200])
                json.loads(body)  # always valid JSON
                if status == 201:
                    stored += 1
                    self.assertEqual(self.store.validate(r), [])
        self.assertEqual(self.store.count(), stored)
        tables = {row[0] for row in self.store.raw_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("records", tables)  # the SQL-looking strings were data, not SQL

    def test_random_static_paths_never_escape_the_dashboard(self):
        rng = random.Random(SEED + 1)
        pieces = ["..", "%2e%2e", ".", "", "data", "index.html", "%00", "\\..", "//", "LICENSE",
                  "server", "README.md", "..%2f", "%2F", "~"]
        for _ in range(80):
            path = "/dashboard/" + "/".join(rng.choice(pieces) for _ in range(rng.randint(1, 5)))
            status, body = self.get(path.encode())
            with self.subTest(path=path):
                self.assertIn(status, {200, 301, 404})
                if status == 200:
                    self.assertNotIn(b"Apache License", body)  # repo-root LICENSE never served
                    self.assertNotIn(b"import ", body)  # no python sources


class TokenBucketPropertyTest(unittest.TestCase):
    def test_never_allows_more_than_burst_plus_refill(self):
        rng = random.Random(SEED + 2)
        for trial in range(20):
            per_hour, burst = rng.choice([60, 120, 3600]), rng.randint(1, 10)
            now = [0.0]
            b = TokenBucket(per_hour, burst, clock=lambda: now[0])
            allowed = 0
            for _ in range(200):
                now[0] += rng.expovariate(1 / 5.0)
                allowed += b.take("k")[0]
            with self.subTest(trial=trial):
                self.assertLessEqual(allowed, burst + now[0] * per_hour / 3600 + 1e-9)

    def test_clock_going_backwards_does_not_mint_tokens(self):
        now = [1000.0]
        b = TokenBucket(3600, 1, clock=lambda: now[0])
        self.assertTrue(b.take("k")[0])
        now[0] = 0.0  # e.g. a patched clock; monotonic() never does this, but be safe
        self.assertFalse(b.take("k")[0])
        now[0] = 1000.5
        self.assertFalse(b.take("k")[0])


if __name__ == "__main__":
    unittest.main()
