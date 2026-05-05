"""Static inspection helper for TASK-1038 v3.5.x closure snapshot.

Standard library only. Read-only. No writes outside TASK-1038 evidence.
Runs static checks against:
  - artifacts/governance/v3.5.x-governance-closure-snapshot.md
  - artifacts/governance/v3.5.x-governance-closure-index.json
  - artifacts/verify/TASK-1038/closure-snapshot-inspection.json

Invocation:
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python -B \
      artifacts/verify/TASK-1038/inspect_closure_snapshot.py

Exit code:
  0 -> all static checks pass
  1 -> at least one check failed (printed to stdout)
"""

import sys

sys.dont_write_bytecode = True

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_MD = REPO_ROOT / "artifacts" / "governance" / "v3.5.x-governance-closure-snapshot.md"
INDEX_JSON = REPO_ROOT / "artifacts" / "governance" / "v3.5.x-governance-closure-index.json"
INSPECTION_JSON = REPO_ROOT / "artifacts" / "verify" / "TASK-1038" / "closure-snapshot-inspection.json"

REQUIRED_VERSIONS = ["v3.5.0", "v3.5.1", "v3.5.2", "v3.5.3", "v3.5.4", "v3.5.5"]
REQUIRED_GROUP_IDS = [
    "TASK-1023..TASK-1027",
    "TASK-1028..TASK-1032",
    "TASK-1033..TASK-1034",
    "TASK-1035",
    "TASK-1036",
    "TASK-1037",
    "TASK-1037-repair",
]
REQUIRED_CAPABILITY_IDS = [
    "quality_baseline",
    "quality_gates",
    "qc_sync_post_baseline_coverage",
    "minimal_pcacc",
    "artifact_obligation_matrix",
    "negative_case_proving",
    "validator_characterization",
    "policy_registry_extraction_design",
    "evidence_ref_registry_prototype",
    "evidence_ref_runtime_extraction_plan",
    "evidence_ref_controlled_runtime_extraction",
    "golden_cli_coverage_plan",
    "golden_cli_coverage_implementation",
    "golden_cli_status_semantics_repair",
]
REQUIRED_PROTECTED_PATHS = [
    "artifacts/scripts/run_precommit_check.py",
    "template/artifacts/scripts/run_precommit_check.py",
    "artifacts/scripts/run_quality_gates.py",
    "template/artifacts/scripts/run_quality_gates.py",
    "artifacts/scripts/guard_status_validator.py",
    "artifacts/scripts/guard_contract_validator.py",
    "artifacts/scripts/workflow_constants.py",
    "artifacts/scripts/run_red_team_suite.py",
    "artifacts/scripts/test_guard_units.py",
]
REQUIRED_NON_AUTH_KEYS = [
    "task_1039_plus_authorized",
    "new_runtime_registry_extraction_authorized",
    "pcacc_active_check_expansion_authorized",
    "pcacc_005_authorized",
    "ac_to_verify_authorized",
    "validator_split_authorized",
    "production_validator_modification_authorized",
    "production_runner_modification_authorized",
    "new_golden_cli_expansion_authorized",
    "reasoning_or_saver_surfaces_authorized",
]


def check(label, ok, detail=""):
    marker = "OK" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"[{marker}] {label}{suffix}")
    return ok


