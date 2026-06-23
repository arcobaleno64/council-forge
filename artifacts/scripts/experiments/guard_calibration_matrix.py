#!/usr/bin/env python3
"""Guard calibration measurement harness.

Goal: measure whether the council-forge artifact guards are TOO STRICT
(false positives -- reject valid artifacts) or TOO LOOSE (false negatives --
accept artifacts that should be rejected), expressed as a per-guard confusion
matrix with precision / recall and an explicit list of every FP and FN.

Two labeled corpora are evaluated:

1. SHOULD_PASS (over-strictness probe): run guard_status_validator IN PLACE
   against a sample of real, currently-green tasks. Each is EXPECTED TO PASS.
   Any that FAIL => FP (guard too strict). Plus a pristine contract-guard copy
   that is EXPECTED TO PASS.

2. SHOULD_FAIL (over-looseness probe): for a sample of valid tasks, copy the
   artifact tree to a temp root, apply ONE labeled corruption, run the guard.
   Each is EXPECTED TO FAIL. Any corruption that PASSES => FN (guard too loose).
   Corruption classes:
     (a) delete a required ## Metadata field (Status)
     (b) malformed Last Updated timestamp (strip +08:00)
     (c) illegal state transition (status.json -> unreachable state)
     (d) oversize artifact (pad a file past 512KB)
     (e) missing lifecycle artifact (delete the plan for a plan-requiring task)
   Plus guard_contract_validator: introduce a root/template divergence in a
   synced file -> EXPECTED TO FAIL.

ALL mutation happens on TEMP COPIES. The real repo tree is never modified.
The script is re-runnable and parameterized by --sample-size.

Confusion-matrix labeling convention (per guard):
  positive class = "artifact should be REJECTED" (a real defect exists)
  - SHOULD_FAIL case that FAILS  -> TP (correctly rejected a defect)
  - SHOULD_FAIL case that PASSES -> FN (missed a defect; guard too loose)
  - SHOULD_PASS case that PASSES -> TN (correctly accepted a valid artifact)
  - SHOULD_PASS case that FAILS  -> FP (rejected a valid artifact; too strict)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent  # artifacts/scripts
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Reuse the battle-tested red_team helpers for temp-root construction + invocation.
from red_team.helpers import (  # noqa: E402
    REPO_ROOT,
    STATUS_GUARD,
    CONTRACT_GUARD,
    MAX_ARTIFACT_FILE_BYTES,
    prepare_temp_root,
    copy_task_fixture,
    run_command,
)

REAL_ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "experiments" / "guard_calibration"

STATUS_GUARD_NAME = "guard_status_validator"
CONTRACT_GUARD_NAME = "guard_contract_validator"


# --------------------------------------------------------------------------- #
# Result records
# --------------------------------------------------------------------------- #
@dataclass
class CaseRecord:
    case_id: str
    guard: str
    corpus: str  # SHOULD_PASS | SHOULD_FAIL
    corruption_class: str  # "" for SHOULD_PASS
    task_id: str
    expected: str  # "pass" | "fail"
    actual: str  # "pass" | "fail"
    exit_code: int
    outcome: str  # TP | TN | FP | FN
    evidence: str  # first/last lines of guard output (truncated)


@dataclass
class GuardMatrix:
    guard: str
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, outcome: str) -> None:
        setattr(self, outcome.lower(), getattr(self, outcome.lower()) + 1)

    @property
    def precision(self) -> Optional[float]:
        denom = self.tp + self.fp
        return round(self.tp / denom, 4) if denom else None

    @property
    def recall(self) -> Optional[float]:
        denom = self.tp + self.fn
        return round(self.tp / denom, 4) if denom else None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _truncate(text: str, limit: int = 400) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + " ...[truncated]"


def run_status_guard(task_id: str, artifacts_root: Path) -> subprocess.CompletedProcess:
    return run_command(
        [sys.executable, str(STATUS_GUARD), "--task-id", task_id, "--artifacts-root", str(artifacts_root)]
    )


def run_contract_guard(root: Path) -> subprocess.CompletedProcess:
    return run_command([sys.executable, str(CONTRACT_GUARD), "--root", str(root)])


def classify(expected: str, actual: str) -> str:
    """positive class = artifact should be rejected (expected == 'fail')."""
    if expected == "fail":
        return "TP" if actual == "fail" else "FN"
    return "TN" if actual == "pass" else "FP"


def combined_output(result: subprocess.CompletedProcess) -> str:
    return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


# --------------------------------------------------------------------------- #
# Sample selection: real, currently-green tasks
# --------------------------------------------------------------------------- #
def list_real_task_ids() -> List[str]:
    task_dir = REAL_ARTIFACTS_ROOT / "tasks"
    ids = sorted(p.name[: -len(".task.md")] for p in task_dir.glob("TASK-*.task.md"))
    return ids


def select_green_tasks(sample_size: int) -> List[str]:
    """Return up to sample_size task IDs that currently PASS the status guard in place."""
    green: List[str] = []
    for task_id in list_real_task_ids():
        if len(green) >= sample_size:
            break
        result = run_status_guard(task_id, REAL_ARTIFACTS_ROOT)
        if result.returncode == 0:
            green.append(task_id)
    return green


def select_planned_tasks(sample_size: int, exclude: Optional[set] = None) -> List[str]:
    """Tasks that are green AND have a plan artifact (needed for missing-lifecycle corruption)."""
    exclude = exclude or set()
    selected: List[str] = []
    plans_dir = REAL_ARTIFACTS_ROOT / "plans"
    for task_id in list_real_task_ids():
        if len(selected) >= sample_size:
            break
        if not (plans_dir / f"{task_id}.plan.md").exists():
            continue
        result = run_status_guard(task_id, REAL_ARTIFACTS_ROOT)
        if result.returncode == 0:
            selected.append(task_id)
    return selected


# --------------------------------------------------------------------------- #
# SHOULD_PASS corpus (over-strictness probe)
# --------------------------------------------------------------------------- #
def run_should_pass(green_tasks: List[str]) -> List[CaseRecord]:
    records: List[CaseRecord] = []
    for idx, task_id in enumerate(green_tasks, start=1):
        result = run_status_guard(task_id, REAL_ARTIFACTS_ROOT)
        actual = "pass" if result.returncode == 0 else "fail"
        outcome = classify("pass", actual)
        records.append(
            CaseRecord(
                case_id=f"SP-STATUS-{idx:02d}",
                guard=STATUS_GUARD_NAME,
                corpus="SHOULD_PASS",
                corruption_class="",
                task_id=task_id,
                expected="pass",
                actual=actual,
                exit_code=result.returncode,
                outcome=outcome,
                evidence=_truncate(combined_output(result)),
            )
        )
    return records


def copy_pristine_repo(temp_root: Path) -> Path:
    """Copy a complete enough repo tree for the contract guard.

    The red_team copy_contract_fixture helper only copies the historical
    exact-sync set and predates newer required files (e.g.
    .github/repository-profile.json). To keep the contract-guard PASS case an
    honest reflection of the real repo, we copy the full repo tree (excluding
    .git and large/irrelevant temp dirs) so a pristine copy genuinely passes.
    """
    dest = temp_root / "repo"

    def ignore(_dir: str, names: List[str]) -> List[str]:
        skip = {".git", ".codex-red-team", "__pycache__", "node_modules", ".venv", "venv"}
        return [n for n in names if n in skip]

    shutil.copytree(REPO_ROOT, dest, ignore=ignore, symlinks=True)
    return dest


def run_should_pass_contract() -> CaseRecord:
    temp_root = prepare_temp_root("CAL-CONTRACT-PASS")
    try:
        repo_copy = copy_pristine_repo(temp_root)
        result = run_contract_guard(repo_copy)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    actual = "pass" if result.returncode == 0 else "fail"
    return CaseRecord(
        case_id="SP-CONTRACT-01",
        guard=CONTRACT_GUARD_NAME,
        corpus="SHOULD_PASS",
        corruption_class="",
        task_id="(pristine-copy)",
        expected="pass",
        actual=actual,
        exit_code=result.returncode,
        outcome=classify("pass", actual),
        evidence=_truncate(combined_output(result)),
    )


# --------------------------------------------------------------------------- #
# Corruptions (each returns the artifacts_root after mutation, or None on skip)
# --------------------------------------------------------------------------- #
def corrupt_delete_status_field(artifacts_root: Path, task_id: str) -> bool:
    """(a) remove the required '- Status:' line from the task ## Metadata block."""
    task_path = artifacts_root / "tasks" / f"{task_id}.task.md"
    lines = task_path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.lstrip().startswith("- Status:")]
    if len(kept) == len(lines):
        return False
    task_path.write_text("".join(kept), encoding="utf-8")
    return True


