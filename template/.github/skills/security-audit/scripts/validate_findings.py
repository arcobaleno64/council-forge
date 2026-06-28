#!/usr/bin/env python3
"""Validate a security-audit findings.json against report-schema.json.

Stdlib reimplementation of the upstream validate-findings.cjs (cloudflare/
security-audit-skill, MIT — see ../NOTICE), matching council-forge's CLI-first,
dependency-light convention. It reads report-schema.json directly (the single
source of truth) and interprets the JSON-Schema subset the schema uses:
type / const / enum / required / properties / additionalProperties:false /
items / minItems / oneOf — plus the one prose rule the schema documents but
cannot express: a confirmed finding's trace must start with an 'entrypoint'
step and end with a 'sink' step.

findings.json may be either a JSON array of finding objects, or an object with a
top-level "findings" array. Each finding must match output_schema.oneOf
(a 'confirmed' object with all required fields, or a 'rejected' object).

Exit 0 = valid, 1 = schema violation(s), 2 = usage/IO error (fail-closed).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_ERROR = 2

SCHEMA_DEFAULT = Path(__file__).resolve().parent.parent / "report-schema.json"

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def _type_ok(value: Any, t: str) -> bool:
    py = _TYPE_MAP[t]
    if t == "integer":
        # JSON has no int/float distinction for floats like 1.0; bools are not ints here
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    return isinstance(value, py)


def validate(value: Any, schema: dict, path: str, errors: List[str]) -> None:
    """Validate value against a JSON-Schema-subset node, appending dotted-path errors."""
    if "oneOf" in schema:
        branch_errors = []
        matches = 0
        for i, sub in enumerate(schema["oneOf"]):
            local: List[str] = []
            validate(value, sub, path, local)
            if not local:
                matches += 1
            else:
                branch_errors.append((i, local))
        if matches != 1:
            errors.append(
                f"{path or '<root>'}: must match exactly one schema branch "
                f"(matched {matches}); branch errors: {branch_errors}"
            )
        return

    t = schema.get("type")
    if t and not _type_ok(value, t):
        errors.append(f"{path or '<root>'}: expected type {t}, got {type(value).__name__}")
        return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path or '<root>'}: must equal {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path or '<root>'}: {value!r} not in enum {schema['enum']}")

    if t == "object" and isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path or '<root>'}: missing required field '{req}'")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path or '<root>'}: unexpected field '{key}'")
        for key, sub in props.items():
            if key in value:
                validate(value[key], sub, f"{path}.{key}" if path else key, errors)

    if t == "array" and isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path or '<root>'}: needs >= {schema['minItems']} items, got {len(value)}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                validate(item, item_schema, f"{path}[{i}]", errors)


def check_trace_endpoints(finding: dict, path: str, errors: List[str]) -> None:
    """Schema-documented prose rule: trace starts at an entrypoint, ends at a sink."""
    trace = finding.get("trace")
    if isinstance(trace, list) and trace:
        first, last = trace[0], trace[-1]
        if isinstance(first, dict) and first.get("kind") != "entrypoint":
            errors.append(f"{path}.trace[0]: first step must be kind 'entrypoint'")
        if isinstance(last, dict) and last.get("kind") != "sink":
            errors.append(f"{path}.trace[-1]: last step must be kind 'sink'")


def load_findings(payload: Any) -> List[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        return payload["findings"]
    raise ValueError("findings.json must be a JSON array, or an object with a 'findings' array")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate security-audit findings.json against report-schema.json")
    parser.add_argument("--findings", required=True, help="path to findings.json")
    parser.add_argument("--schema", default=str(SCHEMA_DEFAULT), help="path to report-schema.json")
    args = parser.parse_args(argv)

    try:
        schema_doc = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        finding_schema = schema_doc["output_schema"]
        payload = json.loads(Path(args.findings).read_text(encoding="utf-8"))
        findings = load_findings(payload)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot load inputs: {exc}", file=sys.stderr)
        return EXIT_ERROR

    errors: List[str] = []
    confirmed = rejected = 0
    for i, finding in enumerate(findings):
        path = f"findings[{i}]"
        validate(finding, finding_schema, path, errors)
        if isinstance(finding, dict) and finding.get("verdict") == "confirmed":
            confirmed += 1
            check_trace_endpoints(finding, path, errors)
        elif isinstance(finding, dict) and finding.get("verdict") == "rejected":
            rejected += 1

    print(f"findings: {len(findings)} ({confirmed} confirmed, {rejected} rejected)")
    if errors:
        print(f"[FAIL] {len(errors)} schema violation(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return EXIT_INVALID
    print("[OK] findings.json conforms to report-schema.json")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
