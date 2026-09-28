"""Schema v0.2, migration, validator dispatch, local signals and the next-prompt
retry backfill. All inputs are SYNTHETIC. Run from repo root:

    python3 -m unittest discover -s collector/tests
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

COLLECTOR = Path(__file__).resolve().parents[1]
REPO = COLLECTOR.parent
sys.path.insert(0, str(COLLECTOR))

from modelreceipts import SCHEMA_DIR, SCHEMA_FILES  # noqa: E402
from modelreceipts.hook import main as hook_main  # noqa: E402
from modelreceipts.migrate import main as migrate_main  # noqa: E402
from modelreceipts.migrate import migrate_record  # noqa: E402
from modelreceipts.signals import detect_retry, extract_claim, near_duplicate  # noqa: E402
from modelreceipts.validate import load_validator  # noqa: E402
from modelreceipts.validate import main as validate_main  # noqa: E402

EXAMPLES = REPO / "schema" / "examples"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


class PackagedSchemaTest(unittest.TestCase):
    def test_packaged_copies_are_identical(self):
        for name in SCHEMA_FILES.values():
            with self.subTest(schema=name):
                self.assertEqual((REPO / "schema" / name).read_bytes(),
                                 (COLLECTOR / "modelreceipts" / "schemas" / name).read_bytes())

    def test_repo_schema_dir_is_used_in_a_checkout(self):
        self.assertEqual(SCHEMA_DIR, REPO / "schema")


class ValidatorDispatchTest(unittest.TestCase):
    def setUp(self):
        self.v = load_validator()
        self.rec = _load(EXAMPLES / "01-stop-hook-bugfix-tests-passed.json")

    def test_both_versions_accepted_by_default(self):
        self.assertEqual(self.v.errors(self.rec), [])
        self.assertEqual(self.v.errors(_load(EXAMPLES / "v0.1" / "01-stop-hook-bugfix-tests-passed.json")), [])

    def test_version_restriction_and_unknown_versions(self):
        only02 = load_validator(versions=("0.2.0",))
        self.assertTrue(only02.errors(_load(EXAMPLES / "v0.1" / "01-stop-hook-bugfix-tests-passed.json")))
        bad = dict(self.rec, schema_version="9.9.9")
        self.assertIn("not supported", self.v.errors(bad)[0])
        self.assertEqual(self.v.errors([1, 2]), ["$: expected a JSON object"])

    def test_seed_cells_only_when_allowed(self):
        cell = _load(EXAMPLES / "seed-cells" / "preference-cell.json")
        self.assertTrue(self.v.errors(cell))
        self.assertEqual(load_validator(allow_seed_cells=True).errors(cell), [])

    def test_v02_rules(self):
        cases = {
            "server cost in body": lambda r: r["usage"].__setitem__("cost_usd_server", 0.1),
            "signature in body": lambda r: r["source"].__setitem__("install_key_sig", "abc"),
            "missing retry_detector": lambda r: r["outcome"]["evidence"].pop("retry_detector"),
            "self_assessment without extractor": lambda r: r["outcome"].__setitem__(
                "self_assessment", {"score": 1, "rater": "self_claim", "judge_model": None}),
            "unknown rater": lambda r: r["outcome"].__setitem__(
                "self_assessment", {"score": 1, "rater": "vibes", "judge_model": None, "extractor": None}),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label):
                r = json.loads(json.dumps(self.rec))
                mutate(r)
                self.assertTrue(self.v.errors(r))
        nullable = json.loads(json.dumps(self.rec))
        nullable["outcome"]["evidence"].update(committed=None, tool_error_count=None, test_runs=None)
        nullable["usage"].update(turns=None, input_tokens=None)
        self.assertEqual(self.v.errors(nullable), [])

    def test_validate_cli_reads_jsonl(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            f = tmp / "recs.jsonl"
            f.write_text(json.dumps(self.rec) + "\n" + json.dumps(dict(self.rec, schema_version="x")) + "\n")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(validate_main([str(f)]), 1)
            self.assertIn("1/2 valid", out.getvalue())
        finally:
            shutil.rmtree(tmp)


class MigrationTest(unittest.TestCase):
    def test_examples_migrate_to_valid_v02_without_touching_input(self):
        v = load_validator(versions=("0.2.0",))
        for p in sorted((EXAMPLES / "v0.1").glob("*.json")):
            before = p.read_bytes()
            new, _notes = migrate_record(_load(p))
            with self.subTest(example=p.name):
                self.assertEqual(new["schema_version"], "0.2.0")
                self.assertEqual(new["record_id"], _load(p)["record_id"])
                self.assertEqual(v.errors(new), [])
                self.assertEqual(p.read_bytes(), before)

    def test_seed_placeholders_become_null_but_field_reports_keep_values(self):
        seed = _load(EXAMPLES / "v0.1" / "01-stop-hook-bugfix-tests-passed.json")
        seed["source"].update(source_type="benchmark", collector="seed-import")
        seed["outcome"]["evidence"].update(committed=False, tool_error_count=0)
        seed["usage"].update(turns=0, input_tokens=0, output_tokens=5)
        new, notes = migrate_record(seed)
        self.assertIsNone(new["outcome"]["evidence"]["committed"])
        self.assertIsNone(new["outcome"]["evidence"]["tool_error_count"])
        self.assertIsNone(new["usage"]["turns"])
        self.assertIsNone(new["usage"]["input_tokens"])
        self.assertEqual(new["usage"]["output_tokens"], 5)
        self.assertTrue(any("seed" in n for n in notes))

        field = _load(EXAMPLES / "v0.1" / "01-stop-hook-bugfix-tests-passed.json")
        field["outcome"]["evidence"].update(committed=False, tool_error_count=0)
        new, _ = migrate_record(field)
        self.assertIs(new["outcome"]["evidence"]["committed"], False)
        self.assertEqual(new["outcome"]["evidence"]["tool_error_count"], 0)

    def test_server_cost_is_dropped_with_a_note_and_v02_is_idempotent(self):
        rec = _load(EXAMPLES / "v0.1" / "02-self-assessment-disagrees-with-evidence.json")
        new, notes = migrate_record(rec)
        self.assertIsNone(new["usage"]["cost_usd_server"])
        self.assertTrue(any("cost_usd_server" in n for n in notes))
        self.assertEqual(migrate_record(new), (new, []))
        with self.assertRaises(ValueError):
            migrate_record(dict(rec, schema_version="0.0.1"))

    def test_cli_writes_out_dir_and_refuses_in_place(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            src = tmp / "a.json"
            shutil.copy(EXAMPLES / "v0.1" / "01-stop-hook-bugfix-tests-passed.json", src)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(migrate_main([str(src), "--out-dir", str(tmp / "out")]), 0)
                self.assertEqual(_load(tmp / "out" / "a.json")["schema_version"], "0.2.0")
                self.assertEqual(migrate_main([str(src), "--out-dir", str(tmp)]), 1)
            self.assertEqual(_load(src)["schema_version"], "0.1.0")
        finally:
            shutil.rmtree(tmp)


class SignalsTest(unittest.TestCase):
    def test_retry_rules(self):
        retries = ["아직도 테스트가 실패해", "still failing with the same error", "그게 아니라 로그인 쪽을 고쳐줘",
                   "That's not what I asked for", "되돌려줘", "it doesn't work", "여전히 안 돼"]
        fresh = ["좋아, 이제 README 업데이트해줘", "Thanks! Now add a CSV export", "다음은 결제 모듈 리팩터링"]
        for t in retries:
            with self.subTest(prompt=t):
                self.assertTrue(detect_retry(t))
        for t in fresh:
            with self.subTest(prompt=t):
                self.assertFalse(detect_retry(t))

    def test_near_duplicate_prompt_counts_as_retry(self):
        prev = "fix the login redirect bug in auth service"
        self.assertTrue(near_duplicate("fix the login redirect bug in the auth service please", prev))
        self.assertTrue(detect_retry("fix the login redirect bug in the auth service please", prev))
        self.assertFalse(detect_retry("add dark mode to the settings page", prev))

    def test_claim_rules(self):
        self.assertEqual(extract_claim("I've fixed the bug and all tests pass."), 1.0)
        self.assertEqual(extract_claim("수정 완료했습니다. 테스트 모두 통과합니다."), 1.0)
        self.assertEqual(extract_claim("This should work now, but I haven't run the tests. Fixed."), 0.75)
        self.assertEqual(extract_claim("I couldn't get the integration test to pass."), 0.0)
        self.assertEqual(extract_claim("Fixed the parser, but the e2e test still fails."), 0.5)
        self.assertIsNone(extract_claim("Here is an overview of the repository layout."))
        self.assertIsNone(extract_claim(""))


def _entry(kind: str, uid: str, text: str, msg_id: str | None = None) -> str:
    if kind == "user":
        return json.dumps({"type": "user", "uuid": uid, "isSidechain": False,
                           "timestamp": "2026-09-27T09:00:00Z", "message": {"role": "user", "content": text}})
    return json.dumps({"type": "assistant", "uuid": uid, "isSidechain": False, "timestamp": "2026-09-27T09:00:05Z",
                       "message": {"id": msg_id, "role": "assistant", "model": "example-model-a",
                                   "content": [{"type": "text", "text": text}],
                                   "usage": {"input_tokens": 10, "output_tokens": 20}}})


class RetryBackfillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.transcript = self.tmp / "session.jsonl"
        self.preview = self.tmp / "preview"
        self.payload = self.tmp / "payload.json"
        self.payload.write_text(json.dumps({"transcript_path": str(self.transcript),
                                            "hook_event_name": "Stop"}), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _append(self, *lines: str):
        with open(self.transcript, "a", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line + "\n")

    def _hook(self) -> dict:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(hook_main(["--hook", "--payload", str(self.payload), "--preview-dir", str(self.preview)]), 0)
        state = next((self.preview / ".state").glob("*.json"))
        rid = json.loads(state.read_text(encoding="utf-8"))["record_id"]
        return _load(self.preview / f"{rid}.json")

    def test_next_prompt_fills_previous_record_only(self):
        self._append(_entry("user", "u1", "Fix the crash in the parser module"),
                     _entry("assistant", "a1", "Fixed. All tests pass.", "m1"))
        first = self._hook()
        self.assertIsNone(first["outcome"]["evidence"]["user_retry_next_prompt"])
        self.assertEqual(first["outcome"]["self_assessment"],
                         {"score": 1.0, "rater": "self_claim", "judge_model": None, "extractor": "claim-rules-v1"})

        self._append(_entry("user", "u2", "아직도 같은 에러가 나. 다시 고쳐줘"),
                     _entry("assistant", "a2", "I couldn't reproduce it.", "m2"))
        second = self._hook()
        prev = _load(self.preview / f"{first['record_id']}.json")
        self.assertIs(prev["outcome"]["evidence"]["user_retry_next_prompt"], True)
        self.assertEqual(prev["outcome"]["evidence"]["retry_detector"], "retry-rules-v1")
        self.assertEqual(load_validator().errors(prev), [])
        self.assertIsNone(second["outcome"]["evidence"]["user_retry_next_prompt"])
        self.assertEqual(second["outcome"]["self_assessment"]["score"], 0.0)
        # No text from the transcript reaches any preview file.
        for p in self.preview.glob("*.json"):
            body = p.read_text(encoding="utf-8")
            self.assertNotIn("parser module", body)
            self.assertNotIn("같은 에러", body)

    def test_new_task_is_not_a_retry_and_refire_does_not_touch_it(self):
        self._append(_entry("user", "u1", "Add a CSV export endpoint"), _entry("assistant", "a1", "Done.", "m1"))
        first = self._hook()
        self._hook()  # the Stop hook fired again for the same turn: nothing to fill
        self.assertIsNone(_load(self.preview / f"{first['record_id']}.json")["outcome"]["evidence"]["user_retry_next_prompt"])
        # the re-fire wrote a second preview for the same turn; the state now points at it
        state = json.loads(next((self.preview / ".state").glob("*.json")).read_text(encoding="utf-8"))
        self._append(_entry("user", "u2", "Thanks! Now update the README"), _entry("assistant", "a2", "Updated.", "m2"))
        self._hook()
        prev = _load(self.preview / f"{state['record_id']}.json")
        self.assertIs(prev["outcome"]["evidence"]["user_retry_next_prompt"], False)


if __name__ == "__main__":
    unittest.main()