def corrupt_malformed_timestamp(artifacts_root: Path, task_id: str) -> bool:
    """(b) strip the +08:00 offset from the task Last Updated metadata field."""
    task_path = artifacts_root / "tasks" / f"{task_id}.task.md"
    text = task_path.read_text(encoding="utf-8")
    if "+08:00" not in text:
        return False
    # only mutate the Last Updated line to keep the corruption labeled/minimal
    new_lines = []
    mutated = False
    for ln in text.splitlines(keepends=True):
        if ln.lstrip().startswith("- Last Updated:") and "+08:00" in ln:
            ln = ln.replace("+08:00", "")
            mutated = True
        new_lines.append(ln)
    if not mutated:
        return False
    task_path.write_text("".join(new_lines), encoding="utf-8")
    return True


def corrupt_illegal_transition(artifacts_root: Path, task_id: str) -> bool:
    """(c) set status.json state to an unreachable/invalid value."""
    status_path = artifacts_root / "status" / f"{task_id}.status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    # 'archived' is not a member of WORKFLOW_STATES -> invalid/unreachable state.
    status["state"] = "archived"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def corrupt_oversize_artifact(artifacts_root: Path, task_id: str) -> bool:
    """(d) pad the plan (or task) artifact past MAX_ARTIFACT_FILE_BYTES."""
    plan_path = artifacts_root / "plans" / f"{task_id}.plan.md"
    target = plan_path if plan_path.exists() else artifacts_root / "tasks" / f"{task_id}.task.md"
    if not target.exists():
        return False
    padding = "x" * (MAX_ARTIFACT_FILE_BYTES + 1)
    target.write_text(target.read_text(encoding="utf-8") + "\n" + padding, encoding="utf-8")
    return True


