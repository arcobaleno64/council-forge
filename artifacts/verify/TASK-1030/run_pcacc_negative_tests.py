#!/usr/bin/env python3
"""TASK-1030 PCACC controlled negative tests.

Imports run_precommit_check as a module and invokes run_pcacc_001..004 and
validate_policy against synthetic fixture repo_roots and synthetic policy
mutations. Real lifecycle artifacts and real policy files are NOT mutated.

Active PCACC surface tested: PCACC-001..PCACC-004 only. AC-to-verify coverage,
reasoning faithfulness, belief-state, model self-confidence, free-text
rationale, and SAVeR markdown remain excluded; cases 007/008 prove that
attempts to activate forbidden output fields or expand the active check
surface are rejected by validate_policy.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import os
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import copy
import importlib.util
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

THIS = Path(__file__).resolve()
BASE = THIS.parent
REPO_ROOT = THIS.parents[3]
RUNNER_PATH = REPO_ROOT / "artifacts" / "scripts" / "run_precommit_check.py"
POLICY_PATH = REPO_ROOT / "artifacts" / "governance" / "precommit-check-policy.v3.5.json"
FIXTURE_ROOT = BASE / "fixtures"
RESULT_PATH = BASE / "pcacc-negative-test-result.json"

TAIPEI_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).replace(microsecond=0).isoformat()


def import_runner():
    spec = importlib.util.spec_from_file_location("pcacc_runner_mod", str(RUNNER_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load runner spec from " + str(RUNNER_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pcacc_runner_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def reset_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)).replace("\\", "/")


def task_md(task_id: str, owner: str = "Claude", final_approver: str = "arcobaleno") -> str:
    return (
        "# Task: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Owner: " + owner + "\n"
        "- Status: drafted\n"
        "- Last Updated: 2026-05-04T16:00:00+08:00\n\n"
        "## Agent Roles\n\n"
        "agent_roles:\n"
        "  final_approver:\n"
        "    reviewer_id: " + final_approver + "\n"
    )


def plan_md(task_id: str) -> str:
    return (
        "# Plan: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Status: ready\n"
        "- Last Updated: 2026-05-04T16:00:00+08:00\n"
    )


def decision_md(task_id: str) -> str:
    return (
        "# Decision: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Status: done\n"
        "- Last Updated: 2026-05-04T16:00:00+08:00\n"
    )


def verify_md(
    task_id: str,
    refs: List[str],
    last_updated: str = "2026-05-04T17:00:00+08:00",
) -> str:
    if not refs:
        section = "## Evidence Refs\n- None\n"
    else:
        section = "## Evidence Refs\n" + "\n".join("- " + r for r in refs) + "\n"
    return (
        "# Verification: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Owner: Claude\n"
        "- Status: pass\n"
        "- Last Updated: " + last_updated + "\n\n"
        + section
    )


def write_lifecycle(
    case_root: Path,
    task_id: str,
    *,
    owner: str = "Claude",
    refs: List[str] | None = None,
    status_extra: Dict[str, Any] | None = None,
    include_status: bool = True,
    include_verify: bool = True,
) -> None:
    write_text(case_root / "artifacts/tasks" / (task_id + ".task.md"), task_md(task_id, owner=owner))
    write_text(case_root / "artifacts/plans" / (task_id + ".plan.md"), plan_md(task_id))
    write_text(case_root / "artifacts/decisions" / (task_id + ".decision.md"), decision_md(task_id))
    if include_verify:
        write_text(
            case_root / "artifacts/verify" / (task_id + ".verify.md"),
            verify_md(task_id, refs or []),
        )
    if include_status:
        status: Dict[str, Any] = {"task_id": task_id, "state": "done", "current_owner": owner}
        if status_extra:
            status.update(status_extra)
        write_json(case_root / "artifacts/status" / (task_id + ".status.json"), status)


def case_001(runner) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-001-missing-lifecycle"
    task_id = "TASK-9001"
    write_lifecycle(case_root, task_id, include_status=False)
    check = runner.run_pcacc_001(case_root, task_id)
    return {
        "case_id": "PCACC-NEG-001",
        "title": "Missing lifecycle artifact (status.json absent)",
        "pcacc_check_id": "PCACC-001",
        "fixture_paths": [rel(case_root) + "/"],
        "expected_status": "fail",
        "actual_status": check["status"],
        "expected_reason_code": "lifecycle_missing:status",
        "actual_reason_code": check["reason_code"],
        "pass": (
            check["status"] == "fail"
            and check["reason_code"].startswith("lifecycle_missing")
            and "status" in check["reason_code"]
        ),
        "notes": "Synthetic lifecycle missing status.json; PCACC-001 must report lifecycle_missing:status.",
    }


def case_002(runner) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-002-malformed-evidence-ref"
    task_id = "TASK-9002"
    write_lifecycle(case_root, task_id, refs=["garbage_token_not_a_known_prefix"])
    check = runner.run_pcacc_002(case_root, task_id)
    return {
        "case_id": "PCACC-NEG-002",
        "title": "Malformed Evidence Ref",
        "pcacc_check_id": "PCACC-002",
        "fixture_paths": [rel(case_root) + "/"],
        "expected_status": "fail",
        "actual_status": check["status"],
        "expected_reason_code": "malformed_refs",
        "actual_reason_code": check["reason_code"],
        "pass": check["status"] == "fail" and "malformed_refs" in check["reason_code"],
        "notes": "Verify Evidence Refs entry 'garbage_token_not_a_known_prefix' matches no allowed path/HEAD/commit prefix; PCACC-002 must flag malformed_refs.",
    }


def case_003(runner) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-003-missing-evidence-ref"
    task_id = "TASK-9003"
    write_lifecycle(case_root, task_id, refs=[])
    check = runner.run_pcacc_002(case_root, task_id)
    return {
        "case_id": "PCACC-NEG-003",
        "title": "Missing Evidence Ref when required (empty section)",
        "pcacc_check_id": "PCACC-002",
        "fixture_paths": [rel(case_root) + "/"],
        "expected_status": "fail",
        "actual_status": check["status"],
        "expected_reason_code": "evidence_refs_section_empty",
        "actual_reason_code": check["reason_code"],
        "pass": check["status"] == "fail" and "evidence_refs_section_empty" in check["reason_code"],
        "notes": "Verify file '## Evidence Refs' contains only '- None'; PCACC-002 must flag empty section.",
    }


def case_004(runner, policy: Dict[str, Any]) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-004-non-canonical-owner"
    task_id = "TASK-9004"
    write_lifecycle(case_root, task_id, owner="RogueAgent")
    check = runner.run_pcacc_003(case_root, task_id, policy)
    return {
        "case_id": "PCACC-NEG-004",
        "title": "Non-canonical owner/reviewer reference",
        "pcacc_check_id": "PCACC-003",
        "fixture_paths": [rel(case_root) + "/"],
        "expected_status": "fail",
        "actual_status": check["status"],
        "expected_reason_code": "non_canonical",
        "actual_reason_code": check["reason_code"],
        "pass": check["status"] == "fail" and "non_canonical" in check["reason_code"],
        "notes": "status.current_owner='RogueAgent' and task.Owner='RogueAgent' violate canonical_owners=['Claude','Codex','Gemini'].",
    }


def case_005(runner) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-005-review-before-evidence"
    task_id = "TASK-9005"
    evidence_ref_rel = "artifacts/verify/" + task_id + "/evidence.json"
    write_lifecycle(
        case_root,
        task_id,
        refs=[],
        status_extra={
            "last_updated": "2026-05-04T10:00:00+08:00",
            "self_check_result_ref": evidence_ref_rel,
        },
    )
    write_json(
        case_root / "artifacts/verify" / task_id / "evidence.json",
        {"generated_at": "2026-05-04T15:00:00+08:00", "task_id": task_id},
    )
    check = runner.run_pcacc_004(case_root, task_id)
    return {
        "case_id": "PCACC-NEG-005",
        "title": "review_timestamp earlier than evidence_generated_at",
        "pcacc_check_id": "PCACC-004",
        "fixture_paths": [rel(case_root) + "/"],
        "expected_status": "fail",
        "actual_status": check["status"],
        "expected_reason_code": "review_before_evidence",
        "actual_reason_code": check["reason_code"],
        "pass": check["status"] == "fail" and check["reason_code"] == "review_before_evidence",
        "notes": "review_ts=2026-05-04T10:00:00+08:00 < evidence_ts=2026-05-04T15:00:00+08:00; PCACC-004 strict comparison must reject review-before-evidence.",
    }


def case_006(runner) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-006-missing-timestamp-explicit-reason"
    task_id = "TASK-9006"
    write_lifecycle(
        case_root,
        task_id,
        include_verify=False,
        status_extra={"state": "verifying"},
    )
    check = runner.run_pcacc_004(case_root, task_id)
    return {
        "case_id": "PCACC-NEG-006",
        "title": "Missing timestamps must yield explicit reason_code (never silent pass)",
        "pcacc_check_id": "PCACC-004",
        "fixture_paths": [rel(case_root) + "/"],
        "expected_status": "skipped_with_reason_code",
        "actual_status": check["status"],
        "expected_reason_code": "no_review_or_evidence_timestamp",
        "actual_reason_code": check["reason_code"],
        "pass": (
            check["status"] == "skipped_with_reason_code"
            and check["reason_code"] == "no_review_or_evidence_timestamp"
            and check["status"] != "pass"
        ),
        "notes": "v3.5.0 PCACC-004 policy: 'Missing review_timestamp or evidence_generated_at returns skipped_with_reason_code, never silent pass.' This case proves no silent pass when timestamps are missing — operational equivalent of fail-without-silent-pass per prompt 8.6 'or equivalent' clause.",
    }


def case_007(runner, base_policy: Dict[str, Any]) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-007-forbidden-free-text-rationale"
    case_root.mkdir(parents=True, exist_ok=True)
    mutated = copy.deepcopy(base_policy)
    mutated["output_policy"]["free_text_rationale"] = True
    policy_path = case_root / "mutated-policy.json"
    write_json(policy_path, mutated)
    err = runner.validate_policy(mutated)
    pass_ok = err == "output_policy_free_text_rationale_must_be_false"
    return {
        "case_id": "PCACC-NEG-007",
        "title": "Forbidden free_text_rationale field activation",
        "pcacc_check_id": "policy.output_policy.free_text_rationale",
        "fixture_paths": [rel(policy_path)],
        "expected_status": "fail",
        "actual_status": "fail" if err else "pass",
        "expected_reason_code": "output_policy_free_text_rationale_must_be_false",
        "actual_reason_code": err or "policy_accepted_unsafely",
        "pass": pass_ok,
        "notes": "Synthetic policy mutation sets output_policy.free_text_rationale=true. validate_policy must reject and return the exact reason_code. Real precommit-check-policy.v3.5.json is NOT mutated.",
    }


def case_008(runner, base_policy: Dict[str, Any]) -> Dict[str, Any]:
    case_root = FIXTURE_ROOT / "case-008-ac-coverage-activation"
    case_root.mkdir(parents=True, exist_ok=True)
    mutated = copy.deepcopy(base_policy)
    mutated["checks"].append({
        "check_id": "PCACC-005",
        "title": "AC-to-verify coverage (forbidden activation)",
        "severity": "blocking",
        "rationale": "Attempted activation of v3.5.1-deferred AC-to-verify coverage as an active 5th PCACC check.",
        "implemented_by": "synthetic_policy_mutation",
    })
    policy_path = case_root / "mutated-policy.json"
    write_json(policy_path, mutated)
    err = runner.validate_policy(mutated)
    pass_ok = err is not None and err.startswith("checks_count_must_be_exactly_4_got_")
    return {
        "case_id": "PCACC-NEG-008",
        "title": "Attempted AC-to-verify coverage activation as 5th active check",
        "pcacc_check_id": "policy.checks_count",
        "fixture_paths": [rel(policy_path)],
        "expected_status": "fail",
        "actual_status": "fail" if err else "pass",
        "expected_reason_code": "checks_count_must_be_exactly_4_got_5",
        "actual_reason_code": err or "policy_accepted_unsafely",
        "pass": pass_ok,
        "notes": "Synthetic policy mutation appends PCACC-005 (AC-to-verify coverage) as a 5th active check. validate_policy must reject (must be exactly 4 checks). v3.5.1 explicitly defers AC-to-verify coverage. Real policy is NOT mutated.",
    }


def main() -> int:
    runner = import_runner()
    base_policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    sanity_err = runner.validate_policy(base_policy)
    if sanity_err is not None:
        print(json.dumps({"error": "real_policy_failed_sanity", "detail": sanity_err}))
        return 2

    reset_dir(FIXTURE_ROOT)

    cases = [
        case_001(runner),
        case_002(runner),
        case_003(runner),
        case_004(runner, base_policy),
        case_005(runner),
        case_006(runner),
        case_007(runner, base_policy),
        case_008(runner, base_policy),
    ]

    overall = "pass" if all(c["pass"] for c in cases) else "fail"

    result = {
        "schema_version": "pcacc-negative-test-result/v1",
        "task_id": "TASK-1030",
        "generated_at": now_iso(),
        "runner_ref": "artifacts/scripts/run_precommit_check.py",
        "policy_ref": "artifacts/governance/precommit-check-policy.v3.5.json",
        "fixture_root": "artifacts/verify/TASK-1030/fixtures/",
        "isolation_strategy": "import run_precommit_check as module; invoke run_pcacc_001..004 with synthetic fixture repo_roots; invoke validate_policy with deepcopied synthetic policy mutations; runner unchanged; mirror unchanged; real policy unchanged",
        "overall_status": overall,
        "cases": cases,
        "limitations": [
            "PCACC v3.5.0 controlled-negative tests run against synthetic fixtures and synthetic policy mutations only.",
            "Real artifacts/scripts/run_precommit_check.py and template/artifacts/scripts/run_precommit_check.py are NOT modified by TASK-1030.",
            "Real artifacts/governance/precommit-check-policy.v3.5.json is NOT mutated by TASK-1030.",
            "Real production lifecycle artifacts (TASK-1023..TASK-1029) are NOT mutated to create negative cases.",
            "Active PCACC check surface remains exactly PCACC-001..PCACC-004; AC-to-verify coverage and reasoning-faithfulness/belief-state/SAVeR remain excluded.",
            "Case PCACC-NEG-006 expected_status='skipped_with_reason_code' aligns with v3.5.0 policy: missing timestamps yield explicit reason_code (never silent pass) — operational equivalent of fail-without-silent-pass per prompt 8.6 'or equivalent' clause.",
            "Cases PCACC-NEG-007 and PCACC-NEG-008 exercise validate_policy on deepcopied synthetic policies; real policy is loaded read-only.",
        ],
    }

    write_json(RESULT_PATH, result)
    summary = {
        "output_written": rel(RESULT_PATH),
        "overall_status": overall,
        "cases_total": len(cases),
        "cases_passed": sum(1 for c in cases if c["pass"]),
    }
    print(json.dumps(summary))
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
