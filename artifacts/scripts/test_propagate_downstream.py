"""Unit tests for propagate_downstream.py — full-coverage, in-process, fixture-driven."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import propagate_downstream as pp


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def template_root(tmp_path: Path) -> Path:
    root = tmp_path / "template"
    _write(root / "artifacts" / "scripts" / "guard.py", "GUARD v2\n")  # owned, no placeholder
    _write(root / "docs" / "spec.md", "spec v2\n")                     # owned, no placeholder
    _write(root / "CLAUDE.md", "# {{PROJECT_NAME}}\n")                 # placeholder
    _write(root / "LICENSE", "MIT\n")                                  # optional
    _write(root / "artifacts" / "tasks" / "TASK-900.task.md", "seed\n")  # optional seed
    return root


def _brownfield_drifted(tmp_path: Path) -> Path:
    """A brownfield downstream with guard.py drifted, spec.md in sync, CLAUDE own,
    LICENSE + seed pruned (optional-absent)."""
    ds = tmp_path / "ds"
    _write(ds / ".council-forge-brownfield", "bf\n")
    _write(ds / "artifacts" / "scripts" / "guard.py", "GUARD v1 OLD\n")  # drifted
    _write(ds / "docs" / "spec.md", "spec v2\n")                          # in sync
    _write(ds / "CLAUDE.md", "# MyProj\n")                                # instantiated (template has placeholder)
    return ds


# --------------------------------------------------------------------------- #
def test_plan_refresh_only_drifted(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    assert plan.refresh == ["artifacts/scripts/guard.py"]
    assert plan.add == []
    assert plan.skipped_placeholder == []
    assert plan.change_count == 1


def test_plan_add_missing_skips_placeholder(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    # remove guard.py (now a missing non-placeholder owned file) and CLAUDE (missing placeholder)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    (ds / "CLAUDE.md").unlink()
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=True)
    assert "artifacts/scripts/guard.py" in plan.add
    assert "CLAUDE.md" in plan.skipped_placeholder
    # LICENSE / TASK-900 are optional-absent -> never added
    assert "LICENSE" not in plan.add
    assert "artifacts/tasks/TASK-900.task.md" not in plan.add


def test_plan_no_add_missing_ignores_missing(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    assert plan.add == []  # missing not added without --add-missing


def test_apply_refreshes_and_preserves(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    pp.apply_plan(template_root, ds, plan)
    assert plan.applied
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v2\n"  # refreshed
    assert (ds / "CLAUDE.md").read_text(encoding="utf-8") == "# MyProj\n"  # untouched
    assert not (ds / "LICENSE").exists()  # pruned, not re-added
    assert not (ds / "artifacts" / "tasks" / "TASK-900.task.md").exists()  # seed not re-added
    # idempotent: re-plan after apply -> nothing
    again = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    assert again.refresh == []


def test_apply_add_missing_creates_parent(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=True)
    pp.apply_plan(template_root, ds, plan)
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v2\n"


# --------------------------------------------------------------------------- #
def test_render_markdown_dry_run_and_apply(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    md = pp.render_markdown([plan], apply=False)
    assert "Would change (dry-run)" in md
    assert "### refresh (1)" in md
    assert "artifacts/scripts/guard.py" in md
    md2 = pp.render_markdown([plan], apply=True)
    assert "Applied" in md2


def test_render_markdown_no_changes(template_root: Path, tmp_path: Path):
    ds = tmp_path / "clean"
    _write(ds / "artifacts" / "scripts" / "guard.py", "GUARD v2\n")
    _write(ds / "docs" / "spec.md", "spec v2\n")
    plan = pp.plan_propagation(template_root, ds, "clean", add_missing=False)
    md = pp.render_markdown([plan], apply=False)
    assert "## clean" not in md  # no detail section when nothing to do


def test_build_json(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    payload = pp.build_json([plan], apply=False)
    assert payload["mode"] == "dry-run"
    assert payload["downstreams"][0]["refresh"] == ["artifacts/scripts/guard.py"]


# --------------------------------------------------------------------------- #
def test_run_requires_downstream(capsys):
    assert pp.run([]) == pp.EXIT_ERROR
    assert "at least one --downstream" in capsys.readouterr().err


def test_run_bad_template_root(tmp_path: Path):
    ds = tmp_path / "ds"
    ds.mkdir()
    assert pp.run([f"--downstream=A={ds}", "--template-root", str(tmp_path / "nope")]) == pp.EXIT_ERROR


def test_run_bad_downstream_path(template_root: Path, tmp_path: Path):
    assert pp.run([f"--downstream=A={tmp_path/'ghost'}", "--template-root", str(template_root)]) == pp.EXIT_ERROR


def test_run_dry_run_markdown(template_root: Path, tmp_path: Path, capsys):
    ds = _brownfield_drifted(tmp_path)
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root)])
    assert rc == pp.EXIT_OK
    out = capsys.readouterr().out
    assert "dry-run" in out and "guard.py" in out
    # dry-run must NOT mutate
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v1 OLD\n"


def test_run_apply_json(template_root: Path, tmp_path: Path, capsys):
    ds = _brownfield_drifted(tmp_path)
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--apply", "--json"])
    assert rc == pp.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "apply"
    assert payload["downstreams"][0]["applied"] is True
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v2\n"


def test_run_add_missing(template_root: Path, tmp_path: Path, capsys):
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--add-missing", "--apply"])
    assert rc == pp.EXIT_OK
    assert (ds / "artifacts" / "scripts" / "guard.py").exists()
