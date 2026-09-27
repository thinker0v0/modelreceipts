"""Parse the tiny YAML subset used by Aider's leaderboard files, stdlib only.

Supported: a top-level list of flat mappings (``- key: value`` / ``  key: value``),
blank lines, full-line and trailing ``#`` comments, single/double-quoted
strings, ints, floats, booleans and null. Anything else raises ``ValueError``
so a format change upstream fails loudly instead of being misread.

Scalar resolution follows PyYAML's YAML 1.1 rules for the cases that appear in
the file (e.g. ``8e3`` stays a string, ``2025-01-17`` is a date). Dates are
returned as ISO strings. The test-suite cross-checks against PyYAML when it is
installed.
"""

from __future__ import annotations

import json
import re

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:[ \t]+(.*))?$")
_INT_RE = re.compile(r"^[-+]?(?:0|[1-9][0-9_]*)$")
_FLOAT_RE = re.compile(r"^[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*(?:[eE][-+][0-9]+)?$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_DQ_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"[ \t]*(?:#.*)?$')
_SQ_RE = re.compile(r"^'((?:[^']|'')*)'[ \t]*(?:#.*)?$")


def _scalar(text: str, lineno: int):
    text = text.strip()
    if text.startswith('"'):
        m = _DQ_RE.match(text)
        if not m:
            raise ValueError(f"line {lineno}: unterminated double-quoted string")
        return json.loads('"' + m.group(1) + '"')
    if text.startswith("'"):
        m = _SQ_RE.match(text)
        if not m:
            raise ValueError(f"line {lineno}: unterminated single-quoted string")
        return m.group(1).replace("''", "'")
    # A comment starts at '#' preceded by whitespace.
    text = re.split(r"[ \t]+#", text, maxsplit=1)[0].strip()
    if text.startswith("#"):
        text = ""
    if text in {"", "~", "null", "Null", "NULL"}:
        return None
    if text in {"true", "True", "TRUE"}:
        return True
    if text in {"false", "False", "FALSE"}:
        return False
    if text[0] in "[{&*!|>%@`":
        raise ValueError(f"line {lineno}: unsupported YAML value {text[:20]!r}")
    if _INT_RE.match(text):
        return int(text.replace("_", ""))
    if _FLOAT_RE.match(text) and text not in {".", "+.", "-."}:
        return float(text.replace("_", ""))
    if _DATE_RE.match(text):
        return text
    if re.search(r":[ \t]", text):
        raise ValueError(f"line {lineno}: nested mapping is not supported")
    return text


def parse_list_of_maps(text: str) -> list[dict]:
    rows: list[dict] = []
    current: dict | None = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("- "):
            current = {}
            rows.append(current)
            body = line[2:]
        elif line.startswith("  ") and not line.startswith("   ") and current is not None:
            body = line[2:]
        else:
            raise ValueError(f"line {lineno}: unsupported YAML structure")
        m = _KEY_RE.match(body)
        if not m:
            raise ValueError(f"line {lineno}: expected 'key: value'")
        key, value = m.group(1), m.group(2) or ""
        if key in current:
            raise ValueError(f"line {lineno}: duplicate key {key!r}")
        current[key] = _scalar(value, lineno)
    return rows