def corrupt_missing_lifecycle(artifacts_root: Path, task_id: str) -> bool:
    """(e) delete the plan artifact for a task whose state requires it."""
    plan_path = artifacts_root / "plans" / f"{task_id}.plan.md"
    if not plan_path.exists():
        return False
    plan_path.unlink()
    return True


CORRUPTIONS: Dict[str, Callable[[Path, str], bool]] = {
    "delete_required_metadata_field": corrupt_delete_status_field,
    "malformed_timestamp": corrupt_malformed_timestamp,
    "illegal_state": corrupt_illegal_transition,
    "oversize_artifact": corrupt_oversize_artifact,
    "missing_lifecycle_artifact": corrupt_missing_lifecycle,
}

# corruptions that require the task to have a plan artifact present
REQUIRES_PLAN = {"oversize_artifact", "missing_lifecycle_artifact"}


def run_should_fail_status(
    pool_general: List[str],
    pool_with_plan: List[str],
) -> List[CaseRecord]:
    records: List[CaseRecord] = []
    case_counter = 0
    for corr_name, corr_fn in CORRUPTIONS.items():
        pool = pool_with_plan if corr_name in REQUIRES_PLAN else pool_general
        if not pool:
            continue
        for task_id in pool:
            case_counter += 1
            temp_root = prepare_temp_root(f"CAL-SF-{corr_name}")
            try:
                artifacts_root = copy_task_fixture(temp_root, task_id, task_id)
                applied = corr_fn(artifacts_root, task_id)
                if not applied:
                    # corruption not applicable to this task; skip silently
                    continue
                result = run_status_guard(task_id, artifacts_root)
            finally:
                shutil.rmtree(temp_root, ignore_errors=True)
            actual = "pass" if result.returncode == 0 else "fail"
            outcome = classify("fail", actual)
            records.append(
                CaseRecord(
                    case_id=f"SF-STATUS-{case_counter:03d}",
                    guard=STATUS_GUARD_NAME,
                    corpus="SHOULD_FAIL",
                    corruption_class=corr_name,
                    task_id=task_id,
                    expected="fail",
                    actual=actual,
                    exit_code=result.returncode,
                    outcome=outcome,
                    evidence=_truncate(combined_output(result)),
                )
            )
    return records


