# Claude Code Hooks (opt-in governance automation)

council-forge ships hooks as an **opt-in example** at `.claude/settings.json.example`.
They are not active until you copy that file to `.claude/settings.json` (or
`.claude/settings.local.json`). This matches the repo's CLI-first, no-hidden-state
philosophy: hooks are reminders/guards layered on top of the deterministic gates, never a
substitute for them.

## Activation

```bash
cp .claude/settings.json.example .claude/settings.json
# review, trim to taste, then restart Claude Code
```

Hook scripts live in `.claude/hooks/` and are pure stdlib Python 3 (cross-platform; use
`python3` on systems where `python` is Python 2). They are advisory by default and never
break a tool call on error.

## What each hook does

| Event | Script | Purpose | Blocking? |
|---|---|---|---|
| **SessionStart** | `session_start_context.py` | Inject the artifact-first contract (read order, phase pipeline, STOP triggers) into session context — keeps the orchestrator oriented to CLAUDE.md without relying on memory. | No (stdout → context) |
| **PreToolUse(Edit\|Write)** | `scope_guard.py` | Warn when an edit targets `template/` (SSOT mirror), a `guard_*`/`*_gate.py` control-plane script, or `release-manifest.json` — reminders for single-writer discipline, byte-identical template sync, manifest regeneration, gate tests. | No by default; set `CF_HOOK_BLOCK=1` to hard-block (exit 2) |
| **PostToolUse(Write\|Edit)** | `post_artifact_guard.py` | After an `artifacts/**/*.md` write, surface the matching guard command (`guard_status_validator --task-id TASK-NNN`), shifting the gate left. | No (advisory) |
| **Stop** | `stop_closure_reminder.py` | Closure-phase reminder: Build Guarantee evidence, update `PROCESS_LEDGER.md`, run guards. | No (advisory) |

The example also keeps the original cross-platform desktop-notification hooks
(Notification/Stop via BurntToast/osascript/notify-send) and the optional prettier
auto-format PostToolUse hook.

## Making a hook fail-closed

The scope guard is the natural candidate for hard enforcement (e.g. block edits to
`template/` without going through the sync flow). Two options:

- Per-session: run with `CF_HOOK_BLOCK=1` in the environment so `scope_guard.py` exits 2
  (which tells Claude Code to block the tool call and surface the stderr message).
- Permanently: change the hook's behavior in your local `settings.json`.

Keep enforcement local/opt-in; the authoritative, CI-enforced controls remain the
fail-closed gates in `.github/workflows/` (`guard_status_validator`, `guard_contract_validator`,
`regex_safety_audit`, `prompt_injection_scan`, `repo_security_scan`, etc.).

## Reference

- Official hook schema and events: https://code.claude.com/docs/en/hooks
