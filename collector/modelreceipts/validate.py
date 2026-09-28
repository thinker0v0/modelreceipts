"""Tiny stdlib-only JSON Schema validator for the ModelReceipts record schema.

It implements only the draft 2020-12 keywords the record schema uses, and it
FAILS LOUDLY on any other keyword, so the schema cannot silently outgrow it.
If the third-party ``jsonschema`` package is installed, the test-suite also
cross-checks results against it.

The schema is chosen per document: ``kind: "seed_cell"`` -> seed-cell schema,
otherwise ``schema_version`` 0.1.0 / 0.2.0 -> the matching record schema.

CLI::

    python3 -m modelreceipts validate schema/examples/*.json
    python3 -m modelreceipts validate --allow-seed-cells seeds/out/*.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from . import SCHEMA_DIR, SCHEMA_FILES

# Keywords that carry no validation meaning here.
_ANNOTATIONS = {"$schema", "$id", "$defs", "$comment", "title", "description", "default", "examples"}
_SUPPORTED = {
    "type", "enum", "const", "properties", "required", "additionalProperties",
    "items", "maxItems", "minItems", "uniqueItems", "pattern", "minLength", "maxLength",
    "minimum", "maximum", "format", "$ref", "anyOf", "allOf", "if", "then", "else",
}
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class SchemaError(Exception):
    """The schema uses something this mini validator does not implement."""


def _is_type(value: Any, name: str) -> bool:
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise SchemaError(f"unknown type {name!r}")


def _json_equal(a: Any, b: Any) -> bool:
    # JSON equality: booleans are not numbers.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def _check_format(value: str, fmt: str) -> bool:
    if fmt == "date-time":
        if "T" not in value and "t" not in value:
            return False
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
        except ValueError:
            return False
        return dt.tzinfo is not None  # RFC 3339 requires an offset
    if fmt == "uuid":
        return bool(_UUID_RE.match(value))
    raise SchemaError(f"unsupported format {fmt!r}")


class Validator:
    def __init__(self, schema: dict):
        self.root = schema

    def _resolve(self, ref: str) -> dict:
        if not ref.startswith("#/"):
            raise SchemaError(f"only local refs are supported, got {ref!r}")
        node: Any = self.root
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    def iter_errors(self, instance: Any, schema: dict | None = None, path: str = "$") -> Iterator[str]:
        schema = self.root if schema is None else schema
        if schema is True:
            return
        if schema is False:
            yield f"{path}: not allowed"
            return
        for key in schema:
            if key not in _SUPPORTED and key not in _ANNOTATIONS and not key.startswith("x-"):
                raise SchemaError(f"unsupported keyword {key!r} at {path}")

        if "$ref" in schema:
            yield from self.iter_errors(instance, self._resolve(schema["$ref"]), path)

        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is_type(instance, t) for t in types):
                yield f"{path}: expected type {'|'.join(types)}, got {type(instance).__name__}"
                return  # further checks would only add noise

        if "const" in schema and not _json_equal(instance, schema["const"]):
            yield f"{path}: must equal {schema['const']!r}"
        if "enum" in schema and not any(_json_equal(instance, e) for e in schema["enum"]):
            yield f"{path}: {instance!r} not in {schema['enum']}"

        if isinstance(instance, str):
            if "pattern" in schema and not re.search(schema["pattern"], instance):
                yield f"{path}: {instance!r} does not match {schema['pattern']}"
            if "minLength" in schema and len(instance) < schema["minLength"]:
                yield f"{path}: shorter than {schema['minLength']}"
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                yield f"{path}: longer than {schema['maxLength']}"
            if "format" in schema and not _check_format(instance, schema["format"]):
                yield f"{path}: {instance!r} is not a valid {schema['format']}"

        if _is_type(instance, "number"):
            if "minimum" in schema and instance < schema["minimum"]:
                yield f"{path}: {instance} < minimum {schema['minimum']}"
            if "maximum" in schema and instance > schema["maximum"]:
                yield f"{path}: {instance} > maximum {schema['maximum']}"

        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                yield f"{path}: fewer than {schema['minItems']} items"
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                yield f"{path}: more than {schema['maxItems']} items"
            if schema.get("uniqueItems"):
                seen = [json.dumps(v, sort_keys=True) for v in instance]
                if len(seen) != len(set(seen)):
                    yield f"{path}: items are not unique"
            if "items" in schema:
                for i, item in enumerate(instance):
                    yield from self.iter_errors(item, schema["items"], f"{path}[{i}]")

        if isinstance(instance, dict):
            for req in schema.get("required", []):
                if req not in instance:
                    yield f"{path}: missing required property {req!r}"
            props = schema.get("properties", {})
            for key, value in instance.items():
                if key in props:
                    yield from self.iter_errors(value, props[key], f"{path}.{key}")
                elif schema.get("additionalProperties") is False:
                    yield f"{path}: unexpected property {key!r}"

        for sub in schema.get("allOf", []):
            yield from self.iter_errors(instance, sub, path)
        if "anyOf" in schema:
            if not any(not list(self.iter_errors(instance, sub, path)) for sub in schema["anyOf"]):
                yield f"{path}: does not match any allowed alternative"
        if "if" in schema:
            branch = "then" if not list(self.iter_errors(instance, schema["if"], path)) else "else"
            if branch in schema:
                yield from self.iter_errors(instance, schema[branch], path)

    def errors(self, instance: Any) -> list[str]:
        return list(self.iter_errors(instance))


class AutoValidator:
    """Pick the schema per document from ``kind`` / ``schema_version``."""

    def __init__(self, versions: tuple[str, ...] = ("0.1.0", "0.2.0"), allow_seed_cells: bool = False,
                 schema_dir: Path = SCHEMA_DIR):
        self.versions = versions
        self.allow_seed_cells = allow_seed_cells
        self.schema_dir = Path(schema_dir)
        self._cache: dict[tuple[str, str], Validator] = {}

    def schema_key(self, instance: Any) -> tuple[str, str] | None:
        if not isinstance(instance, dict):
            return None
        kind = "seed_cell" if instance.get("kind") == "seed_cell" else "record"
        return kind, str(instance.get("schema_version"))

    def _validator(self, key: tuple[str, str]) -> Validator:
        if key not in self._cache:
            with open(self.schema_dir / SCHEMA_FILES[key], encoding="utf-8") as fh:
                self._cache[key] = Validator(json.load(fh))
        return self._cache[key]

    def errors(self, instance: Any) -> list[str]:
        key = self.schema_key(instance)
        if key is None:
            return ["$: expected a JSON object"]
        if key[0] == "seed_cell" and not self.allow_seed_cells:
            return ["$.kind: seed cells are not accepted here"]
        if key not in SCHEMA_FILES or (key[0] == "record" and key[1] not in self.versions):
            allowed = [v for (k, v) in SCHEMA_FILES if k == key[0] and (k != "record" or v in self.versions)]
            return [f"$.schema_version: {key[1]!r} is not supported for {key[0]} (supported: {allowed})"]
        return self._validator(key).errors(instance)


def load_validator(schema_path: Path | str | None = None, **kwargs):
    """A fixed-schema ``Validator`` if ``schema_path`` is given, else an ``AutoValidator``."""
    if schema_path is None:
        return AutoValidator(**kwargs)
    with open(schema_path, encoding="utf-8") as fh:
        return Validator(json.load(fh))


def iter_documents(path: Path) -> Iterator[tuple[str, Any]]:
    """Yield (label, document) from a .json file or each line of a .jsonl file."""
    if path.suffix == ".jsonl":
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if line.strip():
                    yield f"{path}:{i}", json.loads(line)
    else:
        with open(path, encoding="utf-8") as fh:
            yield str(path), json.load(fh)


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="modelreceipts validate",
        description="Validate record / seed-cell JSON (.json) or JSON Lines (.jsonl) files. "
                    "The schema is picked per document from kind/schema_version unless --schema is given.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--schema", type=Path, help="force one schema file for every document")
    parser.add_argument("--allow-seed-cells", action="store_true", help="accept kind=seed_cell documents")
    parser.add_argument("--only-version", choices=["0.1.0", "0.2.0"], help="reject records of other versions")
    parser.add_argument("--quiet", action="store_true", help="print failures and the summary only")
    args = parser.parse_args(argv)

    if args.schema:
        validator = load_validator(args.schema)
    else:
        versions = (args.only_version,) if args.only_version else ("0.1.0", "0.2.0")
        validator = load_validator(versions=versions, allow_seed_cells=args.allow_seed_cells)
    total = failed = 0
    for path in args.files:
        try:
            docs = list(iter_documents(path))
        except (OSError, json.JSONDecodeError) as exc:
            docs = [(str(path), exc)]
        for label, doc in docs:
            total += 1
            errs = [f"cannot read: {doc}"] if isinstance(doc, Exception) else validator.errors(doc)
            if errs:
                failed += 1
                print(f"FAIL {label}")
                for e in errs:
                    print(f"  - {e}")
            elif not args.quiet:
                version = doc.get("schema_version") if isinstance(doc, dict) else "?"
                kind = "seed_cell" if isinstance(doc, dict) and doc.get("kind") == "seed_cell" else "record"
                print(f"OK   {label}  ({kind} {version})")
    print(f"{total - failed}/{total} valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
