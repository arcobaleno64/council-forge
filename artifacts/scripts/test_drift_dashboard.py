"""Unit tests for drift_dashboard.py — full-coverage, in-process, fixture-driven."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import drift_dashboard as dd


# --------------------------------------------------------------------------- #
# Fixtures: a mini template/ and assorted downstreams.
# --------------------------------------------------------------------------- #
def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def template_root(tmp_path: Path) -> Path:
    root = tmp_path / "template"
    _write(root / "docs" / "guide.md", "plain governance doc\n")
    _write(root / "CLAUDE.md", "# {{PROJECT_NAME}} orchestrator\n")  # placeholder
    _write(root / "AGENTS.md", "template agents guide\n")            # no placeholder
    _write(root / ".gitignore", "template-ignore\n")                 # no placeholder
    _write(root / "README.zh-TW.md", "zh readme\n")                  # optional
    _write(root / "LICENSE", "MIT\n")                                # optional
    _write(root / "artifacts" / "tasks" / "TASK-900.task.md", "seed\n")  # optional seed
    _write(root / ".github" / "workflows" / "security-scan.yml", "ci\n")  # optional workflow
    (root / "logo.bin").write_bytes(b"\x00\x01\x02\xff")             # binary
    return root


def _greenfield_in_sync(tmp_path: Path, template_root: Path) -> Path:
    """A downstream that copied the whole template verbatim (greenfield, in sync)."""
    root = tmp_path / "green"
    for tf in dd.iter_files(template_root):
        rel = tf.relative_to(template_root)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(tf.read_bytes())
    return root


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def test_is_optional_absent():
    assert dd.is_optional_absent("README.zh-TW.md")
    assert dd.is_optional_absent("LICENSE")
    assert dd.is_optional_absent(".github/workflows/workflow-guards.yml")
    assert dd.is_optional_absent("artifacts/tasks/TASK-900.task.md")
    assert dd.is_optional_absent("artifacts/decisions/TASK-951.decision.md")
    assert not dd.is_optional_absent("docs/guide.md")
    assert not dd.is_optional_absent("artifacts/tasks/TASK-1000.task.md")  # not a 9xx seed


def test_normalised_bytes_text_crlf(tmp_path: Path):
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"a\nb\n")
    crlf.write_bytes(b"a\r\nb\r\n")
    assert dd.normalised_bytes(lf) == dd.normalised_bytes(crlf)


def test_normalised_bytes_binary(tmp_path: Path):
    b = tmp_path / "x.bin"
    b.write_bytes(b"\x00\xff\r\n")
    # binary path: returned as-is (CRLF not normalised because not decodable utf-8)
    assert dd.normalised_bytes(b) == b"\x00\xff\r\n"


def test_template_has_placeholder(template_root: Path):
    assert dd.template_has_placeholder(template_root / "CLAUDE.md")
    assert not dd.template_has_placeholder(template_root / "AGENTS.md")
    assert not dd.template_has_placeholder(template_root / "logo.bin")  # binary -> False


# --------------------------------------------------------------------------- #
# classify_file — every branch
# --------------------------------------------------------------------------- #
def test_classify_file_missing_and_optional(template_root: Path, tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    # non-optional template file absent -> missing
    assert dd.classify_file(template_root / "docs" / "guide.md", empty / "docs" / "guide.md", "docs/guide.md", False) == dd.MISSING
    # optional absent
    assert dd.classify_file(template_root / "LICENSE", empty / "LICENSE", "LICENSE", False) == dd.OPTIONAL_ABSENT


def test_classify_file_instantiated_precedes_brownfield(template_root: Path):
    # CLAUDE.md has placeholder -> instantiated even when present + brownfield
    df = template_root / "CLAUDE.md"  # present, content has placeholder
    assert dd.classify_file(template_root / "CLAUDE.md", df, "CLAUDE.md", True) == dd.INSTANTIATED


def test_classify_file_brownfield_owned(template_root: Path, tmp_path: Path):
    own = tmp_path / "own_agents.md"
    own.write_text("project's own agents\n", encoding="utf-8")
    # AGENTS.md differs + brownfield -> brownfield-owned (not drifted)
    assert dd.classify_file(template_root / "AGENTS.md", own, "AGENTS.md", True) == dd.BROWNFIELD_OWNED
    # same file, greenfield -> drifted (project differs and not brownfield-owned)
    assert dd.classify_file(template_root / "AGENTS.md", own, "AGENTS.md", False) == dd.DRIFTED


def test_classify_file_in_sync_and_drifted(template_root: Path, tmp_path: Path):
    same = tmp_path / "same.md"
    same.write_text("plain governance doc\n", encoding="utf-8")
    assert dd.classify_file(template_root / "docs" / "guide.md", same, "docs/guide.md", False) == dd.IN_SYNC
    diff = tmp_path / "diff.md"
    diff.write_text("EDITED governance doc\n", encoding="utf-8")
    assert dd.classify_file(template_root / "docs" / "guide.md", diff, "docs/guide.md", False) == dd.DRIFTED


# --------------------------------------------------------------------------- #
# DownstreamReport
# --------------------------------------------------------------------------- #
def test_report_aggregates():
    r = dd.DownstreamReport(name="x", path="/x")
    r.add(dd.IN_SYNC, "a")
    r.add(dd.IN_SYNC, "b")
    r.add(dd.DRIFTED, "c")
    assert r.count(dd.IN_SYNC) == 2
    assert r.count(dd.MISSING) == 0
    assert r.owned_total == 3
    assert r.has_problems
    assert r.overall == "DRIFT DETECTED"
    clean = dd.DownstreamReport(name="y", path="/y")
    clean.add(dd.IN_SYNC, "a")
    assert not clean.has_problems
    assert clean.overall == "IN SYNC"


# --------------------------------------------------------------------------- #
# count_project_owned
# --------------------------------------------------------------------------- #
def test_count_project_owned_skips_ignored(tmp_path: Path):
    root = tmp_path / "ds"
    _write(root / "owned.txt", "x")
    _write(root / "src" / "app.cs", "y")
    _write(root / "node_modules" / "dep" / "index.js", "z")  # ignored dir
    _write(root / "CLAUDE.md", "owned-too")  # in template_rel -> not counted
    template_rel = frozenset({"CLAUDE.md"})
    assert dd.count_project_owned(root, template_rel) == 2  # owned.txt + src/app.cs


# --------------------------------------------------------------------------- #
# classify_downstream — greenfield (in sync) and brownfield
# --------------------------------------------------------------------------- #
def test_classify_downstream_greenfield_in_sync(template_root: Path, tmp_path: Path):
    ds = _greenfield_in_sync(tmp_path, template_root)
    report = dd.classify_downstream(template_root, ds, "green")
    assert not report.brownfield
    assert report.count(dd.DRIFTED) == 0
    assert report.count(dd.MISSING) == 0
    assert report.count(dd.IN_SYNC) >= 4  # guide, AGENTS, .gitignore, README.zh-TW, LICENSE, TASK seed, workflow, logo (non-placeholder)
    assert report.count(dd.INSTANTIATED) == 1  # CLAUDE.md
    assert report.overall == "IN SYNC"


def test_classify_downstream_brownfield(template_root: Path, tmp_path: Path):
    ds = tmp_path / "brown"
    (ds).mkdir()
    (ds / dd.BROWNFIELD_MARKER).write_text("brownfield\n", encoding="utf-8")
    # own AGENTS.md/.gitignore (differ from template) -> brownfield-owned
    _write(ds / "AGENTS.md", "PROJECT own agents\n")
    _write(ds / ".gitignore", "project-ignore\n")
    # in-sync governance doc + binary
    _write(ds / "docs" / "guide.md", "plain governance doc\n")
    (ds / "logo.bin").write_bytes((template_root / "logo.bin").read_bytes())
    # CLAUDE.md present (instantiated)
    _write(ds / "CLAUDE.md", "# MyProj orchestrator\n")
    # pruned optional files absent (README.zh-TW, LICENSE, TASK-900, workflow) -> optional-absent
    report = dd.classify_downstream(template_root, ds, "brown")
    assert report.brownfield
    assert report.count(dd.BROWNFIELD_OWNED) == 2  # AGENTS.md + .gitignore
    assert report.count(dd.OPTIONAL_ABSENT) == 4   # README.zh-TW, LICENSE, TASK-900, security-scan.yml
    assert report.count(dd.INSTANTIATED) == 1
    assert report.count(dd.IN_SYNC) == 2           # guide.md + logo.bin
    assert report.count(dd.DRIFTED) == 0
    assert not report.has_problems


def test_classify_downstream_detects_real_drift(template_root: Path, tmp_path: Path):
    ds = _greenfield_in_sync(tmp_path, template_root)
    (ds / "docs" / "guide.md").write_text("TAMPERED\n", encoding="utf-8")
    report = dd.classify_downstream(template_root, ds, "drifty")
    assert report.count(dd.DRIFTED) == 1
    assert "docs/guide.md" in report.verdicts[dd.DRIFTED]
    assert report.has_problems


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def test_render_markdown_lists_problems(template_root: Path, tmp_path: Path):
    ds = _greenfield_in_sync(tmp_path, template_root)
    (ds / "docs" / "guide.md").write_text("TAMPERED\n", encoding="utf-8")
    (ds / "AGENTS.md").unlink()  # non-brownfield -> missing (AGENTS.md not optional)
    report = dd.classify_downstream(template_root, ds, "drifty")
    md = dd.render_markdown([report])
    assert "drifty: DRIFT DETECTED" in md
    assert "### drifted (1)" in md
    assert "docs/guide.md" in md
    assert "### missing (1)" in md
    assert "AGENTS.md" in md


def test_render_markdown_clean(template_root: Path, tmp_path: Path):
    ds = _greenfield_in_sync(tmp_path, template_root)
    md = dd.render_markdown([dd.classify_downstream(template_root, ds, "green")])
    assert "IN SYNC" in md
    assert "### drifted" not in md  # no problem detail section


def test_build_json(template_root: Path, tmp_path: Path):
    ds = _greenfield_in_sync(tmp_path, template_root)
    payload = dd.build_json([dd.classify_downstream(template_root, ds, "green")])
    assert payload[0]["name"] == "green"
    assert payload[0]["overall"] == "IN SYNC"
    assert payload[0]["counts"][dd.INSTANTIATED] == 1
    assert payload[0]["drifted"] == []


# --------------------------------------------------------------------------- #
# CLI plumbing
# --------------------------------------------------------------------------- #
def test_parse_downstream_arg():
    assert dd.parse_downstream_arg("Foo=/path/to/foo") == ("Foo", Path("/path/to/foo"))
    name, path = dd.parse_downstream_arg("/bare/path")
    assert name == "path" and path == Path("/bare/path")
    # empty name before '=' falls back to basename
    assert dd.parse_downstream_arg("=/p/q")[0] == "q"


def test_default_template_root():
    root = dd.default_template_root()
    assert root.name == "template"


def test_run_requires_downstream(capsys):
    assert dd.run([]) == dd.EXIT_ERROR
    assert "at least one --downstream" in capsys.readouterr().err


def test_run_bad_template_root(tmp_path: Path):
    ds = tmp_path / "ds"
    ds.mkdir()
    rc = dd.run([f"--downstream=A={ds}", "--template-root", str(tmp_path / "nope")])
    assert rc == dd.EXIT_ERROR


def test_run_bad_downstream_path(template_root: Path, tmp_path: Path):
    rc = dd.run([f"--downstream=A={tmp_path / 'ghost'}", "--template-root", str(template_root)])
    assert rc == dd.EXIT_ERROR


def test_run_markdown_ok(template_root: Path, tmp_path: Path, capsys):
    ds = _greenfield_in_sync(tmp_path, template_root)
    rc = dd.run([f"--downstream=Green={ds}", "--template-root", str(template_root), "--fail-on-drift"])
    assert rc == dd.EXIT_OK
    assert "IN SYNC" in capsys.readouterr().out


def test_run_json_and_fail_on_drift(template_root: Path, tmp_path: Path, capsys):
    ds = _greenfield_in_sync(tmp_path, template_root)
    (ds / "docs" / "guide.md").write_text("TAMPERED\n", encoding="utf-8")
    rc = dd.run([f"--downstream=D={ds}", "--template-root", str(template_root), "--json", "--fail-on-drift"])
    assert rc == dd.EXIT_DRIFT
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["overall"] == "DRIFT DETECTED"


def test_run_drift_without_fail_flag_exits_ok(template_root: Path, tmp_path: Path):
    ds = _greenfield_in_sync(tmp_path, template_root)
    (ds / "docs" / "guide.md").write_text("TAMPERED\n", encoding="utf-8")
    rc = dd.run([f"--downstream=D={ds}", "--template-root", str(template_root)])
    assert rc == dd.EXIT_OK  # drift present but not gated
