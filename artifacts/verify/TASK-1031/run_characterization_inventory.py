#!/usr/bin/env python3
# TASK-1031 Validator/Test Monolith Characterization Inventory Helper.
#
# Read-only static analysis. Recomputes static metrics for the five target
# files and the governance characterization artifact, then writes a
# machine-readable verification result to:
#   artifacts/verify/TASK-1031/characterization-result.json
#
# Constraints (per TASK-1031 prompt section 19):
#   - standard library only
#   - no writes outside artifacts/verify/TASK-1031/
#   - no imports of repository modules
#   - no __pycache__ creation (sys.dont_write_bytecode + python -B)
#   - no network, no package installation, no production-file mutation
import sys
sys.dont_write_bytecode = True

import os
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import ast
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "verify" / "TASK-1031"
GOVERNANCE_JSON = REPO_ROOT / "artifacts" / "governance" / "validator-test-monolith-characterization.v3.5.1.json"
RESULT_JSON = EVIDENCE_DIR / "characterization-result.json"

TARGETS = [
    "artifacts/scripts/guard_status_validator.py",
    "artifacts/scripts/guard_contract_validator.py",
    "artifacts/scripts/workflow_constants.py",
    "artifacts/scripts/run_red_team_suite.py",
    "artifacts/scripts/test_guard_units.py",
]

LIFECYCLE = [
    "artifacts/tasks/TASK-1031.task.md",
    "artifacts/plans/TASK-1031.plan.md",
    "artifacts/decisions/TASK-1031.decision.md",
    "artifacts/verify/TASK-1031.verify.md",
    "artifacts/status/TASK-1031.status.json",
]

DEPENDENCIES = ["TASK-1029", "TASK-1030"]


