"""Append-only SQLite store for schema v0.1 records.

* ``records`` and ``seed_sources`` reject UPDATE and DELETE with triggers, so
  "append-only" holds even for code (or people) holding a raw connection.
* A duplicate ``record_id`` is refused (``DuplicateRecord``), never overwritten.
* Contributors are stored as a salted SHA-256 of the client's random install id.
  The salt lives in the database and never leaves it. Records without an
  install id all count as ONE contributor ("anonymous"), so they cannot inflate k.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from modelreceipts.validate import load_validator

ANONYMOUS = "anonymous"

DDL = """
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seed_sources (
  source_id    TEXT PRIMARY KEY,
  source_type  TEXT NOT NULL,
  name         TEXT NOT NULL,
  url          TEXT NOT NULL,
  commit_sha   TEXT,
  commit_date  TEXT,
  sha256       TEXT,
  license      TEXT NOT NULL,
  license_note TEXT,
  imported_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS records (
  seq              INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id        TEXT NOT NULL UNIQUE,
  received_at      TEXT NOT NULL,
  source_type      TEXT NOT NULL,
  contributor      TEXT NOT NULL,
  seed_source_id   TEXT REFERENCES seed_sources(source_id),
  l1               TEXT NOT NULL,
  l2               TEXT,
  model_id         TEXT NOT NULL,
  harness          TEXT NOT NULL,
  tests_passed     INTEGER,
  committed        INTEGER NOT NULL,
  tool_error_count INTEGER NOT NULL,
  cost_usd_client  REAL,
  cost_usd_server  REAL,
  latency_ms       INTEGER,
  self_score       REAL,
  body             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS records_cell ON records (source_type, l1, l2, model_id, harness);
CREATE TRIGGER IF NOT EXISTS records_no_update BEFORE UPDATE ON records
  BEGIN SELECT RAISE(ABORT, 'records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS records_no_delete BEFORE DELETE ON records
  BEGIN SELECT RAISE(ABORT, 'records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS seed_sources_no_update BEFORE UPDATE ON seed_sources
  BEGIN SELECT RAISE(ABORT, 'seed sources are append-only'); END;
CREATE TRIGGER IF NOT EXISTS seed_sources_no_delete BEFORE DELETE ON seed_sources
  BEGIN SELECT RAISE(ABORT, 'seed sources are append-only'); END;
"""

COLUMNS = ("record_id", "received_at", "source_type", "contributor", "seed_source_id", "l1", "l2",
           "model_id", "harness", "tests_passed", "committed", "tool_error_count",
           "cost_usd_client", "cost_usd_server", "latency_ms", "self_score", "body")


class InvalidRecord(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("record failed schema validation")
        self.errors = errors


class DuplicateRecord(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bool(v):
    return None if v is None else int(bool(v))


def _row(record: dict, contributor: str, seed_source_id: str | None, received_at: str) -> tuple:
    ev = record["outcome"]["evidence"]
    sa = record["outcome"].get("self_assessment")
    usage = record["usage"]
    return (
        record["record_id"], received_at, record["source"]["source_type"], contributor, seed_source_id,
        record["task"]["l1"], record["task"]["l2"], record["model"]["id"], record["method"]["harness"],
        _bool(ev["tests_passed"]), _bool(ev["committed"]), ev["tool_error_count"],
        usage["cost_usd_client"], usage["cost_usd_server"], usage["latency_ms"],
        sa["score"] if isinstance(sa, dict) else None,
        json.dumps(record, separators=(",", ":"), sort_keys=True),
    )


class Store:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript(DDL)
        self._validator = load_validator()
        with self._db:
            self._db.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('contributor_salt', ?)",
                             (secrets.token_hex(16),))
        self._salt = self._db.execute("SELECT value FROM meta WHERE key = 'contributor_salt'").fetchone()[0]

    # ---- identity -------------------------------------------------------
    def contributor_key(self, install_id: str | None) -> str:
        if not install_id:
            return ANONYMOUS
        digest = hashlib.sha256(f"{self._salt}:{install_id}".encode("utf-8")).hexdigest()
        return "c:" + digest[:24]

    # ---- writes ---------------------------------------------------------
    def validate(self, record) -> list[str]:
        if not isinstance(record, dict):
            return ["$: expected a JSON object"]
        return self._validator.errors(record)

    def add_field_report(self, record: dict, install_id: str | None = None) -> None:
        """Validate and append one user record. Raises InvalidRecord / DuplicateRecord."""
        errors = self.validate(record)
        if errors:
            raise InvalidRecord(errors)
        if record["source"]["source_type"] != "field_report":
            raise InvalidRecord(["$.source.source_type: only 'field_report' is accepted over HTTP; "
                                 "seed layers are imported locally by the operator"])
        row = _row(record, self.contributor_key(install_id), None, _now())
        with self._lock:
            try:
                with self._db:
                    self._db.execute(f"INSERT INTO records ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})", row)
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc):
                    raise DuplicateRecord(record["record_id"]) from None
                raise

    def import_seed(self, meta: dict, records: Iterable[dict], validate: bool = True) -> tuple[int, int]:
        """Append seed records with provenance. Idempotent: existing record ids are skipped.

        Returns (inserted, skipped).
        """
        source_id = meta["source_id"]
        now = _now()
        rows = []
        for rec in records:
            if validate:
                errors = self.validate(rec)
                if errors:
                    raise InvalidRecord([f"{rec.get('record_id')}: {e}" for e in errors[:5]])
            if rec["source"]["source_type"] != meta["source_type"] or meta["source_type"] == "field_report":
                raise InvalidRecord([f"{rec.get('record_id')}: source_type does not match seed source"])
            rows.append(_row(rec, f"seed:{source_id}", source_id, now))
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO seed_sources (source_id, source_type, name, url, commit_sha, commit_date,"
                " sha256, license, license_note, imported_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (source_id, meta["source_type"], meta["name"], meta["url"], meta.get("commit"),
                 meta.get("commit_date"), meta.get("sha256"), meta["license"], meta.get("license_note"), now),
            )
            before = self._db.total_changes
            self._db.executemany(
                f"INSERT OR IGNORE INTO records ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})", rows)
            inserted = self._db.total_changes - before
        return inserted, len(rows) - inserted

    # ---- reads ----------------------------------------------------------
    def rows(self) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._db.execute(
                "SELECT source_type, contributor, l1, l2, model_id, harness, tests_passed, committed,"
                " tool_error_count, cost_usd_client, cost_usd_server, latency_ms, self_score FROM records")
            cur.row_factory = sqlite3.Row
            return cur.fetchall()

    def seed_sources(self) -> list[dict]:
        with self._lock:
            cur = self._db.execute(
                "SELECT source_id, source_type, name, url, commit_sha, commit_date, sha256, license, license_note"
                " FROM seed_sources ORDER BY source_id")
            cur.row_factory = sqlite3.Row
            return [dict(r) for r in cur.fetchall()]

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM records").fetchone()[0]

    def raw_connection(self) -> sqlite3.Connection:
        """For tests and operator tooling only."""
        return self._db

    def close(self) -> None:
        self._db.close()
