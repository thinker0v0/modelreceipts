"""``python3 -m modelreceipts {hook,submit,validate,version} ...``"""

import sys

from . import __version__

USAGE = """usage: python3 -m modelreceipts <command> [options]

commands:
  hook       build a record from a Claude Code Stop-hook payload and PREVIEW it (dry run, no network)
  submit     preview a record; send it ONLY if --endpoint URL is given (opt-in, loopback-only by default)
  validate   validate record / seed-cell JSON or JSONL (schema picked by schema_version)
  migrate    convert schema v0.1 records to v0.2 (inputs are never modified)
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
    if cmd == "validate":
        from .validate import main as validate_main
        return validate_main(rest)
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
