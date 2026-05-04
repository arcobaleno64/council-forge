#!/usr/bin/env python3
"""TASK-1029 controlled QC-SYNC-001 negative-test driver.

Imports the production run_quality_gates.py runner without modification and
invokes its run_qc_sync_001 function against fixture repo roots and synthetic
baseline / policy dictionaries. No real production source/template pair under
artifacts/scripts/ <-> template/artifacts/scripts/ is mutated.

Six controlled negative cases (matches TASK-1028 v3.5.1 plan section 5.2):
  QC-SYNC-NEG-001  post-baseline source-only addition         -> fail
  QC-SYNC-NEG-002  post-baseline template-only addition       -> fail
  QC-SYNC-NEG-003  post-baseline source/template drift        -> fail
  QC-SYNC-NEG-004  valid unexpired waiver covers drift        -> skipped_with_reason_code
  QC-SYNC-NEG-005  expired waiver does not cover drift        -> fail
  QC-SYNC-NEG-006  baseline-existing unchanged drift          -> pass (baseline_existing)

Cache-safety: sys.dont_write_bytecode = True is set BEFORE importing
run_quality_gates, so importing the runner does not create __pycache__.

Usage:
  python -B artifacts/verify/TASK-1029/run_negative_tests.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

THIS_FILE = Path(__file__).resolve()
TASK_DIR = THIS_FILE.parent                     # artifacts/verify/TASK-1029/
REPO_ROOT = TASK_DIR.parents[2]                 # repo root
RUNNER_DIR = REPO_ROOT / "artifacts" / "scripts"
FIXTURES = TASK_DIR / "fixtures"

if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import run_quality_gates as rqg  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_relpath(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)).replace(os.sep, "/")


def list_fixture_paths(fixture_dir: Path) -> List[str]:
    return sorted(repo_relpath(p) for p in fixture_dir.rglob("*.py") if p.is_file())


def find_check_for_target(checks: List[Dict[str, Any]], target: str) -> Dict[str, Any]:
    for c in checks:
        if c.get("target") == target:
            return c
    return {}


def run_case(
    case_id: str,
    title: str,
    fixture_subdir: str,
    target_rel: str,
    baseline: Dict[str, Any],
    policy: Dict[str, Any],
    today_iso: str,
    expected_status: str,
    expected_reason_substring: str,
    notes: str,
) -> Dict[str, Any]:
    fixture_dir = FIXTURES / fixture_subdir
    checks = rqg.run_qc_sync_001(fixture_dir, baseline, policy, today_iso)
    chk = find_check_for_target(checks, target_rel)
    actual_status = chk.get("status", "no_check_for_target")
    actual_reason: str = chk.get("reason_code", "")
    case_pass = (actual_status == expected_status) and (expected_reason_substring in actual_reason)
    return {
        "case_id": case_id,
        "title": title,
        "fixture_repo_root": repo_relpath(fixture_dir),
        "fixture_paths": list_fixture_paths(fixture_dir),
        "target": target_rel,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "expected_reason_code": expected_reason_substring,
        "actual_reason_code": actual_reason,
        "pass": case_pass,
        "notes": notes,
        "checks_count": len(checks),
        "matched_check": chk,
    }


def main() -> int:
    today_iso = rqg.now_taipei_iso()

    cases: List[Dict[str, Any]] = []

    cases.append(
        run_case(
            "QC-SYNC-NEG-001",
            "post-baseline source-only addition",
            "case-001-source-only",
            "artifacts/scripts/orphan_src.py",
            {"source_template_pairs": []},
            {"waivers": []},
            today_iso,
            "fail",
            "post_baseline_new_pair_missing_template",
            "Pass 2 discovers a NEW source under artifacts/scripts/ with no template mirror under template/artifacts/scripts/. Expected blocking failure.",
        )
    )

    cases.append(
        run_case(
            "QC-SYNC-NEG-002",
            "post-baseline template-only addition",
            "case-002-template-only",
            "artifacts/scripts/orphan_tpl.py",
            {"source_template_pairs": []},
            {"waivers": []},
            today_iso,
            "fail",
            "post_baseline_new_pair_missing_source",
            "Pass 2 discovers a NEW template under template/artifacts/scripts/ with no source mirror under artifacts/scripts/. Expected blocking failure.",
        )
    )

    cases.append(
        run_case(
            "QC-SYNC-NEG-003",
            "post-baseline source/template drift",
            "case-003-drift",
            "artifacts/scripts/drift.py",
            {"source_template_pairs": []},
            {"waivers": []},
            today_iso,
            "fail",
            "post_baseline_new_pair_drift",
            "Pass 2 discovers a NEW pair with differing SHA-256 between source and template. Expected blocking drift failure.",
        )
    )

    cases.append(
        run_case(
            "QC-SYNC-NEG-004",
            "valid unexpired waiver covers post-baseline drift",
            "case-004-valid-waiver",
            "artifacts/scripts/waivered.py",
            {"source_template_pairs": []},
            {
                "waivers": [
                    {
                        "rule_id": "QC-SYNC-001",
                        "scope": ["artifacts/scripts/waivered.py"],
                        "reason_code": "controlled_negative_test_valid_waiver",
                        "owner": "arcobaleno",
                        "evidence_ref": "artifacts/verify/TASK-1029.verify.md",
                        "expires_at": "2099-12-31",
                    }
                ]
            },
            today_iso,
            "skipped_with_reason_code",
            "post_baseline_new_pair_waivered_until:2099-12-31",
            "Six-field waiver with future expires_at. Expected skipped_with_reason_code.",
        )
    )

    cases.append(
        run_case(
            "QC-SYNC-NEG-005",
            "expired waiver does not cover post-baseline drift",
            "case-005-expired-waiver",
            "artifacts/scripts/expired_waiver.py",
            {"source_template_pairs": []},
            {
                "waivers": [
                    {
                        "rule_id": "QC-SYNC-001",
                        "scope": ["artifacts/scripts/expired_waiver.py"],
                        "reason_code": "controlled_negative_test_expired_waiver",
                        "owner": "arcobaleno",
                        "evidence_ref": "artifacts/verify/TASK-1029.verify.md",
                        "expires_at": "2020-01-01",
                    }
                ]
            },
            today_iso,
            "fail",
            "post_baseline_new_pair_waiver_invalid:expired:2020-01-01",
            "Six-field waiver with past expires_at. Expected blocking failure with expired reason.",
        )
    )

    case_006_dir = FIXTURES / "case-006-baseline-existing-drift"
    case_006_src = case_006_dir / "artifacts" / "scripts" / "legacy_drift.py"
    case_006_tpl = case_006_dir / "template" / "artifacts" / "scripts" / "legacy_drift.py"
    case_006_src_sha = sha256_file(case_006_src)
    case_006_tpl_sha = sha256_file(case_006_tpl)
    case_006_baseline = {
        "source_template_pairs": [
            {
                "baseline_id": "QB-FIXTURE-006",
                "source_path": "artifacts/scripts/legacy_drift.py",
                "template_path": "template/artifacts/scripts/legacy_drift.py",
                "status": "drift",
                "sha256_source": case_006_src_sha,
                "sha256_template": case_006_tpl_sha,
            }
        ]
    }
    cases.append(
        run_case(
            "QC-SYNC-NEG-006",
            "baseline-existing unchanged drift remains non-failing",
            "case-006-baseline-existing-drift",
            "artifacts/scripts/legacy_drift.py",
            case_006_baseline,
            {"waivers": []},
            today_iso,
            "pass",
            "baseline_existing",
            "Synthetic baseline pair with status=drift; current SHA-256 of fixture files exactly matches the baseline-recorded SHAs. Expected pass with reason_code baseline_existing.",
        )
    )

    overall = "pass" if all(c["pass"] for c in cases) else "fail"

    result: Dict[str, Any] = {
        "schema_version": "qc-sync-negative-test-result/v1",
        "task_id": "TASK-1029",
        "generated_at": today_iso,
        "gate_id": "QC-SYNC-001",
        "runner_ref": "artifacts/scripts/run_quality_gates.py",
        "runner_function_under_test": "run_qc_sync_001",
        "runner_modified_by_task_1029": False,
        "fixture_root": "artifacts/verify/TASK-1029/fixtures/",
        "isolation_strategy": (
            "Driver imports run_quality_gates as a Python module without modification. "
            "It invokes run_qc_sync_001(fixture_repo_root, synthetic_baseline, synthetic_policy, today_iso) "
            "directly with fixture repo roots under artifacts/verify/TASK-1029/fixtures/. "
            "Real production source/template pairs under artifacts/scripts/ <-> template/artifacts/scripts/ are NOT touched. "
            "sys.dont_write_bytecode = True is set before import, and PYTHONDONTWRITEBYTECODE=1 is set in the parent env, "
            "so no __pycache__ is created during this test run."
        ),
        "overall_status": overall,
        "cases": cases,
        "limitations": [
            "Driver invokes run_qc_sync_001 directly with synthetic baseline/policy. QC-SCHEMA-001, QC-IMPORT-001, QC-GOLDEN-001, QC-RUFF-001 are NOT exercised here (out of TASK-1029 scope).",
            "Six cases match TASK-1028 v3.5.1 plan section 5.2; PCACC negative cases belong to TASK-1030.",
            "Real production source/template pairs and the v3.5.0 quality-baseline.v3.5.json are NOT mutated.",
            "Today timestamp uses real Asia/Taipei time; case-004 uses expires_at=2099-12-31 (future) and case-005 uses expires_at=2020-01-01 (past) so cases stay stable across re-runs.",
            "Synthetic policy.waivers carries the controlled waiver per case; v3.5.0 policy that forbids a standalone waiver registry is preserved.",
            "Real repository baseline drift (QB-DRIFT-0001..QB-DRIFT-0003) is NOT remediated.",
        ],
    }

    out_path = TASK_DIR / "qc-sync-negative-test-result.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({
        "output_written": repo_relpath(out_path),
        "overall_status": overall,
        "cases_total": len(cases),
        "cases_passed": sum(1 for c in cases if c["pass"]),
    }))
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
