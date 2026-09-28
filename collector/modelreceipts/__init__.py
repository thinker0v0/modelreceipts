"""ModelReceipts collector (pre-alpha).

Builds a task-run record from a Claude Code ``Stop`` hook payload and previews
it locally. The ``hook`` command never sends anything. Sending is a separate,
explicit command (``submit --endpoint URL``) implemented only in ``submit.py``.
"""

from pathlib import Path

__version__ = "0.0.2"

SCHEMA_VERSION = "0.2.0"
TAXONOMY_VERSION = "t0.1"
CLASSIFIER_ID = "rules-v1"
RETRY_DETECTOR_ID = "retry-rules-v1"
CLAIM_EXTRACTOR_ID = "claim-rules-v1"

# Canonical schemas live in <repo>/schema/. The package ships byte-identical
# copies (modelreceipts/schemas/, checked by a test) for installs without the repo.
_REPO_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"
_PACKAGED_SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMA_DIR = _REPO_SCHEMA_DIR if (_REPO_SCHEMA_DIR / "record.v0.2.schema.json").is_file() else _PACKAGED_SCHEMA_DIR
SCHEMA_FILES = {
    ("record", "0.1.0"): "record.v0.1.schema.json",
    ("record", "0.2.0"): "record.v0.2.schema.json",
    ("seed_cell", "0.2.0"): "seed_cell.v0.2.schema.json",
}
DEFAULT_SCHEMA_PATH = SCHEMA_DIR / SCHEMA_FILES[("record", SCHEMA_VERSION)]
