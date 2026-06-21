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
