#!/usr/bin/env python3
"""PostToolUse(Write|Edit) hook: after an artifact markdown write, surface the
matching guard command (shift-left). Advisory — never blocks.

Opt-in via .claude/settings.json.example.
"""
import json
import re
import sys

TASK_RE = re.compile(r"(TASK-\d+)\.")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response") or {}
    path = str(tool_response.get("filePath") or tool_input.get("file_path") or "").replace("\\", "/")
    if "/artifacts/" not in ("/" + path) or not path.endswith(".md"):
        return 0
    name = path.rsplit("/", 1)[-1]
    match = TASK_RE.match(name)
    if match:
        print(
            f"[post-artifact] {name} changed -> verify: "
            f"python artifacts/scripts/guard_status_validator.py --task-id {match.group(1)}",
            file=sys.stderr,
        )
    else:
        print(
            f"[post-artifact] {name} changed -> consider: "
            f"python artifacts/scripts/prompt_injection_scan.py scan --root .",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
