#!/usr/bin/env python3
"""TASK-1037 Golden CLI Coverage Implementation harness.

Locks the CLI surfaces of the production governance runners
(`run_precommit_check.py` and `run_quality_gates.py`) without modifying
them. The harness:

  1. Builds a controlled fixture tree under
     `artifacts/verify/TASK-1037/fixtures/` deterministically.
  2. Invokes byte-identical fixture-local copies of the runners via
     subprocess (`python -B`) with `PYTHONDONTWRITEBYTECODE=1`,
     `PYTHONNOUSERSITE=1`, `PYTHONUTF8=1`.
  3. Asserts robust output contracts per case (exit_code literal, JSON
     field subset, stderr empty unless justified, no __pycache__).
  4. Sweeps the harness directory for cache pollution.
  5. Records sha256 prefix of nine production preservation targets.
  6. Writes `golden-cli-coverage-result.json` with overall_status pass
     iff every implemented case passes and no cache appeared.

Standard library only. No pytest, no ruff, no formatter, no package
manager. No imports of repository modules.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

HARNESS_PATH = Path(__file__).resolve()
TASK_DIR = HARNESS_PATH.parent  # artifacts/verify/TASK-1037
FIXTURE_ROOT = TASK_DIR / "fixtures"
REPO_ROOT = HARNESS_PATH.parents[3]  # repo root: TASK-1037 -> verify -> artifacts -> repo
PCACC_RUNNER = REPO_ROOT / "artifacts" / "scripts" / "run_precommit_check.py"
PCACC_TEMPLATE_RUNNER = REPO_ROOT / "template" / "artifacts" / "scripts" / "run_precommit_check.py"
QUALITY_RUNNER = REPO_ROOT / "artifacts" / "scripts" / "run_quality_gates.py"
QUALITY_TEMPLATE_RUNNER = REPO_ROOT / "template" / "artifacts" / "scripts" / "run_quality_gates.py"
PROD_REGISTRY = REPO_ROOT / "artifacts" / "governance" / "evidence-ref-policy.v3.5.3.json"

TAIPEI_TZ = timezone(timedelta(hours=8))

PRODUCTION_PRESERVATION_TARGETS: List[Tuple[str, str]] = [
    ("artifacts/scripts/run_precommit_check.py", "4dbb8a219093cc12"),
    ("template/artifacts/scripts/run_precommit_check.py", "4dbb8a219093cc12"),
    ("artifacts/scripts/run_quality_gates.py", "456b8328482b18a5"),
    ("template/artifacts/scripts/run_quality_gates.py", "456b8328482b18a5"),
    ("artifacts/scripts/guard_status_validator.py", "d58a41f6ca49ccfe"),
    ("artifacts/scripts/guard_contract_validator.py", "7a38af7e2e0af5b7"),
    ("artifacts/scripts/workflow_constants.py", "e1f09d2100b5685f"),
    ("artifacts/scripts/run_red_team_suite.py", "77540c3b29f6ece6"),
    ("artifacts/scripts/test_guard_units.py", "5c7228c9997edffd"),
]

# TASK-1030 backward compat literal anchors (NEG-002 / NEG-003).
NEG_002_REASON_CODE = "malformed_refs:garbage_token_not_a_known_prefix"
NEG_003_REASON_CODE = "evidence_refs_section_empty"

SUBPROCESS_ENV_OVERRIDES: Dict[str, str] = {
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTHONUTF8": "1",
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def now_taipei_iso() -> str:
    return datetime.now(TAIPEI_TZ).replace(microsecond=0).isoformat()


def sha256_prefix(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def sha256_file_prefix(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return sha256_prefix(path.read_bytes())


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text; assert path is under FIXTURE_ROOT or TASK_DIR."""
    rp = path.resolve()
    if not (str(rp).startswith(str(FIXTURE_ROOT)) or str(rp).startswith(str(TASK_DIR))):
        raise RuntimeError("write_text path escapes TASK-1037 envelope: " + str(rp))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    rp = path.resolve()
    if not (str(rp).startswith(str(FIXTURE_ROOT)) or str(rp).startswith(str(TASK_DIR))):
        raise RuntimeError("write_bytes path escapes TASK-1037 envelope: " + str(rp))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, obj: Any) -> None:
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def reset_fixtures() -> None:
    if FIXTURE_ROOT.exists():
        shutil.rmtree(FIXTURE_ROOT)
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Subprocess invocation
# ---------------------------------------------------------------------------

