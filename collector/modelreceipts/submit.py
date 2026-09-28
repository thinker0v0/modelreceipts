"""Explicit, opt-in submit — the ONLY module in the collector that may touch the network.

``python3 -m modelreceipts submit (--payload STOP.json | --record RECORD.json) [--endpoint URL]``

* Always builds (or loads) the record, validates it and prints the preview first.
* Without ``--endpoint`` it stops there: preview only, nothing is sent.
* With ``--endpoint`` it POSTs exactly that previewed JSON to ``<URL>/v1/records``.
* Pre-alpha safety: only loopback endpoints (127.0.0.1, ::1, localhost) are
  allowed unless ``--allow-non-loopback`` is also given. There is no public
  ModelReceipts server yet.
* Contributor counting (k-threshold) uses a local Ed25519 install key
  (``signing.py``): the request is signed and the server counts verified public
  keys (stored as a salted hash). ``--anonymous`` sends an unsigned request,
  which servers in the default ``--signatures required`` mode refuse. The key
  file is created only when actually sending.

``query`` (same module, because it uses the network) fetches the
contributor-only detailed aggregates with a signed GET.

The ``hook`` command never imports this module.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlsplit

from .signing import DEFAULT_KEY_FILE, InstallKey, load_or_create_key, sign_request
from .validate import load_validator

if TYPE_CHECKING:  # the hook path must not import network modules at runtime
    import urllib.request

PREVIEW_BANNER = "[modelreceipts] PREVIEW — this is exactly what would be sent:"


class SubmitError(Exception):
    pass


def is_loopback(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def records_url(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise SubmitError(f"endpoint must be an http(s) URL, got {endpoint!r}")
    base = endpoint.rstrip("/")
    return base if base.endswith("/v1/records") else base + "/v1/records"


def _open(req: urllib.request.Request, timeout: float, endpoint: str) -> tuple[int, dict]:
    import urllib.error
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        # Following a 30x would re-send the signed headers to a host that was never
        # checked against the loopback rule. A redirect is reported as its status.
        def redirect_request(self, *args, **kwargs) -> None:
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            detail = json.loads(err.read() or b"{}")
        except ValueError:
            detail = {}
        return err.code, detail
    except (urllib.error.URLError, OSError) as exc:
        raise SubmitError(f"could not reach {endpoint}: {exc}") from None


def send(record: dict, endpoint: str, key: InstallKey | None, timeout: float = 10.0) -> tuple[int, dict]:
    import urllib.request

    url = records_url(endpoint)
    body = json.dumps(record, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "modelreceipts-collector"}
    if key is not None:
        headers.update(sign_request(key, "POST", urlsplit(url).path, body))
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return _open(req, timeout, endpoint)


def fetch_detail(endpoint: str, key: InstallKey, params: dict, timeout: float = 10.0) -> tuple[int, dict]:
    import urllib.request

    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise SubmitError(f"endpoint must be an http(s) URL, got {endpoint!r}")
    query = urlencode({k: v for k, v in params.items() if v})
    path = "/v1/aggregates/detail" + (f"?{query}" if query else "")
    headers = {"User-Agent": "modelreceipts-collector", **sign_request(key, "GET", path)}
    req = urllib.request.Request(endpoint.rstrip("/") + path, headers=headers, method="GET")
    return _open(req, timeout, endpoint)


def _load_record(args: argparse.Namespace) -> dict:
    if args.record:
        return json.loads(args.record.read_text(encoding="utf-8"))
    from .hook import run
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    record, _errors = run(payload)
    return record


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="modelreceipts submit",
        description="Preview a record and, only if --endpoint is given, send it (opt-in).",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--payload", type=Path, help="Claude Code Stop-hook payload JSON (record is built locally)")
    src.add_argument("--record", type=Path, help="an existing record JSON (e.g. from hook --preview-dir)")
    parser.add_argument("--endpoint", help="server base URL, e.g. http://127.0.0.1:8787 — without it nothing is sent")
    parser.add_argument("--allow-non-loopback", action="store_true", help="permit endpoints other than 127.0.0.1/::1/localhost")
    ident = parser.add_mutually_exclusive_group()
    ident.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE,
                       help=f"local Ed25519 install key, created on first send (default {DEFAULT_KEY_FILE})")
    ident.add_argument("--anonymous", action="store_true",
                       help="send unsigned (servers requiring signatures refuse it; otherwise counts as one shared contributor)")
    args = parser.parse_args(argv)

    try:
        record = _load_record(args)
    except (OSError, ValueError) as exc:
        print(f"[modelreceipts] cannot build record: {exc}", file=sys.stderr)
        return 2

    errors = load_validator().errors(record)
    print(PREVIEW_BANNER, file=sys.stderr)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if errors:
        print("[modelreceipts] record failed schema validation — not sending:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if not args.endpoint:
        print("[modelreceipts] not sent: no --endpoint given (preview only).", file=sys.stderr)
        return 0

    try:
        url = records_url(args.endpoint)
        if not args.allow_non_loopback and not is_loopback(url):
            raise SubmitError(f"refusing non-loopback endpoint {args.endpoint!r} (pre-alpha); "
                              "pass --allow-non-loopback if you really mean it")
        key = None if args.anonymous else load_or_create_key(args.key_file)
        status, reply = send(record, url, key)
    except (SubmitError, OSError, ValueError) as exc:
        print(f"[modelreceipts] not sent: {exc}", file=sys.stderr)
        return 2
    print(f"[modelreceipts] POST {url} -> {status} {json.dumps(reply, ensure_ascii=False)}", file=sys.stderr)
    return 0 if status == 201 else 1


def query_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="modelreceipts query",
        description="Fetch the contributor-only detailed aggregates (signed GET /v1/aggregates/detail).")
    parser.add_argument("--endpoint", required=True, help="server base URL, e.g. http://127.0.0.1:8787")
    parser.add_argument("--allow-non-loopback", action="store_true")
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE,
                        help="the install key you contributed with (must already exist)")
    for name in ("source-type", "l1", "l2", "level"):
        parser.add_argument(f"--{name}")
    args = parser.parse_args(argv)
    if not args.allow_non_loopback and not is_loopback(args.endpoint):
        print(f"[modelreceipts] refusing non-loopback endpoint {args.endpoint!r}", file=sys.stderr)
        return 2
    if not args.key_file.exists():
        print(f"[modelreceipts] no install key at {args.key_file}; contribute a record first", file=sys.stderr)
        return 2
    from .signing import load_key
    try:
        status, reply = fetch_detail(args.endpoint, load_key(args.key_file),
                                     {"source_type": args.source_type, "l1": args.l1, "l2": args.l2, "level": args.level})
    except (SubmitError, OSError, ValueError) as exc:
        print(f"[modelreceipts] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(reply, ensure_ascii=False, indent=2))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
