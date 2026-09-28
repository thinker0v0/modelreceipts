"""HTTP API on ``http.server`` (stdlib). Loopback only.

Routes
  POST /v1/records            one record (schema v0.1 or v0.2), Ed25519-signed.
                              201 stored / 400 invalid / 401 signature / 409 duplicate / 413 / 429 rate limit
  GET  /v1/overview           PUBLIC overview (field reports at L1 x model, seeds as published)
  GET  /v1/aggregates         alias of /v1/overview (kept for older dashboards)
  GET  /v1/aggregates/detail  CONTRIBUTORS ONLY when the gate is on: signed GET from a key with a field
                              report in the last 90 days. Query: source_type, l1, l2, level=l1|l2
  GET  /healthz               liveness
  GET  /                      redirect to the dashboard reading /v1/overview
  GET  /dashboard/...         static files from dashboard/ (read-only)
Everything else answers 404/405. There is no update or delete route (append-only).

Signatures (``modelreceipts.signing``): with ``signatures="required"`` (default for
``serve``) unsigned POSTs are refused with 401. With ``"optional"`` they are
accepted and identified by the legacy ``X-ModelReceipts-Install`` header (salted
hash) or as the shared anonymous contributor.

Privacy: request logs omit client addresses and headers; keys and install ids are
stored only as salted hashes.
"""

from __future__ import annotations

import json
import mimetypes
import socket
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from modelreceipts.signing import SignatureError, has_signature, verify_request

from . import DASHBOARD_DIR, LOOPBACK_HOSTS, __version__
from .aggregate import SOURCE_TYPES, Thresholds, aggregate, overview
from .ratelimit import RateLimits, TokenBucket
from .store import DuplicateRecord, InvalidRecord, Store, cell_key

MAX_BODY = 64 * 1024
INSTALL_HEADER = "X-ModelReceipts-Install"
GATE_DAYS = 90


class NotLoopback(ValueError):
    pass


@dataclass
class Policy:
    signatures: str = "required"  # "required" | "optional"
    gate: bool = True  # detailed view only for recent contributors
    limits: RateLimits = field(default_factory=RateLimits)

    def __post_init__(self):
        if self.signatures not in {"required", "optional"}:
            raise ValueError("signatures must be 'required' or 'optional'")


