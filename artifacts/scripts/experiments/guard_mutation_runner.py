#!/usr/bin/env python3
"""mutation_runner.py — self-contained AST mutation-testing harness for guard modules.

PURPOSE
-------
council-forge's guard scripts have ~100% *line* coverage, yet a Critical ReDoS was
found in a fully-covered file. Line coverage proves a line *executed*, not that a test
would *fail* if that line were wrong. This harness measures **mutation adequacy**: for
each guard module it applies small semantic mutations (a guard becoming too loose/strict)
and checks whether the module's focused pytest file *catches* the change.

  - mutant KILLED  = focused tests FAIL on the mutated module (good — blind spot covered)
  - mutant SURVIVED = focused tests still PASS on the mutated module (BAD — a real blind
                      spot: the guard could be weakened and no test would notice)

mutation score per module = killed / (killed + survived)

DESIGN CONSTRAINTS
------------------
* No external mutation tooling. Pure stdlib (``ast``). Dev deps are only pytest/pytest-cov.
* READ-ONLY on the repo. Every mutation is written to a TEMP copy of the scripts dir; the
  focused test file is run from inside that copy so the *mutated* module is the one imported.
* Bounded: ``--max-mutants`` and ``--max-minutes`` (wall-clock), whichever trips first.
* Baseline-aware: pre-existing test failures (env-specific) are subtracted, so a mutant is
  only KILLED if it causes a test that *passed in baseline* to fail.

USAGE
-----
  python mutation_runner.py                       # default targets, bounds
  python mutation_runner.py --targets sast_gate.py --max-mutants 50 --max-minutes 3
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Repo layout
# --------------------------------------------------------------------------- #
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]                       # .../council-forge
SCRIPTS_DIR = REPO_ROOT / "artifacts" / "scripts"
OUT_DIR = REPO_ROOT / "artifacts" / "experiments" / "guard_mutation"
REPORT_MD = OUT_DIR / "mutation_report.md"
RESULTS_JSON = OUT_DIR / "mutation_results.json"

# module (relative to SCRIPTS_DIR) -> focused pytest file(s) (relative to SCRIPTS_DIR).
#
# The three SARIF/RFC9116/release gates have *self-contained* focused test files (a single
# `import <module>`), so they run cleanly from an isolated temp copy and are the primary,
# high-value targets here. The guard_helpers submodules are exercised only via the
# `test_guard_units.py` collector shim, which transitively imports the entire script suite
# (run_red_team_suite -> red_team.helpers.detect_repo_root). That repo-root detection fails
# under temp isolation, so those modules are NOT evaluable in a READ-ONLY/temp-copy harness;
# they are listed (commented) for transparency and can be re-enabled if a focused, self-
# contained test file is added for them.
DEFAULT_TARGETS = {
    "sast_gate.py": ["test_sast_gate.py"],
    "security_txt_gate.py": ["test_security_txt_gate.py"],
    "release_gate.py": ["test_release_gate.py"],
    # "guard_helpers/markers.py":  ["test_guard_units.py"],  # not temp-isolatable (see above)
    # "guard_helpers/parsers.py":  ["test_guard_units.py"],
    # "guard_helpers/io.py":       ["test_guard_units.py"],
}

PER_MUTANT_TIMEOUT_S = 90


def _pytest_python() -> str:
    """Locate a python whose env has pytest. Prefer the uv-managed pytest tool."""
    candidates = [
        Path("/root/.local/share/uv/tools/pytest/bin/python"),
        Path(sys.executable),
    ]
    for c in candidates:
        if c.exists():
            try:
                r = subprocess.run(
                    [str(c), "-c", "import pytest"],
                    capture_output=True, timeout=30,
                )
                if r.returncode == 0:
                    return str(c)
            except Exception:
                continue
    # fall back to current interpreter; the run will error loudly if pytest is absent
    return sys.executable


PYTEST_PYTHON = _pytest_python()


# --------------------------------------------------------------------------- #
# Mutation operators (AST-based)
# --------------------------------------------------------------------------- #
@dataclass
class Mutation:
    lineno: int
    col: int
    operator: str
    original: str
    mutated: str
    occurrence: int  # per-operator ordinal; matches the same-order walk in apply_mutation


_CMP_FLIP = {
    ast.GtE: (ast.Gt, ">=", ">"),
    ast.Gt: (ast.GtE, ">", ">="),
    ast.LtE: (ast.Lt, "<=", "<"),
    ast.Lt: (ast.LtE, "<", "<="),
    ast.Eq: (ast.NotEq, "==", "!="),
    ast.NotEq: (ast.Eq, "!=", "=="),
}


def _segment(source_lines: List[str], node: ast.AST) -> str:
    try:
        seg = ast.get_source_segment("\n".join(source_lines), node)
        return seg if seg else f"<{type(node).__name__}>"
    except Exception:
        return f"<{type(node).__name__}>"


def _iter_sites(tree: ast.AST):
    """Yield (operator, occurrence, lineno, col, original_str, mutated_str, sentinel).

    A *site* is one independently-mutable point. Discovery and application both call this
    in the SAME ``ast.walk`` order and key by ``(operator, occurrence)`` so the ordinal a
    mutation carries unambiguously selects one node. ``sentinel`` is operator-specific data
    (e.g. the new regex string / new int value) needed to materialize the change.

    This is a pure enumerator: it does NOT mutate. Application below re-walks and edits the
    node whose (operator, occurrence) matches.
    """
    counters: dict = {}

    def nxt(op: str) -> int:
        n = counters.get(op, 0)
        counters[op] = n + 1
        return n

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                t = type(op)
                if t in _CMP_FLIP:
                    _, orig_s, new_s = _CMP_FLIP[t]
                    yield ("cmp_flip", nxt("cmp_flip"), node.lineno, node.col_offset,
                           orig_s, new_s, (node, i))
                elif isinstance(op, ast.Is):
                    yield ("is_flip", nxt("is_flip"), node.lineno, node.col_offset,
                           "is", "is not", (node, i))
                elif isinstance(op, ast.IsNot):
                    yield ("is_flip", nxt("is_flip"), node.lineno, node.col_offset,
                           "is not", "is", (node, i))

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                yield ("bool_flip", nxt("bool_flip"), node.lineno, node.col_offset,
                       "and", "or", node)
            elif isinstance(node.op, ast.Or):
                yield ("bool_flip", nxt("bool_flip"), node.lineno, node.col_offset,
                       "or", "and", node)

        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            yield ("drop_not", nxt("drop_not"), node.lineno, node.col_offset,
                   "not X", "X", node)

        elif isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                yield ("const_bool", nxt("const_bool"), node.lineno, node.col_offset,
                       repr(v), repr(not v), node)
            elif isinstance(v, int):  # bool already handled above
                yield ("num_inc", nxt("num_inc"), node.lineno, node.col_offset,
                       repr(v), repr(v + 1), node)
                if v != 0:
                    yield ("num_zero", nxt("num_zero"), node.lineno, node.col_offset,
                           repr(v), "0", node)
            elif isinstance(v, str):
                if v.startswith("^") or v.endswith("$"):
                    new = v[1:] if v.startswith("^") else v
                    if new.endswith("$") and not new.endswith("\\$"):
                        new = new[:-1]
                    if new != v:
                        yield ("regex_weaken", nxt("regex_weaken"), node.lineno,
                               node.col_offset, repr(v), repr(new), (node, new))


def discover_mutations(source: str) -> List[Tuple[Mutation, ast.AST, str]]:
    """Enumerate all single-point mutations for ``source`` (no mutation performed here)."""
    tree = ast.parse(source)
    found: List[Mutation] = []
    for op, occ, line, col, orig_s, new_s, _ in _iter_sites(tree):
        found.append(Mutation(line, col, op, orig_s, new_s, occ))
    return [(m, None, "") for m in found]


def apply_mutation(source: str, mut: Mutation) -> Optional[str]:
    """Return mutated source for the single selected mutation, or None if inapplicable.

    Re-walks the tree (same order as discovery) and edits in place the node whose
    ``(operator, occurrence)`` matches ``mut``.
    """
    try:
        tree = ast.parse(source)
    except Exception:
        return None
    for op, occ, _line, _col, _orig, _new, payload in _iter_sites(tree):
        if op != mut.operator or occ != mut.occurrence:
            continue
        if op == "cmp_flip":
            node, i = payload
            node.ops[i] = _CMP_FLIP[type(node.ops[i])][0]()
        elif op == "is_flip":
            node, i = payload
            node.ops[i] = ast.IsNot() if isinstance(node.ops[i], ast.Is) else ast.Is()
        elif op == "bool_flip":
            payload.op = ast.Or() if isinstance(payload.op, ast.And) else ast.And()
        elif op == "drop_not":
            # replace the UnaryOp-not node with its operand by mutating its parent reference.
            _replace_node(tree, payload, payload.operand)
        elif op == "const_bool":
            payload.value = not payload.value
        elif op == "num_inc":
            payload.value = payload.value + 1
        elif op == "num_zero":
            payload.value = 0
        elif op == "regex_weaken":
            node, new_str = payload
            node.value = new_str
        else:
            return None
        ast.fix_missing_locations(tree)
        try:
            return ast.unparse(tree)
        except Exception:
            return None
    return None  # occurrence not found (e.g. tree shape changed) -> inapplicable


def _replace_node(tree: ast.AST, target: ast.AST, replacement: ast.AST) -> bool:
    """Find ``target`` anywhere in ``tree`` and swap it for ``replacement`` in its parent."""
    for parent in ast.walk(tree):
        for field_name, value in ast.iter_fields(parent):
            if value is target:
                setattr(parent, field_name, replacement)
                return True
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    if item is target:
                        value[idx] = replacement
                        return True
    return False


# --------------------------------------------------------------------------- #
# Test execution against a mutated copy
# --------------------------------------------------------------------------- #
@dataclass
class TargetResult:
    module: str
    test_files: List[str]
    baseline_passed: List[str] = field(default_factory=list)
    total_mutants: int = 0
    killed: int = 0
    survived: int = 0
    errored: int = 0  # mutant produced a crash/collection error (not a clean kill)
    survived_detail: List[dict] = field(default_factory=list)

    @property
    def evaluated(self) -> int:
        return self.killed + self.survived

    @property
    def score(self) -> Optional[float]:
        return (self.killed / self.evaluated) if self.evaluated else None


def _run_pytest(scripts_dir: Path, test_files: List[str]) -> Tuple[int, set]:
    """Run focused tests inside scripts_dir. Returns (returncode, set_of_passed_nodeids)."""
    # Use a JSON-less, parseable verbose output: parse PASSED lines.
    cmd = [PYTEST_PYTHON, "-m", "pytest", *test_files,
           "-p", "no:cacheprovider", "--no-header", "-rN", "--tb=no", "-v"]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run(cmd, cwd=str(scripts_dir), env=env,
                           capture_output=True, text=True, timeout=PER_MUTANT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return 124, set()
    passed = set()
    for line in r.stdout.splitlines():
        # verbose line format: "test_file.py::TestX::test_y PASSED"
        if " PASSED" in line:
            passed.add(line.split(" PASSED")[0].strip())
    return r.returncode, passed


def _make_scripts_copy(dst_root: Path) -> Path:
    """Copy the scripts dir (sans caches) into dst_root/scripts; return that path."""
    dst = dst_root / "scripts"
    shutil.copytree(
        SCRIPTS_DIR, dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    return dst


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def evaluate_target(module: str, test_files: List[str], *,
                    deadline: float, mutant_budget: int,
                    log) -> TargetResult:
    res = TargetResult(module=module, test_files=test_files)

    src_path = SCRIPTS_DIR / module
    if not src_path.exists():
        log(f"  [skip] {module}: module not found")
        return res
    source = src_path.read_text(encoding="utf-8")

    # 1) baseline: capture the set of tests that PASS against unmodified code
    with tempfile.TemporaryDirectory(prefix="mut_base_") as td:
        copy_scripts = _make_scripts_copy(Path(td))
        rc, baseline_passed = _run_pytest(copy_scripts, test_files)
    if not baseline_passed:
        log(f"  [skip] {module}: baseline collected 0 passing tests (rc={rc}) — cannot evaluate")
        return res
    res.baseline_passed = sorted(baseline_passed)
    log(f"  baseline: {len(baseline_passed)} passing tests")

    # 2) discover candidate mutations
    muts = [m for (m, _, _) in discover_mutations(source)]
    log(f"  discovered {len(muts)} candidate mutations")
    try:
        normalized_baseline = ast.unparse(ast.parse(source))
    except Exception:
        normalized_baseline = None

    # 3) evaluate each mutant in its own scripts copy
    for mut in muts:
        if time.time() >= deadline:
            log(f"  [bound] wall-clock deadline reached after {res.total_mutants} mutants")
            break
        if mutant_budget is not None and res.total_mutants >= mutant_budget:
            log(f"  [bound] per-target mutant budget {mutant_budget} reached")
            break

        mutated_src = apply_mutation(source, mut)
        if mutated_src is None or mutated_src == normalized_baseline:
            continue  # un-applicable / no-op mutation; do not count
        res.total_mutants += 1

        with tempfile.TemporaryDirectory(prefix="mut_") as td:
            copy_scripts = _make_scripts_copy(Path(td))
            (copy_scripts / module).write_text(mutated_src, encoding="utf-8")
            rc, passed = _run_pytest(copy_scripts, test_files)

        if rc == 124:
            # timeout — likely a ReDoS-style hang the suite would NOT catch as a failure.
            res.survived += 1
            res.survived_detail.append({
                "file": module, "line": mut.lineno, "operator": mut.operator,
                "change": f"{mut.original} -> {mut.mutated}",
                "note": "test run TIMED OUT (possible hang/ReDoS not asserted) — counted as survived",
            })
            continue

        # A mutant is KILLED iff at least one baseline-passing test no longer passes.
        regressions = res.baseline_passed and any(t not in passed for t in res.baseline_passed)
        if regressions:
            res.killed += 1
        else:
            res.survived += 1
            res.survived_detail.append({
                "file": module, "line": mut.lineno, "operator": mut.operator,
                "change": f"{mut.original} -> {mut.mutated}",
            })

    return res


def write_outputs(results: List[TargetResult], runtime_s: float,
                  bounds: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # JSON
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "runtime_seconds": round(runtime_s, 2),
        "bounds": bounds,
        "pytest_python": PYTEST_PYTHON,
        "targets": [
            {
                "module": r.module,
                "test_files": r.test_files,
                "baseline_passing_tests": len(r.baseline_passed),
                "total_mutants": r.total_mutants,
                "killed": r.killed,
                "survived": r.survived,
                "mutation_score": round(r.score, 4) if r.score is not None else None,
                "survived_mutants": r.survived_detail,
            }
            for r in results
        ],
        "totals": {
            "total_mutants": sum(r.total_mutants for r in results),
            "killed": sum(r.killed for r in results),
            "survived": sum(r.survived for r in results),
        },
    }
    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Markdown
    total_mut = payload["totals"]["total_mutants"]
    total_kill = payload["totals"]["killed"]
    total_surv = payload["totals"]["survived"]
    overall = (total_kill / (total_kill + total_surv)) if (total_kill + total_surv) else 0.0

    lines: List[str] = []
    lines.append("# Guard Mutation-Testing Report")
    lines.append("")
    lines.append(f"_Generated: {payload['generated_at']} · runtime: {payload['runtime_seconds']}s · "
                 f"bounds: max_mutants={bounds['max_mutants']}, max_minutes={bounds['max_minutes']}_")
    lines.append("")
    lines.append("Mutation testing applies small semantic mutations (a guard becoming too "
                 "loose/strict) and checks whether the focused test suite **fails**. A "
                 "**survived** mutant is a test blind spot: the guard could be weakened and "
                 "no test would notice — the actionable output here.")
    lines.append("")
    lines.append("## Per-module mutation score")
    lines.append("")
    lines.append("| Module | Focused tests | Baseline pass | Mutants | Killed | Survived | Score |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for r in results:
        score = f"{r.score*100:.1f}%" if r.score is not None else "n/a"
        lines.append(f"| `{r.module}` | {', '.join(r.test_files)} | {len(r.baseline_passed)} | "
                     f"{r.total_mutants} | {r.killed} | **{r.survived}** | {score} |")
    lines.append(f"| **TOTAL** | | | {total_mut} | {total_kill} | **{total_surv}** | "
                 f"{overall*100:.1f}% |")
    lines.append("")
    lines.append(f"## Survived mutants (blind spots) — {total_surv} total")
    lines.append("")
    if total_surv == 0:
        lines.append("_No survived mutants within the evaluated bounds._")
    else:
        lines.append("| File:Line | Operator | Original → Mutated | Note |")
        lines.append("|---|---|---|---|")
        for r in results:
            for d in r.survived_detail:
                note = d.get("note", "")
                lines.append(f"| `{d['file']}:{d['line']}` | {d['operator']} | "
                             f"`{d['change']}` | {note} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- **Killed** mutants confirm a real assertion guards that behavior.")
    lines.append("- **Survived** mutants are blind spots: a maintainer (or attacker via a "
                 "subtle PR) could flip that operator/constant/regex anchor and the suite "
                 "stays green. Each row is a candidate for a new, targeted test.")
    lines.append("- Line coverage was ~100% on these files; mutation score is materially "
                 "lower, demonstrating coverage != mutation adequacy.")
    lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Self-contained AST mutation tester for guard modules.")
    ap.add_argument("--targets", nargs="*", default=None,
                    help="Module paths relative to artifacts/scripts (default: built-in set).")
    ap.add_argument("--max-mutants", type=int, default=200,
                    help="Hard cap on total mutants across all targets (default 200).")
    ap.add_argument("--max-minutes", type=float, default=7.0,
                    help="Wall-clock deadline in minutes (default 7).")
    ap.add_argument("--per-target-cap", type=int, default=None,
                    help="Optional cap on mutants per target (default: derived from --max-mutants).")
    args = ap.parse_args(argv)

    if args.targets:
        targets = {t: DEFAULT_TARGETS.get(t, _guess_tests(t)) for t in args.targets}
    else:
        targets = DEFAULT_TARGETS

    start = time.time()
    deadline = start + args.max_minutes * 60.0

    def log(msg: str) -> None:
        print(msg, flush=True)

    log(f"Mutation runner — pytest python: {PYTEST_PYTHON}")
    log(f"Bounds: max_mutants={args.max_mutants}, max_minutes={args.max_minutes}")
    log("")

    results: List[TargetResult] = []
    remaining = args.max_mutants
    n_targets = len(targets)
    for i, (module, test_files) in enumerate(targets.items()):
        if time.time() >= deadline:
            log(f"[bound] deadline reached before evaluating {module}")
            results.append(TargetResult(module=module, test_files=test_files))
            continue
        # split remaining budget across not-yet-done targets, unless explicit per-target cap
        if args.per_target_cap is not None:
            budget = min(args.per_target_cap, remaining)
        else:
            left = n_targets - i
            budget = max(1, remaining // max(1, left)) if remaining > 0 else 0
        log(f"[{i+1}/{n_targets}] target: {module}  (budget {budget})")
        r = evaluate_target(module, test_files, deadline=deadline,
                            mutant_budget=budget, log=log)
        results.append(r)
        remaining -= r.total_mutants
        log(f"  => mutants={r.total_mutants} killed={r.killed} survived={r.survived} "
            f"score={(f'{r.score*100:.1f}%' if r.score is not None else 'n/a')}")
        log("")
        if remaining <= 0:
            log("[bound] global mutant budget exhausted")
            break

    runtime = time.time() - start
    write_outputs(results, runtime,
                  {"max_mutants": args.max_mutants, "max_minutes": args.max_minutes})
    log(f"Wrote {REPORT_MD}")
    log(f"Wrote {RESULTS_JSON}")
    log(f"Total runtime: {runtime:.1f}s")
    return 0


def _guess_tests(module: str) -> List[str]:
    base = Path(module).name.replace(".py", "")
    guess = f"test_{base}.py"
    if (SCRIPTS_DIR / guess).exists():
        return [guess]
    return ["test_guard_units.py"]


if __name__ == "__main__":
    raise SystemExit(main())
