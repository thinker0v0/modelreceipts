"""Explicit, opt-in submit — the ONLY module in the collector that may touch the network.

``python3 -m modelreceipts submit (--payload STOP.json | --record RECORD.json) [--endpoint URL]``

* Always builds (or loads) the record, validates it and prints the preview first.
* Without ``--endpoint`` it stops there: preview only, nothing is sent.
* With ``--endpoint`` it POSTs exactly that previewed JSON to ``<URL>/v1/records``.
* Pre-alpha safety: only loopback endpoints (127.0.0.1, ::1, localhost) are
  allowed unless ``--allow-non-loopback`` is also given. There is no public
  ModelReceipts server yet.
* Contributor counting (k-threshold) uses a random install id kept in a local
  file and sent as ``X-ModelReceipts-Install``; the server stores only a salted
  hash. ``--anonymous`` sends none. The file is created only when actually sending.

The ``hook`` command never imports this module.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .validate import load_validator

DEFAULT_INSTALL_ID_FILE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "modelreceipts" / "install_id"
INSTALL_HEADER = "X-ModelReceipts-Install"
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


def load_install_id(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    except OSError:
        pass
    value = str(uuid.uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value


def send(record: dict, endpoint: str, install_id: str | None, timeout: float = 10.0) -> tuple[int, dict]:
    import urllib.error
    import urllib.request

    body = json.dumps(record, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "modelreceipts-collector"}
    if install_id:
        headers[INSTALL_HEADER] = install_id
    req = urllib.request.Request(records_url(endpoint), data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        try:
            detail = json.loads(err.read() or b"{}")
        except ValueError:
            detail = {}
        return err.code, detail
    except (urllib.error.URLError, OSError) as exc:
        raise SubmitError(f"could not reach {endpoint}: {exc}") from None


def _load_record(args) -> dict:
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
    ident.add_argument("--install-id-file", type=Path, default=DEFAULT_INSTALL_ID_FILE,
                       help=f"random install id used for contributor counting (default {DEFAULT_INSTALL_ID_FILE})")
    ident.add_argument("--anonymous", action="store_true", help="send no install id (counts as the shared 'anonymous' contributor)")
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
        install_id = None if args.anonymous else load_install_id(args.install_id_file)
        status, reply = send(record, url, install_id)
    except SubmitError as exc:
        print(f"[modelreceipts] not sent: {exc}", file=sys.stderr)
        return 2
    print(f"[modelreceipts] POST {url} -> {status} {json.dumps(reply, ensure_ascii=False)}", file=sys.stderr)
    return 0 if status == 201 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
