"""Unit tests for propagate_downstream.py — full-coverage, in-process, fixture-driven.

Covers the P8-D2 release-integrity safety model: published-manifest preflight, durable
snapshot marker (fail-closed ownership), per-file atomic copy, and transactional
preflight-before-any-write (no partial application from a detectable cause).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import propagate_downstream as pp
import snapshot_manifest as sm

MARKER = Path(".council-forge") / "release-snapshot.json"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def publish_manifest(template_root: Path) -> str:
    """Generate + publish the manifest at <repo>/.well-known/release-manifest.json. Returns root."""
    manifest = sm.compute_manifest(template_root)
    out = template_root.parent / pp.PUBLISHED_MANIFEST_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    sm.write_manifest(str(out), manifest)
    return manifest["root"]


@pytest.fixture()
def template_root(tmp_path: Path) -> Path:
    root = tmp_path / "template"
    _write(root / "artifacts" / "scripts" / "guard.py", "GUARD v2\n")  # owned, no placeholder
    _write(root / "docs" / "spec.md", "spec v2\n")                     # owned, no placeholder
    _write(root / "CLAUDE.md", "# {{PROJECT_NAME}}\n")                 # placeholder
    _write(root / "LICENSE", "MIT\n")                                  # optional
    _write(root / "artifacts" / "tasks" / "TASK-900.task.md", "seed\n")  # optional seed
    return root


def _brownfield_drifted(tmp_path: Path, name: str = "ds") -> Path:
    """A brownfield downstream with guard.py drifted, spec.md in sync, CLAUDE own."""
    ds = tmp_path / name
    _write(ds / ".council-forge-brownfield", "bf\n")
    _write(ds / "artifacts" / "scripts" / "guard.py", "GUARD v1 OLD\n")  # drifted
    _write(ds / "docs" / "spec.md", "spec v2\n")                          # in sync
    _write(ds / "CLAUDE.md", "# MyProj\n")                                # instantiated
    return ds


# --- planning (unchanged behaviour) -------------------------------------------------------
def test_plan_refresh_only_drifted(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    assert plan.refresh == ["artifacts/scripts/guard.py"]
    assert plan.add == []
    assert plan.skipped_placeholder == []
    assert plan.change_count == 1


def test_plan_add_missing_skips_placeholder(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    (ds / "CLAUDE.md").unlink()
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=True)
    assert "artifacts/scripts/guard.py" in plan.add
    assert "CLAUDE.md" in plan.skipped_placeholder
    assert "LICENSE" not in plan.add
    assert "artifacts/tasks/TASK-900.task.md" not in plan.add


def test_plan_no_add_missing_ignores_missing(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    assert plan.add == []


# --- apply_plan (per-file atomic) ---------------------------------------------------------
def test_apply_refreshes_and_preserves(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    pp.apply_plan(template_root, ds, plan)
    assert plan.applied
    assert plan.propagated == [{"path": "artifacts/scripts/guard.py", "sha256": sm.sha256_file(template_root / "artifacts/scripts/guard.py")}]
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v2\n"
    assert (ds / "CLAUDE.md").read_text(encoding="utf-8") == "# MyProj\n"
    assert not (ds / "LICENSE").exists()
    again = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    assert again.refresh == []


def test_apply_add_missing_creates_parent(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=True)
    pp.apply_plan(template_root, ds, plan)
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v2\n"


# --- atomic helpers -----------------------------------------------------------------------
def test_atomic_copy(tmp_path: Path):
    src = tmp_path / "s"
    src.write_text("data", encoding="utf-8")
    dst = tmp_path / "sub" / "d"
    pp.atomic_copy(src, dst)
    assert dst.read_text(encoding="utf-8") == "data"
    assert not (dst.parent / (dst.name + ".cf-tmp")).exists()


def test_atomic_copy_cleans_temp_on_replace_failure(tmp_path: Path):
    src = tmp_path / "s"
    src.write_text("data", encoding="utf-8")
    dst = tmp_path / "existingdir"
    dst.mkdir()
    (dst / "child").write_text("x", encoding="utf-8")  # non-empty -> os.replace fails
    with pytest.raises(OSError):
        pp.atomic_copy(src, dst)
    assert not (tmp_path / "existingdir.cf-tmp").exists()  # temp cleaned up


def test_atomic_write_text(tmp_path: Path):
    dst = tmp_path / "sub" / "f"
    pp.atomic_write_text(dst, "hello")
    assert dst.read_text(encoding="utf-8") == "hello"


def test_atomic_write_text_cleans_temp_on_replace_failure(tmp_path: Path):
    dst = tmp_path / "existingdir"
    dst.mkdir()
    (dst / "child").write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        pp.atomic_write_text(dst, "hello")
    assert not (tmp_path / "existingdir.cf-tmp").exists()


# --- marker ownership (CM1) ---------------------------------------------------------------
def test_check_marker_absent(tmp_path: Path):
    assert pp.check_marker_ownership(tmp_path) is None


def test_check_marker_valid(tmp_path: Path):
    _write(tmp_path / MARKER, json.dumps({"schema": pp.MARKER_SCHEMA}))
    assert pp.check_marker_ownership(tmp_path) is None


def test_check_marker_malformed(tmp_path: Path):
    _write(tmp_path / MARKER, "{bad")
    assert "malformed" in pp.check_marker_ownership(tmp_path)


def test_check_marker_foreign(tmp_path: Path):
    _write(tmp_path / MARKER, json.dumps({"schema": "someone-else"}))
    assert "not a council-forge" in pp.check_marker_ownership(tmp_path)


# --- preflight_manifest -------------------------------------------------------------------
def test_preflight_manifest_ok(template_root: Path):
    root = publish_manifest(template_root)
    error, released = pp.preflight_manifest(template_root)
    assert error is None and released == root


def test_preflight_manifest_missing(template_root: Path):
    error, released = pp.preflight_manifest(template_root)
    assert "not found" in error and released is None


def test_preflight_manifest_mismatch(template_root: Path):
    publish_manifest(template_root)
    (template_root / "docs" / "spec.md").write_text("spec v3 CHANGED\n", encoding="utf-8")
    error, released = pp.preflight_manifest(template_root)
    assert "does not match" in error


def test_preflight_manifest_malformed(template_root: Path):
    out = template_root.parent / pp.PUBLISHED_MANIFEST_REL
    _write(out, "{bad")
    error, released = pp.preflight_manifest(template_root)
    assert "cannot read published manifest" in error


def test_preflight_manifest_non_dict(template_root: Path):
    out = template_root.parent / pp.PUBLISHED_MANIFEST_REL
    _write(out, "[]")
    error, released = pp.preflight_manifest(template_root)
    assert "not a JSON object" in error


# --- render / build (unchanged + released root) -------------------------------------------
def test_render_markdown_dry_run_and_apply(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    md = pp.render_markdown([plan], apply=False)
    assert "Would change (dry-run)" in md
    assert "### refresh (1)" in md
    md2 = pp.render_markdown([plan], apply=True, released_root="abc123")
    assert "Applied" in md2 and "abc123" in md2


def test_render_markdown_no_changes(template_root: Path, tmp_path: Path):
    ds = tmp_path / "clean"
    _write(ds / "artifacts" / "scripts" / "guard.py", "GUARD v2\n")
    _write(ds / "docs" / "spec.md", "spec v2\n")
    plan = pp.plan_propagation(template_root, ds, "clean", add_missing=False)
    md = pp.render_markdown([plan], apply=False)
    assert "## clean" not in md


def test_build_json(template_root: Path, tmp_path: Path):
    ds = _brownfield_drifted(tmp_path)
    plan = pp.plan_propagation(template_root, ds, "ds", add_missing=False)
    payload = pp.build_json([plan], apply=False)
    assert payload["mode"] == "dry-run"
    assert payload["released_snapshot_root"] is None
    assert payload["downstreams"][0]["refresh"] == ["artifacts/scripts/guard.py"]


# --- run: usage / dry-run -----------------------------------------------------------------
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
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v1 OLD\n"


# --- run: apply (release-integrity) -------------------------------------------------------
def test_run_apply_json(template_root: Path, tmp_path: Path, capsys):
    root = publish_manifest(template_root)
    ds = _brownfield_drifted(tmp_path)
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--apply", "--json"])
    assert rc == pp.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "apply"
    assert payload["released_snapshot_root"] == root
    assert payload["downstreams"][0]["applied"] is True
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v2\n"


def test_run_add_missing(template_root: Path, tmp_path: Path):
    publish_manifest(template_root)
    ds = _brownfield_drifted(tmp_path)
    (ds / "artifacts" / "scripts" / "guard.py").unlink()
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--add-missing", "--apply"])
    assert rc == pp.EXIT_OK
    assert (ds / "artifacts" / "scripts" / "guard.py").exists()


def test_run_apply_writes_durable_marker(template_root: Path, tmp_path: Path):
    root = publish_manifest(template_root)
    ds = _brownfield_drifted(tmp_path)
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--apply"])
    assert rc == pp.EXIT_OK
    marker = json.loads((ds / MARKER).read_text(encoding="utf-8"))
    assert marker["schema"] == pp.MARKER_SCHEMA
    assert marker["released_snapshot_root"] == root
    assert {entry["path"] for entry in marker["propagated"]} == {"artifacts/scripts/guard.py"}


def test_run_apply_updates_valid_existing_marker(template_root: Path, tmp_path: Path):
    publish_manifest(template_root)
    ds = _brownfield_drifted(tmp_path)
    _write(ds / MARKER, json.dumps(
        {"schema": pp.MARKER_SCHEMA, "released_snapshot_root": "old", "algorithm": "sha256", "propagated": []}
    ))
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--apply"])
    assert rc == pp.EXIT_OK
    marker = json.loads((ds / MARKER).read_text(encoding="utf-8"))
    assert marker["released_snapshot_root"] != "old"  # updated in place


def test_run_apply_no_manifest_aborts_no_partial(template_root: Path, tmp_path: Path, capsys):
    ds = _brownfield_drifted(tmp_path)  # no manifest published
    rc = pp.run([f"--downstream=Demo={ds}", "--template-root", str(template_root), "--apply"])
    assert rc == pp.EXIT_ERROR
    assert "snapshot_manifest.py generate" in capsys.readouterr().err
    # preflight failed before any write -> drifted file UNCHANGED (no partial application)
    assert (ds / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v1 OLD\n"
    assert not (ds / MARKER).exists()


def test_run_apply_aborts_before_any_write_on_foreign_marker(template_root: Path, tmp_path: Path, capsys):
    """Transactional: a foreign marker on the SECOND target aborts before the FIRST is touched."""
    publish_manifest(template_root)
    ds_a = _brownfield_drifted(tmp_path, name="dsa")
    ds_b = _brownfield_drifted(tmp_path, name="dsb")
    _write(ds_b / MARKER, json.dumps({"schema": "someone-else-owns-this"}))  # foreign
    rc = pp.run([
        f"--downstream=A={ds_a}", f"--downstream=B={ds_b}",
        "--template-root", str(template_root), "--apply",
    ])
    assert rc == pp.EXIT_ERROR
    assert "refusing to overwrite" in capsys.readouterr().err
    # A was preflighted before any apply -> A's drifted file is UNCHANGED (no partial mutation)
    assert (ds_a / "artifacts" / "scripts" / "guard.py").read_text(encoding="utf-8") == "GUARD v1 OLD\n"
    assert not (ds_a / MARKER).exists()


def test_no_skip_manifest_check_flag():
    """The --skip-manifest-check escape hatch must not exist (zero bypass)."""
    with pytest.raises(SystemExit):
        pp.parse_args(["--downstream=A=/x", "--apply", "--skip-manifest-check"])
