#!/usr/bin/env python3
"""SessionStart hook: inject the artifact-first contract as session context.

Stdout from a SessionStart hook is added to the model's context, so this keeps the
orchestrator oriented to CLAUDE.md's "文件即事實" without relying on memory.
Opt-in: wired only via .claude/settings.json.example. Never blocks.
"""
import sys

MESSAGE = (
    "[council-forge] Artifact-first workflow is in effect. "
    "Read order: AGENTS.md -> docs/orchestration.md -> the current task artifact. "
    "Artifacts (not memory) are the single source of truth. "
    "Phases must not be skipped: Intake -> Research -> Planning -> Coding -> Verification -> Closure. "
    "STOP if a task/plan/code/verify artifact or required metadata (Task ID, status, +08:00 timestamp) "
    "is missing, or a status transition violates the workflow state machine."
)

if __name__ == "__main__":
    print(MESSAGE)
    sys.exit(0)
