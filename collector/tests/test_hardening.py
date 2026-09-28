"""v1.0.0rc2 self-review: regression tests for the validator, signature
verification and the submit client, plus randomized checks with a FIXED seed.
All inputs are SYNTHETIC. Run from repo root:

    python3 -m unittest discover -s collector/tests
"""

from __future__ import annotations

import copy
import json
import random
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

COLLECTOR = Path(__file__).resolve().parents[1]
REPO = COLLECTOR.parent
sys.path.insert(0, str(COLLECTOR))

from modelreceipts import ed25519  # noqa: E402
from modelreceipts.signing import (KEY_HEADER, SIG_HEADER, TS_HEADER, SignatureError, b64d, b64e,  # noqa: E402
                                   generate_key, sign_request, verify_request)
from modelreceipts.submit import fetch_detail, send  # noqa: E402
from modelreceipts.validate import load_validator  # noqa: E402

EXAMPLE = json.loads((REPO / "schema" / "examples" / "01-stop-hook-bugfix-tests-passed.json").read_text(encoding="utf-8"))
SEED = 20260928
NOW = 1_790_000_000


class ValidatorEdgeTest(unittest.TestCase):
    def setUp(self):
        self.v = load_validator()

    def mutate(self, section, key, value) -> list[str]:
        r = copy.deepcopy(EXAMPLE)
        r[section][key] = value
        return self.v.errors(r)

    def test_pattern_dollar_does_not_accept_a_trailing_newline(self):
        # Bug (rc1): patterns were applied with re.search, where `$` also matches
        # before a final "\n"; JSON Schema (ECMA-262) `$` means end of input.
        self.assertTrue(self.mutate("model", "id", "example-model-a\n"))
        self.assertTrue(self.mutate("method", "harness", "claude-code\n"))
        self.assertEqual(self.mutate("model", "id", "example-model-a"), [])

    def test_non_finite_numbers_are_rejected(self):
        # Bug (rc1): NaN/Infinity passed as "number" (JSON cannot represent them).
        for value in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=value):
                self.assertTrue(self.mutate("usage", "cost_usd_client", value))

    def test_integers_outside_the_interoperable_range_are_rejected(self):
        # Bug (rc1): 10**30 passed "integer" and later overflowed SQLite INTEGER.
        self.assertTrue(self.mutate("usage", "latency_ms", 10 ** 30))
        self.assertTrue(self.mutate("usage", "input_tokens", 2 ** 53))
        self.assertEqual(self.mutate("usage", "input_tokens", 2 ** 53 - 1), [])

    def test_error_messages_truncate_echoed_values(self):
        errors = self.mutate("model", "id", "y" * 5000)
        self.assertTrue(errors)
        self.assertLess(max(len(e) for e in errors), 400)

    def test_random_strings_never_smuggle_text_into_constrained_fields(self):
        # Property: every string field is enum/pattern constrained, so free text with
        # spaces or newlines (what a prompt would look like) is always rejected.
        rng = random.Random(SEED)
        fields = [("model", "id"), ("method", "harness"), ("task", "l2"), ("task", "classifier"),
                  ("source", "client_version"), ("model", "effort")]
        alphabet = "abcXYZ019 ._-:/@\n\t\"'é한"
        for _ in range(300):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(2, 40)))
            if not any(c in text for c in " \n\t\"'é한"):
                continue
            section, key = rng.choice(fields)
            with self.subTest(field=f"{section}.{key}", text=text):
                self.assertTrue(self.mutate(section, key, text))


def _small_order_points() -> list[bytes]:
    """Encodings of the low-order points with y in {0, 1, p-1} (orders 1, 2 and 4)."""
    found = []
    for y in (0, 1, 2 ** 255 - 20):
        for sign in (0, 1):
            enc = int.to_bytes(y | (sign << 255), 32, "little")
            P = ed25519._decompress(enc)
            if P is not None and ed25519._equal(ed25519._mul(8, P), (0, 1, 1, 0)):
                found.append(enc)
    return sorted(set(found))