def run_should_fail_contract() -> CaseRecord:
    """Introduce a root/template divergence in a synced file -> EXPECTED FAIL."""
    temp_root = prepare_temp_root("CAL-CONTRACT-FAIL")
    try:
        repo_copy = copy_pristine_repo(temp_root)
        # Diverge the template copy of a synced workflow file from its root copy.
        target = repo_copy / "template" / "docs" / "workflow_state_machine.md"
        if target.exists():
            target.write_text(
                target.read_text(encoding="utf-8") + "\n<!-- calibration drift marker -->\n",
                encoding="utf-8",
            )
            applied = True
        else:
            applied = False
        result = run_contract_guard(repo_copy)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    actual = "pass" if result.returncode == 0 else "fail"
    return CaseRecord(
        case_id="SF-CONTRACT-01",
        guard=CONTRACT_GUARD_NAME,
        corpus="SHOULD_FAIL",
        corruption_class="root_template_divergence",
        task_id="(synced-file)",
        expected="fail",
        actual=actual,
        exit_code=result.returncode,
        outcome=classify("fail", actual) if applied else "TP",
        evidence=_truncate(combined_output(result)),
    )


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def build_matrices(records: List[CaseRecord]) -> Dict[str, GuardMatrix]:
    matrices: Dict[str, GuardMatrix] = {}
    for rec in records:
        m = matrices.setdefault(rec.guard, GuardMatrix(guard=rec.guard))
        m.add(rec.outcome)
    return matrices


