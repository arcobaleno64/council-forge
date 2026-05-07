from __future__ import annotations

from pathlib import Path


WRAPPER = Path(__file__).resolve().parent / "Invoke-CodexAgent.ps1"


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
