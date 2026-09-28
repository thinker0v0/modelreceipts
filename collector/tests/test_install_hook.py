"""install-hook / uninstall-hook. Every test works in a fresh temp directory with
HOME pointed at it; nothing here reads or writes the real ~/.claude/settings.json.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

COLLECTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COLLECTOR))

from modelreceipts import install_hook  # noqa: E402
from modelreceipts.install_hook import is_ours  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

OTHER = {
    "permissions": {"allow": ["Bash(ls:*)"]},
    "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "notify-send done"}]}],
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo pre"}]}],
    },
}


class InstallHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = mock.patch.dict(os.environ, {"HOME": str(self.tmp), "XDG_STATE_HOME": str(self.tmp / "state")})
        self.home.start()
        self.settings = self.tmp / "claude" / "settings.json"
        self.preview = self.tmp / "preview"

    def tearDown(self):
        self.home.stop()
        shutil.rmtree(self.tmp)

    def run_cmd(self, action, *extra, confirm=None):
        argv = ["--settings", str(self.settings), *extra]
        if action == "install":
            argv += ["--preview-dir", str(self.preview), "--python", sys.executable]
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = install_hook.main(argv, action=action, confirm=confirm)
        return code, out.getvalue()

    def write(self, obj):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def backups(self):
        return sorted(self.settings.parent.glob("settings.json.modelreceipts-backup-*"))

    def ours(self):
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        return [h for g in data.get("hooks", {}).get("Stop", []) for h in g["hooks"] if is_ours(h)]

    def test_settings_path_is_required(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            install_hook.main([], action="install")

    def test_default_is_dry_run_with_diff(self):
        self.write(OTHER)
        before = self.settings.read_bytes()
        code, out = self.run_cmd("install", confirm=lambda q: self.fail("dry run must not ask"))
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", out)
        self.assertIn("+", out)
        self.assertIn("modelreceipts hook --hook", out)
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertEqual(self.backups(), [])

    def test_dry_run_on_missing_file_creates_nothing(self):
        code, _ = self.run_cmd("install")
        self.assertEqual(code, 0)
        self.assertFalse(self.settings.exists())

    def test_apply_requires_confirmation(self):
        self.write(OTHER)
        before = self.settings.read_bytes()
        code, out = self.run_cmd("install", "--apply", confirm=lambda q: False)
        self.assertEqual(code, 1)
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertEqual(self.backups(), [])

    def test_non_interactive_confirmation_refuses(self):
        with mock.patch.object(sys, "stdin", io.StringIO("yes\n")), redirect_stderr(io.StringIO()):
            self.assertFalse(install_hook._interactive_confirm("?"))

    def test_apply_backs_up_preserves_other_settings_and_is_idempotent(self):
        self.write(OTHER)
        original = self.settings.read_bytes()
        os.chmod(self.settings, 0o600)
        code, out = self.run_cmd("install", "--apply", confirm=lambda q: True)
        self.assertEqual(code, 0, out)
        backups = self.backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(self.settings.stat().st_mode & 0o777, 0o600)
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(data["permissions"], OTHER["permissions"])
        self.assertEqual(data["hooks"]["PreToolUse"], OTHER["hooks"]["PreToolUse"])
        self.assertIn({"type": "command", "command": "notify-send done"}, data["hooks"]["Stop"][0]["hooks"])
        self.assertEqual(len(self.ours()), 1)
        self.assertEqual(self.ours()[0]["timeout"], install_hook.HOOK_TIMEOUT_S)

        after = self.settings.read_bytes()
        code, out = self.run_cmd("install", "--apply", confirm=lambda q: self.fail("no change, no question"))
        self.assertEqual(code, 0)
        self.assertIn("no change needed", out)
        self.assertEqual(self.settings.read_bytes(), after)
        self.assertEqual(len(self.backups()), 1)

    def test_outdated_entry_is_replaced_not_duplicated(self):
        self.write(OTHER)
        self.run_cmd("install", "--apply", confirm=lambda q: True)
        self.preview = self.tmp / "elsewhere"
        code, _ = self.run_cmd("install", "--apply", confirm=lambda q: True)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.ours()), 1)
        self.assertIn("elsewhere", self.ours()[0]["command"])

    def test_missing_file_is_created_without_backup(self):
        code, out = self.run_cmd("install", "--apply", confirm=lambda q: True)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.ours()), 1)
        self.assertEqual(self.backups(), [])

    def test_uninstall_removes_only_ours_and_cleans_up(self):
        self.write(OTHER)
        self.run_cmd("install", "--apply", confirm=lambda q: True)
        code, out = self.run_cmd("uninstall")
        self.assertIn("DRY RUN", out)
        self.assertEqual(len(self.ours()), 1)
        code, out = self.run_cmd("uninstall", "--apply", confirm=lambda q: True)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8")), OTHER)
        code, out = self.run_cmd("uninstall", "--apply", confirm=lambda q: self.fail("nothing to do"))
        self.assertIn("no change needed", out)

    def test_uninstall_drops_containers_it_emptied(self):
        self.run_cmd("install", "--apply", confirm=lambda q: True)
        self.run_cmd("uninstall", "--apply", confirm=lambda q: True)
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8")), {})

    def test_invalid_settings_are_never_touched(self):
        self.settings.parent.mkdir(parents=True)
        for bad in ("{not json", "[1, 2]", '{"hooks": {"Stop": {"oops": 1}}}'):
            with self.subTest(bad=bad):
                self.settings.write_text(bad, encoding="utf-8")
                code, _ = self.run_cmd("install", "--apply", confirm=lambda q: True)
                self.assertEqual(code, 2)
                self.assertEqual(self.settings.read_text(encoding="utf-8"), bad)
        self.assertEqual(self.backups(), [])

    def test_installed_command_runs_the_preview_only_hook(self):
        self.run_cmd("install", "--apply", confirm=lambda q: True)
        command = self.ours()[0]["command"]
        payload = json.loads((FIXTURES / "stop_payload.json").read_text(encoding="utf-8"))
        payload["transcript_path"] = str(FIXTURES / "synthetic_transcript.jsonl")
        proc = subprocess.run(["/bin/sh", "-c", command], input=json.dumps(payload), capture_output=True,
                              text=True, timeout=60, env={**os.environ, "PYTHONPATH": ""})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")  # a Stop hook must keep stdout empty
        self.assertEqual(len(list(self.preview.glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
