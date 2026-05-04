#!/usr/bin/env python3
"""TASK-1035 controlled registry regression driver.

Runs the 11 EVREF-REG-* cases against the production PCACC runner with the
explicitly supplied production Evidence Ref policy registry, and emits two
machine-readable evidence files:

  - artifacts/verify/TASK-1035/registry-regression-result.json
  - artifacts/verify/TASK-1035/evidence-ref-runtime-extraction-result.json

Design constraints (TASK-1035):
- Standard library only.
- sys.dont_write_bytecode=True; no __pycache__ created.
- Loads run_precommit_check.py via importlib.util (no sys.path pollution).
- Each case operates on a self-contained synthetic repo_root under
  artifacts/verify/TASK-1035/fixtures/.
- TASK-1030 NEG-002 / NEG-003 anchor reason_codes are preserved string-identical.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

HELPER_PATH = Path(__file__).resolve()
TASK_VERIFY_DIR = HELPER_PATH.parent
TASK_FIXTURE_ROOT = TASK_VERIFY_DIR / "fixtures"
REPO_ROOT = HELPER_PATH.parents[3]
RUNNER_PATH = REPO_ROOT / "artifacts" / "scripts" / "run_precommit_check.py"
TEMPLATE_RUNNER_PATH = REPO_ROOT / "template" / "artifacts" / "scripts" / "run_precommit_check.py"
REGISTRY_PATH = REPO_ROOT / "artifacts" / "governance" / "evidence-ref-policy.v3.5.3.json"
TAIPEI_TZ = timezone(timedelta(hours=8))


def now_taipei_iso() -> str:
    return datetime.now(TAIPEI_TZ).replace(microsecond=0).isoformat()


def sha256_prefix(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_runner_module():
    spec = importlib.util.spec_from_file_location(
        "run_precommit_check_t1035", str(RUNNER_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    runner = load_runner_module()
    registry = runner.load_evidence_ref_registry(REGISTRY_PATH)

    cases: List[Dict[str, Any]] = []

    def run_case(
        case_id: str,
        title: str,
        fixture_repo_root: Path,
        task_id: str,
        expected_status: str,
        expected_reason_substr: str,
        evidence_ref: str,
        notes: str,
    ) -> None:
        check = runner.run_pcacc_002(fixture_repo_root, task_id, registry)
        actual_status = check["status"]
        actual_reason = check.get("reason_code", "")
        passed = (
            actual_status == expected_status
            and (expected_reason_substr == "" or expected_reason_substr in actual_reason)
        )
        cases.append({
            "case_id": case_id,
            "title": title,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "expected_reason_code": expected_reason_substr,
            "actual_reason_code": actual_reason,
            "pass": passed,
            "evidence_ref": evidence_ref,
            "notes": notes,
        })

    f001 = TASK_FIXTURE_ROOT / "evref-reg-001-malformed"
    f002 = TASK_FIXTURE_ROOT / "evref-reg-002-empty"
    f003 = TASK_FIXTURE_ROOT / "evref-reg-003-valid-local"
    f004 = TASK_FIXTURE_ROOT / "evref-reg-004-absolute"
    f005 = TASK_FIXTURE_ROOT / "evref-reg-005-parent-traversal"
    f006 = TASK_FIXTURE_ROOT / "evref-reg-006-remote-url"
    f007 = TASK_FIXTURE_ROOT / "evref-reg-007-shell-token"
    f008 = TASK_FIXTURE_ROOT / "evref-reg-008-wildcard"
    f009 = TASK_FIXTURE_ROOT / "evref-reg-009-orc-skip"
    f010 = TASK_FIXTURE_ROOT / "evref-reg-010-empty-no-orc"

    run_case(
        "EVREF-REG-001",
        "TASK-1030 NEG-002 malformed_refs anchor remains fail under registry mode",
        f001, "TASK-99001", "fail",
        "malformed_refs:garbage_token_not_a_known_prefix",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-001-malformed/",
        "Registry-driven PCACC-002 must preserve TASK-1030 NEG-002 reason_code byte-identical.",
    )
    run_case(
        "EVREF-REG-002",
        "TASK-1030 NEG-003 evidence_refs_section_empty anchor remains fail under registry mode (no ORC marker)",
        f002, "TASK-99002", "fail",
        "evidence_refs_section_empty",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-002-empty/",
        "Empty section without ORC reason_code remains fail under registry mode (matches TASK-1030 NEG-003).",
    )
    run_case(
        "EVREF-REG-003",
        "Valid local artifact ref passes under registry mode",
        f003, "TASK-99003", "pass",
        "evidence_refs_resolved",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-003-valid-local/",
        "Ref resolves to artifacts/stub/local.txt under fixture repo_root.",
    )
    run_case(
        "EVREF-REG-004",
        "Absolute path fails under registry mode",
        f004, "TASK-99004", "fail",
        "malformed_refs",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-004-absolute/",
        "/etc/passwd ref classified as malformed.",
    )
    run_case(
        "EVREF-REG-005",
        "Parent traversal fails under registry mode",
        f005, "TASK-99005", "fail",
        "malformed_refs",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-005-parent-traversal/",
        "../../../etc/passwd ref blocked by registry parent-traversal sieve.",
    )
    run_case(
        "EVREF-REG-006",
        "Remote URL fails under registry mode",
        f006, "TASK-99006", "fail",
        "malformed_refs",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-006-remote-url/",
        "https:// ref blocked by registry forbidden_url_schemes sieve.",
    )
    run_case(
        "EVREF-REG-007",
        "Shell command token fails under registry mode",
        f007, "TASK-99007", "fail",
        "malformed_refs",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-007-shell-token/",
        "$(whoami) ref does not match any allowed prefix; classified malformed.",
    )
    run_case(
        "EVREF-REG-008",
        "Wildcard-only ref fails under registry mode",
        f008, "TASK-99008", "fail",
        "malformed_refs",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-008-wildcard/",
        "Glob '**' ref does not match any allowed prefix; classified malformed.",
    )
    run_case(
        "EVREF-REG-009",
        "Missing optional ref with ORC reason_code is skipped",
        f009, "TASK-99009", "skipped_with_reason_code",
        "evidence_refs_optional_per_orc_1",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-009-orc-skip/",
        "Empty Evidence Refs section with explicit ORC-1 marker is skipped under registry mode.",
    )
    run_case(
        "EVREF-REG-010",
        "Missing optional ref without reason_code fails under registry mode",
        f010, "TASK-99010", "fail",
        "evidence_refs_section_empty",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-010-empty-no-orc/",
        "Empty Evidence Refs section without ORC marker remains fail under registry mode.",
    )

    # EVREF-REG-011: registry load failure when explicitly requested + default
    # behavior unchanged when registry not requested.
    missing_registry_path = (
        TASK_FIXTURE_ROOT / "evref-reg-011-missing-registry" / "missing.json"
    )
    try:
        runner.load_evidence_ref_registry(missing_registry_path)
        load_failed_correctly = False
        load_reason = "no_exception_raised"
    except runner.EvidenceRefRegistryError as e:
        load_failed_correctly = (e.reason_code == "evidence_ref_registry_missing")
        load_reason = e.reason_code
    default_check = runner.run_pcacc_002(f002, "TASK-99002", None)
    default_unchanged = (
        default_check["status"] == "fail"
        and default_check.get("reason_code") == "evidence_refs_section_empty"
    )
    case_011_pass = load_failed_correctly and default_unchanged
    cases.append({
        "case_id": "EVREF-REG-011",
        "title": "Registry load failure fails closed when requested; default behavior unchanged when not requested",
        "expected_status": "pass",
        "actual_status": "pass" if case_011_pass else "fail",
        "expected_reason_code": "load_failed_with_evidence_ref_registry_missing AND default_unchanged",
        "actual_reason_code": (
            "load_reason=" + load_reason
            + ";default_status=" + default_check["status"]
            + ";default_reason=" + str(default_check.get("reason_code"))
        ),
        "pass": case_011_pass,
        "evidence_ref": "artifacts/verify/TASK-1035/fixtures/evref-reg-011-missing-registry/missing.json",
        "notes": "load_evidence_ref_registry on missing path raises EvidenceRefRegistryError(reason_code=evidence_ref_registry_missing); run_pcacc_002 on empty fixture without registry continues to return fail/evidence_refs_section_empty.",
    })

    overall_pass = all(c["pass"] for c in cases)
    regression_out = {
        "schema_version": "evidence-ref-registry-regression/v1",
        "task_id": "TASK-1035",
        "generated_at": now_taipei_iso(),
        "runner_ref": "artifacts/scripts/run_precommit_check.py",
        "registry_ref": "artifacts/governance/evidence-ref-policy.v3.5.3.json",
        "overall_status": "pass" if overall_pass else "fail",
        "cases": cases,
        "limitations": [
            "Cases EVREF-REG-001..010 invoke run_pcacc_002 directly with synthetic fixture repo_roots; runner module is loaded once via importlib.util (no sys.path pollution); sys.dont_write_bytecode=True prevents __pycache__ creation.",
            "EVREF-REG-001 / EVREF-REG-002 inherit TASK-1030 NEG-002 / NEG-003 anchor strings; reason_codes are byte-identical.",
            "EVREF-REG-009 ORC skip semantics are activated only under registry-driven mode; default in-module mode continues to fail on empty section.",
            "EVREF-REG-011 covers the registry-missing failure mode and the default-mode preservation; malformed-JSON / schema-invalid / pcacc-conflict failure modes are exercised in evidence-ref-runtime-extraction-result.json.",
        ],
    }
    regression_path = TASK_VERIFY_DIR / "registry-regression-result.json"
    with regression_path.open("w", encoding="utf-8") as f:
        json.dump(regression_out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("registry-regression-result:", regression_out["overall_status"])

    # ---- evidence-ref-runtime-extraction-result.json ----
    re_checks: List[Dict[str, Any]] = []

    def re_add(check_id, target, expected, actual, status, evidence_ref, reason_code):
        re_checks.append({
            "check_id": check_id,
            "target": target,
            "expected": expected,
            "actual": actual,
            "status": status,
            "evidence_ref": evidence_ref,
            "reason_code": reason_code,
        })

    re_add(
        "RTX-001",
        "artifacts/governance/evidence-ref-policy.v3.5.3.json",
        "registry_file_exists",
        "exists" if REGISTRY_PATH.is_file() else "missing",
        "pass" if REGISTRY_PATH.is_file() else "fail",
        "artifacts/governance/evidence-ref-policy.v3.5.3.json",
        "registry_present_on_disk",
    )

    valid_load = True
    try:
        runner.load_evidence_ref_registry(REGISTRY_PATH)
    except runner.EvidenceRefRegistryError:
        valid_load = False
    re_add(
        "RTX-002",
        "evidence-ref-policy.v3.5.3.json schema",
        "schema_valid_per_load_evidence_ref_registry",
        "valid" if valid_load else "invalid",
        "pass" if valid_load else "fail",
        "artifacts/governance/evidence-ref-policy.v3.5.3.json",
        "schema_validated_no_exception",
    )

    rc_auth = registry.get("runtime_consumption_authorized") is True
    re_add(
        "RTX-003",
        "registry.runtime_consumption_authorized",
        "true",
        str(registry.get("runtime_consumption_authorized")),
        "pass" if rc_auth else "fail",
        "artifacts/governance/evidence-ref-policy.v3.5.3.json#runtime_consumption_authorized",
        "runtime_consumption_authorized_true",
    )

    runner_text = RUNNER_PATH.read_text(encoding="utf-8")
    has_arg = "--evidence-ref-policy" in runner_text and "load_evidence_ref_registry" in runner_text
    re_add(
        "RTX-004",
        "run_precommit_check.py --evidence-ref-policy + load_evidence_ref_registry",
        "cli_argument_and_loader_present",
        "present" if has_arg else "absent",
        "pass" if has_arg else "fail",
        "artifacts/scripts/run_precommit_check.py",
        "explicit_cli_flag_supported",
    )

    default_unchanged_002 = runner.run_pcacc_002(f002, "TASK-99002", None)
    default_pass_002 = (
        default_unchanged_002["status"] == "fail"
        and default_unchanged_002.get("reason_code") == "evidence_refs_section_empty"
    )
    default_unchanged_001 = runner.run_pcacc_002(f001, "TASK-99001", None)
    default_pass_001 = (
        default_unchanged_001["status"] == "fail"
        and default_unchanged_001.get("reason_code")
        == "malformed_refs:garbage_token_not_a_known_prefix"
    )
    default_pass = default_pass_001 and default_pass_002
    re_add(
        "RTX-005",
        "default behavior on TASK-1030 NEG-002 / NEG-003 fixtures without registry",
        "fail+malformed_refs:garbage_token_not_a_known_prefix AND fail+evidence_refs_section_empty",
        (
            "neg002_status=" + default_unchanged_001["status"]
            + ";neg002_reason=" + str(default_unchanged_001.get("reason_code"))
            + ";neg003_status=" + default_unchanged_002["status"]
            + ";neg003_reason=" + str(default_unchanged_002.get("reason_code"))
        ),
        "pass" if default_pass else "fail",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-001-malformed/;artifacts/verify/TASK-1035/fixtures/evref-reg-002-empty/",
        "default_in_module_behavior_unchanged_without_flag",
    )

    try:
        runner.load_evidence_ref_registry(missing_registry_path)
        miss_fail_closed = False
        miss_reason = "no_exception_raised"
    except runner.EvidenceRefRegistryError as e:
        miss_fail_closed = (e.reason_code == "evidence_ref_registry_missing")
        miss_reason = e.reason_code
    re_add(
        "RTX-006",
        "load_evidence_ref_registry on missing path",
        "raise_evidence_ref_registry_missing",
        miss_reason,
        "pass" if miss_fail_closed else "fail",
        "artifacts/verify/TASK-1035/fixtures/evref-reg-011-missing-registry/missing.json",
        "fail_closed_on_missing_registry",
    )

    malformed_path = TASK_FIXTURE_ROOT / "registry-malformed" / "malformed-json.json"
    try:
        runner.load_evidence_ref_registry(malformed_path)
        mj_fail_closed = False
        mj_reason = "no_exception_raised"
    except runner.EvidenceRefRegistryError as e:
        mj_fail_closed = (e.reason_code == "evidence_ref_registry_malformed_json")
        mj_reason = e.reason_code
    re_add(
        "RTX-007",
        "load_evidence_ref_registry on malformed JSON",
        "raise_evidence_ref_registry_malformed_json",
        mj_reason,
        "pass" if mj_fail_closed else "fail",
        "artifacts/verify/TASK-1035/fixtures/registry-malformed/malformed-json.json",
        "fail_closed_on_malformed_json",
    )

    schema_invalid_path = TASK_FIXTURE_ROOT / "registry-malformed" / "schema-version-mismatch.json"
    try:
        runner.load_evidence_ref_registry(schema_invalid_path)
        si_fail_closed = False
        si_reason = "no_exception_raised"
    except runner.EvidenceRefRegistryError as e:
        si_fail_closed = (e.reason_code == "evidence_ref_registry_schema_version_mismatch")
        si_reason = e.reason_code
    re_add(
        "RTX-008",
        "load_evidence_ref_registry on schema_version mismatch",
        "raise_evidence_ref_registry_schema_version_mismatch",
        si_reason,
        "pass" if si_fail_closed else "fail",
        "artifacts/verify/TASK-1035/fixtures/registry-malformed/schema-version-mismatch.json",
        "fail_closed_on_schema_version_mismatch",
    )

    conflict_path = TASK_FIXTURE_ROOT / "registry-malformed" / "pcacc-conflict.json"
    try:
        runner.load_evidence_ref_registry(conflict_path)
        pc_fail_closed = False
        pc_reason = "no_exception_raised"
    except runner.EvidenceRefRegistryError as e:
        pc_fail_closed = (e.reason_code == "evidence_ref_registry_pcacc_002_conflict")
        pc_reason = e.reason_code
    re_add(
        "RTX-009",
        "load_evidence_ref_registry on pcacc compatibility conflict",
        "raise_evidence_ref_registry_pcacc_002_conflict",
        pc_reason,
        "pass" if pc_fail_closed else "fail",
        "artifacts/verify/TASK-1035/fixtures/registry-malformed/pcacc-conflict.json",
        "fail_closed_on_pcacc_002_conflict",
    )

    neg_preserved = all(
        c["pass"] for c in cases if c["case_id"] in ("EVREF-REG-001", "EVREF-REG-002")
    )
    re_add(
        "RTX-010",
        "TASK-1030 NEG-002 / NEG-003 anchor reason_codes",
        "preserved_under_registry_mode_via_EVREF-REG-001_and_EVREF-REG-002",
        "preserved" if neg_preserved else "drifted",
        "pass" if neg_preserved else "fail",
        "artifacts/verify/TASK-1035/registry-regression-result.json#cases[0..1]",
        "task_1030_anchor_preserved",
    )

    all_pass = all(c["pass"] for c in cases)
    re_add(
        "RTX-011",
        "EVREF-REG-001..011 registry regression",
        "all_eleven_cases_pass",
        ("11/11_pass" if all_pass else "some_failed"),
        "pass" if all_pass else "fail",
        "artifacts/verify/TASK-1035/registry-regression-result.json#overall_status",
        "registry_regression_overall_pass",
    )

    root_runner_sha = hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest()
    mirror_runner_sha = hashlib.sha256(TEMPLATE_RUNNER_PATH.read_bytes()).hexdigest()
    byte_eq = root_runner_sha == mirror_runner_sha
    re_add(
        "RTX-012",
        "runner / template mirror byte equality",
        "sha256_match",
        "match" if byte_eq else "drift",
        "pass" if byte_eq else "fail",
        "artifacts/scripts/run_precommit_check.py;template/artifacts/scripts/run_precommit_check.py",
        "byte_identical_mirror;sha256_root=" + root_runner_sha[:16],
    )

    pcacc_compat = registry.get("pcacc_compatibility", {})
    no_expansion = (
        pcacc_compat.get("prototype_introduces_pcacc_005") is False
        and pcacc_compat.get("current_pcacc_active_check_count") == 4
        and list(pcacc_compat.get("current_pcacc_active_check_surface", []))
        == ["PCACC-001", "PCACC-002", "PCACC-003", "PCACC-004"]
    )
    re_add(
        "RTX-013",
        "PCACC active check surface expansion",
        "exactly_PCACC-001..004_no_PCACC-005",
        "compliant" if no_expansion else "non_compliant",
        "pass" if no_expansion else "fail",
        "artifacts/governance/evidence-ref-policy.v3.5.3.json#pcacc_compatibility",
        "pcacc_active_check_surface_unchanged",
    )

    ac_excl = (
        pcacc_compat.get("ac_to_verify_coverage_activated") is False
        and pcacc_compat.get("ac_to_verify_coverage_remains_excluded") is True
    )
    re_add(
        "RTX-014",
        "AC-to-verify coverage exclusion",
        "remains_excluded",
        "excluded" if ac_excl else "activated",
        "pass" if ac_excl else "fail",
        "artifacts/governance/evidence-ref-policy.v3.5.3.json#pcacc_compatibility",
        "ac_to_verify_coverage_remains_excluded",
    )

    expected_target_shas = {
        "artifacts/scripts/guard_status_validator.py": "d58a41f6ca49ccfe",
        "artifacts/scripts/guard_contract_validator.py": "7a38af7e2e0af5b7",
        "artifacts/scripts/workflow_constants.py": "e1f09d2100b5685f",
        "artifacts/scripts/run_red_team_suite.py": "77540c3b29f6ece6",
        "artifacts/scripts/test_guard_units.py": "5c7228c9997edffd",
    }
    target_unchanged = True
    target_actual: Dict[str, str] = {}
    for rel, expected_prefix in expected_target_shas.items():
        sha = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()[:16]
        target_actual[rel] = sha
        if sha != expected_prefix:
            target_unchanged = False
    re_add(
        "RTX-015",
        "production validator/test files sha256",
        "all_five_match_TASK-1034_snapshot_prefix",
        "match" if target_unchanged else "drift",
        "pass" if target_unchanged else "fail",
        ";".join(expected_target_shas.keys()),
        "production_validator_test_files_unchanged;"
        + ";".join(k + "=" + v for k, v in target_actual.items()),
    )

    glob_hits: List[str] = []
    for prefix in ("TASK-1036", "TASK-1037", "TASK-1038", "TASK-1039"):
        for sub in ("tasks", "plans", "decisions", "verify", "status"):
            for p in (REPO_ROOT / "artifacts" / sub).glob(prefix + "*"):
                glob_hits.append(str(p.relative_to(REPO_ROOT)).replace("\\", "/"))
    no_future = (len(glob_hits) == 0)
    re_add(
        "RTX-016",
        "TASK-1036+ lifecycle artifact absence",
        "zero_hits",
        "0_hits" if no_future else "found:" + ",".join(glob_hits),
        "pass" if no_future else "fail",
        "artifacts/{tasks,plans,decisions,verify,status}/TASK-1036*..TASK-1039*",
        "no_task_1036_plus_artifacts_present",
    )

    rtx_overall = "pass" if all(c["status"] == "pass" for c in re_checks) else "fail"
    rtx_out = {
        "schema_version": "evidence-ref-runtime-extraction-result/v1",
        "task_id": "TASK-1035",
        "generated_at": now_taipei_iso(),
        "registry_ref": "artifacts/governance/evidence-ref-policy.v3.5.3.json",
        "runner_ref": "artifacts/scripts/run_precommit_check.py",
        "template_runner_ref": "template/artifacts/scripts/run_precommit_check.py",
        "overall_status": rtx_overall,
        "checks": re_checks,
        "limitations": [
            "Each negative-load case re-loads the registry via load_evidence_ref_registry; controlled malformed registries live under artifacts/verify/TASK-1035/fixtures/registry-malformed/.",
            "EVREF-REG-001 / EVREF-REG-002 anchor TASK-1030 NEG-002 / NEG-003 reason_codes; aggregated under RTX-010 here; per-case detail recorded in registry-regression-result.json.",
            "Runtime extraction does not modify production validator/test files (RTX-015) and does not create TASK-1036+ artifacts (RTX-016); both are evidence-only assertions.",
            "Byte-equality of root runner and template mirror is asserted at RTX-012 via sha256.",
        ],
    }
    rtx_path = TASK_VERIFY_DIR / "evidence-ref-runtime-extraction-result.json"
    with rtx_path.open("w", encoding="utf-8") as f:
        json.dump(rtx_out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("evidence-ref-runtime-extraction-result:", rtx_overall)

    return 0 if (overall_pass and rtx_overall == "pass") else 1


if __name__ == "__main__":
    sys.exit(main())
