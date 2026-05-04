#!/usr/bin/env python3
"""v3.5.0 baseline-aware P0 quality gate runner (TASK-1025 deliverable).

Consumes:
- artifacts/governance/quality-baseline.v3.5.json (TASK-1024 frozen baseline)
- artifacts/governance/quality-gate-policy.v3.5.json (this task's policy)

Implements baseline-aware enforcement for QC-SYNC-001, QC-SCHEMA-001,
QC-IMPORT-001, QC-GOLDEN-001 plus advisory QC-RUFF-001.

Existing baseline drift with unchanged sha256 is NOT a TASK-1025 failure.
New or modified drift after baseline IS blocking unless covered by a
valid unexpired waiver. Expired waivers are blocking.

Usage:
  python artifacts/scripts/run_quality_gates.py [--baseline PATH] [--policy PATH]
                                                [--format json] [--self-check]
                                                [--output PATH]

Exit codes:
  0 = no blocking failures
  1 = at least one blocking gate failed
  2 = invocation error / missing inputs
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_PATH = Path(__file__).resolve()
TAIPEI_TZ = timezone(timedelta(hours=8))

REQUIRED_WAIVER_FIELDS = (
    "rule_id",
    "scope",
    "reason_code",
    "owner",
    "evidence_ref",
    "expires_at",
)


# ---------------------------------------------------------------------------
# Stream init (CLI entrypoint only — do NOT call at import time)
# ---------------------------------------------------------------------------

def init_streams(stdout: Any = None, stderr: Any = None) -> None:
    """Apply UTF-8 encoding wrapper to streams. CLI entrypoint only."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    if hasattr(out, "buffer") and getattr(out, "encoding", "utf-8").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(out.buffer, encoding="utf-8", errors="replace")
    if hasattr(err, "buffer") and getattr(err, "encoding", "utf-8").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(err.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Repo helpers
# ---------------------------------------------------------------------------

def detect_repo_root() -> Path:
    matches = [
        parent
        for parent in SCRIPT_PATH.parents
        if (parent / "consilium-fabri-governance-repair-plan-v3.5.md").is_file()
        and (parent / "artifacts" / "governance" / "quality-baseline.v3.5.json").is_file()
        and (parent / "template").is_dir()
    ]
    if not matches:
        raise RuntimeError(f"Unable to detect repo root from {SCRIPT_PATH}")
    return matches[-1]


def sha256_of_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_taipei_iso() -> str:
    return datetime.now(TAIPEI_TZ).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Waiver helpers
# ---------------------------------------------------------------------------

def is_waiver_shape_valid(waiver: Dict[str, Any]) -> Tuple[bool, str]:
    missing = [f for f in REQUIRED_WAIVER_FIELDS if f not in waiver]
    if missing:
        return False, "missing_fields:" + ",".join(missing)
    scope = waiver.get("scope")
    if not isinstance(scope, list) or not scope:
        return False, "scope_must_be_nonempty_list"
    return True, "ok"


def is_waiver_unexpired(waiver: Dict[str, Any], today_iso: str) -> Tuple[bool, str]:
    expires = waiver.get("expires_at", "")
    if not isinstance(expires, str) or not expires:
        return False, "expires_at_missing"
    today_date = today_iso[:10]
    if today_date > expires:
        return False, "expired:" + expires
    return True, "ok"


def find_applicable_waivers(
    rule_id: str, target_path: str, policy_waivers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for w in policy_waivers:
        if w.get("rule_id") != rule_id:
            continue
        scope = w.get("scope") or []
        if isinstance(scope, list) and target_path in scope:
            out.append(w)
    return out


def select_valid_waivers(
    waivers: List[Dict[str, Any]], today_iso: str
) -> Tuple[List[Dict[str, Any]], List[str]]:
    valid: List[Dict[str, Any]] = []
    invalid_reasons: List[str] = []
    for w in waivers:
        ok_s, msg_s = is_waiver_shape_valid(w)
        if not ok_s:
            invalid_reasons.append(msg_s)
            continue
        ok_e, msg_e = is_waiver_unexpired(w, today_iso)
        if not ok_e:
            invalid_reasons.append(msg_e)
            continue
        valid.append(w)
    return valid, invalid_reasons


# ---------------------------------------------------------------------------
# QC-SYNC-001 source/template baseline-aware enforcement
# ---------------------------------------------------------------------------

def run_qc_sync_001(
    repo_root: Path, baseline: Dict[str, Any], policy: Dict[str, Any], today_iso: str
) -> List[Dict[str, Any]]:
    pairs = baseline.get("source_template_pairs", []) or []
    waivers = policy.get("waivers", []) or []
    checks: List[Dict[str, Any]] = []

    for pair in pairs:
        bid = pair.get("baseline_id", "?")
        src_rel = pair.get("source_path") or ""
        tpl_rel = pair.get("template_path") or ""
        baseline_status = pair.get("status")
        baseline_src_sha = pair.get("sha256_source")
        baseline_tpl_sha = pair.get("sha256_template")

        src_path = repo_root / src_rel if src_rel else None
        tpl_path = repo_root / tpl_rel if tpl_rel else None
        current_src_sha = sha256_of_file(src_path) if src_path else None
        current_tpl_sha = sha256_of_file(tpl_path) if tpl_path else None

        if current_src_sha is None and current_tpl_sha is None:
            current_status = "missing_both"
        elif current_src_sha is None:
            current_status = "missing_source"
        elif current_tpl_sha is None:
            current_status = "missing_template"
        elif current_src_sha == current_tpl_sha:
            current_status = "in_sync"
        else:
            current_status = "drift"

        baseline_unchanged = (
            current_src_sha == baseline_src_sha
            and current_tpl_sha == baseline_tpl_sha
        )

        check: Dict[str, Any] = {
            "gate_id": "QC-SYNC-001",
            "target": src_rel,
            "expected": "in_sync_or_unchanged_baseline_drift_or_valid_waiver",
            "actual": (
                "current_status=" + str(current_status)
                + "; baseline_status=" + str(baseline_status)
                + "; baseline_unchanged=" + str(baseline_unchanged)
            ),
            "evidence_ref": "baseline_id=" + str(bid),
        }

        if current_status == "in_sync":
            check["status"] = "pass"
            check["reason_code"] = "in_sync"
        elif baseline_status in ("drift", "missing_template", "missing_source") and baseline_unchanged:
            check["status"] = "pass"
            check["reason_code"] = "baseline_existing"
        else:
            applicable = find_applicable_waivers("QC-SYNC-001", src_rel, waivers)
            valid, invalid_reasons = select_valid_waivers(applicable, today_iso)
            if valid:
                check["status"] = "skipped_with_reason_code"
                check["reason_code"] = (
                    "waivered_until:" + valid[0].get("expires_at", "")
                )
            else:
                check["status"] = "fail"
                if invalid_reasons:
                    check["reason_code"] = "waiver_invalid:" + ";".join(invalid_reasons)
                elif baseline_status not in ("drift", "missing_template", "missing_source"):
                    check["reason_code"] = "new_or_modified_drift_after_baseline"
                else:
                    check["reason_code"] = "baseline_drift_changed_without_waiver"
        checks.append(check)
    return checks


# ---------------------------------------------------------------------------
# QC-SCHEMA-001 minimal JSON schema / structure validation
# ---------------------------------------------------------------------------

REQUIRED_JSON_TARGETS: List[Tuple[str, Optional[str], List[str]]] = [
    (
        "governance-repair-manifest.v3.5.json",
        "governance-repair-manifest/v1",
        ["plan_version", "execution_order", "findings"],
    ),
    ("artifacts/status/TASK-1023.status.json", None, ["task_id", "state"]),
    ("artifacts/status/TASK-1024.status.json", None, ["task_id", "state"]),
    ("artifacts/status/TASK-1025.status.json", None, ["task_id", "state"]),
    (
        "artifacts/governance/quality-baseline.v3.5.json",
        "quality-baseline/v1",
        ["plan_version", "metrics", "source_template_pairs"],
    ),
    (
        "artifacts/governance/quality-gate-policy.v3.5.json",
        "quality-gate-policy/v1",
        ["gates", "rollout_phase"],
    ),
]


def run_qc_schema_001(repo_root: Path) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    for rel, expected_schema, required_keys in REQUIRED_JSON_TARGETS:
        path = repo_root / rel
        check: Dict[str, Any] = {
            "gate_id": "QC-SCHEMA-001",
            "target": rel,
            "evidence_ref": rel,
        }
        if not path.is_file():
            check["expected"] = "file_present"
            check["actual"] = "missing"
            check["status"] = "skipped_with_reason_code"
            check["reason_code"] = "file_not_present_yet"
            checks.append(check)
            continue
        try:
            data = load_json(path)
        except (json.JSONDecodeError, OSError) as e:
            check["expected"] = "valid_json"
            check["actual"] = "parse_error:" + type(e).__name__
            check["status"] = "fail"
            check["reason_code"] = "json_parse_error"
            checks.append(check)
            continue
        if expected_schema is not None:
            actual_schema = data.get("schema_version") if isinstance(data, dict) else None
            if actual_schema != expected_schema:
                check["expected"] = "schema_version=" + expected_schema
                check["actual"] = "schema_version=" + str(actual_schema)
                check["status"] = "fail"
                check["reason_code"] = "schema_version_mismatch"
                checks.append(check)
                continue
        missing_keys = [k for k in required_keys if not (isinstance(data, dict) and k in data)]
        if missing_keys:
            check["expected"] = "required_keys:" + ",".join(required_keys)
            check["actual"] = "missing:" + ",".join(missing_keys)
            check["status"] = "fail"
            check["reason_code"] = "missing_required_keys"
        else:
            check["expected"] = "required_keys_present:" + ",".join(required_keys)
            check["actual"] = "ok"
            check["status"] = "pass"
            check["reason_code"] = "schema_and_keys_ok"
        checks.append(check)
    return checks


# ---------------------------------------------------------------------------
# QC-IMPORT-001 import-time side-effect gate (subprocess; no __pycache__)
# ---------------------------------------------------------------------------

def run_qc_import_001(
    repo_root: Path, baseline: Dict[str, Any], policy: Dict[str, Any]
) -> List[Dict[str, Any]]:
    surface = baseline.get("import_side_effect_surface", []) or []
    gate_cfg = next(
        (g for g in policy.get("gates", []) if g.get("gate_id") == "QC-IMPORT-001"), {}
    )
    expected_clean = set(gate_cfg.get("expected_import_clean", []) or [])
    advisory_for_unlisted = bool(gate_cfg.get("first_cycle_advisory_for_unlisted_candidates", True))

    checks: List[Dict[str, Any]] = []
    for entry in surface:
        if not entry.get("candidate_for_import_side_effect_gate"):
            continue
        rel = entry.get("path", "")
        path = repo_root / rel
        check: Dict[str, Any] = {
            "gate_id": "QC-IMPORT-001",
            "target": rel,
            "expected": "import_clean_when_in_expected_clean_else_advisory",
            "evidence_ref": rel,
        }
        if not path.is_file():
            check["actual"] = "missing"
            check["status"] = "skipped_with_reason_code"
            check["reason_code"] = "file_not_found"
            checks.append(check)
            continue

        module_name = path.stem
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONUTF8"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        code = (
            "import sys\n"
            "sys.path.insert(0, " + repr(str(path.parent)) + ")\n"
            "__import__(" + repr(module_name) + ")\n"
        )
        try:
            r = subprocess.run(
                [sys.executable, "-S", "-B", "-c", code],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(repo_root),
            )
        except subprocess.TimeoutExpired:
            check["actual"] = "timeout_30s"
            check["status"] = "fail" if rel in expected_clean else "advisory"
            check["reason_code"] = "import_timeout"
            checks.append(check)
            continue

        out_text = r.stdout or ""
        err_text = r.stderr or ""
        if r.returncode != 0:
            tail = err_text.strip()[-200:]
            check["actual"] = "exit=" + str(r.returncode) + "; stderr_tail=" + tail
            if rel in expected_clean:
                check["status"] = "fail"
                check["reason_code"] = "import_error_when_expected_clean"
            elif advisory_for_unlisted:
                check["status"] = "advisory"
                check["reason_code"] = "first_cycle_observation_import_error"
            else:
                check["status"] = "fail"
                check["reason_code"] = "import_error"
        elif out_text or err_text:
            check["actual"] = (
                "stdout_len=" + str(len(out_text))
                + "; stderr_len=" + str(len(err_text))
            )
            if rel in expected_clean:
                check["status"] = "fail"
                check["reason_code"] = "import_emitted_output_when_expected_clean"
            elif advisory_for_unlisted:
                check["status"] = "advisory"
                check["reason_code"] = "first_cycle_observation_dirty_import"
            else:
                check["status"] = "fail"
                check["reason_code"] = "import_emitted_output"
        else:
            check["actual"] = "stdout_and_stderr_empty;exit=0"
            check["status"] = "pass"
            check["reason_code"] = "import_clean"
        checks.append(check)
    return checks


# ---------------------------------------------------------------------------
# QC-GOLDEN-001 golden CLI harness bootstrap (no execution)
# ---------------------------------------------------------------------------

def run_qc_golden_001(repo_root: Path, baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = baseline.get("golden_cli_candidates", []) or []
    checks: List[Dict[str, Any]] = []
    for c in candidates:
        cmd_id = c.get("command_id", "")
        cmd = c.get("command", "")
        capture_policy = c.get("capture_policy", "")
        check: Dict[str, Any] = {
            "gate_id": "QC-GOLDEN-001",
            "target": cmd_id,
            "expected": "capture_policy=post_task_evidence_only_and_no_execution",
            "actual": "command=" + cmd + "; capture_policy=" + str(capture_policy),
            "evidence_ref": cmd_id,
        }
        if capture_policy == "post_task_evidence_only":
            check["status"] = "skipped_with_reason_code"
            check["reason_code"] = "post_task_evidence_only_capture_deferred"
        else:
            check["status"] = "fail"
            check["reason_code"] = "unsafe_capture_policy:" + str(capture_policy)
        checks.append(check)
    return checks


# ---------------------------------------------------------------------------
# QC-RUFF-001 advisory only (do NOT invoke ruff)
# ---------------------------------------------------------------------------

def run_qc_ruff_001(repo_root: Path) -> List[Dict[str, Any]]:
    config_files = ["ruff.toml", ".ruff.toml", "pyproject.toml"]
    found = [name for name in config_files if (repo_root / name).is_file()]
    return [
        {
            "gate_id": "QC-RUFF-001",
            "target": "ruff_config",
            "expected": "advisory_only_in_v3.5.0_no_invocation",
            "actual": "config_files_found=" + ",".join(found) if found else "no_config_found",
            "status": "advisory",
            "reason_code": "advisory_only_in_v3.5.0",
            "evidence_ref": "ruff_config_search",
        }
    ]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all_gates(
    repo_root: Path,
    baseline: Dict[str, Any],
    policy: Dict[str, Any],
    today_iso: str,
) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    checks.extend(run_qc_sync_001(repo_root, baseline, policy, today_iso))
    checks.extend(run_qc_schema_001(repo_root))
    checks.extend(run_qc_import_001(repo_root, baseline, policy))
    checks.extend(run_qc_golden_001(repo_root, baseline))
    checks.extend(run_qc_ruff_001(repo_root))
    return checks


def overall_status(checks: List[Dict[str, Any]]) -> str:
    return "fail" if any(c.get("status") == "fail" for c in checks) else "pass"


def build_result(
    repo_root: Path,
    baseline_path: Path,
    policy_path: Path,
    checks: List[Dict[str, Any]],
    today_iso: str,
    self_check: bool,
) -> Dict[str, Any]:
    return {
        "schema_version": "quality-gate-result/v1",
        "task_id": "TASK-1025",
        "generated_at": today_iso,
        "self_check": self_check,
        "baseline_ref": str(baseline_path.relative_to(repo_root)).replace("\\", "/"),
        "policy_ref": str(policy_path.relative_to(repo_root)).replace("\\", "/"),
        "overall_status": overall_status(checks),
        "checks": checks,
        "limitations": [
            "Ruff is P1 advisory only and is not invoked.",
            "Golden CLI capture is post_task_evidence_only and deferred to a future task.",
            "Waiver discovery uses policy.waivers array; no global waiver registry in v3.5.0.",
            "Baseline-existing drift is allowed when sha256 unchanged from baseline.",
            "QC-IMPORT-001 first cycle treats unlisted candidates as advisory.",
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    init_streams()
    parser = argparse.ArgumentParser(
        description="v3.5.0 baseline-aware P0 quality gate runner (TASK-1025)"
    )
    parser.add_argument("--baseline", default=None, help="path to quality-baseline.v3.5.json")
    parser.add_argument("--policy", default=None, help="path to quality-gate-policy.v3.5.json")
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="dry-run; print result to stdout; do not write evidence file",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="optional evidence output path (only honored when --self-check is NOT set)",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = detect_repo_root()
    except RuntimeError as e:
        print(json.dumps({"error": "repo_root_detection_failed", "detail": str(e)}))
        return 2

    baseline_path = (
        Path(args.baseline) if args.baseline
        else repo_root / "artifacts" / "governance" / "quality-baseline.v3.5.json"
    )
    policy_path = (
        Path(args.policy) if args.policy
        else repo_root / "artifacts" / "governance" / "quality-gate-policy.v3.5.json"
    )

    if not baseline_path.is_file():
        print(json.dumps({"error": "baseline_not_found", "path": str(baseline_path)}))
        return 2
    if not policy_path.is_file():
        print(json.dumps({"error": "policy_not_found", "path": str(policy_path)}))
        return 2

    baseline = load_json(baseline_path)
    policy = load_json(policy_path)
    today_iso = now_taipei_iso()

    checks = run_all_gates(repo_root, baseline, policy, today_iso)
    result = build_result(repo_root, baseline_path, policy_path, checks, today_iso, args.self_check)

    if args.output and not args.self_check:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = repo_root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(json.dumps({"output_written": str(out_path), "overall_status": result["overall_status"]}))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["overall_status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
