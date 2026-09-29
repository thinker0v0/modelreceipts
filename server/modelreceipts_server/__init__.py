"""ModelReceipts ingest server (pre-alpha, localhost only).

Python standard library only: ``http.server`` + ``sqlite3``. It reuses the
collector's schema validator so client and server can never disagree on what
a valid v0.1 record is.
"""

import sys
from pathlib import Path

__version__ = "1.0.0rc3"

SERVER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_DIR.parent
DASHBOARD_DIR = REPO_ROOT / "dashboard"

# Source-checkout support: make the sibling collector/ and seeds/ packages importable.
for _sub in ("collector", "seeds"):
    _p = str(REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
