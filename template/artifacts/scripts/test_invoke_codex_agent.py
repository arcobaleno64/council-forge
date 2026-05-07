from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


WRAPPER = Path(__file__).resolve().parent / "Invoke-CodexAgent.ps1"


def _build_lifecycle_inspector_exe(tmp_path: Path, command_name: str) -> tuple[Path, str]:
    directory = tmp_path / f"inspector-{command_name}"
    directory.mkdir()
    script_path = directory / f"{command_name}_inspector.py"
    marker_name = f"{command_name}_lifecycle_marker.txt"
    script_path.write_text(
        textwrap.dedent(f"""
        from __future__ import annotations
        import sys
        from pathlib import Path
        cwd = Path.cwd()
        task_path = cwd / "artifacts" / "tasks" / "TASK-fake.task.md"
        plan_path = cwd / "artifacts" / "plans" / "TASK-fake.plan.md"
        marker = cwd / "{marker_name}"
        lines = [
            f"task_visible={{int(task_path.exists())}}",
            f"plan_visible={{int(plan_path.exists())}}",
        ]
        marker.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        sys.exit(0)
        """).strip(),
        encoding="utf-8",
    )
    if os.name == "nt":
        exe_path = directory / f"{command_name}.cmd"
        exe_path.write_text(
            f'@echo off\r\n"{sys.executable}" "{script_path}" %*\r\nexit /b %ERRORLEVEL%\r\n',
            encoding="utf-8",
        )
    else:
        exe_path = directory / command_name
        exe_path.write_text(
            f'#!/usr/bin/env sh\nexec "{sys.executable}" "{script_path}" "$@"\n',
            encoding="utf-8",
        )
        exe_path.chmod(0o755)
    return exe_path, marker_name


def _seed_lifecycle_artifacts(repo: Path) -> None:
    (repo / "artifacts" / "tasks").mkdir(parents=True, exist_ok=True)
    (repo / "artifacts" / "plans").mkdir(parents=True, exist_ok=True)
    (repo / "artifacts" / "tasks" / "TASK-fake.task.md").write_text("fake task\n", encoding="utf-8")
    (repo / "artifacts" / "plans" / "TASK-fake.plan.md").write_text("fake plan\n", encoding="utf-8")


def _model_arg(calls: list[dict]) -> str:
    args = calls[-1]["args"]
    return args[args.index("-m") + 1]


def test_task_scale_maps_legacy_values_to_v2_model_ladder(fake_codex_exe, run_wrapper):
    expected = {
        "tiny": "gpt-5.4-mini",
        "docs-only": "gpt-5.4-mini",
        "standard": "gpt-5.4",
        "high-risk": "gpt-5.5",
        "cross-module": "gpt-5.5",
        "critical": "gpt-5.5",
        "security": "gpt-5.5",
        "architecture": "gpt-5.5",
    }
    fake_codex_exe.configure(stdout="__OK__", exit_code=0)
    for scale, model in expected.items():
        fake_codex_exe.clear_log()
        result = run_wrapper(
            WRAPPER,
            "-Prompt",
            "hello",
            "-TaskScale",
            scale,
            "-Executable",
            fake_codex_exe.path,
            "-MaxRetriesPerTier",
            "0",
            "-BaseBackoffSeconds",
            "0",
        )
        assert result.returncode == 0, result.combined_output
        assert _model_arg(fake_codex_exe.calls()) == model
        assert any(arg.startswith("model_reasoning_effort=") and "high" in arg for arg in fake_codex_exe.calls()[-1]["args"])


def test_stdin_pipe_threshold_uses_wrapper_side_log(fake_codex_exe, run_wrapper):
    fake_codex_exe.configure(stdout="__OK__", exit_code=0)
    short_prompt = "A" * 6999
    long_prompt = "A" * 7001

    short_result = run_wrapper(
        WRAPPER,
        "-Prompt",
        short_prompt,
        "-Executable",
        fake_codex_exe.path,
        "-MaxRetriesPerTier",
        "0",
        "-BaseBackoffSeconds",
        "0",
    )
    long_result = run_wrapper(
        WRAPPER,
        "-Prompt",
        long_prompt,
        "-Executable",
        fake_codex_exe.path,
        "-MaxRetriesPerTier",
        "0",
        "-BaseBackoffSeconds",
        "0",
    )

    assert short_result.returncode == 0, short_result.combined_output
    assert long_result.returncode == 0, long_result.combined_output
    assert "(stdin_pipe=False, prompt_size=6999)" in short_result.combined_output
    assert "(stdin_pipe=True, prompt_size=7001)" in long_result.combined_output


