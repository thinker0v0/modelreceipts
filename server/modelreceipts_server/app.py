"""HTTP API on ``http.server`` (stdlib). Loopback only.

Routes
  POST /v1/records      one schema-v0.1 record (JSON). 201 stored / 400 invalid / 409 duplicate / 413 too large
  GET  /v1/aggregates   per-cell stats with k/n thresholds; query: source_type, l1, l2, level=l1|l2
  GET  /healthz         liveness
  GET  /                redirect to the dashboard reading this server's aggregates
  GET  /dashboard/...   static files from dashboard/ (read-only)
Everything else answers 404/405. There is no update or delete route (append-only).

Privacy: request logs omit client addresses; the optional ``X-ModelReceipts-Install``
header (a random id the client generated) is only stored as a salted hash.
"""

from __future__ import annotations

import json
import mimetypes
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import DASHBOARD_DIR, LOOPBACK_HOSTS, __version__
from .aggregate import SOURCE_TYPES, Thresholds, aggregate
from .store import DuplicateRecord, InvalidRecord, Store

MAX_BODY = 64 * 1024
INSTALL_HEADER = "X-ModelReceipts-Install"


class NotLoopback(ValueError):
    pass


def make_handler(store: Store, thresholds: Thresholds, dashboard_dir: Path = DASHBOARD_DIR, quiet: bool = False):
    dashboard_root = dashboard_dir.resolve()

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

        def _error(self, status: int, code: str, details=None):
            obj = {"error": code}
            if details:
                obj["details"] = details
            self._json(status, obj)

        # -- routes --------------------------------------------------------
        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/healthz":
                return self._json(200, {"ok": True, "version": __version__, "schema_version": "0.1.0"})
            if url.path == "/v1/aggregates":
                return self._aggregates(parse_qs(url.query))
            if url.path == "/":
                return self._send(302, b"", "text/plain", {"Location": "/dashboard/?data=/v1/aggregates"})
            if url.path == "/dashboard":
                return self._send(301, b"", "text/plain", {"Location": "/dashboard/"})
            if url.path.startswith("/dashboard/"):
                return self._static(url.path[len("/dashboard/"):])
            return self._error(404, "not_found")

        do_HEAD = do_GET

        def do_POST(self):
            path = urlsplit(self.path).path
            if path in {"/v1/aggregates", "/healthz"}:
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
            if ctype != "application/json":
                self.rfile.read(length)
                return self._error(415, "unsupported_media_type", ["use Content-Type: application/json"])
            raw = self.rfile.read(length)
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return self._error(400, "invalid_json", [str(exc)])
            install_id = (self.headers.get(INSTALL_HEADER) or "").strip()[:128] or None
            try:
                store.add_field_report(record, install_id=install_id)
            except InvalidRecord as exc:
                return self._error(400, "schema_validation_failed", exc.errors[:20])
            except DuplicateRecord:
                return self._error(409, "duplicate_record_id", ["records are append-only; ids cannot be reused"])
            return self._json(201, {"status": "stored", "record_id": record["record_id"]})

        def _method_not_allowed(self):
            allow = "POST" if urlsplit(self.path).path == "/v1/records" else "GET, HEAD"
            self._send(405, b'{"error": "method_not_allowed"}\n', "application/json", {"Allow": allow})

        do_PUT = do_DELETE = do_PATCH = _method_not_allowed

        def _aggregates(self, query: dict):
            def one(name):
                vals = query.get(name)
                return vals[0] if vals else None
            source_type, level = one("source_type"), one("level") or "l2"
            if source_type and source_type not in SOURCE_TYPES:
                return self._error(400, "bad_query", [f"source_type must be one of {list(SOURCE_TYPES)}"])
            if level not in {"l1", "l2"}:
                return self._error(400, "bad_query", ["level must be l1 or l2"])
            result = aggregate(store.rows(), thresholds, level=level, source_type=source_type,
                               l1=one("l1"), l2=one("l2"), seed_sources=store.seed_sources())
            result["dataset"] = {
                "label": "LOCAL DEV SERVER — whatever this instance has ingested. Check `sources` and source_type before reading anything into it.",
                "synthetic_field_reports": None,
            }
            # Aggregates are the public layer, so browsers on other origins may read them.
            return self._json(200, result, {"Access-Control-Allow-Origin": "*"})

        def _static(self, rel: str):
            rel = rel or "index.html"
            target = (dashboard_root / rel).resolve()
            if not target.is_relative_to(dashboard_root) or not target.is_file():
                return self._error(404, "not_found")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in {"application/json", "application/javascript"}:
                ctype += "; charset=utf-8"
            return self._send(200, target.read_bytes(), ctype)

    return Handler


def make_server(store: Store, host: str = "127.0.0.1", port: int = 8787,
                thresholds: Thresholds | None = None, quiet: bool = False) -> ThreadingHTTPServer:
    if host not in LOOPBACK_HOSTS:
        raise NotLoopback(f"refusing to bind {host!r}: pre-alpha server is loopback-only ({sorted(LOOPBACK_HOSTS)})")
    handler = make_handler(store, thresholds or Thresholds(), quiet=quiet)
    if host == "::1":
        class V6Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6
        return V6Server((host, port), handler)
    return ThreadingHTTPServer(("127.0.0.1" if host == "localhost" else host, port), handler)
