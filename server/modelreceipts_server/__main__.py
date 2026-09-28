"""``PYTHONPATH=server python3 -m modelreceipts_server <command>``

commands:
  serve         run the ingest API on 127.0.0.1 (loopback only)
  import-seed   load a seed source into the database (local operator action; not exposed over HTTP)
  aggregates    print the public overview or the detailed aggregates JSON for a database
  make-sample   regenerate dashboard/data/*.sample.json and docs/figures/*.synthetic.svg
                (real seeds + SYNTHETIC field reports and pairs)
  migrate-db    copy a database into a NEW file with every record converted to schema v0.2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import DASHBOARD_DIR, SERVER_DIR
from .aggregate import Thresholds, aggregate, overview
from .prices import DEFAULT_PRICES, PriceTable
from .ratelimit import RateLimits
from .store import LegacyDatabase, Store, migrate_database

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
    g.add_argument("--max-contributor-share", type=float, default=0.5, help="max share of one contributor in a field cell (default 0.5)")
    g.add_argument("--seed-min-contributors", type=int, default=_env_int("MR_SEED_MIN_CONTRIBUTORS", 1), help="k for seed cells (default 1)")
    g.add_argument("--seed-min-records", type=int, default=_env_int("MR_SEED_MIN_RECORDS", 30), help="n for seed cells / battles (default 30)")
    g.add_argument("--pair-min-pairs", type=int, default=10, help="pairs needed to publish a head-to-head result (default 10)")
    g.add_argument("--pair-min-contributors", type=int, default=3, help="contributors needed for a head-to-head result (default 3)")


def _thresholds(a) -> Thresholds:
    return Thresholds.build(a.min_contributors, a.min_records, a.seed_min_contributors, a.seed_min_records,
                            a.max_contributor_share, a.pair_min_pairs, a.pair_min_contributors)


def _open_store(path: Path, prices: Path = DEFAULT_PRICES) -> Store:
    path.parent.mkdir(parents=True, exist_ok=True)
    return Store(path, prices=PriceTable.load(prices))


def _seed(source: str, input_path: Path | None):
    """Return (meta, per_run_records, seed_cells)."""
    if source == "aider-polyglot":
        from modelreceipts_seeds import aider_polyglot
        meta, _index, records = aider_polyglot.build()
        return meta, records, []
    if source == "arena-55k":
        from modelreceipts_seeds import arena
        meta, cells = arena.build()
        return meta, [], cells
    from modelreceipts_seeds import openrouter
    meta, cells = openrouter.build(input_path)
    return meta, [], cells


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts_server", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="run the API (loopback only)")
    p_serve.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_serve.add_argument("--host", default="127.0.0.1", help="127.0.0.1 (default), ::1 or localhost; anything else is refused")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.add_argument("--prices", type=Path, default=DEFAULT_PRICES, help="price table JSON for server-side cost")
    p_serve.add_argument("--signatures", choices=["required", "optional"], default="required",
                         help="required (default): unsigned POSTs get 401; optional: accept legacy/anonymous")
    p_serve.add_argument("--gate", choices=["on", "off"], default="on",
                         help="on (default): /v1/aggregates/detail only for recent contributors; off: open (local dev)")
    p_serve.add_argument("--rate-per-hour", type=float, default=120.0, help="records per contributor per hour (default 120)")
    p_serve.add_argument("--burst", type=int, default=30, help="burst size per contributor (default 30)")
    p_serve.add_argument("--cell-daily-cap", type=int, default=50, help="records per contributor per cell per 24h (default 50)")
    _add_threshold_args(p_serve)

    p_seed = sub.add_parser("import-seed", help="load a seed source (idempotent)")
    p_seed.add_argument("source", choices=["aider-polyglot", "arena-55k", "openrouter"])
    p_seed.add_argument("--input", type=Path, help="openrouter: an export you obtained (default: SYNTHETIC fixture)")
    p_seed.add_argument("--db", type=Path, default=DEFAULT_DB)

    p_agg = sub.add_parser("aggregates", help="print aggregates JSON")
    p_agg.add_argument("--db", type=Path, default=DEFAULT_DB)
    p_agg.add_argument("--view", choices=["overview", "detail"], default="detail")
    p_agg.add_argument("--level", choices=["l1", "l2"], default="l2")
    _add_threshold_args(p_agg)

    p_sample = sub.add_parser("make-sample", help="regenerate the dashboard sample JSON files")
    p_sample.add_argument("--out-dir", type=Path, default=DASHBOARD_DIR / "data")
    p_sample.add_argument("--figure", type=Path, default=DASHBOARD_DIR.parent / "docs" / "figures" / "self-vs-evidence.synthetic.svg",
                          help="also write the SYNTHETIC self-vs-evidence demo figure here")
    _add_threshold_args(p_sample)

    p_mig = sub.add_parser("migrate-db", help="copy a database into a new file with v0.2 record bodies")
    p_mig.add_argument("--from", dest="src", type=Path, required=True)
    p_mig.add_argument("--to", dest="dst", type=Path, required=True)
    p_mig.add_argument("--prices", type=Path, default=DEFAULT_PRICES)

    a = parser.parse_args(argv)

    if a.cmd == "serve":
        from .app import NotLoopback, Policy, make_server
        store = _open_store(a.db, a.prices)
        policy = Policy(signatures=a.signatures, gate=a.gate == "on",
                        limits=RateLimits(a.rate_per_hour, a.burst, a.cell_daily_cap))
        try:
            httpd = make_server(store, a.host, a.port, _thresholds(a), policy=policy)
        except NotLoopback as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        host, port = httpd.server_address[:2]
        print(f"[modelreceipts-server] listening on http://{host}:{port}  db={a.db}  records={store.count()}", flush=True)
        print(f"[modelreceipts-server] signatures={policy.signatures} gate={'on' if policy.gate else 'off'} "
              f"limits={policy.limits} prices={store.prices.id}", flush=True)
        print(f"[modelreceipts-server] thresholds={json.dumps(_thresholds(a).as_json())}", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
            store.close()
        return 0

    if a.cmd == "import-seed":
        meta, records, cells = _seed(a.source, a.input)
        store = _open_store(a.db)
        try:
            if records:
                inserted, skipped = store.import_seed(meta, records)
            else:
                inserted, skipped = store.import_seed_cells(meta, cells)
        except LegacyDatabase as exc:
            print(f"error: {exc}", file=sys.stderr)
            store.close()
            return 2
        kind = "records" if records else "cells"
        note = "  [SYNTHETIC fixture]" if meta.get("synthetic") else ""
        print(f"{meta['source_id']}: {kind} inserted={inserted} skipped(existing)={skipped}{note}")
        store.close()
        return 0

    if a.cmd == "aggregates":
        store = _open_store(a.db)
        if a.view == "overview":
            result = overview(store.rows(), _thresholds(a), seed_sources=store.seed_sources(),
                              seed_cells=store.seed_cell_rows())
        else:
            result = aggregate(store.rows(), _thresholds(a), level=a.level, seed_sources=store.seed_sources(),
                               seed_cells=store.seed_cell_rows(), prices=store.prices.describe())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        store.close()
        return 0

    if a.cmd == "make-sample":
        from .sample import build_samples
        detail, public = build_samples(_thresholds(a))
        a.out_dir.mkdir(parents=True, exist_ok=True)
        for name, obj in (("aggregates.sample.json", detail), ("overview.sample.json", public)):
            (a.out_dir / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        from .figure import render
        a.figure.parent.mkdir(parents=True, exist_ok=True)
        a.figure.write_text(render(detail), encoding="utf-8")
        print(f"wrote {a.out_dir}: detail cells={len(detail['cells'])} suppressed={len(detail['suppressed'])} "
              f"pairwise={len(detail['pairwise']['results'])} seed_cells={len(detail['seed_cells']['cells'])}; "
              f"overview cells={len(public['cells'])}")
        return 0

    if a.cmd == "migrate-db":
        try:
            counts = migrate_database(a.src, a.dst, PriceTable.load(a.prices))
        except FileExistsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"migrated {a.src} -> {a.dst}: {json.dumps(counts)}  (the source file was not modified)")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
