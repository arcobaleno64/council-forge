"""Tests for the repo-root detection of the quality-gate runner scripts.

TASK-1100: both ``run_quality_gates.py`` and ``run_precommit_check.py`` previously
keyed ``detect_repo_root()`` on a marker file
(``council-forge-governance-repair-plan-v3.5.md``) that does not exist and was never
tracked in git, so their bare CLI always raised ``repo_root_detection_failed``. The
marker was replaced with the canonical source sentinel ``.council-forge-source-repo``.
These tests lock the detector (positive + negative) and assert the CLI no longer fails
detection. Root-only test (the runner scripts are source-only by their ``template/``
condition); not shipped to ``template/``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import run_precommit_check as rpc  # noqa: E402
import run_quality_gates as rqg  # noqa: E402


def test_run_quality_gates_detect_repo_root_returns_source_root() -> None:
    assert rqg.detect_repo_root() == REPO_ROOT


def test_run_precommit_check_detect_repo_root_returns_source_root() -> None:
    assert rpc.detect_repo_root() == REPO_ROOT


def test_run_quality_gates_detect_repo_root_raises_without_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No ancestor of a fresh tmp path carries the source markers -> contract preserved.
    monkeypatch.setattr(rqg, "SCRIPT_PATH", tmp_path / "a" / "b" / "fake.py")
    with pytest.raises(RuntimeError, match="Unable to detect repo root"):
        rqg.detect_repo_root()


def test_run_precommit_check_detect_repo_root_raises_without_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rpc, "SCRIPT_PATH", tmp_path / "a" / "b" / "fake.py")
    with pytest.raises(RuntimeError, match="Unable to detect repo root"):
        rpc.detect_repo_root()


def test_run_quality_gates_cli_self_check_does_not_fail_detection() -> None:
    # The bare CLI must reach repo-root detection successfully. The downstream QC
    # exit code (0 clean / 3 findings) is gate behaviour, not part of this fix; the
    # only assertion is that detection no longer fails.
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run_quality_gates.py"), "--self-check"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined = f"{result.stdout}\n{result.stderr}"
    assert "repo_root_detection_failed" not in combined
    assert "Unable to detect repo root" not in combined


# --- TASK-1101: QC-SYNC-001 source-only exemption (Pass 2) ---------------------
# Pass 2 must treat a post-baseline missing_template .py as a FAILURE only when the
# file is a must-sync file (in EXACT_SYNC_FILES); deliberately source-only files
# (no twin expected) must PASS. Detection of genuine must-sync drift must NOT weaken.

_QC_EMPTY_BASELINE = {"source_template_pairs": []}  # empty -> everything is a post-baseline pair
_QC_EMPTY_POLICY = {"waivers": []}
_QC_TODAY = "2026-06-21T00:00:00+08:00"


def _qc_make_repo(tmp_path: Path, name: str, source: str = "x = 1\n", template=None) -> Path:
    src_dir = tmp_path / "artifacts" / "scripts"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / name).write_text(source, encoding="utf-8")
    if template is not None:
        tpl_dir = tmp_path / "template" / "artifacts" / "scripts"
        tpl_dir.mkdir(parents=True, exist_ok=True)
        (tpl_dir / name).write_text(template, encoding="utf-8")
    return tmp_path


def _qc_find(checks, target):
    return next((c for c in checks if c.get("target") == target), None)


def test_qc_sync_001_post_baseline_source_only_passes(tmp_path: Path) -> None:
    # source-only file, no twin, NOT in the real EXACT_SYNC_FILES -> exempted (pass).
    repo = _qc_make_repo(tmp_path, "task_1101_src_only.py")
    checks = rqg.run_qc_sync_001(repo, _QC_EMPTY_BASELINE, _QC_EMPTY_POLICY, _QC_TODAY)
    c = _qc_find(checks, "artifacts/scripts/task_1101_src_only.py")
    assert c is not None
    assert c["status"] == "pass"
    assert c["reason_code"] == "post_baseline_source_only_no_twin_expected"


def test_qc_sync_001_must_sync_missing_twin_still_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A file that IS in the must-sync authority but lacks its twin must STILL fail
    # (non-weakening guarantee). Inject a synthetic must-sync path.
    monkeypatch.setattr(rqg, "EXACT_SYNC_FILES", ["artifacts/scripts/task_1101_must_sync.py"])
    repo = _qc_make_repo(tmp_path, "task_1101_must_sync.py")  # source only, no twin
    checks = rqg.run_qc_sync_001(repo, _QC_EMPTY_BASELINE, _QC_EMPTY_POLICY, _QC_TODAY)
    c = _qc_find(checks, "artifacts/scripts/task_1101_must_sync.py")
    assert c is not None
    assert c["status"] == "fail"
    assert c["reason_code"] == "post_baseline_new_pair_missing_template"


def test_qc_sync_001_post_baseline_drift_still_fails(tmp_path: Path) -> None:
    # both sides present but different -> drift -> still fail (exemption is missing_template-only).
    repo = _qc_make_repo(tmp_path, "task_1101_drift.py", source="a = 1\n", template="a = 2\n")
    checks = rqg.run_qc_sync_001(repo, _QC_EMPTY_BASELINE, _QC_EMPTY_POLICY, _QC_TODAY)
    c = _qc_find(checks, "artifacts/scripts/task_1101_drift.py")
    assert c is not None
    assert c["status"] == "fail"
    assert c["reason_code"] == "post_baseline_new_pair_drift"
