"""In-process unit tests for scaffold_downstream.py (TASK-1072).

Tests import the module and call its functions directly so that line coverage is
attributed to scaffold_downstream.py (subprocess children would not be counted).
A small synthetic mini-template fixture is used for speed; the real template/ +
real guard chain are exercised separately in the P3 throwaway dry-run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

import scaffold_downstream as sd


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _make_mini_template(root: Path) -> Path:
    """A minimal template/ tree exercising every substitution branch."""
    template = root / "template"
    (template / "docs" / "templates" / "adr").mkdir(parents=True)
    (template / "artifacts" / "scripts").mkdir(parents=True)
    # instantiation keys -> substituted
    (template / "README.md").write_text(
        "# {{PROJECT_NAME}}\nrepo={{REPO_NAME}} org={{ORG}} year={{YEAR}}\n",
        encoding="utf-8",
    )
    # per-task key -> must survive
    (template / "docs" / "templates" / "adr" / "TEMPLATE.md").write_text(
        "ADR for {{TASK_ID}} number {{NNNN}}\n", encoding="utf-8"
    )
    # test fixture file -> must NOT be substituted
    (template / "artifacts" / "scripts" / "test_guard_contract_validator.py").write_text(
        "FIXTURE = '{{PROJECT_NAME}}'\n", encoding="utf-8"
    )
    # binary file -> skipped by decode failure
    (template / "logo.png").write_bytes(b"\x89PNG\x00\xff\xfe{{PROJECT_NAME}}")
    return template


def _config(target: Path, template: Path, **overrides) -> sd.ScaffoldConfig:
    base = dict(
        target=target,
        template_root=template,
        project_name="Sentinel",
        repo_name="sentinel",
        project_summary="uptime monitor",
        owner="arco",
        upstream_org="arco",
        author="arco",
        year="2026",
        topics=None,
        git_init=False,
        force=False,
    )
    base.update(overrides)
    return sd.ScaffoldConfig(**base)


class _FakeCompleted:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


# --------------------------------------------------------------------------- #
# pure functions
# --------------------------------------------------------------------------- #
def test_build_substitution_map_has_all_keys(tmp_path):
    cfg = _config(tmp_path / "t", tmp_path / "tpl")
    mapping = sd.build_substitution_map(cfg)
    assert mapping["{{PROJECT_NAME}}"] == "Sentinel"
    assert mapping["{{REPO}}"] == "sentinel"
    assert set(mapping) == {f"{{{{{k}}}}}" for k in sd.INSTANTIATION_KEYS}


def test_is_text_file_true_and_false(tmp_path):
    text = tmp_path / "a.md"
    text.write_text("hi", encoding="utf-8")
    binary = tmp_path / "a.png"
    binary.write_bytes(b"\xff\xfe\x00")
    assert sd.is_text_file(text) is True
    assert sd.is_text_file(binary) is False


def test_should_substitute(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("hi", encoding="utf-8")
    testpy = tmp_path / "test_x.py"
    testpy.write_text("hi", encoding="utf-8")
    binary = tmp_path / "x.png"
    binary.write_bytes(b"\xff\xfe")
    assert sd.should_substitute(md) is True
    assert sd.should_substitute(testpy) is False
    assert sd.should_substitute(binary) is False


def test_substitute_text_keeps_per_task_keys():
    out = sd.substitute_text(
        "{{PROJECT_NAME}} {{TASK_ID}}", {"{{PROJECT_NAME}}": "S"}
    )
    assert out == "S {{TASK_ID}}"


def test_find_leftover_instantiation_keys():
    assert sd.find_leftover_instantiation_keys("clean text") == []
    assert sd.find_leftover_instantiation_keys("{{ORG}} {{TASK_ID}}") == ["ORG"]


# --------------------------------------------------------------------------- #
# filesystem helpers
# --------------------------------------------------------------------------- #
def test_copy_template_and_refuse_nonempty(tmp_path):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    count = sd.copy_template(template, target, force=False)
    assert count >= 4
    assert (target / "README.md").exists()
    # non-empty without force -> raises
    with pytest.raises(FileExistsError):
        sd.copy_template(template, target, force=False)
    # force -> overwrite
    count2 = sd.copy_template(template, target, force=True)
    assert count2 == count


def test_copy_template_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        sd.copy_template(tmp_path / "nope", tmp_path / "out", force=False)


def test_apply_substitutions_scopes_correctly(tmp_path):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    sd.copy_template(template, target, force=False)
    cfg = _config(target, template)
    mapping = sd.build_substitution_map(cfg)
    substituted, leftovers = sd.apply_substitutions(target, mapping)
    assert substituted >= 1
    assert leftovers == {}
    assert "Sentinel" in (target / "README.md").read_text(encoding="utf-8")
    # per-task key survives
    assert "{{TASK_ID}}" in (target / "docs/templates/adr/TEMPLATE.md").read_text(encoding="utf-8")
    # test fixture file is untouched
    assert "{{PROJECT_NAME}}" in (
        target / "artifacts/scripts/test_guard_contract_validator.py"
    ).read_text(encoding="utf-8")


def test_apply_substitutions_reports_leftovers(tmp_path):
    target = tmp_path / "out"
    (target / "sub").mkdir(parents=True)
    (target / "sub" / "facts.md").write_text("owner={{ORG}}\n", encoding="utf-8")
    # map without ORG -> leftover remains
    substituted, leftovers = sd.apply_substitutions(target, {"{{PROJECT_NAME}}": "S"})
    assert leftovers == {"sub/facts.md": ["ORG"]}


# --------------------------------------------------------------------------- #
# subprocess-backed helpers (call sites covered, children faked)
# --------------------------------------------------------------------------- #
def test_run_repository_profile_invokes_tool(tmp_path, monkeypatch):
    recorded = {}

    def fake_run(cmd, *args, **kwargs):
        recorded["cmd"] = cmd
        return _FakeCompleted(0)

    monkeypatch.setattr(sd.subprocess, "run", fake_run)
    cfg = _config(tmp_path / "t", tmp_path / "tpl", topics="a,b")
    code = sd.run_repository_profile(cfg)
    assert code == 0
    assert "--project-name" in recorded["cmd"]
    assert "--topics" in recorded["cmd"]


def test_run_downstream_guards_runs_both(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return _FakeCompleted(0)

    monkeypatch.setattr(sd.subprocess, "run", fake_run)
    results = sd.run_downstream_guards(tmp_path / "t")
    assert results == {"contract": 0, "prompt_regression": 0}
    assert len(calls) == 2


def test_git_init(tmp_path, monkeypatch):
    monkeypatch.setattr(sd.subprocess, "run", lambda cmd, *a, **k: _FakeCompleted(0))
    assert sd.git_init(tmp_path) == 0


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def test_scaffold_happy_path(tmp_path, monkeypatch):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    monkeypatch.setattr(sd, "run_repository_profile", lambda config: 0)
    monkeypatch.setattr(sd, "run_downstream_guards", lambda t: {"contract": 0, "prompt_regression": 0})
    cfg = _config(target, template, git_init=True)
    monkeypatch.setattr(sd, "git_init", lambda t: 0)
    result = sd.scaffold(cfg)
    assert result.has_leftovers is False
    assert result.guards_ok is True
    assert not (target / sd.SOURCE_REPO_SENTINEL).exists()


def test_scaffold_removes_stray_sentinel(tmp_path, monkeypatch):
    template = _make_mini_template(tmp_path)
    # template defensively carries a stray source-repo sentinel; scaffold must strip it
    (template / sd.SOURCE_REPO_SENTINEL).write_text("x", encoding="utf-8")
    target = tmp_path / "out"
    monkeypatch.setattr(sd, "run_repository_profile", lambda config: 0)
    monkeypatch.setattr(sd, "run_downstream_guards", lambda t: {"contract": 0, "prompt_regression": 0})
    result = sd.scaffold(_config(target, template))
    assert not (target / sd.SOURCE_REPO_SENTINEL).exists()
    assert result.has_leftovers is False


def test_dry_run_preview_counts(tmp_path):
    template = _make_mini_template(tmp_path)
    cfg = _config(tmp_path / "out", template)
    mapping = sd.build_substitution_map(cfg)
    total, would_sub = sd.dry_run_preview(template, mapping)
    assert total >= 4
    assert would_sub >= 1


def test_default_template_root_is_path():
    assert isinstance(sd.default_template_root(), Path)


# --------------------------------------------------------------------------- #
# argument resolution
# --------------------------------------------------------------------------- #
def test_config_from_args_default_chains():
    args = argparse.Namespace(
        target="t", project_name="P", repo_name="r", project_summary="s",
        owner="", upstream_org="up", author="", year="", topics=None,
        template_root="", git_init=False, force=False,
    )
    cfg = sd.config_from_args(args)
    assert cfg.owner == "up"  # owner falls back to upstream_org
    assert cfg.author == "up"  # author falls back to owner
    assert cfg.year != ""  # year defaults to current year


# --------------------------------------------------------------------------- #
# run() entrypoint branches
# --------------------------------------------------------------------------- #
def _base_argv(target: Path, template: Path):
    return [
        "--target", str(target),
        "--project-name", "Sentinel",
        "--repo-name", "sentinel",
        "--project-summary", "uptime monitor",
        "--owner", "arco",
        "--template-root", str(template),
    ]


def test_run_dry_run(tmp_path, capsys):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    code = sd.run(_base_argv(target, template) + ["--dry-run"])
    assert code == sd.EXIT_OK
    assert not target.exists()
    assert "DRY-RUN" in capsys.readouterr().out


def test_run_refuses_nonempty_target(tmp_path):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    target.mkdir()
    (target / "x").write_text("existing", encoding="utf-8")
    code = sd.run(_base_argv(target, template))
    assert code == sd.EXIT_TARGET_NOT_EMPTY


def test_run_happy_path(tmp_path, monkeypatch):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    monkeypatch.setattr(sd, "run_repository_profile", lambda config: 0)
    monkeypatch.setattr(sd, "run_downstream_guards", lambda t: {"contract": 0, "prompt_regression": 0})
    code = sd.run(_base_argv(target, template))
    assert code == sd.EXIT_OK
    assert (target / "README.md").exists()


def test_run_leftover_exit3(tmp_path, monkeypatch):
    template = _make_mini_template(tmp_path)
    # add an unmapped instantiation key by removing it from the map via a doctored template
    (template / "extra.md").write_text("x={{AUTHOR}}\n", encoding="utf-8")
    target = tmp_path / "out"
    monkeypatch.setattr(sd, "run_repository_profile", lambda config: 0)
    monkeypatch.setattr(sd, "run_downstream_guards", lambda t: {"contract": 0})
    # force AUTHOR to remain by monkeypatching build_substitution_map to omit AUTHOR
    real_map = sd.build_substitution_map

    def partial_map(cfg):
        m = real_map(cfg)
        m["{{AUTHOR}}"] = "{{AUTHOR}}"  # self-map -> remains -> leftover
        return m

    monkeypatch.setattr(sd, "build_substitution_map", partial_map)
    code = sd.run(_base_argv(target, template))
    assert code == sd.EXIT_LEFTOVER_PLACEHOLDER


def test_run_guard_fail_exit4(tmp_path, monkeypatch):
    template = _make_mini_template(tmp_path)
    target = tmp_path / "out"
    monkeypatch.setattr(sd, "run_repository_profile", lambda config: 0)
    monkeypatch.setattr(sd, "run_downstream_guards", lambda t: {"contract": 1})
    code = sd.run(_base_argv(target, template))
    assert code == sd.EXIT_GUARD_FAILED
