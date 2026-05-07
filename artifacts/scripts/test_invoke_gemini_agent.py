from __future__ import annotations

from pathlib import Path


WRAPPER = Path(__file__).resolve().parent / "Invoke-GeminiAgent.ps1"


def _models_from_calls(calls: list[dict]) -> list[str]:
    models = []
    for call in calls:
        args = call["args"]
        models.append(args[args.index("-m") + 1])
    return models


def test_default_model_is_flash_lite(fake_gemini_exe, run_wrapper):
    fake_gemini_exe.configure(stdout="__OK__", exit_code=0)
    result = run_wrapper(
        WRAPPER,
        "-Prompt",
        "hello",
        "-Executable",
        fake_gemini_exe.path,
        "-MaxRetriesPerTier",
        "0",
        "-BaseBackoffSeconds",
        "0",
    )
    assert result.returncode == 0, result.combined_output
    assert _models_from_calls(fake_gemini_exe.calls()) == ["gemini-3.1-flash-lite-preview"]


def test_flash_lite_capacity_failure_falls_back_to_flash_preview(fake_gemini_exe, run_wrapper):
    fake_gemini_exe.configure(
        stdout="__OK__",
        exit_code=0,
        sequence=[
            {"stdout": "429 MODEL_CAPACITY_EXHAUSTED", "exit_code": 1},
            {"stdout": "429 MODEL_CAPACITY_EXHAUSTED", "exit_code": 1},
            {"stdout": "429 MODEL_CAPACITY_EXHAUSTED", "exit_code": 1},
        ],
    )
    result = run_wrapper(
        WRAPPER,
        "-Prompt",
        "hello",
        "-Executable",
        fake_gemini_exe.path,
        "-MaxRetriesPerTier",
        "2",
        "-BaseBackoffSeconds",
        "0",
    )
    assert result.returncode == 0, result.combined_output
    models = _models_from_calls(fake_gemini_exe.calls())
    assert models[:3] == ["gemini-3.1-flash-lite-preview"] * 3
    assert models[3] == "gemini-3-flash-preview"


def test_auto_fallback_models_array_does_not_include_pro(fake_gemini_exe, run_wrapper):
    text = WRAPPER.read_text(encoding="utf-8")
    models_block = text.split("$Models = @(", 1)[1].split(")", 1)[0]
    assert "gemini-3.1-pro-preview" not in models_block

    fake_gemini_exe.configure(stdout="429 MODEL_CAPACITY_EXHAUSTED", exit_code=1)
    result = run_wrapper(
        WRAPPER,
        "-Prompt",
        "hello",
        "-Executable",
        fake_gemini_exe.path,
        "-MaxRetriesPerTier",
        "0",
        "-BaseBackoffSeconds",
        "0",
    )
    assert result.returncode == 1
    assert "gemini-3.1-pro-preview" not in _models_from_calls(fake_gemini_exe.calls())
