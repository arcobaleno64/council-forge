#!/usr/bin/env python3
"""PreToolUse(Edit|Write) hook: warn on edits to governed, security-critical paths.

Reads the tool-call JSON on stdin, extracts the target file path, and warns when it
touches the template/ SSOT mirror, a guard/gate control-plane script, or the release
manifest — each of which carries extra discipline (single-writer, byte-identical
template sync, manifest regeneration, gate tests).

Non-blocking by default (exit 0, warning to stderr). Set CF_HOOK_BLOCK=1 to turn the
warning into a hard block (exit 2). Opt-in via .claude/settings.json.example.
"""
import json
import os
import sys


def target_path(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    return str(tool_input.get("file_path") or tool_input.get("path") or "")


def sensitivity(path: str) -> str:
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    if p.startswith("template/") or "/template/" in p:
        return "template/ SSOT mirror — keep byte-identical and regenerate .well-known/release-manifest.json"
    if name.startswith("guard_") or name.endswith("_gate.py") or name in (
        "regex_safety_audit.py", "prompt_injection_scan.py", "mcp_config_audit.py", "repo_security_scan.py"
    ):
        return "guard/gate control-plane — security-critical; sync template and run the gate's tests"
    if "release-manifest.json" in p:
        return "release manifest — regenerate via snapshot_manifest.py; do not hand-edit"
    return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the tool call on a parse error
    path = target_path(payload)
    reason = sensitivity(path)
    if not reason:
        return 0
    print(f"[scope-guard] {path}: {reason}", file=sys.stderr)
    return 2 if os.environ.get("CF_HOOK_BLOCK") == "1" else 0


if __name__ == "__main__":
    sys.exit(main())
