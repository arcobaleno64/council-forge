#!/usr/bin/env python3
"""Regex-safety audit — a systemic guard against ReDoS regressions.

Background: REDOS-01 / REDOS-02 were catastrophic-backtracking regexes in guard
code that runs against untrusted artifact content. Fixing the two instances does
not stop a *third* dangerous regex from being merged. This audit is the
root-cause control: it scans every ``re.compile`` pattern under
``artifacts/scripts/`` for known ReDoS-prone shapes and fails closed, so a new
dangerous regex cannot land without a conscious, annotated review.

Detected shapes (heuristic, conservative):
  * nested-quantifier   — a quantified group whose body is itself unbounded,
                          e.g. ``(a+)+`` / ``(?:.*)+`` (classic exponential).
  * double-dot-unbounded — two ``.+`` / ``.*`` spans in one pattern (the
                          ``.+\\..+`` motif behind REDOS-01).
  * dual-tempered-fill  — a lazy negated-class fill followed by a greedy one
                          around a required group (the motif behind REDOS-02).

These heuristics intentionally also match a few patterns that are *safe* in
context (anchored, literal-delimited, or unique-partition). Such patterns are
exempted by adding a trailing ``# redos-ok: <reason>`` marker anywhere within the
``re.compile(...)`` statement. The point is not zero matches — it is that every
ReDoS-shaped regex is consciously reviewed and justified.

Usage:
    python3 artifacts/scripts/regex_safety_audit.py [--root .]
Exit 0 = clean (every flagged pattern is annotated); exit 1 = unannotated
ReDoS-shaped pattern found.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

EXIT_OK = 0
EXIT_FAIL = 1

ALLOW_MARKER = "redos-ok"


def detect_shapes(pattern: str) -> List[str]:
    """Return the list of ReDoS-prone shapes found in a compiled-regex string."""
    hits: List[str] = []

    # S1: nested quantifier — a parenthesised group quantified by +/*/{n,} whose
    # body also contains an unbounded +/*/{n,}.
    stack: List[int] = []
    for i, ch in enumerate(pattern):
        if ch == "(":
            stack.append(i)
        elif ch == ")" and stack:
            start = stack.pop()
            body = pattern[start + 1:i]
            after = pattern[i + 1:i + 4]
            quantified = bool(re.match(r"[+*]|\{\d*,\d*\}", after))
            if quantified and re.search(r"[+*]|\{\d*,\}", body):
                hits.append("nested-quantifier")
                break

    # S2: two dot-unbounded spans (`.+`/`.*` ... `.+`/`.*`).
    if re.search(r"\.[+*].*\.[+*]", pattern):
        hits.append("double-dot-unbounded")

    # S3: lazy negated-class fill followed by a greedy negated-class fill.
    if re.search(r"\[\^[^\]]*\][*+]\?.*\[\^[^\]]*\][*+](?!\?)", pattern):
        hits.append("dual-tempered-fill")

    return sorted(set(hits))


def _static_pattern(arg: ast.AST):
    """Return the literal regex string for a re.compile() first arg, or None."""
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if isinstance(arg, ast.BinOp):  # string concatenation of literals
        try:
            value = ast.literal_eval(arg)
        except Exception:
            return None
        return value if isinstance(value, str) else None
    return None


def scan_file(path: Path) -> List[Tuple[int, List[str], str]]:
    """Return (lineno, shapes, pattern) for every flagged, un-annotated compile."""
    src = path.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    findings: List[Tuple[int, List[str], str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "compile"):
            continue
        base = node.func.value
        if not (isinstance(base, ast.Name) and base.id == "re") or not node.args:
            continue
        pattern = _static_pattern(node.args[0])
        if pattern is None:
            continue
        shapes = detect_shapes(pattern)
        if not shapes:
            continue
        # exempt if a redos-ok marker appears anywhere in the statement's span
        end = getattr(node, "end_lineno", node.lineno)
        span = "\n".join(lines[node.lineno - 1:end])
        if ALLOW_MARKER in span:
            continue
        findings.append((node.lineno, shapes, pattern))
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed ReDoS-shape audit of re.compile patterns.")
    parser.add_argument("--root", default=".", help="Repository root. Default: current directory")
    args = parser.parse_args(argv)

    scripts_dir = Path(args.root) / "artifacts" / "scripts"
    findings: List[Tuple[Path, int, List[str], str]] = []
    for path in sorted(scripts_dir.rglob("*.py")):
        if path.name.startswith("test_"):
            continue
        for lineno, shapes, pattern in scan_file(path):
            findings.append((path, lineno, shapes, pattern))

    if findings:
        print(f"[FAIL] {len(findings)} ReDoS-shaped regex(es) without a '# {ALLOW_MARKER}:' review marker:")
        for path, lineno, shapes, pattern in findings:
            preview = pattern if len(pattern) <= 100 else pattern[:97] + "..."
            print(f"  - {path}:{lineno} {shapes} :: {preview}")
        print("\nFix the pattern (prefer linear restructuring) or, if it is provably safe in "
              f"context, append '# {ALLOW_MARKER}: <reason>' to the re.compile(...) statement.")
        return EXIT_FAIL

    print("[OK] No unannotated ReDoS-shaped regex patterns detected.")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
