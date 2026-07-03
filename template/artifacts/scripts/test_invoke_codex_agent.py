from __future__ import annotations

import os
import shutil
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
        "-SuppressSizeWarn",
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
        "-SuppressSizeWarn",
    )

    assert short_result.returncode == 0, short_result.combined_output
    assert long_result.returncode == 0, long_result.combined_output
    # TASK-1062 Bug B fix: wrapper now always pipes via stdin (regardless of
    # prompt size) to avoid Windows cmd.exe batch-parser truncating multiline
    # prompts at the first LF/CR. The 7000-char threshold becomes a documented
    # lower-bound rationale; both branches log stdin_pipe=True. Spec change.
    assert "(stdin_pipe=True, prompt_size=6999)" in short_result.combined_output
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


# region TASK-1092 / FB-5: retry-pattern match is scoped to STDERR, not the combined
# stream. A successful (exit 0) review whose STDOUT *answer* quotes a transport-error
# substring (e.g. "429", "Failed to fetch") must NOT be treated as a failure.


def test_exit0_with_transient_substring_in_stdout_is_success_not_retried(fake_codex_exe, run_wrapper):
    # The review answer legitimately discusses transport errors; with stderr clean and
    # exit 0 the dispatch must succeed WITHOUT any spurious interception/backoff.
    fake_codex_exe.configure(
        stdout="VERDICT: approve. Note: handles 429 Too Many Requests and 'Failed to fetch' / ECONNRESET.",
        stderr="",
        exit_code=0,
    )
    result = run_wrapper(
        WRAPPER,
        "-Prompt", "review this",
        "-Executable", fake_codex_exe.path,
        "-MaxRetriesPerTier", "1",
        "-BaseBackoffSeconds", "0",
    )
    assert result.returncode == 0, result.combined_output
    assert "VERDICT: approve" in result.stdout
    assert len(fake_codex_exe.calls()) == 1, "must not retry a successful exit-0 review"
    assert "Intercepted API/Execution Error" not in result.combined_output
    assert "Backoff" not in result.combined_output


def test_exit0_with_transient_in_stderr_is_success_not_retried(fake_codex_exe, run_wrapper):
    # exit 0 is UNCONDITIONAL success. The codex CLI echoes reviewed content (including
    # transport-error tokens) to STDERR as well as stdout (tool traces / reasoning), so a
    # stderr scan on exit 0 ALSO false-positives. This is the exact scenario that made the
    # FB-5 impl-review run exhaust on an exit-0 dispatch: exit code is the sole truth.
    fake_codex_exe.configure(
        stdout="__OK__",
        stderr="...tool trace mentioning 429 Too Many Requests and ECONNRESET...",
        exit_code=0,
    )
    result = run_wrapper(
        WRAPPER,
        "-Prompt", "review this",
        "-Executable", fake_codex_exe.path,
        "-MaxRetriesPerTier", "1",
        "-BaseBackoffSeconds", "0",
    )
    assert result.returncode == 0, result.combined_output
    assert "__OK__" in result.stdout
    assert len(fake_codex_exe.calls()) == 1, "exit 0 must succeed even when stderr contains a transient token"
    assert "Intercepted API/Execution Error" not in result.combined_output
    assert "Backoff" not in result.combined_output


def test_failure_with_transient_only_in_stdout_is_generic_not_targeted(fake_codex_exe, run_wrapper):
    # exit != 0 with the transient substring ONLY in STDOUT (stderr empty) must classify
    # as a GENERIC backoff, NOT "Target error string matched" -- proving the match target
    # moved off the combined stream (old code matched stdout "429" => targeted).
    fake_codex_exe.configure(
        stdout="some review text mentioning 429 and Failed to fetch",
        stderr="",
        exit_code=1,
    )
    result = run_wrapper(
        WRAPPER,
        "-Prompt", "review this",
        "-TaskScale", "tiny",
        "-Executable", fake_codex_exe.path,
        "-MaxRetriesPerTier", "1",
        "-BaseBackoffSeconds", "0",
    )
    assert result.returncode == 1, result.combined_output
    assert "Backoff] Generic failure" in result.combined_output
    assert "Target error string matched" not in result.combined_output