def test_codex_args_keep_top_level_flags_before_exec(fake_codex_exe, run_wrapper):
    fake_codex_exe.configure(stdout="__OK__", exit_code=0)
    result = run_wrapper(
        WRAPPER,
        "-Prompt",
        "hello",
        "-Executable",
        fake_codex_exe.path,
        "-MaxRetriesPerTier",
        "0",
        "-BaseBackoffSeconds",
        "0",
    )
    assert result.returncode == 0, result.combined_output
    args = fake_codex_exe.calls()[-1]["args"]
    assert args[0:5] == ["-a", "never", "-s", "workspace-write", "exec"]
    assert args[5] == "-m"


def test_best_effort_stdout_is_returned_when_all_tiers_fail(fake_codex_exe, run_wrapper):
    fake_codex_exe.configure(stdout="__BEST_EFFORT_REVIEW__", exit_code=1)
    result = run_wrapper(
        WRAPPER,
        "-Prompt",
        "review this",
        "-Executable",
        fake_codex_exe.path,
        "-MaxRetriesPerTier",
        "0",
        "-BaseBackoffSeconds",
        "0",
    )
    assert result.returncode == 1
    assert "__BEST_EFFORT_REVIEW__" in result.stdout


# region TASK-1060: lifecycle exclusion in pre-dispatch stash baseline


class TestCodexLifecycleExclusion:
    def test_default_exclude_keeps_lifecycle_visible_during_dispatch(self, tmp_path, tmp_repo, run_wrapper):
        _seed_lifecycle_artifacts(tmp_repo)
        exe_path, marker_name = _build_lifecycle_inspector_exe(tmp_path, "codex")
        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hello",
            "-Executable", str(exe_path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "out.code.md",
        )
        assert result.returncode == 0, result.combined_output
        marker_path = tmp_repo / marker_name
        assert marker_path.exists(), f"inspector marker missing; wrapper output:\n{result.combined_output}"
        marker_text = marker_path.read_text(encoding="utf-8")
        assert "task_visible=1" in marker_text, marker_text
        assert "plan_visible=1" in marker_text, marker_text
        assert "Pre-dispatch state stashed at" in result.combined_output

    def test_opt_in_include_stashes_lifecycle_during_dispatch(self, tmp_path, tmp_repo, run_wrapper):
        _seed_lifecycle_artifacts(tmp_repo)
        exe_path, marker_name = _build_lifecycle_inspector_exe(tmp_path, "codex")
        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hello",
            "-Executable", str(exe_path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "out.code.md",
            "-IncludeLifecycleInBaseline",
        )
        assert result.returncode == 0, result.combined_output
        marker_path = tmp_repo / marker_name
        assert marker_path.exists(), f"inspector marker missing; wrapper output:\n{result.combined_output}"
        marker_text = marker_path.read_text(encoding="utf-8")
        assert "task_visible=0" in marker_text, marker_text
        assert "plan_visible=0" in marker_text, marker_text
        assert "Pre-dispatch state stashed at" in result.combined_output

    def test_user_pre_existing_stash_not_misclaimed(self, tmp_path, tmp_repo, run_wrapper, fake_codex_exe):
        subprocess.run(
            ["git", "stash", "push", "-u", "-m", "user-pre-existing"],
            cwd=tmp_repo, check=True, capture_output=True, text=True,
        )
        _seed_lifecycle_artifacts(tmp_repo)
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hello",
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "out.code.md",
        )
        assert result.returncode == 0, result.combined_output
        assert "stash msg" in result.combined_output and "not found" in result.combined_output, result.combined_output
        list_result = subprocess.run(
            ["git", "stash", "list"],
            cwd=tmp_repo, capture_output=True, text=True, check=True,
        )
        assert "user-pre-existing" in list_result.stdout, list_result.stdout


# endregion TASK-1060
