"""``python3 -m modelreceipts {hook,validate} ...``"""

import sys

from . import __version__

USAGE = """usage: python3 -m modelreceipts <command> [options]

commands:
  hook       build a record from a Claude Code Stop-hook payload and PREVIEW it (dry run, no network)
  validate   validate record JSON files against schema/record.v0.1.schema.json
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
    if cmd == "validate":
        from .validate import main as validate_main
        return validate_main(rest)
    if cmd == "version":
        print(__version__)
        return 0
    print(USAGE, file=sys.stderr)
    return 2


def _entry() -> None:  # console-script entry point
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    _entry()