def now_taipei_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def sha256_of(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_metrics(path: Path):
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    top_funcs = sum(
        1 for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    top_classes = sum(1 for n in tree.body if isinstance(n, ast.ClassDef))
    all_funcs = sum(
        1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    all_classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    has_main_guard = any(
        isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name)
        and n.test.left.id == "__name__"
        for n in tree.body
    )
    return {
        "loc": len(text.splitlines()),
        "function_count": all_funcs,
        "top_function_count": top_funcs,
        "class_count": all_classes,
        "top_class_count": top_classes,
        "top_level_statement_count": len(tree.body),
        "main_guard_present": has_main_guard,
    }


def status_done(task_id: str) -> tuple[bool, str]:
    p = REPO_ROOT / "artifacts" / "status" / f"{task_id}.status.json"
    if not p.exists():
        return False, "status_artifact_missing"
    payload = json.loads(p.read_text(encoding="utf-8"))
    state = payload.get("state")
    verify_result = payload.get("verify_result")
    if state == "done" and verify_result == "pass":
        return True, f"state=done verify_result=pass"
    return False, f"state={state} verify_result={verify_result}"


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []

    # Lifecycle existence
    for rel in LIFECYCLE:
        p = REPO_ROOT / rel
        checks.append({
            "check_id": f"lifecycle_exists:{rel}",
            "target": rel,
            "expected": "file_exists",
            "actual": "exists" if p.exists() else "missing",
            "status": "pass" if p.exists() else "advisory",
            "evidence_ref": rel,
            "reason_code": "" if p.exists() else "lifecycle_artifact_not_yet_written",
        })

    # Dependency satisfaction
    for dep in DEPENDENCIES:
        ok, evidence = status_done(dep)
        checks.append({
            "check_id": f"dependency_satisfied:{dep}",
            "target": f"artifacts/status/{dep}.status.json",
            "expected": "state=done verify_result=pass",
            "actual": evidence,
            "status": "pass" if ok else "advisory",
            "evidence_ref": f"artifacts/status/{dep}.status.json",
            "reason_code": "" if ok else "dependency_not_done",
        })

    # Governance JSON existence + schema_version + plan_version + created_by_task
    if not GOVERNANCE_JSON.exists():
        checks.append({
            "check_id": "characterization_artifact_exists",
            "target": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
            "expected": "exists",
            "actual": "missing",
            "status": "advisory",
            "evidence_ref": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
            "reason_code": "governance_artifact_missing",
        })
        gov = None
    else:
        gov = json.loads(GOVERNANCE_JSON.read_text(encoding="utf-8"))
        checks.append({
            "check_id": "characterization_artifact_exists",
            "target": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
            "expected": "exists",
            "actual": "exists",
            "status": "pass",
            "evidence_ref": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
            "reason_code": "",
        })
        for field, want in (
            ("schema_version", "validator-test-monolith-characterization/v1"),
            ("plan_version", "v3.5.1"),
            ("created_by_task", "TASK-1031"),
        ):
            actual = gov.get(field)
            checks.append({
                "check_id": f"characterization_artifact_field:{field}",
                "target": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
                "expected": want,
                "actual": actual,
                "status": "pass" if actual == want else "advisory",
                "evidence_ref": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
                "reason_code": "" if actual == want else "field_mismatch",
            })

    # Per-target metrics cross-check
    targets_analyzed: list[dict] = []
    gov_targets = {t["path"]: t for t in (gov.get("targets", []) if gov else [])}
    for rel in TARGETS:
        p = REPO_ROOT / rel
        sha = sha256_of(p)
        m = static_metrics(p)
        gov_t = gov_targets.get(rel, {})
        target_record = {
            "path": rel,
            "exists": p.exists(),
            "sha256": sha,
            "metrics": m,
            "governance_match": False,
        }
        if not p.exists():
            checks.append({
                "check_id": f"target_exists:{rel}",
                "target": rel,
                "expected": "exists",
                "actual": "missing",
                "status": "advisory",
                "evidence_ref": rel,
                "reason_code": "target_missing",
            })
            targets_analyzed.append(target_record)
            continue
        # sha256 match
        sha_match = sha == gov_t.get("sha256")
        checks.append({
            "check_id": f"target_sha256_match:{rel}",
            "target": rel,
            "expected": gov_t.get("sha256"),
            "actual": sha,
            "status": "pass" if sha_match else "advisory",
            "evidence_ref": rel,
            "reason_code": "" if sha_match else "sha256_mismatch_with_governance_artifact",
        })
        # loc + counts match
        for key in (
            "loc",
            "function_count",
            "top_function_count",
            "class_count",
            "top_class_count",
            "top_level_statement_count",
            "main_guard_present",
        ):
            actual = m.get(key) if m else None
            expected = gov_t.get(key)
            ok = actual == expected
            checks.append({
                "check_id": f"target_metric:{rel}:{key}",
                "target": rel,
                "expected": expected,
                "actual": actual,
                "status": "pass" if ok else "advisory",
                "evidence_ref": rel,
                "reason_code": "" if ok else "metric_mismatch_with_governance_artifact",
            })
        # template mirror byte-equality status
        template_rel = "template/" + rel
        template_path = REPO_ROOT / template_rel
        template_sha = sha256_of(template_path)
        if template_path.exists():
            byte_identical = template_sha == sha
            expected_status = gov_t.get("template_mirror_status")
            actual_status = "byte_identical" if byte_identical else "drift_baseline_existing"
            ok = expected_status == actual_status
            checks.append({
                "check_id": f"template_mirror_status:{rel}",
                "target": template_rel,
                "expected": expected_status,
                "actual": actual_status,
                "status": "pass" if ok else "advisory",
                "evidence_ref": template_rel,
                "reason_code": "" if ok else "template_mirror_status_unexpected",
            })
        target_record["governance_match"] = sha_match
        targets_analyzed.append(target_record)

    # Required top-level sections
    if gov:
        required_sections = [
            "targets",
            "summary",
            "responsibility_map",
            "source_template_implications",
            "cli_surface",
            "import_side_effect_surface",
            "golden_cli_surface",
            "test_monolith_surface",
            "risk_register",
            "refactor_readiness_criteria",
            "policy_registry_extraction_inputs",
            "limitations",
        ]
        for s in required_sections:
            present = s in gov and gov[s] not in (None, "", [], {})
            checks.append({
                "check_id": f"section_present:{s}",
                "target": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
                "expected": "non_empty",
                "actual": "non_empty" if present else "missing_or_empty",
                "status": "pass" if present else "advisory",
                "evidence_ref": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
                "reason_code": "" if present else "required_section_missing",
            })

        # readiness conservativeness
        readiness = gov.get("summary", {}).get("readiness_status")
        ok_readiness = readiness in (
            "not_ready_for_split",
            "partially_ready_for_split",
            "ready_for_split_candidate",
        )
        checks.append({
            "check_id": "readiness_status_in_vocabulary",
            "target": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
            "expected": "in {not_ready_for_split, partially_ready_for_split, ready_for_split_candidate}",
            "actual": readiness,
            "status": "pass" if ok_readiness else "advisory",
            "evidence_ref": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
            "reason_code": "" if ok_readiness else "readiness_status_invalid",
        })

    # Aggregate overall_status: pass when zero advisory checks remain.
    advisory_count = sum(1 for c in checks if c["status"] == "advisory")
    pass_count = sum(1 for c in checks if c["status"] == "pass")
    skipped_count = sum(1 for c in checks if c["status"] == "skipped_with_reason_code")

    overall_status = "pass" if advisory_count == 0 else "advisory"

    result = {
        "schema_version": "characterization-result/v1",
        "task_id": "TASK-1031",
        "generated_at": now_taipei_iso(),
        "characterization_ref": "artifacts/governance/validator-test-monolith-characterization.v3.5.1.json",
        "overall_status": overall_status,
        "targets_analyzed": targets_analyzed,
        "summary": {
            "checks_total": len(checks),
            "checks_pass": pass_count,
            "checks_advisory": advisory_count,
            "checks_skipped_with_reason_code": skipped_count,
        },
        "checks": checks,
        "limitations": [
            "Helper performs static-only analysis: ast.parse on raw bytes, sha256 on raw bytes; no module is imported from the repository.",
            "Helper does not execute any CLI; argv shapes inside governance artifact are not runtime-verified.",
            "advisory status is used (not fail) so that the helper remains advisory when invoked by Codex post-commit verifier; pass requires zero advisory checks.",
            "PYTHONDONTWRITEBYTECODE=1 + sys.dont_write_bytecode=True set before any heavy import; helper produces no __pycache__.",
        ],
    }

    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "output_written": str(RESULT_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
        "overall_status": overall_status,
        "checks_total": len(checks),
        "checks_pass": pass_count,
        "checks_advisory": advisory_count,
    }, indent=2))

    return 0 if overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
