"""Static inspection helper for TASK-1039 waiver policy registry prototype.

Standard library only. Read-only. No writes outside TASK-1039 evidence.
Runs static checks against:
  - artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json
  - artifacts/governance/waiver-policy-registry-prototype-design.v3.5.7.md
  - artifacts/verify/TASK-1039/waiver-policy-prototype-inspection.json

Invocation:
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python -B \
      artifacts/verify/TASK-1039/inspect_waiver_policy_prototype.py

Exit code:
  0 -> all static checks pass
  1 -> at least one check failed (printed to stdout)
"""

import sys

sys.dont_write_bytecode = True

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE_JSON = (
    REPO_ROOT
    / "artifacts"
    / "governance"
    / "prototypes"
    / "waiver-policy-registry.prototype.v3.5.7.json"
)
DESIGN_NOTE_MD = (
    REPO_ROOT
    / "artifacts"
    / "governance"
    / "waiver-policy-registry-prototype-design.v3.5.7.md"
)
INSPECTION_JSON = (
    REPO_ROOT
    / "artifacts"
    / "verify"
    / "TASK-1039"
    / "waiver-policy-prototype-inspection.json"
)

REQUIRED_TOP_LEVEL_FIELDS = [
    "schema_version",
    "plan_version",
    "created_by_task",
    "generated_at",
    "prototype_status",
    "runtime_consumption_authorized",
    "source_policy_refs",
    "waiver_surface",
    "existing_waiver_semantics_inventory",
    "waiver_schema",
    "waiver_lifecycle_states",
    "expiration_policy",
    "reason_code_policy",
    "owner_policy",
    "evidence_ref_policy",
    "scope_policy",
    "validation_semantics",
    "interaction_notes",
    "future_runtime_extraction_acceptance_criteria",
    "non_authorization",
    "limitations",
]
REQUIRED_WAIVER_SCHEMA_FIELDS = [
    "waiver_id",
    "rule_id",
    "scope",
    "reason_code",
    "owner",
    "evidence_ref",
    "expires_at",
    "created_by_task",
    "created_at",
    "status",
]
REQUIRED_LIFECYCLE_STATES = [
    "active",
    "expired",
    "revoked",
    "superseded",
    "invalid",
    "advisory_only",
]
REQUIRED_NON_AUTH_KEYS = [
    "runtime_consumption_authorized",
    "production_runner_modification_authorized",
    "production_validator_modification_authorized",
    "production_policy_modification_authorized",
    "new_test_implementation_authorized",
    "validator_split_authorized",
    "task_1040_plus_authorized",
]
REQUIRED_DESIGN_SECTIONS = [
    "## 1. Purpose",
    "## 2. Source of truth and limitations",
    "## 3. Existing waiver semantics inventory",
    "## 4. Proposed waiver registry shape",
    "## 5. Required waiver fields",
    "## 6. Waiver lifecycle states",
    "## 7. Expiration and invalidation policy",
    "## 8. Reason code policy",
    "## 9. Owner and accountability policy",
    "## 10. Evidence Ref alignment",
    "## 11. Scope matching policy",
    "## 12. Validation semantics",
    "## 13. Interaction with existing governance surfaces",
    "## 14. Future runtime extraction acceptance criteria",
    "## 15. Risks and limitations",
    "## 16. Explicit non-authorization",
]
REQUIRED_INVENTORY_SOURCES = [
    "artifacts/governance/quality-gate-policy.v3.5.json",
    "artifacts/governance/artifact-obligation-matrix.v3.5.json",
    "artifacts/governance/evidence-ref-policy.v3.5.3.json",
    "artifacts/governance/golden-cli-coverage-matrix.v3.5.4.json",
]


def check(label, ok, detail=""):
    marker = "OK" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"[{marker}] {label}{suffix}")
    return ok


