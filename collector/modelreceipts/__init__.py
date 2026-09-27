"""ModelReceipts collector (pre-alpha).

Builds a task-run record from a Claude Code ``Stop`` hook payload and previews
it locally. The ``hook`` command never sends anything. Sending is a separate,
explicit command (``submit --endpoint URL``) implemented only in ``submit.py``.
"""

from pathlib import Path

__version__ = "0.0.2"

SCHEMA_VERSION = "0.1.0"
TAXONOMY_VERSION = "t0.1"
CLASSIFIER_ID = "rules-v0"

# <repo>/collector/modelreceipts/__init__.py -> <repo>/schema/record.v0.1.schema.json
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "record.v0.1.schema.json"