def main():
    failures = 0

    failures += not check("snapshot markdown present", SNAPSHOT_MD.is_file(), str(SNAPSHOT_MD))
    failures += not check("closure index JSON present", INDEX_JSON.is_file(), str(INDEX_JSON))
    failures += not check("inspection JSON present", INSPECTION_JSON.is_file(), str(INSPECTION_JSON))

    if failures:
        print("aborting further checks; required files missing")
        return 1

    index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    inspection = json.loads(INSPECTION_JSON.read_text(encoding="utf-8"))

    failures += not check(
        "index schema_version",
        index.get("schema_version") == "v3.5.x-governance-closure-index/v1",
        index.get("schema_version"),
    )
    failures += not check(
        "index created_by_task",
        index.get("created_by_task") == "TASK-1038",
        index.get("created_by_task"),
    )
    failures += not check(
        "index plan_version_range",
        index.get("plan_version_range") == "v3.5.0..v3.5.5",
        index.get("plan_version_range"),
    )

    closure_versions = [e["version"] for e in index.get("closure_status", [])]
    failures += not check(
        "closure_status covers v3.5.0..v3.5.5",
        closure_versions == REQUIRED_VERSIONS,
        repr(closure_versions),
    )

    v555 = next(
        (e for e in index.get("closure_status", []) if e.get("version") == "v3.5.5"), None
    )
    failures += not check(
        "v3.5.5 status=closed_verified_after_repair",
        bool(v555) and v555.get("status") == "closed_verified_after_repair",
        v555.get("status") if v555 else "missing",
    )
    others = [e for e in index.get("closure_status", []) if e.get("version") != "v3.5.5"]
    failures += not check(
        "v3.5.0..v3.5.4 status=closed_verified",
        all(e.get("status") == "closed_verified" for e in others),
        repr([(e.get("version"), e.get("status")) for e in others]),
    )

    group_ids = [g.get("group_id") for g in index.get("task_groups", [])]
    failures += not check(
        "task_groups cover required set",
        group_ids == REQUIRED_GROUP_IDS,
        repr(group_ids),
    )

    cap_ids = [c.get("capability_id") for c in index.get("capabilities", [])]
    failures += not check(
        "capabilities cover required fourteen ids",
        cap_ids == REQUIRED_CAPABILITY_IDS,
        repr(cap_ids),
    )

    protected_paths = [p.get("path") for p in index.get("protected_surfaces", [])]
    failures += not check(
        "protected_surfaces cover required nine paths",
        protected_paths == REQUIRED_PROTECTED_PATHS,
        repr(protected_paths),
    )
    failures += not check(
        "protected_surfaces all require explicit task",
        all(
            p.get("modification_requires_explicit_task") is True
            for p in index.get("protected_surfaces", [])
        ),
    )

    non_auth = index.get("non_authorization", {})
    missing_keys = [k for k in REQUIRED_NON_AUTH_KEYS if k not in non_auth]
    failures += not check(
        "non_authorization includes required ten keys",
        not missing_keys,
        repr(missing_keys),
    )
    failures += not check(
        "non_authorization values are all literal false",
        all(v is False for v in non_auth.values()),
        repr({k: v for k, v in non_auth.items() if v is not False}),
    )

    candidates = index.get("next_candidate_lifecycles", [])
    failures += not check(
        "next_candidate_lifecycles has at least five entries",
        len(candidates) >= 5,
        f"len={len(candidates)}",
    )
    failures += not check(
        "every candidate has authorized=false",
        all(c.get("authorized") is False for c in candidates),
        repr([c.get("candidate_id") for c in candidates if c.get("authorized") is not False]),
    )

    failures += not check(
        "inspection schema_version",
        inspection.get("schema_version") == "closure-snapshot-inspection/v1",
        inspection.get("schema_version"),
    )
    failures += not check(
        "inspection task_id",
        inspection.get("task_id") == "TASK-1038",
        inspection.get("task_id"),
    )
    failures += not check(
        "inspection overall_status",
        inspection.get("overall_status") == "pass",
        inspection.get("overall_status"),
    )

    snapshot_text = SNAPSHOT_MD.read_text(encoding="utf-8")
    required_markers = [
        "v3.5.0  closed / verified",
        "v3.5.5  closed / verified after TASK-1037 repair",
        "## 7. TASK-1037 repair summary",
        "## 8. Protected production surfaces",
        "## 9. Explicit non-authorization boundaries",
        "## 10. Known unrelated local noise",
        "## 11. Next candidate lifecycle tasks",
    ]
    missing_markers = [m for m in required_markers if m not in snapshot_text]
    failures += not check(
        "snapshot markdown carries required section markers",
        not missing_markers,
        repr(missing_markers),
    )

    print(
        "summary: "
        f"{'pass' if failures == 0 else 'fail'} "
        f"failures={failures}"
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
