"""Install / uninstall the ModelReceipts ``Stop`` hook in a Claude Code settings file.

    python3 -m modelreceipts install-hook   --settings PATH [--apply] [--preview-dir DIR] [--python EXE]
    python3 -m modelreceipts uninstall-hook --settings PATH [--apply]

Safety rules (tests enforce them):

* ``--settings`` is REQUIRED. There is no default path, so nothing ever edits
  ``~/.claude/settings.json`` unless a person types that path.
* Default is a dry run: print a unified diff and exit. Nothing is written.
* ``--apply`` additionally asks for confirmation on an interactive terminal
  (type ``yes``). Without a terminal it refuses. There is no ``--yes`` flag.
* Before any change the current file is copied to
  ``<settings>.modelreceipts-backup-<UTC timestamp>``; the new file is written to
  a temp file and atomically renamed, keeping the original file mode.
* Idempotent: installing twice changes nothing; an outdated ModelReceipts entry
  is replaced in place. Uninstall removes ONLY entries whose command runs
  ``modelreceipts hook --hook``, then drops groups / keys it left empty.
* The installed hook runs the preview-only ``hook`` command. It never submits.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

COLLECTOR_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PREVIEW_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "modelreceipts" / "preview"
HOOK_TIMEOUT_S = 10
_OURS = re.compile(r"(^|\s)-m\s+modelreceipts\s+hook\b.*\s--hook\b")


class SettingsError(Exception):
    pass


def hook_command(collector_dir: Path, python: str, preview_dir: Path) -> str:
    return (f"PYTHONPATH={shlex.quote(str(collector_dir))} {shlex.quote(python)} -m modelreceipts hook --hook "
            f"--preview-dir {shlex.quote(str(preview_dir))}")


def is_ours(entry: object) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("command"), str) and bool(_OURS.search(entry["command"]))


def load_settings(path: Path) -> tuple[dict, str | None]:
    """Return (settings, original_text). A missing file is an empty object."""
    if not path.exists():
        return {}, None
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as exc:
        raise SettingsError(f"{path} is not valid JSON ({exc}); refusing to touch it") from None
    if not isinstance(data, dict):
        raise SettingsError(f"{path} must contain a JSON object")
    return data, text


def _stop_groups(settings: dict) -> list:
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise SettingsError('"hooks" must be an object')
    stop = hooks.get("Stop", [])
    if not isinstance(stop, list):
        raise SettingsError('"hooks.Stop" must be a list')
    for group in stop:
        if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
            raise SettingsError('every "hooks.Stop" entry must be an object with a "hooks" list')
    return stop


def installed(settings: dict, entry: dict) -> tuple[list, bool]:
    """Return (our existing entries, whether the desired entry is present exactly once)."""
    ours = [h for g in _stop_groups(settings) for h in g.get("hooks", []) if is_ours(h)]
    return ours, ours == [entry]


def with_hook(settings: dict, entry: dict) -> dict:
    new = copy.deepcopy(settings)
    stop = _stop_groups(new)
    if installed(new, entry)[1]:
        return new
    replaced = False
    for group in stop:
        kept = []
        for h in group.get("hooks", []):
            if is_ours(h):
                if not replaced:
                    kept.append(copy.deepcopy(entry))  # update the outdated entry in place
                    replaced = True
            else:
                kept.append(h)
        group["hooks"] = kept
    if not replaced:
        stop.append({"hooks": [copy.deepcopy(entry)]})
    new.setdefault("hooks", {})["Stop"] = stop
    return new


def without_hook(settings: dict) -> dict:
    new = copy.deepcopy(settings)
    stop = _stop_groups(new)
    if not any(is_ours(h) for g in stop for h in g.get("hooks", [])):
        return new
    groups = []
    for group in stop:
        kept = [h for h in group.get("hooks", []) if not is_ours(h)]
        if kept:
            groups.append({**group, "hooks": kept})
        elif not any(is_ours(h) for h in group.get("hooks", [])):
            groups.append(group)  # a group that was already empty is not ours to delete
    hooks = new["hooks"]
    if groups:
        hooks["Stop"] = groups
    else:
        hooks.pop("Stop", None)
    if not hooks:
        new.pop("hooks")
    return new


def render(settings: dict) -> str:
    return json.dumps(settings, ensure_ascii=False, indent=2) + "\n"


def diff(path: Path, old_text: str | None, new_text: str) -> str:
    old_lines = [] if old_text is None else old_text.splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_text.splitlines(keepends=True),
                                        fromfile=f"{path} (current)", tofile=f"{path} (after)"))


def write_with_backup(path: Path, text: str, now: datetime | None = None) -> Path | None:
    """Back up the current file (if any), then atomically replace it. Returns the backup path."""
    target = path.resolve()
    backup = None
    mode = None
    if target.exists():
        stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%S%fZ")
        backup = target.with_name(f"{target.name}.modelreceipts-backup-{stamp}")
        shutil.copy2(target, backup)
        mode = target.stat().st_mode & 0o7777
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return backup


def _interactive_confirm(question: str) -> bool:
    if not sys.stdin.isatty():
        print("[modelreceipts] --apply needs an interactive terminal to confirm; nothing was changed.", file=sys.stderr)
        return False
    try:
        answer = input(f"{question} Type 'yes' to continue: ")
    except EOFError:
        return False
    return answer.strip().lower() == "yes"


def main(argv: list[str], action: str = "install", confirm: Callable[[str], bool] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=f"modelreceipts {action}-hook",
        description=f"{action.capitalize()} the ModelReceipts Stop hook (preview-only) in a Claude Code settings file. "
                    "Dry run unless --apply; --apply asks for confirmation.")
    parser.add_argument("--settings", type=Path, required=True,
                        help="settings file to edit, e.g. ~/.claude/settings.json (required; there is no default)")
    parser.add_argument("--apply", action="store_true", help="write the change (after a backup and confirmation)")
    if action == "install":
        parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW_DIR,
                            help=f"where the hook writes previews (default {DEFAULT_PREVIEW_DIR})")
        parser.add_argument("--python", default=sys.executable or "python3", help="interpreter for the hook")
        parser.add_argument("--collector-dir", type=Path, default=COLLECTOR_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    confirm = confirm or _interactive_confirm
    path = args.settings.expanduser()

    try:
        settings, old_text = load_settings(path)
        if action == "install":
            entry = {"type": "command",
                     "command": hook_command(args.collector_dir.resolve(), args.python,
                                             args.preview_dir.expanduser().resolve()),
                     "timeout": HOOK_TIMEOUT_S}
            new = with_hook(settings, entry)
        else:
            new = without_hook(settings)
    except SettingsError as exc:
        print(f"[modelreceipts] {exc}", file=sys.stderr)
        return 2

    if new == settings and old_text is not None:
        print(f"[modelreceipts] no change needed: {path} is already "
              f"{'set up' if action == 'install' else 'free of ModelReceipts hooks'}.")
        return 0
    if action == "uninstall" and old_text is None:
        print(f"[modelreceipts] {path} does not exist; nothing to uninstall.")
        return 0

    new_text = render(new)
    print(diff(path, old_text, new_text), end="")
    if old_text is not None and render(settings) != old_text:
        print("[modelreceipts] note: the file will be re-serialized with 2-space JSON indentation.")
    if not args.apply:
        print(f"[modelreceipts] DRY RUN — {path} was not modified. Re-run with --apply to write it.")
        return 0
    if not confirm(f"Apply this change to {path}? A backup is written first."):
        print("[modelreceipts] not confirmed; nothing was changed.")
        return 1
    backup = write_with_backup(path, new_text)
    print(f"[modelreceipts] wrote {path}" + (f" (backup: {backup})" if backup else " (new file)"))
    if action == "install":
        print("[modelreceipts] the hook only writes local previews; submitting stays a separate, explicit command.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
