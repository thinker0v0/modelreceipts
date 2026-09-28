"""Append-only SQLite store for records (schema v0.1 and v0.2) and seed cells.

* ``records``, ``seed_sources``, ``seed_cells``, ``server_costs`` and
  ``self_assessments`` reject UPDATE and DELETE with triggers, so
  "append-only" holds even for code (or people) holding a raw connection.
* A duplicate ``record_id`` / ``cell_id`` is refused, never overwritten.
* Contributors are stored as a salted SHA-256: of the verified Ed25519 PUBLIC
  key (``k:``), or, only on servers that allow unsigned submissions, of a
  self-declared install id (``c:``). Records without either all count as ONE
  contributor ("anonymous"), so they cannot inflate k.
* Separation of signals: the server-side cost (price table) lives in
  ``server_costs`` and the self-assessment in ``self_assessments``, both keyed
  by record id. The record body is stored exactly as received.
* Opening a database created by an older version adds the new columns and
  tables in place (additive only; existing rows are not rewritten). Converting
  old record bodies to v0.2 is a separate, copy-based command (``migrate-db``).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from modelreceipts.validate import load_validator

from .prices import PriceTable

ANONYMOUS = "anonymous"
DB_VERSION = 2

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
  committed        INTEGER,
  tool_error_count INTEGER,
  cost_usd_client  REAL,
  cost_usd_server  REAL,
  latency_ms       INTEGER,
  self_score       REAL,
  body             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS records_cell ON records (source_type, l1, l2, model_id, harness);
CREATE TABLE IF NOT EXISTS server_costs (
  record_id      TEXT PRIMARY KEY REFERENCES records(record_id),
  price_table_id TEXT NOT NULL,
  cost_usd       REAL,
  reason         TEXT NOT NULL,
  computed_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS self_assessments (
  record_id   TEXT PRIMARY KEY REFERENCES records(record_id),
  score       REAL NOT NULL,
  rater       TEXT NOT NULL,
  extractor   TEXT,
  judge_model TEXT
);
CREATE TABLE IF NOT EXISTS seed_cells (
  cell_id     TEXT PRIMARY KEY,
  source_id   TEXT NOT NULL REFERENCES seed_sources(source_id),
  source_type TEXT NOT NULL,
  l1          TEXT,
  l2          TEXT,
  provider    TEXT NOT NULL,
  model_id    TEXT NOT NULL,
  harness     TEXT,
  kind        TEXT NOT NULL,
  battles     INTEGER,
  wins        INTEGER,
  losses      INTEGER,
  ties        INTEGER,
  win_rate    REAL,
  tokens      INTEGER,
  share       REAL,
  rank        INTEGER,
  body        TEXT NOT NULL
);
"""

NEW_RECORD_COLUMNS = {  # added to v1 databases in place
    "schema_version": "TEXT",
    "pair_id": "TEXT",
    "retry_next": "INTEGER",
    "key_verified": "INTEGER NOT NULL DEFAULT 0",
}

TRIGGERS = "".join(
    f"""
CREATE TRIGGER IF NOT EXISTS {t}_no_update BEFORE UPDATE ON {t}
  BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;
CREATE TRIGGER IF NOT EXISTS {t}_no_delete BEFORE DELETE ON {t}
  BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;"""
    for t in ("records", "seed_sources", "seed_cells", "server_costs", "self_assessments")
)

COLUMNS = ("record_id", "received_at", "source_type", "contributor", "seed_source_id", "l1", "l2",
           "model_id", "harness", "tests_passed", "committed", "tool_error_count",
           "cost_usd_client", "cost_usd_server", "latency_ms", "self_score", "body",
           "schema_version", "pair_id", "retry_next", "key_verified")

SEED_CELL_COLUMNS = ("cell_id", "source_id", "source_type", "l1", "l2", "provider", "model_id", "harness", "kind",
                     "battles", "wins", "losses", "ties", "win_rate", "tokens", "share", "rank", "body")


