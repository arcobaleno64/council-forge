"""Tests for mcp_config_audit.py — the .mcp.json allowlist auditor."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import mcp_config_audit as mca  # noqa: E402

REPO_ROOT = SCRIPTS_DIR.parent.parent
ALLOWLIST = json.loads((REPO_ROOT / mca.DEFAULT_ALLOWLIST).read_text(encoding="utf-8"))


def _checks(findings):
    return sorted({f.check for f in findings})


class TestApprovedAllowlist:
    def test_repo_example_is_clean(self):
        cfg = json.loads((REPO_ROOT / ".mcp.json.example").read_text(encoding="utf-8"))
        findings = mca.audit(mca._strip_comment_keys(cfg), ALLOWLIST)
        assert findings == [], [f.__dict__ for f in findings]

    def test_example_cli_ok(self):
        assert mca.main(["--root", str(REPO_ROOT), "--config", ".mcp.json.example"]) == mca.EXIT_OK

    def test_unapproved_server_flagged(self):
        cfg = {"mcpServers": {"rogue": {"command": "npx", "args": ["-y", "rogue@1.0.0"]}}}
        assert "unapproved-server" in _checks(mca.audit(cfg, ALLOWLIST))

    def test_version_mismatch_flagged(self):
        # an approved server name but a non-approved pin
        cfg = {"mcpServers": {"tavily": {"command": "npx", "args": ["-y", "tavily-mcp@9.9.9"],
                                          "env": {"TAVILY_API_KEY": "${TAVILY_API_KEY}"}}}}
        assert "version-mismatch" in _checks(mca.audit(cfg, ALLOWLIST))


class TestSecretChecks:
    def test_env_ref_is_not_a_secret(self):
        cfg = {"mcpServers": {"github": {"command": "docker",
                                         "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                                                  "ghcr.io/github/github-mcp-server:v0.21.0"],
                                         "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"}}}}
        assert "hardcoded-secret" not in _checks(mca.audit(cfg, ALLOWLIST))

    def test_hardcoded_github_token_flagged(self):
        cfg = {"mcpServers": {"github": {"command": "docker",
                                         "args": ["run", "ghcr.io/github/github-mcp-server:v0.21.0"],
                                         "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_" + "A" * 36}}}}
        assert "hardcoded-secret" in _checks(mca.audit(cfg, ALLOWLIST))


class TestPinningAndShell:
    def test_latest_flagged(self):
        cfg = {"mcpServers": {"filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem@latest", "."]}}}
        assert "unpinned-dependency" in _checks(mca.audit(cfg, ALLOWLIST))

    def test_npx_without_y_flagged(self):
        cfg = {"mcpServers": {"memory": {"command": "npx", "args": ["@modelcontextprotocol/server-memory@2025.8.4"]}}}
        assert "npx-interactive" in _checks(mca.audit(cfg, ALLOWLIST))

    def test_shell_injection_flagged(self):
        cfg = {"mcpServers": {"x": {"command": "sh", "args": ["-c", "echo hi | grep h"]}}}
        assert "shell-injection" in _checks(mca.audit(cfg, ALLOWLIST))


class TestMalformed:
    def test_empty_config_is_clean(self):
        # no mcpServers key => no servers to audit => clean
        assert mca.audit({}, ALLOWLIST) == []

    def test_mcpservers_not_object_is_malformed(self):
        findings = mca.audit({"mcpServers": ["not", "an", "object"]}, ALLOWLIST)
        assert "malformed" in _checks(findings)

    def test_bad_config_cli_returns_findings(self, tmp_path):
        bad = tmp_path / "bad.mcp.json"
        bad.write_text(json.dumps({"mcpServers": {"rogue": {"command": "npx", "args": ["rogue@latest"]}}}), encoding="utf-8")
        rc = mca.main(["--root", str(tmp_path), "--config", "bad.mcp.json",
                       "--allowlist", str(REPO_ROOT / mca.DEFAULT_ALLOWLIST)])
        assert rc == mca.EXIT_FINDINGS

    def test_missing_file_fails_closed(self, tmp_path):
        assert mca.main(["--root", str(tmp_path), "--config", "nope.json"]) == mca.EXIT_ERROR