class SignatureEdgeTest(unittest.TestCase):
    def test_small_order_public_key_cannot_verify(self):
        # Bug (rc1): the identity point is a valid encoding; with R = identity and
        # s = 0 the equation holds for EVERY message, so a "verified" contributor
        # needed no secret key at all.
        identity = int.to_bytes(1, 32, "little")
        forged = identity + bytes(32)
        self.assertFalse(ed25519.verify(identity, b"any message", forged))
        headers = {KEY_HEADER: b64e(identity), TS_HEADER: str(NOW), SIG_HEADER: b64e(forged)}
        with self.assertRaises(SignatureError):
            verify_request(headers, "POST", "/v1/records", b"{}", now=NOW)
        for enc in _small_order_points():
            with self.subTest(point=enc.hex()):
                self.assertFalse(ed25519.verify(enc, b"m", ed25519._compress((0, 1, 1, 0)) + bytes(32)))

    def test_random_tampering_is_always_rejected(self):
        rng = random.Random(SEED + 1)
        key = generate_key()
        body = b'{"synthetic": true}'
        good = sign_request(key, "POST", "/v1/records", body, now=NOW)
        self.assertEqual(verify_request(good, "POST", "/v1/records", body, now=NOW), key.public)
        for i in range(12):
            h = dict(good)
            which = rng.choice(["sig", "key", "body", "path", "ts"])
            b, path = body, "/v1/records"
            if which == "sig":
                raw = bytearray(b64d(h[SIG_HEADER]))
                raw[rng.randrange(64)] ^= 1 << rng.randrange(8)
                h[SIG_HEADER] = b64e(bytes(raw))
            elif which == "key":
                raw = bytearray(key.public)
                raw[rng.randrange(32)] ^= 1 << rng.randrange(8)
                h[KEY_HEADER] = b64e(bytes(raw))
            elif which == "body":
                b = body + b" "
            elif which == "path":
                path = "/v1/records?x=1"
            else:
                h[TS_HEADER] = str(NOW + rng.choice([1, -1]))
            with self.subTest(i=i, which=which), self.assertRaises(SignatureError):
                verify_request(h, "POST", path, b, now=NOW)

    def test_clock_skew_window_edges(self):
        key = generate_key()
        for delta, ok in ((300, True), (-300, True), (301, False), (-301, False)):
            h = sign_request(key, "GET", "/p", now=NOW + delta)
            with self.subTest(delta=delta):
                if ok:
                    verify_request(h, "GET", "/p", now=NOW)
                else:
                    with self.assertRaises(SignatureError):
                        verify_request(h, "GET", "/p", now=NOW)

    def test_malformed_headers_are_signature_errors(self):
        key = generate_key()
        good = sign_request(key, "GET", "/p", now=NOW)
        cases = {
            "huge ts": {TS_HEADER: "9" * 5000},
            "float ts": {TS_HEADER: "1.79e9"},
            "non-ascii key": {KEY_HEADER: "키"},
            "long sig": {SIG_HEADER: "A" * 500},
            "short key": {KEY_HEADER: b64e(b"\x01" * 31)},
            "empty": {KEY_HEADER: "", SIG_HEADER: "", TS_HEADER: ""},
        }
        for name, override in cases.items():
            with self.subTest(case=name), self.assertRaises(SignatureError):
                verify_request({**good, **override}, "GET", "/p", now=NOW)


class _Recorder(BaseHTTPRequestHandler):
    hits: list = []

    def log_message(self, *a):
        pass

    def _any(self):
        type(self).hits.append((self.command, self.path, dict(self.headers)))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    do_GET = do_POST = _any


class RedirectTest(unittest.TestCase):
    def setUp(self):
        _Recorder.hits = []
        self.target = HTTPServer(("127.0.0.1", 0), _Recorder)
        target_url = f"http://127.0.0.1:{self.target.server_address[1]}/elsewhere"

        class Redirector(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _redirect(self):
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                self.send_response(302)
                self.send_header("Location", target_url)
                self.send_header("Content-Length", "0")
                self.end_headers()

            do_GET = do_POST = _redirect

        self.redirector = HTTPServer(("127.0.0.1", 0), Redirector)
        for srv in (self.target, self.redirector):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.endpoint = f"http://127.0.0.1:{self.redirector.server_address[1]}"

    def tearDown(self):
        for srv in (self.target, self.redirector):
            srv.shutdown()
            srv.server_close()

    def test_submit_and_query_do_not_follow_redirects(self):
        # Bug (rc1): urllib followed 30x, so the loopback-only check applied to the
        # first hop only and the signed headers were forwarded to the new location.
        status, _ = send(EXAMPLE, self.endpoint, generate_key())
        self.assertEqual(status, 302)
        status, _ = fetch_detail(self.endpoint, generate_key(), {})
        self.assertEqual(status, 302)
        self.assertEqual(_Recorder.hits, [])


if __name__ == "__main__":
    unittest.main()
