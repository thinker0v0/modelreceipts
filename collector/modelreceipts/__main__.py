"""``python3 -m modelreceipts {hook,submit,validate,version} ...``"""

import sys

from . import __version__

USAGE = """usage: python3 -m modelreceipts <command> [options]

commands:
  hook       build a record from a Claude Code Stop-hook payload and PREVIEW it (dry run, no network)
  submit     preview a record; send it ONLY if --endpoint URL is given (opt-in, loopback-only, Ed25519-signed)
  query      fetch the contributor-only detailed aggregates (signed GET; needs your install key)
  keygen     create the local Ed25519 install key if missing and print its PUBLIC key
  pair       mark two local preview records as one task run with two models (pair mode)
  validate   validate record / seed-cell JSON or JSONL (schema picked by schema_version)
  migrate    convert schema v0.1 records to v0.2 (inputs are never modified)
  install-hook    add the preview-only Stop hook to a settings file (--settings PATH required; dry run unless --apply)
  uninstall-hook  remove it again (same safety rules)
  eval-classifier  per-class precision/recall of the local task classifier on the SYNTHETIC eval set
  version    print the collector version
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE)
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "hook":
        from .hook import main as hook_main
        return hook_main(rest)
    if cmd == "submit":
        from .submit import main as submit_main  # the only module that may use the network
        return submit_main(rest)
    if cmd == "query":
        from .submit import query_main  # network module
        return query_main(rest)
    if cmd == "keygen":
        import argparse
        from pathlib import Path
        from .signing import DEFAULT_KEY_FILE, load_or_create_key
        p = argparse.ArgumentParser(prog="modelreceipts keygen")
        p.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE)
        a = p.parse_args(rest)
        existed = a.key_file.exists()
        key = load_or_create_key(a.key_file)
        print(f"{'existing' if existed else 'created'} {a.key_file} (secret stays local, mode 0600)")
        print(f"public key: {key.public_b64}")
        return 0
    if cmd == "pair":
        from .pair import main as pair_main
        return pair_main(rest)
    if cmd == "validate":
        from .validate import main as validate_main
        return validate_main(rest)
    if cmd in {"install-hook", "uninstall-hook"}:
        from .install_hook import main as install_main
        return install_main(rest, action=cmd.split("-")[0])
    if cmd == "migrate":
        from .migrate import main as migrate_main
        return migrate_main(rest)
    if cmd == "eval-classifier":
        from .evaluate import main as eval_main
        return eval_main(rest)
    if cmd == "version":
        print(__version__)
        return 0
    print(USAGE, file=sys.stderr)
    return 2


def _entry() -> None:  # console-script entry point
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    _entry()
