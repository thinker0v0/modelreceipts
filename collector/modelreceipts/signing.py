"""Install keys and signed requests (anti-Sybil), shared by collector and server.

Each installation generates an Ed25519 key pair LOCALLY on first send
(``~/.local/state/modelreceipts/install_key``, mode 0600). The secret never
leaves the machine and never belongs in a repository (.gitignore covers
``install_key*``). The server identifies a contributor by a salted hash of the
PUBLIC key, so k (distinct contributors) counts keys that proved possession.

A request is signed as::

    X-ModelReceipts-Key:        base64url(public key, 32 bytes)
    X-ModelReceipts-Timestamp:  unix seconds
    X-ModelReceipts-Signature:  base64url(Ed25519(secret, message))

    message = "modelreceipts-v1\\n" METHOD "\\n" PATH_AND_QUERY "\\n" TIMESTAMP "\\n" sha256hex(body)

The server rejects timestamps more than ``MAX_SKEW_S`` away from its clock.
Replaying a signed POST cannot add a second record: record ids are unique.

Honest limit: keys are free to generate, so signatures raise the cost of fake
contributors (every fake needs its own key, rate limit and per-cell cap) but
do not prove a real person. See the feasibility report, risk #3.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from . import ed25519

PROTOCOL = "modelreceipts-v1"
KEY_HEADER = "X-ModelReceipts-Key"
TS_HEADER = "X-ModelReceipts-Timestamp"
SIG_HEADER = "X-ModelReceipts-Signature"
MAX_SKEW_S = 300
DEFAULT_KEY_FILE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "modelreceipts" / "install_key"


class SignatureError(ValueError):
    pass


def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64d(text: str) -> bytes:
    text = text.strip()
    if len(text) > 200:
        raise ValueError("too long")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class InstallKey:
    secret: bytes
    public: bytes

    @property
    def public_b64(self) -> str:
        return b64e(self.public)


def generate_key() -> InstallKey:
    secret = ed25519.generate_secret()
    return InstallKey(secret, ed25519.public_key(secret))


def save_key(key: InstallKey, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # never overwrite an existing key
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"format": "modelreceipts-install-key-v1", "alg": "Ed25519",
                   "secret": b64e(key.secret), "public": key.public_b64}, fh)
        fh.write("\n")


def load_key(path: Path) -> InstallKey:
    data = json.loads(path.read_text(encoding="utf-8"))
    secret = b64d(data["secret"])
    key = InstallKey(secret, ed25519.public_key(secret))
    if data.get("public") and b64d(data["public"]) != key.public:
        raise SignatureError(f"{path}: public key does not match the secret")
    return key


def load_or_create_key(path: Path) -> InstallKey:
    if path.exists():
        return load_key(path)
    key = generate_key()
    save_key(key, path)
    return key


def message(method: str, path_and_query: str, timestamp: str, body: bytes) -> bytes:
    return "\n".join([PROTOCOL, method.upper(), path_and_query, timestamp,
                      hashlib.sha256(body).hexdigest()]).encode("utf-8")


def sign_request(key: InstallKey, method: str, path_and_query: str, body: bytes = b"",
                 now: float | None = None) -> dict[str, str]:
    ts = str(int(now if now is not None else time.time()))
    sig = ed25519.sign(key.secret, message(method, path_and_query, ts, body))
    return {KEY_HEADER: key.public_b64, TS_HEADER: ts, SIG_HEADER: b64e(sig)}


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive lookup (HTTP header names are case-insensitive; urllib re-cases them)."""
    value = headers.get(name)
    if value is None:
        lowered = name.lower()
        value = next((v for k, v in headers.items() if k.lower() == lowered), None)
    return value


def has_signature(headers: Mapping[str, str]) -> bool:
    return any(_header(headers, h) for h in (KEY_HEADER, TS_HEADER, SIG_HEADER))


def verify_request(headers: Mapping[str, str], method: str, path_and_query: str, body: bytes = b"",
                   now: float | None = None, max_skew: int = MAX_SKEW_S) -> bytes:
    """Return the verified public key, or raise SignatureError."""
    try:
        public = b64d(_header(headers, KEY_HEADER) or "")
        sig = b64d(_header(headers, SIG_HEADER) or "")
        ts = (_header(headers, TS_HEADER) or "").strip()
        ts_int = int(ts)
    except (ValueError, TypeError):
        raise SignatureError("malformed signature headers") from None
    if len(public) != 32 or len(sig) != 64:
        raise SignatureError("malformed key or signature")
    current = now if now is not None else time.time()
    if abs(current - ts_int) > max_skew:
        raise SignatureError("timestamp outside the allowed window")
    if not ed25519.verify(public, message(method, path_and_query, ts, body), sig):
        raise SignatureError("bad signature")
    return public
