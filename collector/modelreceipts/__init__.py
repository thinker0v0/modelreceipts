"""ModelReceipts collector (pre-alpha).

Dry-run only: builds a task-run record from a Claude Code ``Stop`` hook payload
and prints it locally. Nothing is sent over the network in this version.
"""

from pathlib import Path

__version__ = "0.0.1"

SCHEMA_VERSION = "0.1.0"
TAXONOMY_VERSION = "t0.1"
CLASSIFIER_ID = "rules-v0"

# <repo>/collector/modelreceipts/__init__.py -> <repo>/schema/record.v0.1.schema.json
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "record.v0.1.schema.json"
