#!/usr/bin/env python3
"""Audit an .mcp.json against the project's approved-server allowlist.

Headless implementation of the `mcp-security-audit` skill's five checks so they
can run deterministically (and, later, as a fail-closed CI gate):

  1. Hardcoded secrets in server args/env
  2. Shell-injection patterns in args
  3. Unpinned dependencies (@latest, npx without -y)
  4. Dangerous commands (eval / bash -c / curl|sh, etc.)
  5. Server present on .github/mcp/approved-servers.json AND pinned to the
     approved version  <-- the check the skill diagrams but never implemented

Pure stdlib; linear regexes only (passes regex_safety_audit). Mirrors the repo
convention: Finding dataclass, exit 0 (clean) / 1 (findings) / 2 (error).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

DEFAULT_CONFIG = ".mcp.json"
DEFAULT_ALLOWLIST = ".github/mcp/approved-servers.json"

SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|token|secret|password|credential)["\']?\s*[:=]\s*["\'][^"\']{8,}', "Hardcoded secret"),
    (r'(?i)Bearer\s+[A-Za-z0-9\-._~+/]{8,}', "Hardcoded bearer token"),
    (r'(gh[pousr]_)[A-Za-z0-9]{30,}', "GitHub token"),
    (r'sk-[A-Za-z0-9]{20,}', "OpenAI API key"),
    (r'AKIA[0-9A-Z]{16}', "AWS access key"),
    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "Private key"),
]

DANGEROUS_PATTERNS = [
    (r'\$\(', "command substitution $(...)"),
    (r'`[^`]+`', "backtick command substitution"),
    (r';\s*\w', "command chaining with ;"),
    (r'\|\s*\w', "pipe to another command"),
    (r'&&\s*\w', "command chaining with &&"),
    (r'\|\|\s*\w', "command chaining with ||"),
    (r'(?i)\beval\b', "eval usage"),
    (r'(?i)\b(ba)?sh\s+-c\b', "shell -c execution"),
    (r'>\s*/dev/tcp/', "TCP redirect (reverse-shell pattern)"),
    (r'(?i)curl\s', "curl invocation"),
]

# An ${ENV} reference is the APPROVED way to pass a secret — never a finding.
ENV_REF = re.compile(r'^\$\{[A-Za-z_][A-Za-z0-9_]*\}$')


@dataclass
class Finding:
    severity: str
    check: str
    server: str
    message: str
    fix: str


def _is_env_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(ENV_REF.match(value.strip()))


def check_secrets(server: str, config: Any, findings: List[Finding]) -> None:
    # Only scan literal values; an env value that is exactly ${ENV} is fine.
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            if _is_env_ref(node):
                return
            for pattern, desc in SECRET_PATTERNS:
                if re.search(pattern, node):
                    findings.append(Finding("CRITICAL", "hardcoded-secret", server,
                                            f"{desc} in literal value",
                                            "Use an environment reference: ${ENV_VAR}"))
                    break
    walk(config)


def check_shell_injection(server: str, config: dict, findings: List[Finding]) -> None:
    args_text = json.dumps(config.get("args", []))
    for pattern, desc in DANGEROUS_PATTERNS:
        if re.search(pattern, args_text):
            findings.append(Finding("HIGH", "shell-injection", server,
                                    f"dangerous pattern in args: {desc}",
                                    "Use direct command execution, not shell interpolation"))


def check_pinned(server: str, config: dict, findings: List[Finding]) -> None:
    args = config.get("args", [])
    blob = json.dumps(args) + " " + str(config.get("command", ""))
    if "@latest" in blob or ":latest" in blob:
        findings.append(Finding("MEDIUM", "unpinned-dependency", server,
                                "uses @latest / :latest (unpinned)",
                                "Pin to an explicit, verified version"))
    if config.get("command") == "npx" and "-y" not in [str(a) for a in args]:
        findings.append(Finding("LOW", "npx-interactive", server,
                                "npx without -y may prompt interactively in CI",
                                "Add -y: npx -y package@version"))


def check_approved(server: str, config: dict, allowlist: dict, findings: List[Finding]) -> None:
    entries = {e["name"]: e for e in allowlist.get("approved_servers", [])}
    entry = entries.get(server)
    if entry is None:
        findings.append(Finding("HIGH", "unapproved-server", server,
                                "server is not on .github/mcp/approved-servers.json",
                                "Add a vetted, pinned entry to the allowlist or remove the server"))
        return
    pinned = str(entry.get("pinned_version", ""))
    blob = json.dumps(config)
    if pinned and pinned not in blob:
        findings.append(Finding("MEDIUM", "version-mismatch", server,
                                f"configured version is not the approved pin ({pinned})",
                                f"Pin {entry.get('package', server)} to {pinned}"))


def audit(config: dict, allowlist: dict) -> List[Finding]:
    findings: List[Finding] = []
    servers = config.get("mcpServers", {})
    if not isinstance(servers, dict):
        return [Finding("CRITICAL", "malformed", "<root>", "mcpServers is missing or not an object",
                        "Use {\"mcpServers\": {name: {...}}}")]
    for name, sconf in servers.items():
        if not isinstance(sconf, dict):
            continue
        check_secrets(name, sconf, findings)
        check_shell_injection(name, sconf, findings)
        check_pinned(name, sconf, findings)
        check_approved(name, sconf, allowlist, findings)
    return findings


def _strip_comment_keys(obj: Any) -> Any:
    # .mcp.json.example carries _comment/_note guidance keys; ignore them.
    if isinstance(obj, dict):
        return {k: _strip_comment_keys(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_comment_keys(v) for v in obj]
    return obj


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit .mcp.json against the approved-server allowlist")
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="path to .mcp.json (relative to root)")
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST, help="path to approved-servers.json (relative to root)")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        config = json.loads((root / args.config).read_text(encoding="utf-8"))
        allowlist = json.loads((root / args.allowlist).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot load inputs: {exc}", file=sys.stderr)
        return EXIT_ERROR

    findings = audit(_strip_comment_keys(config), allowlist)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        for f in findings:
            print(f"[{f.severity}] {f.check} {f.server}: {f.message}")
            print(f"    fix: {f.fix}")
    if findings:
        if not args.json:
            print(f"\n[FAIL] {len(findings)} MCP-config finding(s).", file=sys.stderr)
        return EXIT_FINDINGS
    if not args.json:
        print("[OK] MCP config passes all five checks (secrets, shell, pinning, dangerous, allowlist).")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