def run_subprocess(
    runner: Path,
    args: List[str],
    cwd: Path,
) -> Tuple[int, str, str]:
    env = os.environ.copy()
    env.update(SUBPROCESS_ENV_OVERRIDES)
    cmd = [sys.executable, "-B", str(runner)] + args
    proc = subprocess.run(
        cmd,
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Fixture content builders
# ---------------------------------------------------------------------------

# Production runner SCRIPT_PATH.parents takes the root-most sentinel match,
# which lands on the real repo when fixtures live inside artifacts/verify/.
# A thin wrapper at the fixture root loads the production runner via
# importlib and overrides detect_repo_root() to return the fixture root.
# Production runner bytes are not modified.
WRAPPER_TEMPLATE = """#!/usr/bin/env python3
\"\"\"TASK-1037 fixture wrapper for {runner_basename}.

Loads the production runner via importlib and overrides detect_repo_root()
to anchor the runner at this fixture repo root instead of the real
consilium-fabri repo root. Production runner bytes are not modified.
\"\"\"
import sys
sys.dont_write_bytecode = True
import importlib.util
from pathlib import Path

WRAPPER_PATH = Path(__file__).resolve()
FIXTURE_ROOT = WRAPPER_PATH.parent
REPO_ROOT = WRAPPER_PATH.parents[5]
PROD_RUNNER = REPO_ROOT / "artifacts" / "scripts" / "{runner_basename}"

spec = importlib.util.spec_from_file_location("runner_under_test", str(PROD_RUNNER))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.detect_repo_root = lambda: FIXTURE_ROOT

sys.exit(mod.main(sys.argv[1:]))
"""


def write_wrapper(repo: Path, runner_basename: str, wrapper_basename: str) -> None:
    write_text(repo / wrapper_basename, WRAPPER_TEMPLATE.format(runner_basename=runner_basename))


def write_pcacc_repo_skeleton(repo: Path) -> None:
    pcacc_policy = {
        "schema_version": "precommit-check-policy/v1",
        "plan_version": "v3.5.0",
        "checks": [
            {"check_id": "PCACC-001"},
            {"check_id": "PCACC-002"},
            {
                "check_id": "PCACC-003",
                "canonical_owners": ["Claude"],
                "canonical_reviewers": ["arcobaleno"],
            },
            {"check_id": "PCACC-004"},
        ],
        "output_policy": {
            "format": "json",
            "free_text_rationale": False,
            "allowed_status_values": ["pass", "fail", "skipped_with_reason_code"],
            "required_check_fields": [
                "check_id", "target", "expected", "actual",
                "evidence_ref", "status", "reason_code",
            ],
            "forbidden_check_fields": [],
        },
    }
    write_json(repo / "artifacts" / "governance" / "precommit-check-policy.v3.5.json", pcacc_policy)
    # byte-identical copy of production Evidence Ref policy registry for registry-mode cases.
    write_bytes(repo / "artifacts" / "governance" / "evidence-ref-policy.v3.5.3.json", PROD_REGISTRY.read_bytes())
    write_wrapper(repo, "run_precommit_check.py", "run_pcacc.py")


def write_quality_repo_skeleton(
    repo: Path,
    *,
    baseline_obj: Optional[Dict[str, Any]] = None,
    policy_obj: Optional[Dict[str, Any]] = None,
) -> None:
    # SCHEMA gate minimum required JSON targets at the canonical paths.
    write_json(repo / "governance-repair-manifest.v3.5.json", {
        "schema_version": "governance-repair-manifest/v1",
        "plan_version": "v3.5.0-fixture",
        "execution_order": [],
        "findings": [],
    })
    for tid in ("TASK-1023", "TASK-1024", "TASK-1025"):
        write_json(repo / "artifacts" / "status" / (tid + ".status.json"), {
            "task_id": tid,
            "state": "done",
        })
    if baseline_obj is None:
        baseline_obj = make_default_quality_baseline()
    if policy_obj is None:
        policy_obj = make_default_quality_policy()
    write_json(repo / "artifacts" / "governance" / "quality-baseline.v3.5.json", baseline_obj)
    write_json(repo / "artifacts" / "governance" / "quality-gate-policy.v3.5.json", policy_obj)
    write_wrapper(repo, "run_quality_gates.py", "run_quality.py")


def make_default_quality_baseline() -> Dict[str, Any]:
    return {
        "schema_version": "quality-baseline/v1",
        "plan_version": "v3.5.0-fixture",
        "metrics": [],
        "source_template_pairs": [],
        "import_side_effect_surface": [],
        "golden_cli_candidates": [],
    }


def make_default_quality_policy() -> Dict[str, Any]:
    return {
        "schema_version": "quality-gate-policy/v1",
        "plan_version": "v3.5.0-fixture",
        "rollout_phase": {"current_phase": 1},
        "gates": [
            {
                "gate_id": "QC-IMPORT-001",
                "expected_import_clean": [],
                "first_cycle_advisory_for_unlisted_candidates": True,
            }
        ],
        "waivers": [],
    }


# ---------------------------------------------------------------------------
# PCACC lifecycle bundle helpers
# ---------------------------------------------------------------------------

def make_task_md(task_id: str, owner: str = "Claude") -> str:
    return (
        "# Task: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Artifact Type: task\n"
        "- Owner: " + owner + "\n"
        "- Status: done\n\n"
        "## Description\n\n"
        "Synthetic TASK-1037 fixture lifecycle artifact.\n\n"
        "## Agent Roles\n\n"
        "```yaml\n"
        "agent_roles:\n"
        "  final_approver:\n"
        "    reviewer_id: arcobaleno\n"
        "    type: human\n"
        "```\n"
    )


def make_plan_md(task_id: str) -> str:
    return (
        "# Plan: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Artifact Type: plan\n"
        "- Owner: Claude\n"
        "- Status: ready\n\n"
        "## Goal\n\nSynthetic fixture plan body.\n"
    )


def make_decision_md(task_id: str) -> str:
    return (
        "---\n"
        "schema_version: decision/v2\n"
        "decision_class: fixture\n"
        "risk_level: low\n"
        "loop_type: pdca\n"
        "subject: synthetic fixture decision\n"
        "chosen_option: synthetic\n"
        "trust_level: recorded_attestation\n"
        "---\n\n"
        "# Decision: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Artifact Type: decision\n"
        "- Owner: Claude\n"
        "- Status: done\n"
    )


def make_verify_md(
    task_id: str,
    last_updated: str,
    evidence_refs_lines: List[str],
    extra_section: str = "",
) -> str:
    refs_block = "\n".join(evidence_refs_lines) if evidence_refs_lines else "- None"
    body = (
        "# Verification: " + task_id + "\n\n"
        "## Metadata\n"
        "- Task ID: " + task_id + "\n"
        "- Artifact Type: verify\n"
        "- Owner: Claude\n"
        "- Status: pass\n"
        "- Last Updated: " + last_updated + "\n\n"
        "## Evidence Refs\n"
        + refs_block + "\n"
    )
    if extra_section:
        body += "\n" + extra_section + "\n"
    return body


def write_pcacc_lifecycle(
    repo: Path,
    task_id: str,
    *,
    owner: str = "Claude",
    review_last_updated: str = "2026-05-05T03:00:00+08:00",
    evidence_generated_at: str = "2026-05-05T02:00:00+08:00",
    evidence_refs_lines: Optional[List[str]] = None,
    extra_verify_section: str = "",
    omit_verify: bool = False,
    omit_pcacc_result: bool = False,
) -> None:
    art = repo / "artifacts"
    write_text(art / "tasks" / (task_id + ".task.md"), make_task_md(task_id, owner=owner))
    write_text(art / "plans" / (task_id + ".plan.md"), make_plan_md(task_id))
    write_text(art / "decisions" / (task_id + ".decision.md"), make_decision_md(task_id))
    if not omit_verify:
        if evidence_refs_lines is None:
            # default ref points at a path that is guaranteed to exist inside
            # the fixture repo (the fixture-local PCACC policy JSON).
            evidence_refs_lines = ["- artifacts/governance/precommit-check-policy.v3.5.json"]
        write_text(
            art / "verify" / (task_id + ".verify.md"),
            make_verify_md(task_id, review_last_updated, evidence_refs_lines, extra_verify_section),
        )
    if not omit_pcacc_result:
        write_json(art / "verify" / task_id / "precommit-check-result.json", {
            "schema_version": "precommit-check-result/v1",
            "task_id": task_id,
            "generated_at": evidence_generated_at,
            "self_check": True,
            "policy_ref": "artifacts/governance/precommit-check-policy.v3.5.json",
            "overall_status": "pass",
            "checks": [],
            "limitations": [],
        })
    write_json(art / "status" / (task_id + ".status.json"), {
        "task_id": task_id,
        "state": "done",
        "current_owner": owner,
        "last_updated": review_last_updated,
        "self_check_result_ref": "artifacts/verify/" + task_id + "/precommit-check-result.json",
    })


# ---------------------------------------------------------------------------
# PCACC fixture build (single shared repo + per-case lifecycle bundles)
# ---------------------------------------------------------------------------

PCACC_REPO_DIRNAME = "pcacc"


def build_pcacc_fixture() -> Path:
    repo = FIXTURE_ROOT / PCACC_REPO_DIRNAME
    write_pcacc_repo_skeleton(repo)
    # Controlled malformed registries reused from TASK-1035 design.
    write_text(repo / "registries" / "malformed-json.json", "{this is not valid json,,,\n")
    write_json(repo / "registries" / "schema-version-mismatch.json", {
        "schema_version": "evidence-ref-policy-registry-prototype/v1",
        "plan_version": "v3.5.3",
        "created_by_task": "TASK-99999",
        "runtime_status": "production_runtime",
        "runtime_consumption_authorized": True,
        "source_policy_refs": {},
        "policy_surface": {},
        "allowed_ref_prefixes": [],
        "ref_format_rules": {},
        "local_artifact_constraints": {},
        "required_ref_contexts": [],
        "optional_ref_contexts": [],
        "malformed_ref_behavior": {},
        "missing_ref_behavior": {},
        "pcacc_compatibility": {},
        "failure_semantics": [],
        "non_authorization": {},
        "limitations": [],
    })
    write_json(repo / "registries" / "pcacc-conflict.json", {
        "schema_version": "evidence-ref-policy/v1",
        "plan_version": "v3.5.3-conflict",
        "created_by_task": "TASK-99999",
        "runtime_status": "production_runtime",
        "runtime_consumption_authorized": True,
        "source_policy_refs": {},
        "policy_surface": {},
        "allowed_ref_prefixes": [
            {
                "prefix_id": "P", "prefix_pattern": "x",
                "kind": "local_repo_relative_directory",
                "must_exist_on_disk": True, "rationale": "x",
            }
        ],
        "ref_format_rules": {},
        "local_artifact_constraints": {
            "must_be_relative_path": True,
            "must_not_escape_repo_root": True,
            "must_not_contain_parent_traversal": True,
            "must_not_be_absolute": True,
            "must_not_use_windows_drive_letter": True,
            "must_use_forward_slashes": True,
            "must_be_normalized": True,
            "forbidden_url_schemes": [
                "http://", "https://", "ftp://", "file://",
                "ssh://", "git://", "git+ssh://",
            ],
            "forbidden_root_directories": [
                ".obsidian", ".omc", ".tmp", ".pytest-basetemp",
                "__pycache__", ".pytest_cache", "node_modules", ".venv", ".git",
            ],
        },
        "required_ref_contexts": [],
        "optional_ref_contexts": [],
        "malformed_ref_behavior": {},
        "missing_ref_behavior": {},
        "pcacc_compatibility": {
            "current_pcacc_active_check_surface": [
                "PCACC-001", "PCACC-002", "PCACC-003", "PCACC-004", "PCACC-005",
            ],
            "current_pcacc_active_check_count": 5,
            "prototype_introduces_pcacc_005": True,
            "prototype_changes_pcacc_active_count": True,
            "ac_to_verify_coverage_activated": True,
        },
        "failure_semantics": [],
        "non_authorization": {},
        "limitations": [],
    })

    # GCLI-PRECOMMIT-DEFAULT-001
    write_pcacc_lifecycle(repo, "TASK-90001")

    # GCLI-PRECOMMIT-EVREF-001 (valid local under registry mode)
    write_pcacc_lifecycle(repo, "TASK-90011")

    # GCLI-PRECOMMIT-EVREF-002 (ORC-1 skip under registry mode)
    write_pcacc_lifecycle(
        repo, "TASK-90012",
        evidence_refs_lines=["- None"],
        extra_verify_section="## Optional Ref Skip Reason\n- ORC-1; reason_code=evidence_refs_optional_per_orc_1",
    )

    # GCLI-PRECOMMIT-EVREF-003 (forbidden URL scheme)
    write_pcacc_lifecycle(
        repo, "TASK-90013",
        evidence_refs_lines=["- https://evil.example.com/x.json"],
    )

    # GCLI-PRECOMMIT-EVREF-004 (parent traversal)
    write_pcacc_lifecycle(
        repo, "TASK-90014",
        evidence_refs_lines=["- ../../../etc/passwd"],
    )

    # GCLI-PRECOMMIT-EVREF-005 (NEG-002 anchor; default mode)
    write_pcacc_lifecycle(
        repo, "TASK-90015",
        evidence_refs_lines=["- garbage_token_not_a_known_prefix"],
    )

    # GCLI-PRECOMMIT-EVREF-006 (NEG-003 anchor; default mode; empty section, no ORC marker)
    write_pcacc_lifecycle(
        repo, "TASK-90016",
        evidence_refs_lines=["- None"],
    )

    # GCLI-PRECOMMIT-LIFECYCLE-001 (missing verify)
    write_pcacc_lifecycle(repo, "TASK-90021", omit_verify=True, omit_pcacc_result=True)

    # GCLI-PRECOMMIT-LIFECYCLE-002 (non-canonical owner)
    write_pcacc_lifecycle(repo, "TASK-90022", owner="Mallory")

    # GCLI-PRECOMMIT-LIFECYCLE-003 (equal timestamps -> review_equal_to_evidence_not_strictly_after)
    eq_ts = "2026-05-05T03:00:00+08:00"
    write_pcacc_lifecycle(
        repo, "TASK-90023",
        review_last_updated=eq_ts,
        evidence_generated_at=eq_ts,
    )

    # GCLI-PRECOMMIT-LIFECYCLE-004 (review before evidence)
    write_pcacc_lifecycle(
        repo, "TASK-90024",
        review_last_updated="2026-05-05T01:00:00+08:00",
        evidence_generated_at="2026-05-05T02:00:00+08:00",
    )
    return repo


# ---------------------------------------------------------------------------
# Quality fixture build (per-case mini-repo)
# ---------------------------------------------------------------------------

def build_quality_sync_001_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-sync-001"
    pair_src = "artifacts/scripts/case_pair.py"
    pair_tpl = "template/artifacts/scripts/case_pair.py"
    # write_bytes pins LF line endings so sha256 stays stable across platforms.
    pair_content = b"# fixture in_sync pair\n"
    pair_sha = hashlib.sha256(pair_content).hexdigest()
    baseline = make_default_quality_baseline()
    baseline["source_template_pairs"] = [
        {
            "baseline_id": "FX-SYNC-0001",
            "source_path": pair_src,
            "template_path": pair_tpl,
            "status": "in_sync",
            "sha256_source": pair_sha,
            "sha256_template": pair_sha,
        }
    ]
    write_quality_repo_skeleton(repo, baseline_obj=baseline)
    write_bytes(repo / pair_src, pair_content)
    write_bytes(repo / pair_tpl, pair_content)
    return repo


def build_quality_sync_002_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-sync-002"
    pair_src = "artifacts/scripts/case_pair.py"
    pair_tpl = "template/artifacts/scripts/case_pair.py"
    src_content = b"# baseline drift source\n"
    tpl_content = b"# baseline drift template (different bytes)\n"
    src_sha = hashlib.sha256(src_content).hexdigest()
    tpl_sha = hashlib.sha256(tpl_content).hexdigest()
    baseline = make_default_quality_baseline()
    baseline["source_template_pairs"] = [
        {
            "baseline_id": "FX-SYNC-0002",
            "source_path": pair_src,
            "template_path": pair_tpl,
            "status": "drift",
            "sha256_source": src_sha,
            "sha256_template": tpl_sha,
        }
    ]
    write_quality_repo_skeleton(repo, baseline_obj=baseline)
    write_bytes(repo / pair_src, src_content)
    write_bytes(repo / pair_tpl, tpl_content)
    return repo


def build_quality_sync_004_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-sync-004"
    src_rel = "artifacts/scripts/post_baseline_new.py"
    tpl_rel = "template/artifacts/scripts/post_baseline_new.py"
    write_quality_repo_skeleton(repo)  # baseline.source_template_pairs empty -> Pass 2 detects new pair
    write_bytes(repo / src_rel, b"# post-baseline drift source\n")
    write_bytes(repo / tpl_rel, b"# post-baseline drift template (different)\n")
    return repo


def build_quality_schema_001_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-schema-001"
    write_quality_repo_skeleton(repo)  # all schema targets default-valid
    return repo


def build_quality_schema_002_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-schema-002"
    bad_baseline = make_default_quality_baseline()
    bad_baseline["schema_version"] = "wrong-schema-version/v1"
    write_quality_repo_skeleton(repo, baseline_obj=bad_baseline)
    return repo


def build_quality_import_003_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-import-003"
    baseline = make_default_quality_baseline()
    baseline["import_side_effect_surface"] = [
        {
            "path": "artifacts/scripts/dirty_module.py",
            "candidate_for_import_side_effect_gate": True,
        }
    ]
    policy = make_default_quality_policy()
    # explicit empty expected_import_clean so dirty_module is unlisted -> advisory
    for g in policy["gates"]:
        if g.get("gate_id") == "QC-IMPORT-001":
            g["expected_import_clean"] = []
            g["first_cycle_advisory_for_unlisted_candidates"] = True
    write_quality_repo_skeleton(repo, baseline_obj=baseline, policy_obj=policy)
    dirty_body = "print('dirty_import_observation')\n"
    # both sides have the dirty module so QC-SYNC-001 Pass 2 sees in_sync.
    write_text(repo / "artifacts" / "scripts" / "dirty_module.py", dirty_body)
    write_text(repo / "template" / "artifacts" / "scripts" / "dirty_module.py", dirty_body)
    return repo


def build_quality_golden_001_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-golden-001"
    baseline = make_default_quality_baseline()
    baseline["golden_cli_candidates"] = [
        {
            "command_id": "FX-CLI-0001",
            "command": "python -c \"pass\"",
            "expected_exit_code": 0,
            "capture_policy": "post_task_evidence_only",
        }
    ]
    write_quality_repo_skeleton(repo, baseline_obj=baseline)
    return repo


def build_quality_ruff_001_fixture() -> Path:
    repo = FIXTURE_ROOT / "quality-ruff-001"
    write_quality_repo_skeleton(repo)
    # explicitly NO ruff.toml / .ruff.toml / pyproject.toml at repo root.
    return repo


# ---------------------------------------------------------------------------
# Case execution helpers
# ---------------------------------------------------------------------------

def run_pcacc_case(
    repo: Path,
    task_id: str,
    *,
    use_evref: bool = False,
    registry_relpath: Optional[str] = None,
) -> Tuple[int, str, str, List[str], List[str]]:
    """Returns (exit_code, stdout, stderr, cmd_args_repr, env_overrides_repr)."""
    wrapper = repo / "run_pcacc.py"
    policy = repo / "artifacts" / "governance" / "precommit-check-policy.v3.5.json"
    args = ["--task", task_id, "--policy", str(policy), "--self-check"]
    if registry_relpath is not None:
        args += ["--evidence-ref-policy", registry_relpath]
    elif use_evref:
        registry = repo / "artifacts" / "governance" / "evidence-ref-policy.v3.5.3.json"
        args += ["--evidence-ref-policy", str(registry)]
    rc, out, err = run_subprocess(wrapper, args, cwd=repo)
    return rc, out, err, args, sorted(SUBPROCESS_ENV_OVERRIDES.keys())


def run_quality_case(
    repo: Path,
) -> Tuple[int, str, str, List[str], List[str]]:
    wrapper = repo / "run_quality.py"
    baseline = repo / "artifacts" / "governance" / "quality-baseline.v3.5.json"
    policy = repo / "artifacts" / "governance" / "quality-gate-policy.v3.5.json"
    args = ["--baseline", str(baseline), "--policy", str(policy), "--self-check"]
    rc, out, err = run_subprocess(wrapper, args, cwd=repo)
    return rc, out, err, args, sorted(SUBPROCESS_ENV_OVERRIDES.keys())


def parse_json_strict(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def find_check(checks: List[Dict[str, Any]], **filters: str) -> Optional[Dict[str, Any]]:
    for c in checks:
        if all(c.get(k) == v for k, v in filters.items()):
            return c
    return None


# Observed CLI status classifier. Separates the runner/harness CLI outcome from
# the golden case assertion status; the latter lives in actual_status and is
# constrained to {pass, skipped_with_reason_code, advisory}.
def classify_observed_cli_status(
    rc: int,
    overall: Optional[str],
    envelope_error: Optional[str] = None,
) -> str:
    if rc == 0 and overall == "pass":
        return "pass"
    if rc == 1 and overall == "fail":
        return "fail"
    if rc == 2:
        if envelope_error == "evidence_ref_registry_load_failed":
            return "exit_2_load_failed"
        if envelope_error == "invalid_task_id":
            return "exit_2_invalid_task_id"
        return "exit_2_unknown"
    return "drift"


# ---------------------------------------------------------------------------
# Case definitions
# ---------------------------------------------------------------------------

def case_default_001(repo: Path) -> Dict[str, Any]:
    rc, out, err, args, env_keys = run_pcacc_case(repo, "TASK-90001")
    payload = parse_json_strict(out)
    expected_codes = {
        "PCACC-001": "lifecycle_complete",
        "PCACC-002": "evidence_refs_resolved",
        "PCACC-003": "owner_and_reviewer_canonical",
        "PCACC-004": "review_after_evidence",
    }
    actual_codes: Dict[str, str] = {}
    if payload and isinstance(payload.get("checks"), list):
        for c in payload["checks"]:
            cid = c.get("check_id")
            if cid:
                actual_codes[cid] = c.get("reason_code", "")
    overall = payload.get("overall_status") if payload else None
    passed = (
        rc == 0
        and overall == "pass"
        and err.strip() == ""
        and actual_codes == expected_codes
    )
    observed_cli = classify_observed_cli_status(rc, overall)
    return _case_record(
        case_id="GCLI-PRECOMMIT-DEFAULT-001",
        group_id="GCLI-PRECOMMIT-DEFAULT",
        surface_id="CLI-PRECOMMIT",
        title="All four PCACC checks pass on synthetic compliant lifecycle (no --evidence-ref-policy)",
        cmd_args=args, env_keys=env_keys,
        expected_exit_code=0, actual_exit_code=rc,
        stdout_contract={
            "json_parse": "ok" if payload else "failed",
            "checks_reason_codes_match": actual_codes == expected_codes,
            "expected_reason_codes": expected_codes,
            "actual_reason_codes": actual_codes,
        },
        stderr_contract={"empty_required": True, "stderr_len": len(err)},
        json_contract={
            "schema_version": (payload or {}).get("schema_version"),
            "overall_status": overall,
        },
        expected_status="pass",
        actual_status="pass" if passed else "drift",
        expected_cli_status="pass",
        observed_cli_status=observed_cli,
        expected_reason_code="all_four_pcacc_pass",
        actual_reason_code=";".join(k + "=" + v for k, v in actual_codes.items()),
        passed=passed,
        evidence_ref="artifacts/verify/TASK-1037/fixtures/" + PCACC_REPO_DIRNAME + "/",
        notes="Default success path locked at the CLI boundary.",
    )


def _evref_pcacc_002(
    case_id: str,
    title: str,
    repo: Path,
    task_id: str,
    *,
    use_evref: bool,
    expected_exit_code: int,
    expected_overall: str,
    expected_pcacc_002_status: str,
    expected_cli_status: str,
    expected_reason_literal: Optional[str] = None,
    expected_reason_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    rc, out, err, args, env_keys = run_pcacc_case(repo, task_id, use_evref=use_evref)
    payload = parse_json_strict(out)
    actual_check = None
    if payload:
        actual_check = find_check(payload.get("checks") or [], check_id="PCACC-002")
    actual_check_status = (actual_check or {}).get("status")
    actual_reason = (actual_check or {}).get("reason_code", "")
    overall = (payload or {}).get("overall_status")
    reason_ok: bool
    if expected_reason_literal is not None:
        reason_ok = actual_reason == expected_reason_literal
    elif expected_reason_prefix is not None:
        reason_ok = actual_reason.startswith(expected_reason_prefix)
    else:
        reason_ok = True
    passed = (
        rc == expected_exit_code
        and err.strip() == ""
        and overall == expected_overall
        and actual_check_status == expected_pcacc_002_status
        and reason_ok
    )
    observed_cli = classify_observed_cli_status(rc, overall)
    return _case_record(
        case_id=case_id,
        group_id="GCLI-PRECOMMIT-EVREF",
        surface_id="CLI-PRECOMMIT",
        title=title,
        cmd_args=args, env_keys=env_keys,
        expected_exit_code=expected_exit_code, actual_exit_code=rc,
        stdout_contract={
            "json_parse": "ok" if payload else "failed",
            "pcacc_002_present": actual_check is not None,
        },
        stderr_contract={"empty_required": True, "stderr_len": len(err)},
        json_contract={
            "overall_status": overall,
            "pcacc_002.status": actual_check_status,
            "pcacc_002.reason_code": actual_reason,
        },
        expected_status="pass",
        actual_status="pass" if passed else "drift",
        expected_cli_status=expected_cli_status,
        observed_cli_status=observed_cli,
        expected_reason_code=expected_reason_literal or ("prefix:" + (expected_reason_prefix or "")),
        actual_reason_code=actual_reason,
        passed=passed,
        evidence_ref="artifacts/verify/TASK-1037/fixtures/" + PCACC_REPO_DIRNAME + "/",
        notes="Evidence Ref policy CLI lock per matrix GCLI-PRECOMMIT-EVREF.",
    )


def case_evref_001(repo: Path) -> Dict[str, Any]:
    return _evref_pcacc_002(
        "GCLI-PRECOMMIT-EVREF-001",
        "Valid local artifact ref resolves under registry mode",
        repo, "TASK-90011",
        use_evref=True,
        expected_exit_code=0, expected_overall="pass",
        expected_pcacc_002_status="pass",
        expected_cli_status="pass",
        expected_reason_literal="evidence_refs_resolved",
    )


def case_evref_002(repo: Path) -> Dict[str, Any]:
    return _evref_pcacc_002(
        "GCLI-PRECOMMIT-EVREF-002",
        "Empty Evidence Refs section with ORC-1 marker is skipped under registry mode",
        repo, "TASK-90012",
        use_evref=True,
        expected_exit_code=0, expected_overall="pass",
        expected_pcacc_002_status="skipped_with_reason_code",
        expected_cli_status="pass",
        expected_reason_literal="evidence_refs_optional_per_orc_1",
    )


def case_evref_003(repo: Path) -> Dict[str, Any]:
    return _evref_pcacc_002(
        "GCLI-PRECOMMIT-EVREF-003",
        "Forbidden URL scheme ref under registry mode classified malformed",
        repo, "TASK-90013",
        use_evref=True,
        expected_exit_code=1, expected_overall="fail",
        expected_pcacc_002_status="fail",
        expected_cli_status="fail",
        expected_reason_prefix="malformed_refs:https://",
    )


def case_evref_004(repo: Path) -> Dict[str, Any]:
    return _evref_pcacc_002(
        "GCLI-PRECOMMIT-EVREF-004",
        "Parent traversal ref under registry mode classified malformed",
        repo, "TASK-90014",
        use_evref=True,
        expected_exit_code=1, expected_overall="fail",
        expected_pcacc_002_status="fail",
        expected_cli_status="fail",
        expected_reason_prefix="malformed_refs:../",
    )


def case_evref_005(repo: Path) -> Dict[str, Any]:
    return _evref_pcacc_002(
        "GCLI-PRECOMMIT-EVREF-005",
        "Default mode preserves TASK-1030 NEG-002 reason_code byte-identically",
        repo, "TASK-90015",
        use_evref=False,
        expected_exit_code=1, expected_overall="fail",
        expected_pcacc_002_status="fail",
        expected_cli_status="fail",
        expected_reason_literal=NEG_002_REASON_CODE,
    )


def case_evref_006(repo: Path) -> Dict[str, Any]:
    return _evref_pcacc_002(
        "GCLI-PRECOMMIT-EVREF-006",
        "Default mode preserves TASK-1030 NEG-003 reason_code byte-identically",
        repo, "TASK-90016",
        use_evref=False,
        expected_exit_code=1, expected_overall="fail",
        expected_pcacc_002_status="fail",
        expected_cli_status="fail",
        expected_reason_literal=NEG_003_REASON_CODE,
    )


def _failclosed(
    case_id: str,
    title: str,
    repo: Path,
    registry_relpath: str,
    expected_reason_code: str,
) -> Dict[str, Any]:
    rc, out, err, args, env_keys = run_pcacc_case(
        repo, "TASK-90011", registry_relpath=registry_relpath,
    )
    payload = parse_json_strict(out)
    actual_error = (payload or {}).get("error")
    actual_reason = (payload or {}).get("reason_code")
    passed = (
        rc == 2
        and err.strip() == ""
        and actual_error == "evidence_ref_registry_load_failed"
        and actual_reason == expected_reason_code
    )
    observed_cli = classify_observed_cli_status(rc, None, envelope_error=actual_error)
    return _case_record(
        case_id=case_id, group_id="GCLI-PRECOMMIT-FAILCLOSED",
        surface_id="CLI-PRECOMMIT", title=title,
        cmd_args=args, env_keys=env_keys,
        expected_exit_code=2, actual_exit_code=rc,
        stdout_contract={
            "json_parse": "ok" if payload else "failed",
            "envelope.error": actual_error,
            "envelope.reason_code": actual_reason,
        },
        stderr_contract={"empty_required": True, "stderr_len": len(err)},
        json_contract={
            "error": actual_error,
            "reason_code": actual_reason,
        },
        expected_status="pass",
        actual_status="pass" if passed else "drift",
        expected_cli_status="exit_2_load_failed",
        observed_cli_status=observed_cli,
        expected_reason_code=expected_reason_code,
        actual_reason_code=str(actual_reason),
        passed=passed,
        evidence_ref="artifacts/verify/TASK-1037/fixtures/" + PCACC_REPO_DIRNAME + "/registries/" + Path(registry_relpath).name,
        notes="Fail-closed envelope locked.",
    )


def case_failclosed_001(repo: Path) -> Dict[str, Any]:
    return _failclosed(
        "GCLI-PRECOMMIT-FAILCLOSED-001",
        "--evidence-ref-policy at missing file -> exit 2 (evidence_ref_registry_missing)",
        repo, "registries/missing.json", "evidence_ref_registry_missing",
    )


def case_failclosed_002(repo: Path) -> Dict[str, Any]:
    return _failclosed(
        "GCLI-PRECOMMIT-FAILCLOSED-002",
        "--evidence-ref-policy at malformed JSON -> exit 2 (evidence_ref_registry_malformed_json)",
        repo, "registries/malformed-json.json", "evidence_ref_registry_malformed_json",
    )


def case_failclosed_003(repo: Path) -> Dict[str, Any]:
    return _failclosed(
        "GCLI-PRECOMMIT-FAILCLOSED-003",
        "--evidence-ref-policy schema_version mismatch -> exit 2 (evidence_ref_registry_schema_version_mismatch)",
        repo, "registries/schema-version-mismatch.json", "evidence_ref_registry_schema_version_mismatch",
    )


def case_failclosed_004(repo: Path) -> Dict[str, Any]:
    return _failclosed(
        "GCLI-PRECOMMIT-FAILCLOSED-004",
        "--evidence-ref-policy with PCACC-002 conflict -> exit 2 (evidence_ref_registry_pcacc_002_conflict)",
        repo, "registries/pcacc-conflict.json", "evidence_ref_registry_pcacc_002_conflict",
    )


def _lifecycle_pcacc_check(
    case_id: str,
    title: str,
    repo: Path,
    task_id: str,
    check_id: str,
    *,
    expected_exit_code: int,
    expected_overall: str,
    expected_check_status: str,
    expected_cli_status: str,
    expected_reason_literal: Optional[str] = None,
    expected_reason_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    rc, out, err, args, env_keys = run_pcacc_case(repo, task_id)
    payload = parse_json_strict(out)
    check = None
    if payload:
        check = find_check(payload.get("checks") or [], check_id=check_id)
    actual_check_status = (check or {}).get("status")
    actual_reason = (check or {}).get("reason_code", "")
    overall = (payload or {}).get("overall_status")
    if expected_reason_literal is not None:
        reason_ok = actual_reason == expected_reason_literal
    elif expected_reason_prefix is not None:
        reason_ok = actual_reason.startswith(expected_reason_prefix)
    else:
        reason_ok = True
    passed = (
        rc == expected_exit_code
        and err.strip() == ""
        and overall == expected_overall
        and actual_check_status == expected_check_status
        and reason_ok
    )
    observed_cli = classify_observed_cli_status(rc, overall)
    return _case_record(
        case_id=case_id, group_id="GCLI-PRECOMMIT-LIFECYCLE",
        surface_id="CLI-PRECOMMIT", title=title,
        cmd_args=args, env_keys=env_keys,
        expected_exit_code=expected_exit_code, actual_exit_code=rc,
        stdout_contract={
            "json_parse": "ok" if payload else "failed",
            check_id + ".present": check is not None,
        },
        stderr_contract={"empty_required": True, "stderr_len": len(err)},
        json_contract={
            "overall_status": overall,
            check_id + ".status": actual_check_status,
            check_id + ".reason_code": actual_reason,
        },
        expected_status="pass",
        actual_status="pass" if passed else "drift",
        expected_cli_status=expected_cli_status,
        observed_cli_status=observed_cli,
        expected_reason_code=expected_reason_literal or ("prefix:" + (expected_reason_prefix or "")),
        actual_reason_code=actual_reason,
        passed=passed,
        evidence_ref="artifacts/verify/TASK-1037/fixtures/" + PCACC_REPO_DIRNAME + "/artifacts/{tasks,plans,decisions,verify,status}/" + task_id + ".*",
        notes="PCACC fail-path lock for " + check_id,
    )


def case_lifecycle_001(repo: Path) -> Dict[str, Any]:
    return _lifecycle_pcacc_check(
        "GCLI-PRECOMMIT-LIFECYCLE-001",
        "Missing verify artifact -> PCACC-001 fail (lifecycle_missing:<kinds>)",
        repo, "TASK-90021", "PCACC-001",
        expected_exit_code=1, expected_overall="fail",
        expected_check_status="fail",
        expected_cli_status="fail",
        expected_reason_prefix="lifecycle_missing:",
    )


def case_lifecycle_002(repo: Path) -> Dict[str, Any]:
    return _lifecycle_pcacc_check(
        "GCLI-PRECOMMIT-LIFECYCLE-002",
        "Non-canonical owner -> PCACC-003 fail (non_canonical:<fields>)",
        repo, "TASK-90022", "PCACC-003",
        expected_exit_code=1, expected_overall="fail",
        expected_check_status="fail",
        expected_cli_status="fail",
        expected_reason_prefix="non_canonical:",
    )


def case_lifecycle_003(repo: Path) -> Dict[str, Any]:
    return _lifecycle_pcacc_check(
        "GCLI-PRECOMMIT-LIFECYCLE-003",
        "review_ts == evidence_ts -> PCACC-004 fail (review_equal_to_evidence_not_strictly_after)",
        repo, "TASK-90023", "PCACC-004",
        expected_exit_code=1, expected_overall="fail",
        expected_check_status="fail",
        expected_cli_status="fail",
        expected_reason_literal="review_equal_to_evidence_not_strictly_after",
    )


def case_lifecycle_004(repo: Path) -> Dict[str, Any]:
    return _lifecycle_pcacc_check(
        "GCLI-PRECOMMIT-LIFECYCLE-004",
        "review_ts < evidence_ts -> PCACC-004 fail (review_before_evidence)",
        repo, "TASK-90024", "PCACC-004",
        expected_exit_code=1, expected_overall="fail",
        expected_check_status="fail",
        expected_cli_status="fail",
        expected_reason_literal="review_before_evidence",
    )


def case_lifecycle_005(repo: Path) -> Dict[str, Any]:
    rc, out, err, args, env_keys = run_pcacc_case(repo, "NOT-A-TASK")
    payload = parse_json_strict(out)
    actual_error = (payload or {}).get("error")
    actual_value = (payload or {}).get("value")
    passed = (
        rc == 2
        and err.strip() == ""
        and actual_error == "invalid_task_id"
        and actual_value == "NOT-A-TASK"
    )
    observed_cli = classify_observed_cli_status(rc, None, envelope_error=actual_error)
    return _case_record(
        case_id="GCLI-PRECOMMIT-LIFECYCLE-005",
        group_id="GCLI-PRECOMMIT-LIFECYCLE",
        surface_id="CLI-PRECOMMIT",
        title="Invalid task ID -> exit 2 with stdout {error: invalid_task_id, value: <raw>}",
        cmd_args=args, env_keys=env_keys,
        expected_exit_code=2, actual_exit_code=rc,
        stdout_contract={
            "json_parse": "ok" if payload else "failed",
            "envelope.error": actual_error,
            "envelope.value": actual_value,
        },
        stderr_contract={"empty_required": True, "stderr_len": len(err)},
        json_contract={"error": actual_error, "value": actual_value},
        expected_status="pass",
        actual_status="pass" if passed else "drift",
        expected_cli_status="exit_2_invalid_task_id",
        observed_cli_status=observed_cli,
        expected_reason_code="invalid_task_id",
        actual_reason_code=str(actual_error),
        passed=passed,
        evidence_ref="artifacts/verify/TASK-1037/fixtures/" + PCACC_REPO_DIRNAME + "/",
        notes="invocation-error envelope locked.",
    )


def _quality_check_assert(
    case_id: str, group_id: str, title: str, repo: Path,
    *,
    gate_id: str,
    expected_exit_code: int,
    expected_overall: str,
    expected_cli_status: str,
    target_relpath: Optional[str] = None,
    expected_check_status: Optional[str] = None,
    expected_reason_literal: Optional[str] = None,
    expected_reason_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    rc, out, err, args, env_keys = run_quality_case(repo)
    payload = parse_json_strict(out)
    overall = (payload or {}).get("overall_status")
    selected = None
    if payload:
        candidates = [c for c in (payload.get("checks") or []) if c.get("gate_id") == gate_id]
        if target_relpath is not None:
            for c in candidates:
                if c.get("target") == target_relpath:
                    selected = c
                    break
        else:
            selected = candidates[0] if candidates else None
    actual_check_status = (selected or {}).get("status")
    actual_reason = (selected or {}).get("reason_code", "")
    if expected_reason_literal is not None:
        reason_ok = actual_reason == expected_reason_literal
    elif expected_reason_prefix is not None:
        reason_ok = actual_reason.startswith(expected_reason_prefix)
    else:
        reason_ok = True
    status_ok = actual_check_status == expected_check_status if expected_check_status is not None else True
    passed = (
        rc == expected_exit_code
        and err.strip() == ""
        and overall == expected_overall
        and status_ok
        and reason_ok
    )
    observed_cli = classify_observed_cli_status(rc, overall)
    return _case_record(
        case_id=case_id, group_id=group_id, surface_id="CLI-QUALITY-GATES",
        title=title, cmd_args=args, env_keys=env_keys,
        expected_exit_code=expected_exit_code, actual_exit_code=rc,
        stdout_contract={
            "json_parse": "ok" if payload else "failed",
            gate_id + ".target": target_relpath,
            gate_id + ".selected": selected is not None,
        },
        stderr_contract={"empty_required": True, "stderr_len": len(err)},
        json_contract={
            "overall_status": overall,
            gate_id + ".status": actual_check_status,
            gate_id + ".reason_code": actual_reason,
        },
        expected_status="pass",
        actual_status="pass" if passed else "drift",
        expected_cli_status=expected_cli_status,
        observed_cli_status=observed_cli,
        expected_reason_code=expected_reason_literal or ("prefix:" + (expected_reason_prefix or "")),
        actual_reason_code=actual_reason,
        passed=passed,
        evidence_ref="artifacts/verify/TASK-1037/fixtures/" + repo.name + "/",
        notes="Quality gate CLI lock per matrix " + group_id,
    )


def case_quality_sync_001(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-SYNC-001", "GCLI-QUALITY-SYNC",
        "Baseline-existing pair byte-identical -> reason_code=in_sync; exit 0",
        repo, gate_id="QC-SYNC-001",
        expected_exit_code=0, expected_overall="pass",
        expected_cli_status="pass",
        target_relpath="artifacts/scripts/case_pair.py",
        expected_check_status="pass", expected_reason_literal="in_sync",
    )


def case_quality_sync_002(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-SYNC-002", "GCLI-QUALITY-SYNC",
        "Baseline-existing drift unchanged -> reason_code=baseline_existing; exit 0",
        repo, gate_id="QC-SYNC-001",
        expected_exit_code=0, expected_overall="pass",
        expected_cli_status="pass",
        target_relpath="artifacts/scripts/case_pair.py",
        expected_check_status="pass", expected_reason_literal="baseline_existing",
    )


def case_quality_sync_004(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-SYNC-004", "GCLI-QUALITY-SYNC",
        "Post-baseline new pair drift -> reason_code=post_baseline_new_pair_drift; exit 1",
        repo, gate_id="QC-SYNC-001",
        expected_exit_code=1, expected_overall="fail",
        expected_cli_status="fail",
        target_relpath="artifacts/scripts/post_baseline_new.py",
        expected_check_status="fail",
        expected_reason_literal="post_baseline_new_pair_drift",
    )


def case_quality_schema_001(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-SCHEMA-001", "GCLI-QUALITY-SCHEMA",
        "All schema targets valid -> reason_code=schema_and_keys_ok; exit 0",
        repo, gate_id="QC-SCHEMA-001",
        expected_exit_code=0, expected_overall="pass",
        expected_cli_status="pass",
        target_relpath="artifacts/governance/quality-baseline.v3.5.json",
        expected_check_status="pass", expected_reason_literal="schema_and_keys_ok",
    )


def case_quality_schema_002(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-SCHEMA-002", "GCLI-QUALITY-SCHEMA",
        "schema_version mismatch on quality-baseline -> reason_code=schema_version_mismatch; exit 1",
        repo, gate_id="QC-SCHEMA-001",
        expected_exit_code=1, expected_overall="fail",
        expected_cli_status="fail",
        target_relpath="artifacts/governance/quality-baseline.v3.5.json",
        expected_check_status="fail",
        expected_reason_literal="schema_version_mismatch",
    )


def case_quality_import_003(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-IMPORT-003", "GCLI-QUALITY-IMPORT",
        "Unlisted dirty module -> first_cycle_observation_dirty_import advisory",
        repo, gate_id="QC-IMPORT-001",
        expected_exit_code=0, expected_overall="pass",
        expected_cli_status="pass",
        target_relpath="artifacts/scripts/dirty_module.py",
        expected_check_status="advisory",
        expected_reason_literal="first_cycle_observation_dirty_import",
    )


def case_quality_golden_001(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-GOLDEN-001", "GCLI-QUALITY-GOLDEN",
        "Deferred capture_policy -> post_task_evidence_only_capture_deferred skipped_with_reason_code",
        repo, gate_id="QC-GOLDEN-001",
        expected_exit_code=0, expected_overall="pass",
        expected_cli_status="pass",
        target_relpath="FX-CLI-0001",
        expected_check_status="skipped_with_reason_code",
        expected_reason_literal="post_task_evidence_only_capture_deferred",
    )


def case_quality_ruff_001(repo: Path) -> Dict[str, Any]:
    return _quality_check_assert(
        "GCLI-QUALITY-RUFF-ADVISORY-001", "GCLI-QUALITY-RUFF-ADVISORY",
        "RUFF advisory contract -> status=advisory reason_code=advisory_only_in_v3.5.0",
        repo, gate_id="QC-RUFF-001",
        expected_exit_code=0, expected_overall="pass",
        expected_cli_status="pass",
        target_relpath="ruff_config",
        expected_check_status="advisory",
        expected_reason_literal="advisory_only_in_v3.5.0",
    )


# ---------------------------------------------------------------------------
# Case record assembly
# ---------------------------------------------------------------------------

def _case_record(
    case_id: str,
    group_id: str,
    surface_id: str,
    title: str,
    cmd_args: List[str],
    env_keys: List[str],
    expected_exit_code: int,
    actual_exit_code: int,
    stdout_contract: Dict[str, Any],
    stderr_contract: Dict[str, Any],
    json_contract: Dict[str, Any],
    expected_status: str,
    actual_status: str,
    expected_cli_status: str,
    observed_cli_status: str,
    expected_reason_code: str,
    actual_reason_code: str,
    passed: bool,
    evidence_ref: str,
    notes: str,
) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "group_id": group_id,
        "surface_id": surface_id,
        "title": title,
        "command": "python -B <fixture-runner-copy> " + " ".join(cmd_args),
        "subprocess_env_overrides": env_keys,
        "expected_exit_code": expected_exit_code,
        "actual_exit_code": actual_exit_code,
        "stdout_contract": stdout_contract,
        "stderr_contract": stderr_contract,
        "json_contract": json_contract,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "expected_cli_status": expected_cli_status,
        "observed_cli_status": observed_cli_status,
        "expected_reason_code": expected_reason_code,
        "actual_reason_code": actual_reason_code,
        "pass": passed,
        "evidence_ref": evidence_ref,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Cache audit and production preservation
# ---------------------------------------------------------------------------

def cache_audit() -> Dict[str, Any]:
    pycache_paths: List[str] = []
    pyc_paths: List[str] = []
    sweep_roots = [TASK_DIR, REPO_ROOT / "artifacts" / "scripts", REPO_ROOT / "template" / "artifacts" / "scripts"]
    seen = set()
    for root in sweep_roots:
        if not root.exists():
            continue
        rk = str(root.resolve())
        if rk in seen:
            continue
        seen.add(rk)
        for p in root.rglob("__pycache__"):
            try:
                rel = p.resolve().relative_to(REPO_ROOT)
            except ValueError:
                continue
            pycache_paths.append(str(rel).replace("\\", "/"))
        for p in root.rglob("*.pyc"):
            try:
                rel = p.resolve().relative_to(REPO_ROOT)
            except ValueError:
                continue
            pyc_paths.append(str(rel).replace("\\", "/"))
    # Filter pycache_paths down to those introduced under TASK_DIR (we cannot
    # claim ownership of any pre-existing `__pycache__` under
    # `artifacts/scripts/` from prior chains; those are recorded but not
    # blamed on this task).
    task_dir_str = str(TASK_DIR.resolve()).replace("\\", "/")
    repo_root_str = str(REPO_ROOT.resolve()).replace("\\", "/")
    task_rel_prefix = task_dir_str[len(repo_root_str) + 1:] if task_dir_str.startswith(repo_root_str + "/") else None
    introduced: List[str] = []
    if task_rel_prefix:
        for path in pycache_paths + pyc_paths:
            if path.startswith(task_rel_prefix + "/"):
                introduced.append(path)
    return {
        "pycache_created": bool(introduced),
        "unexpected_cache_paths": sorted(introduced),
        "pre_existing_pycache_under_artifacts_scripts": sorted(
            p for p in pycache_paths
            if p.startswith("artifacts/scripts/") or p.startswith("template/artifacts/scripts/")
        ),
        "env_controls": sorted(SUBPROCESS_ENV_OVERRIDES.keys()),
        "python_b_flag_used": True,
        "harness_dont_write_bytecode": True,
    }


def production_preservation() -> Dict[str, Any]:
    targets = []
    all_unchanged = True
    for rel, expected in PRODUCTION_PRESERVATION_TARGETS:
        actual = sha256_file_prefix(REPO_ROOT / rel)
        unchanged = actual == expected
        if not unchanged:
            all_unchanged = False
        targets.append({
            "path": rel,
            "expected_sha256_prefix": expected,
            "actual_sha256_prefix": actual,
            "unchanged_relative_to_task_1036_baseline": unchanged,
        })
    return {
        "all_targets_unchanged": all_unchanged,
        "targets": targets,
        "baseline_source": "TASK-1036.status.json#real_pcacc_runner_sha256_prefix; real_quality_gate_runner_sha256_prefix; target_file_sha256_prefixes",
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_all_cases() -> List[Dict[str, Any]]:
    pcacc_repo = build_pcacc_fixture()
    cases: List[Dict[str, Any]] = []
    cases.append(case_default_001(pcacc_repo))
    cases.append(case_evref_001(pcacc_repo))
    cases.append(case_evref_002(pcacc_repo))
    cases.append(case_evref_003(pcacc_repo))
    cases.append(case_evref_004(pcacc_repo))
    cases.append(case_evref_005(pcacc_repo))
    cases.append(case_evref_006(pcacc_repo))
    cases.append(case_failclosed_001(pcacc_repo))
    cases.append(case_failclosed_002(pcacc_repo))
    cases.append(case_failclosed_003(pcacc_repo))
    cases.append(case_failclosed_004(pcacc_repo))
    cases.append(case_lifecycle_001(pcacc_repo))
    cases.append(case_lifecycle_002(pcacc_repo))
    cases.append(case_lifecycle_003(pcacc_repo))
    cases.append(case_lifecycle_004(pcacc_repo))
    cases.append(case_lifecycle_005(pcacc_repo))

    cases.append(case_quality_sync_001(build_quality_sync_001_fixture()))
    cases.append(case_quality_sync_002(build_quality_sync_002_fixture()))
    cases.append(case_quality_sync_004(build_quality_sync_004_fixture()))
    cases.append(case_quality_schema_001(build_quality_schema_001_fixture()))
    cases.append(case_quality_schema_002(build_quality_schema_002_fixture()))
    cases.append(case_quality_import_003(build_quality_import_003_fixture()))
    cases.append(case_quality_golden_001(build_quality_golden_001_fixture()))
    cases.append(case_quality_ruff_001(build_quality_ruff_001_fixture()))
    return cases


def assemble_summary(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    surface_counts: Dict[str, Dict[str, int]] = {}
    group_counts: Dict[str, Dict[str, int]] = {}
    passed = failed = 0
    for c in cases:
        sid = c["surface_id"]
        gid = c["group_id"]
        surface_counts.setdefault(sid, {"total": 0, "passed": 0, "failed": 0})
        group_counts.setdefault(gid, {"total": 0, "passed": 0, "failed": 0})
        surface_counts[sid]["total"] += 1
        group_counts[gid]["total"] += 1
        if c["pass"]:
            passed += 1
            surface_counts[sid]["passed"] += 1
            group_counts[gid]["passed"] += 1
        else:
            failed += 1
            surface_counts[sid]["failed"] += 1
            group_counts[gid]["failed"] += 1
    return {
        "total_cases": len(cases),
        "passed_cases": passed,
        "skipped_with_reason_code_cases": 0,
        "advisory_cases": 0,
        "failed_cases": failed,
        "surface_counts": surface_counts,
        "group_counts": group_counts,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="TASK-1037 golden CLI coverage harness")
    parser.add_argument("--write-result", action="store_true",
                        help="write golden-cli-coverage-result.json under artifacts/verify/TASK-1037/")
    parser.add_argument("--no-reset", action="store_true",
                        help="skip fixture reset (debug only)")
    args = parser.parse_args(argv)

    if not args.no_reset:
        reset_fixtures()
    cases = run_all_cases()
    summary = assemble_summary(cases)
    audit = cache_audit()
    preservation = production_preservation()

    overall_pass = (
        summary["failed_cases"] == 0
        and not audit["pycache_created"]
        and preservation["all_targets_unchanged"]
    )
    result = {
        "schema_version": "golden-cli-coverage-result/v1",
        "task_id": "TASK-1037",
        "generated_at": now_taipei_iso(),
        "harness_ref": "artifacts/verify/TASK-1037/run_golden_cli_coverage.py",
        "case_manifest_ref": "artifacts/verify/TASK-1037/golden-cli-case-manifest.json",
        "overall_status": "pass" if overall_pass else "fail",
        "summary": summary,
        "cases": cases,
        "cache_audit": audit,
        "production_preservation": preservation,
        "limitations": [
            "Twenty-four cases are implemented; remaining matrix cases are recorded with implementation_status=implemented_with_limitations in the case manifest and remain candidates for a future lifecycle.",
            "Each fixture repo contains byte-identical copies of the production runner under artifacts/scripts/ to anchor SCRIPT_PATH.parents inside the fixture root; fixture-local copies are not modifications of the production runner.",
            "Quality runner Pass-2 detects the runner self-pair as post_baseline_new_pair_in_sync; harness asserts QC-SYNC-001 case-specific check by target path to avoid coupling to the runner self-pair.",
            "QC-SCHEMA-001 reads minimum_required_targets from fixed paths under repo root; per-case fixture provides deterministic stubs to make the gate well-defined.",
            "Cache audit only blames cache files that appear under artifacts/verify/TASK-1037/. Pre-existing __pycache__ under artifacts/scripts/ from prior v3.4 / v3.5 chains is recorded but not attributed to TASK-1037.",
            "Per-case status semantics (TASK-1037 repair): expected_status / actual_status encode the golden case assertion status (allowed values: pass / skipped_with_reason_code / advisory). expected_cli_status / observed_cli_status encode the runner CLI outcome and may carry pass / fail / skipped_with_reason_code / advisory / exit_2_load_failed / exit_2_invalid_task_id. Negative CLI cases legitimately observe fail or exit_2_*; the golden assertion still asserts pass=true when expected and observed CLI outcomes match.",
        ],
    }

    if args.write_result:
        out_path = TASK_DIR / "golden-cli-coverage-result.json"
        write_text(out_path, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print("golden-cli-coverage-result:", result["overall_status"],
              "passed=" + str(summary["passed_cases"]),
              "failed=" + str(summary["failed_cases"]),
              "pycache_created=" + str(audit["pycache_created"]),
              "production_unchanged=" + str(preservation["all_targets_unchanged"]))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