class InvalidRecord(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("record failed schema validation")
        self.errors = errors


class DuplicateRecord(ValueError):
    pass


class LegacyDatabase(RuntimeError):
    """A database created before v0.2 keeps NOT NULL on columns that v0.2 allows to be null."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bool(v):
    return None if v is None else int(bool(v))


def cell_key(record: dict) -> tuple:
    return (record["task"]["l1"], record["task"]["l2"], record["model"]["id"], record["method"]["harness"])


def _row(record: dict, contributor: str, seed_source_id: str | None, received_at: str, key_verified: bool) -> tuple:
    ev = record["outcome"]["evidence"]
    usage = record["usage"]
    return (
        record["record_id"], received_at, record["source"]["source_type"], contributor, seed_source_id,
        record["task"]["l1"], record["task"]["l2"], record["model"]["id"], record["method"]["harness"],
        _bool(ev["tests_passed"]), _bool(ev["committed"]), ev["tool_error_count"],
        usage["cost_usd_client"],
        None,  # legacy column; the server value lives in server_costs
        usage["latency_ms"],
        None,  # legacy column; self-assessment lives in self_assessments
        json.dumps(record, separators=(",", ":"), sort_keys=True),
        record["schema_version"], record["pairing"]["pair_id"], _bool(ev.get("user_retry_next_prompt")),
        int(bool(key_verified)),
    )


class Store:
    def __init__(self, path: str | Path = ":memory:", prices: PriceTable | None = None, salt: str | None = None):
        self.path = str(path)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript(DDL)
        self._upgrade()
        self._db.executescript(TRIGGERS)
        self._validator = load_validator()
        self._seed_validator = load_validator(allow_seed_cells=True)
        self.prices = prices if prices is not None else PriceTable.load()
        with self._db:
            self._db.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('contributor_salt', ?)",
                             (salt or secrets.token_hex(16),))
        self._salt = self._db.execute("SELECT value FROM meta WHERE key = 'contributor_salt'").fetchone()[0]

    def _upgrade(self) -> None:
        cols = {r[1] for r in self._db.execute("PRAGMA table_info(records)")}
        with self._db:
            for name, decl in NEW_RECORD_COLUMNS.items():
                if name not in cols:
                    self._db.execute(f"ALTER TABLE records ADD COLUMN {name} {decl}")
            self._db.execute(f"PRAGMA user_version = {DB_VERSION}")

    # ---- identity -------------------------------------------------------
    def _hash(self, prefix: str, value: str | bytes) -> str:
        raw = value if isinstance(value, bytes) else value.encode("utf-8")
        return prefix + hashlib.sha256(self._salt.encode("ascii") + b":" + raw).hexdigest()[:24]

    def contributor_key(self, install_id: str | None = None, public_key: bytes | None = None) -> str:
        if public_key:
            return self._hash("k:", public_key)
        if install_id:
            return self._hash("c:", install_id)
        return ANONYMOUS

    @property
    def salt(self) -> str:
        return self._salt

    # ---- writes ---------------------------------------------------------
    def validate(self, record) -> list[str]:
        if not isinstance(record, dict):
            return ["$: expected a JSON object"]
        return self._validator.errors(record)

    def _insert(self, record: dict, contributor: str, seed_source_id: str | None, received_at: str,
                key_verified: bool) -> None:
        row = _row(record, contributor, seed_source_id, received_at, key_verified)
        try:
            self._db.execute(f"INSERT INTO records ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
                             row)
        except sqlite3.IntegrityError as exc:
            if "NOT NULL constraint failed: records." in str(exc):
                raise LegacyDatabase(
                    f"{exc}: this database was created before schema v0.2 and cannot hold null evidence fields. "
                    "Copy it to a new file first: python3 -m modelreceipts_server migrate-db --from OLD --to NEW"
                ) from None
            raise
        rid = record["record_id"]
        if record["source"]["source_type"] == "field_report":
            cost = self.prices.cost(record)
            self._db.execute("INSERT INTO server_costs (record_id, price_table_id, cost_usd, reason, computed_at)"
                             " VALUES (?,?,?,?,?)", (rid, cost.price_table_id, cost.cost_usd, cost.reason, received_at))
        sa = record["outcome"].get("self_assessment")
        if isinstance(sa, dict):
            self._db.execute("INSERT INTO self_assessments (record_id, score, rater, extractor, judge_model)"
                             " VALUES (?,?,?,?,?)", (rid, sa["score"], sa["rater"], sa.get("extractor"), sa.get("judge_model")))

    def add_field_report(self, record: dict, install_id: str | None = None, *, contributor: str | None = None,
                         key_verified: bool = False, received_at: str | None = None) -> None:
        """Validate and append one user record. Raises InvalidRecord / DuplicateRecord."""
        errors = self.validate(record)
        if errors:
            raise InvalidRecord(errors)
        if record["source"]["source_type"] != "field_report":
            raise InvalidRecord(["$.source.source_type: only 'field_report' is accepted over HTTP; "
                                 "seed layers are imported locally by the operator"])
        contributor = contributor or self.contributor_key(install_id)
        with self._lock:
            try:
                with self._db:
                    self._insert(record, contributor, None, received_at or _now(), key_verified)
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                    raise DuplicateRecord(record["record_id"]) from None
                raise

    def _add_source(self, meta: dict, now: str) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO seed_sources (source_id, source_type, name, url, commit_sha, commit_date,"
            " sha256, license, license_note, imported_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (meta["source_id"], meta["source_type"], meta["name"], meta["url"], meta.get("commit"),
             meta.get("commit_date"), meta.get("sha256"), meta["license"], meta.get("license_note"), now),
        )

    def import_seed(self, meta: dict, records: Iterable[dict], validate: bool = True) -> tuple[int, int]:
        """Append per-run seed records with provenance. Idempotent. Returns (inserted, skipped)."""
        source_id = meta["source_id"]
        now = _now()
        recs = []
        for rec in records:
            if validate:
                errors = self.validate(rec)
                if errors:
                    raise InvalidRecord([f"{rec.get('record_id')}: {e}" for e in errors[:5]])
            if rec["source"]["source_type"] != meta["source_type"] or meta["source_type"] == "field_report":
                raise InvalidRecord([f"{rec.get('record_id')}: source_type does not match seed source"])
            recs.append(rec)
        existing = self._existing_ids("records", "record_id", [r["record_id"] for r in recs])
        with self._lock, self._db:
            self._add_source(meta, now)
            fresh = [r for r in recs if r["record_id"] not in existing]
            for rec in fresh:
                self._insert(rec, f"seed:{source_id}", source_id, now, False)
        return len(fresh), len(recs) - len(fresh)

    def import_seed_cells(self, meta: dict, cells: Iterable[dict], validate: bool = True) -> tuple[int, int]:
        """Append aggregate seed cells (preference / usage). Idempotent. Returns (inserted, skipped)."""
        now = _now()
        rows = []
        for c in cells:
            if validate:
                errors = self._seed_validator.errors(c)
                if errors or c.get("kind") != "seed_cell":
                    raise InvalidRecord([f"{c.get('cell_id')}: {e}" for e in (errors or ['not a seed cell'])[:5]])
            if c["source"]["source_id"] != meta["source_id"] or c["source"]["source_type"] != meta["source_type"]:
                raise InvalidRecord([f"{c['cell_id']}: source does not match {meta['source_id']}"])
            m = c["metrics"]
            rows.append((c["cell_id"], meta["source_id"], meta["source_type"], c["task"]["l1"], c["task"]["l2"],
                         c["model"]["provider"], c["model"]["id"], c["method"]["harness"], m["kind"],
                         m.get("battles"), m.get("wins"), m.get("losses"), m.get("ties"), m.get("win_rate"),
                         m.get("tokens"), m.get("share"), m.get("rank"),
                         json.dumps(c, separators=(",", ":"), sort_keys=True)))
        with self._lock, self._db:
            self._add_source(meta, now)
            before = self._db.total_changes
            self._db.executemany(f"INSERT OR IGNORE INTO seed_cells ({', '.join(SEED_CELL_COLUMNS)})"
                                 f" VALUES ({', '.join('?' * len(SEED_CELL_COLUMNS))})", rows)
            inserted = self._db.total_changes - before
        return inserted, len(rows) - inserted

    def _existing_ids(self, table: str, column: str, ids: list[str]) -> set[str]:
        found: set[str] = set()
        with self._lock:
            for i in range(0, len(ids), 500):
                chunk = ids[i:i + 500]
                q = f"SELECT {column} FROM {table} WHERE {column} IN ({','.join('?' * len(chunk))})"
                found.update(r[0] for r in self._db.execute(q, chunk))
        return found

    # ---- reads ----------------------------------------------------------
    def rows(self) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._db.execute(
                "SELECT r.source_type, r.contributor, r.l1, r.l2, r.model_id, r.harness, r.tests_passed, r.committed,"
                " r.tool_error_count, r.cost_usd_client, COALESCE(sc.cost_usd, r.cost_usd_server) AS cost_usd_server,"
                " r.latency_ms, COALESCE(sa.score, r.self_score) AS self_score, r.pair_id, r.retry_next,"
                " r.key_verified, r.received_at"
                " FROM records r LEFT JOIN server_costs sc ON sc.record_id = r.record_id"
                " LEFT JOIN self_assessments sa ON sa.record_id = r.record_id")
            cur.row_factory = sqlite3.Row
            return cur.fetchall()

    def seed_cell_rows(self) -> list[dict]:
        with self._lock:
            cur = self._db.execute(f"SELECT {', '.join(SEED_CELL_COLUMNS[:-1])} FROM seed_cells")
            cur.row_factory = sqlite3.Row
            return [dict(r) for r in cur.fetchall()]

    def seed_sources(self) -> list[dict]:
        with self._lock:
            cur = self._db.execute(
                "SELECT source_id, source_type, name, url, commit_sha, commit_date, sha256, license, license_note"
                " FROM seed_sources ORDER BY source_id")
            cur.row_factory = sqlite3.Row
            return [dict(r) for r in cur.fetchall()]

    def server_cost(self, record_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT price_table_id, cost_usd, reason FROM server_costs WHERE record_id = ?",
                                   (record_id,)).fetchone()
        return None if row is None else {"price_table_id": row[0], "cost_usd": row[1], "reason": row[2]}

    def has_recent_contribution(self, contributor: str, days: int = 90, now: datetime | None = None) -> bool:
        """True if this contributor added a field report within ``days`` (gate for the detailed view)."""
        if contributor == ANONYMOUS:
            return False
        since = ((now or datetime.now(timezone.utc)) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._lock:
            row = self._db.execute(
                "SELECT 1 FROM records WHERE contributor = ? AND source_type = 'field_report' AND received_at >= ? LIMIT 1",
                (contributor, since)).fetchone()
        return row is not None

    def count_in_cell_since(self, contributor: str, key: tuple, hours: int = 24, now: datetime | None = None) -> int:
        since = ((now or datetime.now(timezone.utc)) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        l1, l2, model, harness = key
        with self._lock:
            return self._db.execute(
                "SELECT COUNT(*) FROM records WHERE contributor = ? AND source_type = 'field_report' AND l1 = ?"
                " AND l2 IS ? AND model_id = ? AND harness = ? AND received_at >= ?",
                (contributor, l1, l2, model, harness, since)).fetchone()[0]

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM records").fetchone()[0]

    def raw_connection(self) -> sqlite3.Connection:
        """For tests and operator tooling only."""
        return self._db

    def close(self) -> None:
        self._db.close()


def migrate_database(src: Path, dst: Path, prices: PriceTable | None = None) -> dict:
    """Copy an existing database into a NEW file with every record body converted to v0.2.

    The source is opened read-only and never modified; the destination must not
    exist. Contributor hashes stay valid because the salt is copied. Server costs
    are recomputed with the current price table. Returns counts.
    """
    from modelreceipts.migrate import migrate_record

    if Path(dst).exists():
        raise FileExistsError(f"{dst} already exists; migrate-db only writes a new file")
    old = sqlite3.connect(f"file:{Path(src).resolve()}?mode=ro", uri=True)
    old.row_factory = sqlite3.Row
    salt = old.execute("SELECT value FROM meta WHERE key = 'contributor_salt'").fetchone()[0]
    new = Store(dst, prices=prices, salt=salt)
    counts = {"records": 0, "migrated_bodies": 0, "seed_sources": 0, "seed_cells": 0}
    tables = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    cols = {r[1] for r in old.execute("PRAGMA table_info(records)")}
    with new._lock, new._db:
        for src_row in old.execute("SELECT * FROM seed_sources"):
            new._db.execute("INSERT INTO seed_sources VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(src_row))
            counts["seed_sources"] += 1
        verified = "key_verified" in cols
        for r in old.execute(f"SELECT record_id, received_at, contributor, seed_source_id, body"
                             f"{', key_verified' if verified else ''} FROM records ORDER BY seq"):
            body = json.loads(r["body"])
            migrated, _notes = migrate_record(body)
            if migrated != body:
                counts["migrated_bodies"] += 1
            errors = new.validate(migrated)
            if errors:
                raise InvalidRecord([f"{r['record_id']}: {e}" for e in errors[:5]])
            new._insert(migrated, r["contributor"], r["seed_source_id"], r["received_at"],
                        bool(r["key_verified"]) if verified else False)
            counts["records"] += 1
        if "seed_cells" in tables:
            for c in old.execute(f"SELECT {', '.join(SEED_CELL_COLUMNS)} FROM seed_cells"):
                new._db.execute(f"INSERT INTO seed_cells ({', '.join(SEED_CELL_COLUMNS)})"
                                f" VALUES ({', '.join('?' * len(SEED_CELL_COLUMNS))})", tuple(c))
                counts["seed_cells"] += 1
    old.close()
    new.close()
    return counts
