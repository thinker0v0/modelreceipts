"""Seed importers for ModelReceipts (pre-alpha).

Seeds are public, license-checked data that give the database something useful
on day one. Every seed record carries ``source.source_type`` != ``field_report``
so it never mixes with user-contributed evidence.

Excluded permanently (terms of use): Artificial Analysis data, LMSYS-Chat-1M.
"""

import sys
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SEEDS_DIR.parent
DATA_DIR = SEEDS_DIR / "data"

# Source checkout support: reuse the collector's validator without installing it.
_collector = str(REPO_ROOT / "collector")
if _collector not in sys.path:
    sys.path.append(_collector)

EXCLUDED_SOURCES = ("artificial-analysis", "lmsys-chat-1m")