def main():
    failures = 0

    failures += not check("prototype JSON present", PROTOTYPE_JSON.is_file(), str(PROTOTYPE_JSON))
    failures += not check("design note present", DESIGN_NOTE_MD.is_file(), str(DESIGN_NOTE_MD))
    failures += not check("inspection JSON present", INSPECTION_JSON.is_file(), str(INSPECTION_JSON))

    if failures:
        print("aborting further checks; required files missing")
        return 1

    proto = json.loads(PROTOTYPE_JSON.read_text(encoding="utf-8"))
    inspection = json.loads(INSPECTION_JSON.read_text(encoding="utf-8"))
    design = DESIGN_NOTE_MD.read_text(encoding="utf-8")

    failures += not check(
        "prototype schema_version",
        proto.get("schema_version") == "waiver-policy-registry-prototype/v1",
        proto.get("schema_version"),
    )
    failures += not check(
        "prototype plan_version",
        proto.get("plan_version") == "v3.5.7",
        proto.get("plan_version"),
    )
    failures += not check(
        "prototype created_by_task",
        proto.get("created_by_task") == "TASK-1039",
        proto.get("created_by_task"),
    )
    failures += not check(
        "prototype prototype_status",
        proto.get("prototype_status") == "design_only",
        proto.get("prototype_status"),
    )
    failures += not check(
        "prototype runtime_consumption_authorized=false",
        proto.get("runtime_consumption_authorized") is False,
        repr(proto.get("runtime_consumption_authorized")),
    )

    missing_top_fields = [f for f in REQUIRED_TOP_LEVEL_FIELDS if f not in proto]
    failures += not check(
        "prototype top-level fields complete",
        not missing_top_fields,
        repr(missing_top_fields),
    )

    schema_required = proto.get("waiver_schema", {}).get("required_fields", [])
    failures += not check(
        "waiver_schema required_fields cover ten required",
        all(f in schema_required for f in REQUIRED_WAIVER_SCHEMA_FIELDS),
        repr([f for f in REQUIRED_WAIVER_SCHEMA_FIELDS if f not in schema_required]),
    )

    state_ids = [s.get("state_id") for s in proto.get("waiver_lifecycle_states", [])]
    failures += not check(
        "waiver_lifecycle_states cover six required",
        all(s in state_ids for s in REQUIRED_LIFECYCLE_STATES),
        repr([s for s in REQUIRED_LIFECYCLE_STATES if s not in state_ids]),
    )

    expiration = proto.get("expiration_policy", {})
    failures += not check(
        "expiration_policy past_expires_at_is_blocking",
        expiration.get("past_expires_at_is_blocking") is True,
    )
    failures += not check(
        "expiration_policy missing_expires_at_is_blocking",
        expiration.get("missing_expires_at_is_blocking") is True,
    )
    failures += not check(
        "expiration_policy malformed_expires_at_is_blocking",
        expiration.get("malformed_expires_at_is_blocking") is True,
    )

    rcp = proto.get("reason_code_policy", {})
    allowed = [c.get("reason_code") for c in rcp.get("allowed_categories", [])]
    rejected = [p.get("pattern") for p in rcp.get("rejected_patterns", [])]
    failures += not check(
        "reason_code_policy has at least four allowed_categories",
        len(allowed) >= 4,
        f"len={len(allowed)}",
    )
    failures += not check(
        "reason_code_policy has at least four rejected_patterns",
        len(rejected) >= 4,
        f"len={len(rejected)}",
    )

    owner_policy = proto.get("owner_policy", {})
    failures += not check(
        "owner_policy rejects AI agent labels",
        bool(owner_policy.get("owner_ai_agent_labels_rejected")),
    )

    evp = proto.get("evidence_ref_policy", {})
    failures += not check(
        "evidence_ref_policy must resolve under v3.5.3",
        evp.get("evidence_ref_must_resolve_under_evidence_ref_policy_v3_5_3") is True,
    )

    scope = proto.get("scope_policy", {})
    shapes = [s.get("shape_id") for s in scope.get("allowed_scope_shapes", [])]
    failures += not check(
        "scope_policy has at least five shapes",
        len(shapes) >= 5,
        f"len={len(shapes)}",
    )

    val = proto.get("validation_semantics", {})
    failures += not check(
        "validation fail_closed_on_malformed_registry",
        val.get("fail_closed_on_malformed_registry") is True,
    )
    failures += not check(
        "validation expired_waiver_cannot_suppress_blocking_finding",
        val.get("expired_waiver_cannot_suppress_blocking_finding") is True,
    )

    fe = proto.get("future_runtime_extraction_acceptance_criteria", [])
    failures += not check(
        "future_runtime_extraction_acceptance_criteria has at least eleven entries",
        len(fe) >= 11,
        f"len={len(fe)}",
    )

    non_auth = proto.get("non_authorization", {})
    missing_keys = [k for k in REQUIRED_NON_AUTH_KEYS if k not in non_auth]
    failures += not check(
        "non_authorization includes required seven keys",
        not missing_keys,
        repr(missing_keys),
    )
    failures += not check(
        "non_authorization values are all literal false",
        all(v is False for v in non_auth.values()),
        repr({k: v for k, v in non_auth.items() if v is not False}),
    )

    inventory = proto.get("existing_waiver_semantics_inventory", [])
    inventory_sources = [e.get("source_artifact") for e in inventory]
    failures += not check(
        "existing_waiver_semantics_inventory covers four sources",
        all(s in inventory_sources for s in REQUIRED_INVENTORY_SOURCES),
        repr([s for s in REQUIRED_INVENTORY_SOURCES if s not in inventory_sources]),
    )

    missing_sections = [m for m in REQUIRED_DESIGN_SECTIONS if m not in design]
    failures += not check(
        "design note carries sixteen section markers",
        not missing_sections,
        repr(missing_sections),
    )

    failures += not check(
        "inspection schema_version",
        inspection.get("schema_version") == "waiver-policy-prototype-inspection/v1",
        inspection.get("schema_version"),
    )
    failures += not check(
        "inspection task_id",
        inspection.get("task_id") == "TASK-1039",
        inspection.get("task_id"),
    )
    failures += not check(
        "inspection overall_status",
        inspection.get("overall_status") == "pass",
        inspection.get("overall_status"),
    )

    print(
        "summary: "
        f"{'pass' if failures == 0 else 'fail'} "
        f"failures={failures}"
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