def make_handler(store: Store, thresholds: Thresholds, policy: Policy | None = None,
                 dashboard_dir: Path = DASHBOARD_DIR, quiet: bool = False):
    dashboard_root = dashboard_dir.resolve()
    policy = policy or Policy()
    bucket = TokenBucket(policy.limits.per_hour, policy.limits.burst)

    class Handler(BaseHTTPRequestHandler):
        server_version = f"ModelReceipts/{__version__}"
        sys_version = ""
        protocol_version = "HTTP/1.1"
        timeout = 15

        # -- helpers -------------------------------------------------------
        def log_message(self, fmt, *args):  # no client address in logs
            if not quiet:
                print(f"[modelreceipts-server] {self.command} {urlsplit(self.path).path} -> {args[1] if len(args) > 1 else ''}", flush=True)

        def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, obj, extra: dict | None = None):
            body = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8", extra)

        def _error(self, status: int, code: str, details=None, extra: dict | None = None):
            obj = {"error": code}
            if details:
                obj["details"] = details
            self._json(status, obj, extra)

        # -- routes --------------------------------------------------------
        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/healthz":
                return self._json(200, {"ok": True, "version": __version__, "schema_versions": ["0.1.0", "0.2.0"],
                                        "signatures": policy.signatures, "gate": policy.gate})
            if url.path in {"/v1/overview", "/v1/aggregates"}:
                result = overview(store.rows(), thresholds, seed_sources=store.seed_sources(),
                                  seed_cells=store.seed_cell_rows())
                result["dataset"] = _dev_label()
                # The overview is the public layer, so browsers on other origins may read it.
                return self._json(200, result, {"Access-Control-Allow-Origin": "*"})
            if url.path == "/v1/aggregates/detail":
                return self._detail(url)
            if url.path == "/":
                return self._send(302, b"", "text/plain", {"Location": "/dashboard/?data=/v1/overview"})
            if url.path == "/dashboard":
                return self._send(301, b"", "text/plain", {"Location": "/dashboard/"})
            if url.path.startswith("/dashboard/"):
                return self._static(url.path[len("/dashboard/"):])
            return self._error(404, "not_found")

        do_HEAD = do_GET

        def do_POST(self):
            path = urlsplit(self.path).path
            if path in {"/v1/aggregates", "/v1/aggregates/detail", "/v1/overview", "/healthz"}:
                return self._method_not_allowed()
            if path != "/v1/records":
                return self._error(404, "not_found")
            if self.headers.get("Transfer-Encoding"):
                return self._error(411, "content_length_required")
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._error(411, "content_length_required")
            if length > MAX_BODY:
                self.close_connection = True
                return self._error(413, "payload_too_large", [f"max {MAX_BODY} bytes"])
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            raw = self.rfile.read(length)
            if ctype != "application/json":
                return self._error(415, "unsupported_media_type", ["use Content-Type: application/json"])

            # 1) identity: verified install key, or (optional mode) legacy id / anonymous
            verified = False
            if has_signature(self.headers):
                try:
                    public = verify_request(self.headers, "POST", path, raw)
                except SignatureError as exc:
                    return self._error(401, "bad_signature", [str(exc)])
                contributor, verified = store.contributor_key(public_key=public), True
            elif policy.signatures == "required":
                return self._error(401, "signature_required",
                                   ["sign the request with your install key (modelreceipts submit does this)"])
            else:
                install_id = (self.headers.get(INSTALL_HEADER) or "").strip()[:128] or None
                contributor = store.contributor_key(install_id)

            # 2) per-contributor rate limit (before any parsing work)
            allowed, retry_after = bucket.take(contributor)
            if not allowed:
                return self._error(429, "rate_limited", [f"retry after {retry_after}s"], {"Retry-After": str(retry_after)})

            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return self._error(400, "invalid_json", [str(exc)])
            errors = store.validate(record)
            if errors:
                return self._error(400, "schema_validation_failed", errors[:20])

            # 3) per-contributor, per-cell daily cap
            if store.count_in_cell_since(contributor, cell_key(record)) >= policy.limits.cell_daily_cap:
                return self._error(429, "cell_daily_cap",
                                   [f"at most {policy.limits.cell_daily_cap} records per cell per contributor per 24h"],
                                   {"Retry-After": "3600"})
            try:
                store.add_field_report(record, contributor=contributor, key_verified=verified)
            except InvalidRecord as exc:
                return self._error(400, "schema_validation_failed", exc.errors[:20])
            except DuplicateRecord:
                return self._error(409, "duplicate_record_id", ["records are append-only; ids cannot be reused"])
            cost = store.server_cost(record["record_id"])
            return self._json(201, {"status": "stored", "record_id": record["record_id"],
                                    "signed": verified, "server_cost": cost})

        def _method_not_allowed(self):
            allow = "POST" if urlsplit(self.path).path == "/v1/records" else "GET, HEAD"
            self._send(405, b'{"error": "method_not_allowed"}\n', "application/json", {"Allow": allow})

        do_PUT = do_DELETE = do_PATCH = _method_not_allowed

        def _detail(self, url):
            if policy.gate:
                path_q = url.path + (f"?{url.query}" if url.query else "")
                try:
                    public = verify_request(self.headers, "GET", path_q, b"")
                except SignatureError as exc:
                    return self._error(401, "contributors_only",
                                       [str(exc), "public data: GET /v1/overview",
                                        "contributors: modelreceipts query --endpoint URL"])
                if not store.has_recent_contribution(store.contributor_key(public_key=public), GATE_DAYS):
                    return self._error(403, "contributors_only",
                                       [f"this key has no field report in the last {GATE_DAYS} days"])
            query = parse_qs(url.query)

            def one(name):
                vals = query.get(name)
                return vals[0] if vals else None
            source_type, level = one("source_type"), one("level") or "l2"
            if source_type and source_type not in SOURCE_TYPES:
                return self._error(400, "bad_query", [f"source_type must be one of {list(SOURCE_TYPES)}"])
            if level not in {"l1", "l2"}:
                return self._error(400, "bad_query", ["level must be l1 or l2"])
            result = aggregate(store.rows(), thresholds, level=level, source_type=source_type,
                               l1=one("l1"), l2=one("l2"), seed_sources=store.seed_sources(),
                               seed_cells=store.seed_cell_rows(), prices=store.prices.describe())
            result["dataset"] = _dev_label()
            result["gate"] = {"enabled": policy.gate, "window_days": GATE_DAYS}
            return self._json(200, result)

        def _static(self, rel: str):
            rel = rel or "index.html"
            target = (dashboard_root / rel).resolve()
            if not target.is_relative_to(dashboard_root) or not target.is_file():
                return self._error(404, "not_found")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in {"application/json", "application/javascript", "image/svg+xml"}:
                ctype += "; charset=utf-8"
            return self._send(200, target.read_bytes(), ctype)

    return Handler


def _dev_label() -> dict:
    return {"label": "LOCAL SERVER — whatever this instance has ingested. Check `sources` and source_type "
                     "before reading anything into it.",
            "synthetic_field_reports": None}


def make_server(store: Store, host: str = "127.0.0.1", port: int = 8787, thresholds: Thresholds | None = None,
                quiet: bool = False, policy: Policy | None = None) -> ThreadingHTTPServer:
    if host not in LOOPBACK_HOSTS:
        raise NotLoopback(f"refusing to bind {host!r}: this server is loopback-only ({sorted(LOOPBACK_HOSTS)}); "
                          "put a TLS-terminating reverse proxy in front of it for a real deployment")
    handler = make_handler(store, thresholds or Thresholds(), policy, quiet=quiet)
    if host == "::1":
        class V6Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6
        return V6Server((host, port), handler)
    return ThreadingHTTPServer(("127.0.0.1" if host == "localhost" else host, port), handler)
