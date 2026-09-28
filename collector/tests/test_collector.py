"""Tests for the collector (dry-run hook + opt-in submit). Run from repo root:

    python3 -m unittest discover -s collector/tests -v
"""

from __future__ import annotations

import ast
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

COLLECTOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COLLECTOR))

from modelreceipts import DEFAULT_SCHEMA_PATH  # noqa: E402
from modelreceipts.classify import classify  # noqa: E402
from modelreceipts.hook import main as hook_main  # noqa: E402
from modelreceipts.hook import run  # noqa: E402
from modelreceipts.submit import main as submit_main  # noqa: E402
from modelreceipts.record import build_record, detect_route  # noqa: E402
from modelreceipts.transcript import TurnSummary, summarize_file, summarize_last_turn  # noqa: E402
from modelreceipts.validate import load_validator  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TRANSCRIPT = FIXTURES / "synthetic_transcript.jsonl"
FIXED_NOW = datetime(2026, 9, 27, 9, 1, tzinfo=timezone.utc)
FIXED_ID = "11111111-2222-4333-8444-555555555555"


def load_payload() -> dict:
    payload = json.loads((FIXTURES / "stop_payload.json").read_text(encoding="utf-8"))
    payload["transcript_path"] = str(TRANSCRIPT)
    return payload


class TranscriptParsingTest(unittest.TestCase):
    def setUp(self):
        self.s = summarize_file(str(TRANSCRIPT))

    def test_only_last_turn_is_counted(self):
        self.assertEqual(self.s.prior_prompts, 1)
        self.assertIn("로그인 테스트가 실패해", self.s.prompt_text)
        self.assertNotIn("claude-sidechain-model", self.s.models)  # sidechain ignored

    def test_usage_dedupes_streamed_message_lines(self):
        self.assertEqual(self.s.api_calls, 7)
        self.assertEqual(self.s.input_tokens, 40)
        self.assertEqual(self.s.output_tokens, 940)  # msg_A counted once, with its final 120
        self.assertEqual(self.s.cache_read_tokens, 164700)
        self.assertEqual(self.s.cache_write_tokens, 5150)
        self.assertEqual(self.s.context_tokens, 23010)

    def test_evidence_signals(self):
        self.assertEqual(len(self.s.test_calls), 2)
        self.assertTrue(self.s.tests_passed)  # last test run passed
        self.assertTrue(self.s.committed)
        self.assertEqual(self.s.tool_error_count, 1)
        self.assertEqual(self.s.files_touched, 2)
        self.assertEqual(self.s.latency_ms, 42000)
        self.assertEqual(self.s.tools_used, ["Bash", "Edit", "Read"])

    def test_failed_last_test_run_and_failed_commit(self):
        lines = [
            json.dumps({"type": "user", "message": {"role": "user", "content": "fix the bug"}}),
            json.dumps({"type": "assistant", "message": {"id": "m1", "model": "claude-x", "usage": {"output_tokens": 1},
                        "content": [{"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "npm test"}},
                                    {"type": "tool_use", "id": "b", "name": "Bash", "input": {"command": "git commit -m x"}}]}}),
            json.dumps({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "a", "is_error": True, "content": "1 failing"},
                {"type": "tool_result", "tool_use_id": "b", "is_error": True, "content": "nothing to commit"}]}}),
        ]
        s = summarize_last_turn(lines)
        self.assertIs(s.tests_passed, False)
        self.assertFalse(s.committed)
        self.assertEqual(s.tool_error_count, 2)

    def test_no_tests_means_unknown_not_false(self):
        s = summarize_last_turn([json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}})])
        self.assertIsNone(s.tests_passed)
        self.assertEqual(s.api_calls, 0)