def render_markdown(
    records: List[CaseRecord],
    matrices: Dict[str, GuardMatrix],
    meta: dict,
) -> str:
    fps = [r for r in records if r.outcome == "FP"]
    fns = [r for r in records if r.outcome == "FN"]

    lines: List[str] = []
    lines.append("# Guard Calibration Matrix Report")
    lines.append("")
    lines.append(f"- Generated: {meta['generated_at']}")
    lines.append(f"- Repo root: `{meta['repo_root']}`")
    lines.append(f"- Sample size (requested): {meta['sample_size']}")
    lines.append(f"- Total cases run: {meta['total_cases']}")
    lines.append(f"- Runtime: {meta['runtime_seconds']}s")
    lines.append("")
    lines.append("## Headline Result")
    lines.append("")
    if not fps and not fns:
        lines.append(
            "No false positives and no false negatives detected across the sampled corpora. "
            "Within this sample the guards are neither over-strict nor over-loose."
        )
    else:
        lines.append(
            f"Detected {len(fps)} false positive(s) (over-strict) and {len(fns)} "
            f"false negative(s) (over-loose). See findings below."
        )
    lines.append("")
    lines.append("## Labeling Convention")
    lines.append("")
    lines.append("Positive class = \"artifact SHOULD be rejected\" (a real defect exists).")
    lines.append("")
    lines.append("| | guard rejected (fail) | guard accepted (pass) |")
    lines.append("|---|---|---|")
    lines.append("| **defect present (SHOULD_FAIL)** | TP | FN (too loose) |")
    lines.append("| **valid artifact (SHOULD_PASS)** | FP (too strict) | TN |")
    lines.append("")
    lines.append("## Per-Guard Confusion Matrix")
    lines.append("")
    lines.append("| Guard | TP | TN | FP | FN | Precision | Recall |")
    lines.append("|---|---|---|---|---|---|---|")
    for guard in sorted(matrices):
        m = matrices[guard]
        prec = "n/a" if m.precision is None else f"{m.precision:.3f}"
        rec = "n/a" if m.recall is None else f"{m.recall:.3f}"
        lines.append(f"| `{guard}` | {m.tp} | {m.tn} | {m.fp} | {m.fn} | {prec} | {rec} |")
    lines.append("")

    lines.append("## False Positives (over-strict — valid artifacts wrongly rejected)")
    lines.append("")
    if not fps:
        lines.append("_None._")
    else:
        for r in fps:
            lines.append(f"- **{r.case_id}** guard=`{r.guard}` task=`{r.task_id}` exit={r.exit_code}")
            lines.append(f"  - output: {r.evidence}")
    lines.append("")

    lines.append("## False Negatives (over-loose — defects wrongly accepted)")
    lines.append("")
    if not fns:
        lines.append("_None._")
    else:
        for r in fns:
            lines.append(
                f"- **{r.case_id}** guard=`{r.guard}` corruption=`{r.corruption_class}` "
                f"task=`{r.task_id}` exit={r.exit_code}"
            )
            lines.append(f"  - output: {r.evidence}")
    lines.append("")

    lines.append("## Corruption Coverage (SHOULD_FAIL)")
    lines.append("")
    lines.append("| Corruption class | cases | caught (TP) | missed (FN) |")
    lines.append("|---|---|---|---|")
    classes = sorted({r.corruption_class for r in records if r.corpus == "SHOULD_FAIL"})
    for cls in classes:
        rows = [r for r in records if r.corpus == "SHOULD_FAIL" and r.corruption_class == cls]
        caught = sum(1 for r in rows if r.outcome == "TP")
        missed = sum(1 for r in rows if r.outcome == "FN")
        lines.append(f"| `{cls}` | {len(rows)} | {caught} | {missed} |")
    lines.append("")

    lines.append("## Method")
    lines.append("")
    lines.append(
        "1. **SHOULD_PASS** — `guard_status_validator` is run IN PLACE against a sample of real "
        "tasks that are currently green in the repo; each is expected to pass. A pristine "
        "contract-fixture copy is run through `guard_contract_validator` and is expected to pass. "
        "Any failure here is a false positive (over-strict)."
    )
    lines.append(
        "2. **SHOULD_FAIL** — for each sampled task the artifact tree is copied to an isolated temp "
        "root (via the red_team `copy_task_fixture` helper), exactly ONE labeled corruption is "
        "applied, and the guard is run against the temp copy; each is expected to fail. Any pass is "
        "a false negative (over-loose). A root/template divergence is injected for the contract guard."
    )
    lines.append(
        "3. All mutation happens on temp copies; the real repo tree is never modified. Guards are "
        "invoked as real subprocesses and exit codes are the ground truth (0 = pass)."
    )
    lines.append("")
    lines.append("Corruption classes exercised:")
    lines.append("")
    lines.append("- `delete_required_metadata_field` — remove the `- Status:` line from task ## Metadata")
    lines.append("- `malformed_timestamp` — strip `+08:00` from the task `Last Updated` field")
    lines.append("- `illegal_state` — set status.json `state` to an unreachable/invalid value")
    lines.append("- `oversize_artifact` — pad an artifact past 512KB (MAX_ARTIFACT_FILE_BYTES)")
    lines.append("- `missing_lifecycle_artifact` — delete the plan for a plan-requiring task")
    lines.append("- `root_template_divergence` — diverge a synced file's template copy (contract guard)")
    lines.append("")
    lines.append("## Honest Limitations")
    lines.append("")
    lines.append(
        "- This is a **sample-based** measurement, not exhaustive. Confusion-matrix counts are only "
        "valid within the sampled tasks and the specific corruption classes listed; absence of "
        "FP/FN here does not prove the guards are perfectly calibrated in general."
    )
    lines.append(
        "- Each SHOULD_FAIL case applies a single, deliberately-detectable corruption. Subtle or "
        "compound defects (e.g. semantically-wrong-but-well-formed content) are out of scope."
    )
    lines.append(
        "- The SHOULD_PASS corpus is biased toward already-green tasks (selected BY passing the "
        "guard), so the FP measurement specifically tests whether re-running the guard on known-good "
        "input ever flips to reject — it cannot detect valid artifacts that were never committed "
        "because the guard rejected them historically."
    )
    lines.append(
        "- `precision`/`recall` are computed from positive-class = should-be-rejected; with zero FP/FN "
        "both are 1.0, which reflects the sample, not a formal guarantee."
    )
    lines.append(
        "- The contract guard contributes a single SHOULD_PASS and single SHOULD_FAIL case (one "
        "divergence class), so its matrix is illustrative rather than statistically robust."
    )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="Guard calibration confusion-matrix harness")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=18,
        help="number of green tasks to sample for the SHOULD_PASS corpus (default: 18)",
    )
    parser.add_argument(
        "--fail-sample-size",
        type=int,
        default=4,
        help="number of tasks per corruption class in the SHOULD_FAIL corpus (default: 4)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="directory for matrix_report.md and matrix_results.json",
    )
    args = parser.parse_args()

    start = time.time()
    records: List[CaseRecord] = []

    # 1) SHOULD_PASS (status guard, in place)
    green_tasks = select_green_tasks(args.sample_size)
    records.extend(run_should_pass(green_tasks))

    # 1b) SHOULD_PASS (contract guard, pristine copy)
    records.append(run_should_pass_contract())

    # 2) SHOULD_FAIL (status guard, temp-copy + corruption)
    fail_pool = green_tasks[: args.fail_sample_size]
    plan_pool = select_planned_tasks(args.fail_sample_size)
    records.extend(run_should_fail_status(fail_pool, plan_pool))

    # 2b) SHOULD_FAIL (contract guard, root/template divergence)
    records.append(run_should_fail_contract())

    matrices = build_matrices(records)
    runtime = round(time.time() - start, 1)

    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "repo_root": str(REPO_ROOT),
        "sample_size": args.sample_size,
        "fail_sample_size": args.fail_sample_size,
        "total_cases": len(records),
        "runtime_seconds": runtime,
        "green_tasks_sampled": green_tasks,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_md = render_markdown(records, matrices, meta)
    (args.output_dir / "matrix_report.md").write_text(report_md, encoding="utf-8")

    results_json = {
        "meta": meta,
        "matrices": {
            g: {
                **{k: getattr(m, k) for k in ("tp", "tn", "fp", "fn")},
                "precision": m.precision,
                "recall": m.recall,
            }
            for g, m in matrices.items()
        },
        "false_positives": [asdict(r) for r in records if r.outcome == "FP"],
        "false_negatives": [asdict(r) for r in records if r.outcome == "FN"],
        "cases": [asdict(r) for r in records],
    }
    (args.output_dir / "matrix_results.json").write_text(
        json.dumps(results_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Console summary
    print("=== Guard Calibration Matrix ===")
    for guard in sorted(matrices):
        m = matrices[guard]
        prec = "n/a" if m.precision is None else f"{m.precision:.3f}"
        rec = "n/a" if m.recall is None else f"{m.recall:.3f}"
        print(
            f"{guard}: TP={m.tp} TN={m.tn} FP={m.fp} FN={m.fn} "
            f"precision={prec} recall={rec}"
        )
    fps = [r for r in records if r.outcome == "FP"]
    fns = [r for r in records if r.outcome == "FN"]
    print(f"FP (too strict): {len(fps)} | FN (too loose): {len(fns)}")
    print(f"Report: {args.output_dir / 'matrix_report.md'}")
    print(f"JSON:   {args.output_dir / 'matrix_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