def test_throw_path_classifies_via_exception_message(tmp_repo):
    # When the invocation itself THROWS (executable not found), the catch must feed the
    # exception message into the retry-pattern classification. The missing executable
    # name contains a RetryPattern so the classification is targeted (proves line 437
    # populates $errText, consumed by the line 442 classification).
    # NB: this throw path makes PowerShell render an error whose pipe-captured bytes are
    # not always valid UTF-8; we decode with errors="replace" here. The shared
    # run_wrapper fixture uses text=True (no errors=) and would crash on that decode --
    # an unrelated harness fragility, so this one test captures directly.
    ps = (shutil.which("powershell.exe") or shutil.which("pwsh")) if os.name == "nt" else shutil.which("pwsh")
    command = [ps, "-NoProfile"]
    if Path(ps).name.lower() == "powershell.exe":
        command += ["-ExecutionPolicy", "Bypass"]
    command += [
        "-File", str(WRAPPER),
        "-Prompt", "review this",
        "-TaskScale", "tiny",
        "-Executable", "ECONNRESET-no-such-codex-binary",
        "-MaxRetriesPerTier", "1",
        "-BaseBackoffSeconds", "0",
    ]
    result = subprocess.run(
        command,
        cwd=tmp_repo,
        env=os.environ.copy(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 1, combined
    assert "Process Exception Caught" in combined, combined
    assert "Target error string matched" in combined, combined


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


# region TASK-1062: Bug A (lifecycle untracked classification) + Bug B (always-stdin)


class TestCodexBugAClassification:
    """TASK-1062 Bug A: lifecycle pre-existing untracked artifacts must not be
    misclassified as sub-agent writes when the post-dispatch guard runs."""

    def test_lifecycle_untracked_preserved_when_unchanged(self, tmp_path, tmp_repo, run_wrapper, fake_codex_exe):
        # C-1 (Bug A reverse): seed pre-dispatch lifecycle untracked artifacts
        # outside AllowedPaths, dispatch with a fake exe that does not touch
        # them, and assert they survive post-dispatch (no false-positive
        # violation, no Restore-PostDispatchDelta deletion).
        _seed_lifecycle_artifacts(tmp_repo)
        (tmp_repo / "artifacts" / "status").mkdir(parents=True, exist_ok=True)
        status_path = tmp_repo / "artifacts" / "status" / "TASK-fake.status.json"
        status_path.write_text('{"task_id": "TASK-fake"}\n', encoding="utf-8")
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hello",
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "artifacts/research/TASK-fake.research.md",
            "-AutoRestore",
        )
        assert result.returncode == 0, result.combined_output
        task_path = tmp_repo / "artifacts" / "tasks" / "TASK-fake.task.md"
        plan_path = tmp_repo / "artifacts" / "plans" / "TASK-fake.plan.md"
        assert task_path.exists(), f"task artifact deleted; output:\n{result.combined_output}"
        assert plan_path.exists(), f"plan artifact deleted; output:\n{result.combined_output}"
        assert status_path.exists(), f"status artifact deleted; output:\n{result.combined_output}"
        assert "Lifecycle pre-existing untracked (unchanged)" in result.combined_output

    def test_lifecycle_untracked_modified_by_subagent_is_restored(self, tmp_path, tmp_repo, run_wrapper):
        # C-2 (Bug A forward): sub-agent modifies a pre-dispatch lifecycle
        # untracked artifact outside AllowedPaths -> wrapper detects violation
        # and restores via git cat-file blob to pre-dispatch content.
        _seed_lifecycle_artifacts(tmp_repo)
        task_path = tmp_repo / "artifacts" / "tasks" / "TASK-fake.task.md"
        original_content = task_path.read_text(encoding="utf-8")

        # Build an inspector exe that mutates the lifecycle file during dispatch.
        directory = tmp_path / "mutator-codex"
        directory.mkdir()
        script_path = directory / "codex_mutator.py"
        script_path.write_text(
            textwrap.dedent("""
            from __future__ import annotations
            import sys
            from pathlib import Path
            cwd = Path.cwd()
            target = cwd / "artifacts" / "tasks" / "TASK-fake.task.md"
            target.write_text("MUTATED BY SUB-AGENT\\n", encoding="utf-8")
            sys.exit(0)
            """).strip(),
            encoding="utf-8",
        )
        if os.name == "nt":
            exe_path = directory / "codex.cmd"
            exe_path.write_text(
                f'@echo off\r\n"{sys.executable}" "{script_path}" %*\r\nexit /b %ERRORLEVEL%\r\n',
                encoding="utf-8",
            )
        else:
            exe_path = directory / "codex"
            exe_path.write_text(
                f'#!/usr/bin/env sh\nexec "{sys.executable}" "{script_path}" "$@"\n',
                encoding="utf-8",
            )
            exe_path.chmod(0o755)

        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hello",
            "-Executable", str(exe_path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "artifacts/research/TASK-fake.research.md",
            "-AutoRestore",
        )
        # Wrapper exits 2 because the sub-agent wrote outside AllowedPaths.
        assert result.returncode == 2, result.combined_output
        assert task_path.exists(), "task artifact deleted instead of restored"
        assert task_path.read_text(encoding="utf-8") == original_content, (
            f"task artifact not restored to pre-dispatch content; got:\n{task_path.read_text(encoding='utf-8')}"
        )
        assert "Restored lifecycle untracked (pre-dispatch blob)" in result.combined_output


class TestCodexBugBStdinAlways:
    """TASK-1062 Bug B: wrapper always pipes prompt via stdin to avoid Windows
    cmd.exe batch-parser truncating multiline prompts at the first LF/CR."""

    def test_multiline_prompt_under_threshold_is_piped_via_stdin(self, fake_codex_exe, run_wrapper):
        # C-3 (Bug B reverse): 5000-char multiline prompt (under the legacy
        # 7000-char threshold) must arrive at the sub-agent intact via stdin,
        # not via -p arg (which would truncate at the first newline).
        body_lines = ["[ROLE]"] + ["payload line " + str(i).rjust(4, "0") for i in range(450)]
        prompt = "\n".join(body_lines)
        # Pad to ~5000 chars while preserving multi-line structure.
        while len(prompt) < 5000:
            prompt += "\nfiller " + str(len(prompt))
        prompt = prompt[:5000]
        assert "\n" in prompt and len(prompt) == 5000

        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        result = run_wrapper(
            WRAPPER,
            "-Prompt", prompt,
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
        )
        assert result.returncode == 0, result.combined_output
        assert "(stdin_pipe=True, prompt_size=5000)" in result.combined_output
        calls = fake_codex_exe.calls()
        assert calls, "fake exe was never called"
        last = calls[-1]
        # Prompt must NOT appear as an argv element.
        assert prompt not in last["args"], "prompt leaked into argv (cmdline truncation risk)"
        # Prompt MUST arrive via stdin, in full, with newlines intact.
        stdin_seen = last.get("stdin", "")
        # Whitespace-tolerant compare: stdin echo may add a trailing newline
        # depending on how PowerShell pipes the string.
        assert prompt.rstrip("\n") in stdin_seen, (
            f"prompt not present in fake exe stdin (got {len(stdin_seen)} chars)"
        )
        assert stdin_seen.count("\n") >= 5, (
            f"newlines lost in stdin transport (got {stdin_seen.count(chr(10))})"
        )

    def test_short_single_line_prompt_still_dispatches(self, fake_codex_exe, run_wrapper):
        # C-4 (Bug B regression smoke): short single-line prompt still works
        # under the always-stdin path; wrapper exit 0; stdin echo present.
        prompt = "x" * 100
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        result = run_wrapper(
            WRAPPER,
            "-Prompt", prompt,
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
        )
        assert result.returncode == 0, result.combined_output
        assert "(stdin_pipe=True, prompt_size=100)" in result.combined_output
        last = fake_codex_exe.calls()[-1]
        assert prompt not in last["args"], "prompt leaked into argv"
        stdin_seen = last.get("stdin", "")
        assert prompt in stdin_seen, "prompt missing from stdin"


# endregion TASK-1062


class TestCodexBoundsCheck:
    """TASK-1067: wrapper enforces prompt size bounds — warn @ 500, reject @ 5000.
    -SuppressSizeWarn opts out (bypass both warn and reject). Aligns with
    docs/dispatch_prompt_discipline.md 500-char threshold."""

    def test_prompt_under_warn_threshold_dispatches_silently(self, fake_codex_exe, run_wrapper):
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        prompt = "x" * 300
        result = run_wrapper(
            WRAPPER,
            "-Prompt", prompt,
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
        )
        assert result.returncode == 0, result.combined_output
        assert "exceeds soft limit" not in result.combined_output
        assert "exceeds reject limit" not in result.combined_output

    def test_prompt_in_warn_range_emits_warning_but_dispatches(self, fake_codex_exe, run_wrapper):
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        prompt = "y" * 600
        result = run_wrapper(
            WRAPPER,
            "-Prompt", prompt,
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
        )
        assert result.returncode == 0, result.combined_output
        normalized = " ".join(result.combined_output.split())
        assert "exceeds soft limit 500" in normalized

    def test_prompt_over_reject_threshold_exits_four(self, fake_codex_exe, run_wrapper):
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        prompt = "z" * 6000
        result = run_wrapper(
            WRAPPER,
            "-Prompt", prompt,
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
        )
        assert result.returncode == 4, result.combined_output
        normalized = " ".join(result.combined_output.split())
        assert "exceeds reject limit 5000" in normalized

    def test_suppress_size_warn_bypasses_reject(self, fake_codex_exe, run_wrapper):
        fake_codex_exe.configure(stdout="__OK__", exit_code=0)
        prompt = "w" * 6000
        result = run_wrapper(
            WRAPPER,
            "-Prompt", prompt,
            "-Executable", str(fake_codex_exe.path),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-SuppressSizeWarn",
        )
        assert result.returncode == 0, result.combined_output
        assert "exceeds reject limit" not in result.combined_output
        assert "exceeds soft limit" not in result.combined_output


class TestCodexRaciAudit:
    """CHG-006: post-dispatch RACI category audit on sub-agent writes. Orthogonal to
    AllowedPaths — a path can be allow-listed yet be the wrong artifact class for the
    agent. RACI violations are reported and (in -AutoRestore mode) exit 2, but are
    never restored/deleted."""

    @staticmethod
    def _build_writer_exe(directory: Path, rel_path: str, content: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        script_path = directory / "codex_writer.py"
        script_path.write_text(
            textwrap.dedent(f"""
            from __future__ import annotations
            from pathlib import Path
            target = Path.cwd() / {rel_path!r}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text({content!r}, encoding="utf-8")
            """).strip(),
            encoding="utf-8",
        )
        exe_path = directory / "codex.cmd"
        exe_path.write_text(
            f'@echo off\r\n"{sys.executable}" "{script_path}" %*\r\nexit /b %ERRORLEVEL%\r\n',
            encoding="utf-8",
        )
        return exe_path

    def test_raci_violation_within_allowedpaths_exits_2(self, tmp_path, tmp_repo, run_wrapper):
        # Sub-agent writes a *task* artifact that IS within AllowedPaths (no path
        # violation) but is the wrong RACI class for Codex CLI -> RACI audit exit 2,
        # and the path-allowed write is NOT restored/deleted.
        exe = self._build_writer_exe(tmp_path / "w", "artifacts/tasks/TASK-raci.task.md", "raci\n")
        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hi",
            "-Executable", str(exe),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "artifacts/tasks/TASK-raci.task.md",
            "-AutoRestore",
        )
        assert result.returncode == 2, result.combined_output
        assert "RACI" in result.combined_output
        assert (tmp_repo / "artifacts" / "tasks" / "TASK-raci.task.md").exists(), (
            "RACI (path-allowed) write must not be deleted/restored"
        )

    def test_raci_allowed_class_within_allowedpaths_passes(self, tmp_path, tmp_repo, run_wrapper):
        # Sub-agent writes a *code* artifact within AllowedPaths -> Codex CLI is
        # authorized for the code class -> no RACI violation, exit 0.
        exe = self._build_writer_exe(tmp_path / "w", "artifacts/code/TASK-raci.code.md", "code\n")
        result = run_wrapper(
            WRAPPER,
            "-Prompt", "hi",
            "-Executable", str(exe),
            "-MaxRetriesPerTier", "0",
            "-BaseBackoffSeconds", "0",
            "-AllowedPaths", "artifacts/code/TASK-raci.code.md",
            "-AutoRestore",
        )
        assert result.returncode == 0, result.combined_output
