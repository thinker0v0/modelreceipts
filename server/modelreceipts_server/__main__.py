"""``PYTHONPATH=server python3 -m modelreceipts_server <command>``

commands:
  serve         run the ingest API on 127.0.0.1 (loopback only)
  import-seed   load a seed source into the database (local operator action; not exposed over HTTP)
  aggregates    print the aggregates JSON for a database
  make-sample   regenerate dashboard/data/aggregates.sample.json (Aider seed + SYNTHETIC field reports)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import DASHBOARD_DIR, SERVER_DIR
from .aggregate import Thresholds, aggregate
from .store import Store

DEFAULT_DB = SERVER_DIR / "var" / "modelreceipts.sqlite3"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _add_threshold_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("disclosure thresholds (also via env MR_MIN_CONTRIBUTORS, MR_MIN_RECORDS, MR_SEED_MIN_CONTRIBUTORS, MR_SEED_MIN_RECORDS)")
    g.add_argument("--min-contributors", type=int, default=_env_int("MR_MIN_CONTRIBUTORS", 5), help="k for field_report cells (default 5)")
    g.add_argument("--min-records", type=int, default=_env_int("MR_MIN_RECORDS", 30), help="n for field_report cells (default 30)")
    g.add_argument("--seed-min-contributors", type=int, default=_env_int("MR_SEED_MIN_CONTRIBUTORS", 1), help="k for seed cells (default 1)")
    g.add_argument("--seed-min-records", type=int, default=_env_int("MR_SEED_MIN_RECORDS", 30), help="n for seed cells (default 30)")


def _thresholds(a) -> Thresholds:
    return Thresholds.build(a.min_contributors, a.min_records, a.seed_min_contributors, a.seed_min_records)


def _open_store(path: Path) -> Store:
    path.parent.mkdir(parents=True, exist_ok=True)
    return Store(path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts_server", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="run the API (loopback only)")
    p_serve.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_serve.add_argument("--host", default="127.0.0.1", help="127.0.0.1 (default), ::1 or localhost; anything else is refused")
    p_serve.add_argument("--port", type=int, default=8787)
    _add_threshold_args(p_serve)

    p_seed = sub.add_parser("import-seed", help="load a seed source (idempotent)")
    p_seed.add_argument("source", choices=["aider-polyglot"])
    p_seed.add_argument("--db", type=Path, default=DEFAULT_DB)

    p_agg = sub.add_parser("aggregates", help="print aggregates JSON")
    p_agg.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_agg.add_argument("--level", choices=["l1", "l2"], default="l2")
    _add_threshold_args(p_agg)

    p_sample = sub.add_parser("make-sample", help="regenerate the dashboard sample JSON")
    p_sample.add_argument("--out", type=Path, default=DASHBOARD_DIR / "data" / "aggregates.sample.json")
    _add_threshold_args(p_sample)

    a = parser.parse_args(argv)

    if a.cmd == "serve":
        from .app import NotLoopback, make_server
        store = _open_store(a.db)
        try:
            httpd = make_server(store, a.host, a.port, _thresholds(a))
        except NotLoopback as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        host, port = httpd.server_address[:2]
        print(f"[modelreceipts-server] listening on http://{host}:{port}  db={a.db}  records={store.count()}")
        print(f"[modelreceipts-server] thresholds={json.dumps(_thresholds(a).as_json())}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
            store.close()
        return 0

    if a.cmd == "import-seed":
        from modelreceipts_seeds import aider_polyglot
        meta, index, records = aider_polyglot.build()
        store = _open_store(a.db)
        inserted, skipped = store.import_seed(meta, records)
        print(f"{meta['source_id']}: rows={len(index)} records inserted={inserted} skipped(existing)={skipped}")
        store.close()
        return 0

    if a.cmd == "aggregates":
        store = _open_store(a.db)
        result = aggregate(store.rows(), _thresholds(a), level=a.level, seed_sources=store.seed_sources())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        store.close()
        return 0

    if a.cmd == "make-sample":
        from .sample import build_sample
        result = build_sample(_thresholds(a))
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {a.out}: cells={len(result['cells'])} suppressed={len(result['suppressed'])} "
              f"totals={result['totals']['records_by_source_type']}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