class ClassifierTest(unittest.TestCase):
    def _cls(self, prompt, edited=True, classifier=None, tools=()):
        from modelreceipts.transcript import ToolCall
        s = TurnSummary(prompt_text=prompt)
        if edited:
            s.tool_calls = [ToolCall(name="Edit", file_path="x.py")]
        s.tool_calls += [ToolCall(name=t) for t in tools]
        return classify(s, classifier=classifier)

    def test_default_classifier_is_recorded_version(self):
        from modelreceipts import CLASSIFIER_ID
        self.assertEqual(CLASSIFIER_ID, "rules-v1")

    def test_rules_v0_is_frozen(self):
        cases = {
            "로그인 버그 고쳐줘": "coding.bugfix",
            "Fix the failing CI job": "coding.bugfix",
            "Write unit tests for the parser": "coding.test",
            "이 모듈 리팩토링해줘": "coding.refactor",
            "Add a CSV export endpoint": "coding.feature",
            "Update the README": "coding.docs",
            "성능 최적화 해줘": "coding.performance",
            "Dockerfile 만들고 배포 파이프라인 구성": "coding.config_devops",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(self._cls(prompt, classifier="rules-v0"), ("coding", expected))
        self.assertEqual(self._cls("hello there", edited=False, classifier="rules-v0"), ("other", None))

    def test_rules_v1(self):
        cases = {
            "로그인 버그 고쳐줘": "coding.bugfix",
            "Fix the crash when the list is empty": "coding.bugfix",
            "Write unit tests for the parser": "coding.test",
            "Add regression tests for yesterday's bug": "coding.test",
            "이 모듈 리팩토링해줘": "coding.refactor",
            "Add a CSV export endpoint": "coding.feature",
            "README에 예시 추가해줘": "coding.docs",
            "성능 최적화 해줘": "coding.performance",
            "Dockerfile 만들고 배포 파이프라인 구성": "coding.config_devops",
            "Upgrade React to 18 and fix breaking changes": "coding.migration",
            "로그인 화면 레이아웃 정리해줘": "coding.ui",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(self._cls(prompt), ("coding", expected))

    def test_readonly_explain_and_review(self):
        self.assertEqual(self._cls("Explain how this function works", edited=False), ("coding", "coding.explain"))
        self.assertEqual(self._cls("코드 리뷰해 줘", edited=False), ("coding", "coding.review"))

    def test_non_coding_has_null_l2(self):
        self.assertEqual(self._cls("이 이메일 번역해 줘", edited=False), ("writing", None))
        self.assertEqual(self._cls("hello there", edited=False), ("conversation", None))
        self.assertEqual(self._cls("Write a haiku about rain", edited=False), ("creative", None))

    def test_bash_alone_is_not_coding(self):
        self.assertEqual(self._cls("다운로드 폴더 정리해줘", edited=False, tools=["Bash"]), ("agentic_ops", None))


class RecordTest(unittest.TestCase):
    def setUp(self):
        self.payload = load_payload()
        self.record = build_record(self.payload, summarize_file(str(TRANSCRIPT)), env={}, now=FIXED_NOW, record_id=FIXED_ID)

    def test_record_is_schema_valid(self):
        self.assertEqual(load_validator().errors(self.record), [])

    def test_record_content(self):
        r = self.record
        self.assertEqual((r["task"]["l1"], r["task"]["l2"]), ("coding", "coding.bugfix"))
        self.assertEqual(r["model"], {"provider": "anthropic", "id": "claude-opus-5-5", "route": "direct", "effort": "high"})
        self.assertEqual(r["source"]["client_version"], "2.1.200")
        self.assertEqual(r["usage"]["turns"], 7)
        ev = r["outcome"]["evidence"]
        self.assertEqual((ev["test_runs"], ev["tests_passed"], ev["committed"]), (2, True, True))
        # "Done! Everything works perfectly." -> the agent's own claim, isolated as self-assessment
        self.assertEqual(r["outcome"]["self_assessment"],
                         {"score": 1.0, "rater": "self_claim", "judge_model": None, "extractor": "claim-rules-v1"})
        self.assertEqual(r["submitted_at"], "2026-09-27T09:01:00Z")

    def test_no_text_paths_or_identifiers_leak(self):
        blob = json.dumps(self.record, ensure_ascii=False)
        for secret in ["CANARY", "alice", "secret-repo", "login.py", "로그인", "Everything works",
                       self.payload["session_id"], "pytest", "git commit"]:
            with self.subTest(secret=secret):
                self.assertNotIn(secret, blob)

    def test_route_detection(self):
        self.assertEqual(detect_route({}), "direct")
        self.assertEqual(detect_route({"CLAUDE_CODE_USE_BEDROCK": "1"}), "bedrock")
        self.assertEqual(detect_route({"ANTHROPIC_BASE_URL": "https://openrouter.ai/api"}), "openrouter")
        self.assertEqual(detect_route({"ANTHROPIC_BASE_URL": "http://localhost:4000"}), "proxy")


class HookCliTest(unittest.TestCase):
    def test_hook_run_end_to_end(self):
        record, errors = run(load_payload(), env={})
        self.assertEqual(errors, [])
        self.assertEqual(record["source"]["collector"], "stop-hook")

    def test_hook_mode_keeps_stdout_empty_and_exits_zero(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            payload_file = tmp / "payload.json"
            payload_file.write_text(json.dumps(load_payload()), encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = hook_main(["--hook", "--payload", str(payload_file), "--preview-dir", str(tmp / "prev")])
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("DRY RUN", err.getvalue())
            written = list((tmp / "prev").glob("*.json"))
            self.assertEqual(len(written), 1)
            self.assertEqual(load_validator().errors(json.loads(written[0].read_text(encoding="utf-8"))), [])
        finally:
            shutil.rmtree(tmp)

    def test_hook_mode_never_fails_on_bad_payload(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            bad = tmp / "bad.json"
            bad.write_text('{"transcript_path": "/nonexistent/x.jsonl"}', encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                self.assertEqual(hook_main(["--hook", "--payload", str(bad)]), 0)
            self.assertEqual(out.getvalue(), "")
        finally:
            shutil.rmtree(tmp)


class NoNetworkTest(unittest.TestCase):
    """The default path (hook / preview) must never send. Only submit.py may network, and only on --endpoint."""

    FORBIDDEN = {"socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp",
                 "ftplib", "smtplib", "telnetlib", "xmlrpc", "subprocess", "asyncio"}
    NETWORK_MODULE = "submit.py"

    @staticmethod
    def _imports(py: Path, top_level_only: bool = False):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        nodes = tree.body if top_level_only else ast.walk(tree)
        for node in nodes:
            if isinstance(node, ast.Import):
                yield from (a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                yield ("." * node.level) + node.module

    def test_only_submit_module_imports_network_code(self):
        for py in sorted((COLLECTOR / "modelreceipts").glob("*.py")):
            if py.name == self.NETWORK_MODULE:
                continue
            for name in self._imports(py):
                with self.subTest(file=py.name, module=name):
                    self.assertNotIn(name.lstrip(".").split(".")[0], self.FORBIDDEN)

    def test_submit_module_imports_network_lazily_and_never_spawns_processes(self):
        py = COLLECTOR / "modelreceipts" / self.NETWORK_MODULE
        top = {n.split(".")[0] for n in self._imports(py, top_level_only=True)}
        self.assertFalse(top & (self.FORBIDDEN - {"urllib"}), top)  # urllib.parse (no I/O) is fine
        self.assertNotIn("urllib.request", set(self._imports(py, top_level_only=True)))
        self.assertNotIn("subprocess", {n.split(".")[0] for n in self._imports(py)})

    def test_hook_never_imports_submit(self):
        names = set(self._imports(COLLECTOR / "modelreceipts" / "hook.py"))
        self.assertFalse({n for n in names if "submit" in n}, names)

    def test_default_hook_path_loads_no_network_modules_at_runtime(self):
        import subprocess  # test-only: a fresh interpreter shows what the hook really loads
        payload = json.dumps(load_payload())
        code = (
            "import sys, io, json, socket\n"
            "def boom(*a, **k): raise AssertionError('network used')\n"
            "socket.socket.connect = boom; socket.create_connection = boom\n"
            "del sys.modules['socket']\n"
            f"sys.path.insert(0, {str(COLLECTOR)!r})\n"
            "from modelreceipts.__main__ import main\n"
            "sys.stdin = io.StringIO(sys.argv[1])\n"
            "rc = main(['hook'])\n"
            "bad = sorted(m for m in sys.modules if m in {'socket','ssl','http.client','urllib.request','modelreceipts.submit'})\n"
            "print(json.dumps({'rc': rc, 'bad': bad}), file=sys.stderr)\n"
        )
        proc = subprocess.run([sys.executable, "-c", code, payload], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stderr.strip().splitlines()[-1])
        self.assertEqual(result, {"rc": 0, "bad": []})
        self.assertIn('"schema_version": "0.2.0"', proc.stdout)


class _Capture(BaseHTTPRequestHandler):
    received: list = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        type(self).received.append((self.path, self.headers, json.loads(body), body))
        out = json.dumps({"status": "stored"}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


class SubmitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.record_file = self.tmp / "record.json"
        self.record_file.write_text((DEFAULT_SCHEMA_PATH.parent / "examples" / "01-stop-hook-bugfix-tests-passed.json")
                                    .read_text(encoding="utf-8"), encoding="utf-8")
        self.id_file = self.tmp / "state" / "install_key"
        self.calls = []
        import socket
        import urllib.request
        self._patches = [(socket.socket, "connect", socket.socket.connect),
                         (urllib.request, "urlopen", urllib.request.urlopen)]

    def tearDown(self):
        for obj, name, orig in self._patches:
            setattr(obj, name, orig)
        shutil.rmtree(self.tmp)

    def _block_network(self):
        def boom(*a, **k):
            self.calls.append(a)
            raise AssertionError("network used")
        for obj, name, _ in self._patches:
            setattr(obj, name, boom)

    def _run(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = submit_main(["--record", str(self.record_file), "--key-file", str(self.id_file), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_without_endpoint_it_previews_and_sends_nothing(self):
        self._block_network()
        code, out, err = self._run()
        self.assertEqual(code, 0)
        self.assertIn("PREVIEW", err)
        self.assertIn("not sent", err)
        self.assertEqual(json.loads(out)["record_id"], "5b1f7c2e-9a41-4d3e-8c0a-2f6b9e1d4a10")
        self.assertEqual(self.calls, [])
        self.assertFalse(self.id_file.exists())

    def test_payload_path_previews_without_endpoint(self):
        self._block_network()
        payload_file = self.tmp / "payload.json"
        payload_file.write_text(json.dumps(load_payload()), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = submit_main(["--payload", str(payload_file)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["task"]["l2"], "coding.bugfix")
        self.assertEqual(self.calls, [])

    def test_non_loopback_endpoint_is_refused_by_default(self):
        self._block_network()
        for url in ("https://example.com", "http://10.0.0.5:8787", "ftp://127.0.0.1"):
            with self.subTest(url=url):
                code, _, err = self._run("--endpoint", url)
                self.assertEqual(code, 2)
                self.assertIn("not sent", err)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.id_file.exists())

    def test_invalid_record_is_never_sent(self):
        self._block_network()
        bad = json.loads(self.record_file.read_text(encoding="utf-8"))
        bad["prompt"] = "leak"
        self.record_file.write_text(json.dumps(bad), encoding="utf-8")
        code, _, err = self._run("--endpoint", "http://127.0.0.1:9")
        self.assertEqual(code, 1)
        self.assertIn("not sending", err)
        self.assertEqual(self.calls, [])

    def test_with_endpoint_it_sends_exactly_the_preview_once(self):
        _Capture.received = []
        httpd = HTTPServer(("127.0.0.1", 0), _Capture)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            code, out, err = self._run("--endpoint", f"http://127.0.0.1:{httpd.server_address[1]}")
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(_Capture.received), 1)
        path, headers, body, raw = _Capture.received[0]
        self.assertEqual(path, "/v1/records")
        self.assertEqual(body, json.loads(out))
        from modelreceipts.signing import load_key, verify_request
        key = load_key(self.id_file)
        self.assertEqual(verify_request(dict(headers), "POST", "/v1/records", raw), key.public)
        self.assertEqual(self.id_file.stat().st_mode & 0o777, 0o600)
        secret_b64 = json.loads(self.id_file.read_text())["secret"]
        self.assertNotIn(secret_b64, "".join(f"{k}{v}" for k, v in headers.items()) + raw.decode())
        self.assertIsNone(headers.get("X-ModelReceipts-Install"))
        self.assertIn("-> 201", err)


class SchemaExamplesTest(unittest.TestCase):
    EXAMPLES = sorted((DEFAULT_SCHEMA_PATH.parent / "examples").glob("*.json"))

    def _mutations(self, base: dict):
        def m(fn):
            r = json.loads(json.dumps(base))
            fn(r)
            return r
        yield "extra top-level prompt field", m(lambda r: r.__setitem__("prompt", "hello"))
        yield "content_included true", m(lambda r: r["privacy"].__setitem__("content_included", True))
        yield "non-coding L1 with coding L2", m(lambda r: r["task"].__setitem__("l1", "writing"))
        yield "unknown L2", m(lambda r: r["task"].__setitem__("l2", "coding.vibes"))
        yield "missing evidence", m(lambda r: r["outcome"].pop("evidence"))
        yield "self score > 1", m(lambda r: r["outcome"].__setitem__("self_assessment", {"score": 1.5, "rater": "self_llm", "judge_model": None}))
        yield "bad uuid", m(lambda r: r.__setitem__("record_id", "not-a-uuid"))
        yield "bool as token count", m(lambda r: r["usage"].__setitem__("turns", True))
        yield "path in tools_used", m(lambda r: r["method"].__setitem__("tools_used", ["/home/alice/x"]))

    def test_examples_exist_and_are_valid(self):
        self.assertGreaterEqual(len(self.EXAMPLES), 2)
        v = load_validator()
        for path in self.EXAMPLES:
            with self.subTest(example=path.name):
                self.assertEqual(v.errors(json.loads(path.read_text(encoding="utf-8"))), [])

    def test_invalid_mutations_are_rejected(self):
        v = load_validator()
        base = json.loads(self.EXAMPLES[0].read_text(encoding="utf-8"))
        for label, bad in self._mutations(base):
            with self.subTest(mutation=label):
                self.assertTrue(v.errors(bad), f"should be invalid: {label}")

    def test_agrees_with_reference_jsonschema_if_installed(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed (optional cross-check)")
        from modelreceipts import SCHEMA_DIR
        mine = load_validator(allow_seed_cells=True)
        groups = {
            "record.v0.2.schema.json": self.EXAMPLES,
            "record.v0.1.schema.json": sorted((self.EXAMPLES[0].parent / "v0.1").glob("*.json")),
            "seed_cell.v0.2.schema.json": sorted(self.EXAMPLES[0].parent.glob("seed-cells/*.json")),
        }
        for schema_file, files in groups.items():
            schema = json.loads((SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
            ref = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
            samples = [(p.name, json.loads(p.read_text(encoding="utf-8"))) for p in files]
            if files and schema_file.startswith("record"):
                samples += list(self._mutations(json.loads(files[0].read_text(encoding="utf-8"))))
            for label, inst in samples:
                with self.subTest(schema=schema_file, sample=label):
                    self.assertEqual(bool(mine.errors(inst)), any(True for _ in ref.iter_errors(inst)))


if __name__ == "__main__":
    unittest.main()
