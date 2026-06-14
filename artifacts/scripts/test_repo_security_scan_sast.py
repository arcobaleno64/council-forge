"""Unit tests for the advisory Python SAST subcommand of repo_security_scan.py.

Covers rule detection, SARIF 2.1.0 emission (round-tripped through sast_gate), advisory
exit-0 semantics, and a regression guard that the existing enforcing secrets/static
subcommands are unchanged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import repo_security_scan as rss
import sast_gate


VULN_PY = "\n".join(
    [
        "import yaml, pickle, tempfile, hashlib, ssl",
        "data = yaml.load(stream)",
        "obj = pickle.loads(blob)",
        "tmp = tempfile.mktemp()",
        "digest = hashlib.md5(payload)",
        'host = "0.0.0.0"',
        "ctx.verify_mode = ssl.CERT_NONE",
        "",
    ]
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- #
# scan_sast — detection + low-FP guards
# --------------------------------------------------------------------------- #
def test_scan_sast_detects_all_curated_rules(tmp_path: Path):
    _write(tmp_path / "artifacts" / "scripts" / "vuln.py", VULN_PY)
    ids = {finding.rule_id for finding in rss.scan_sast(tmp_path)}
    assert ids == {
        "sast-yaml-unsafe-load",
        "sast-insecure-deserialization",
        "sast-insecure-tempfile",
        "sast-weak-hash",
        "sast-bind-all-interfaces",
        "sast-ssl-no-verify",
    }


def test_scan_sast_yaml_safe_loader_not_flagged(tmp_path: Path):
    _write(
        tmp_path / "artifacts" / "scripts" / "ok.py",
        "import yaml\nvalue = yaml.load(stream, Loader=yaml.SafeLoader)\n",
    )
    assert rss.scan_sast(tmp_path) == []


def test_scan_sast_ignores_non_python_targets(tmp_path: Path):
    _write(tmp_path / "docs" / "note.md", "yaml.load(x)\n")
    assert rss.scan_sast(tmp_path) == []


def test_scan_sast_skips_when_read_text_none(tmp_path: Path, monkeypatch):
    sample = tmp_path / "artifacts" / "scripts" / "v.py"
    _write(sample, VULN_PY)
    monkeypatch.setattr(rss, "iter_repo_files", lambda root: [("artifacts/scripts/v.py", sample)])
    monkeypatch.setattr(rss, "read_text", lambda path: None)
    assert rss.scan_sast(tmp_path) == []


# --------------------------------------------------------------------------- #
# findings_to_sarif — round-trips into the gate, severity mapping
# --------------------------------------------------------------------------- #
def test_findings_to_sarif_roundtrips_into_gate(tmp_path: Path):
    _write(tmp_path / "artifacts" / "scripts" / "vuln.py", VULN_PY)
    findings = rss.scan_sast(tmp_path)
    doc = rss.findings_to_sarif(findings)
    assert doc["version"] == "2.1.0"
    parsed, err = sast_gate.extract_findings(doc)
    assert err is None and len(parsed) == len(findings)


def test_findings_to_sarif_empty_roundtrips():
    doc = rss.findings_to_sarif([])
    assert doc["runs"][0]["results"] == []
    parsed, err = sast_gate.extract_findings(doc)
    assert err is None and parsed == []


def test_findings_to_sarif_severity_mapping():
    high = rss.Finding("r1", "high", "a.py", 1, "m", "x")
    unmapped = rss.Finding("r2", "bogus", "a.py", 2, "m", "x")
    doc = rss.findings_to_sarif([high, unmapped])
    levels = [result["level"] for result in doc["runs"][0]["results"]]
    assert levels == ["error", "warning"]  # high -> error; unmapped severity -> warning default


# --------------------------------------------------------------------------- #
# emit_sast — formats, all advisory (exit 0)
# --------------------------------------------------------------------------- #
def test_emit_sast_sarif(capsys):
    finding = rss.Finding("sast-weak-hash", "low", "a.py", 1, "m", "x")
    assert rss.emit_sast([finding], "sarif") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["version"] == "2.1.0" and doc["runs"][0]["results"][0]["level"] == "note"


def test_emit_sast_json(capsys):
    finding = rss.Finding("sast-weak-hash", "low", "a.py", 1, "m", "x")
    assert rss.emit_sast([finding], "json") == 0
    assert '"rule_id": "sast-weak-hash"' in capsys.readouterr().out


def test_emit_sast_text(capsys):
    assert rss.emit_sast([], "text") == 0
    assert "[OK] No findings detected" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# main() dispatch — advisory exit 0; existing subcommands still enforcing
# --------------------------------------------------------------------------- #
def test_main_sast_is_advisory_exit0(tmp_path: Path, capsys):
    _write(tmp_path / "artifacts" / "scripts" / "vuln.py", VULN_PY)
    code = rss.main(["--root", str(tmp_path), "sast", "--format", "sarif"])
    doc = json.loads(capsys.readouterr().out)
    assert code == 0  # advisory: findings present, but exit 0 (sast_gate is the gate)
    assert len(doc["runs"][0]["results"]) >= 6


def test_existing_static_subcommand_still_enforces(tmp_path: Path):
    _write(
        tmp_path / ".github" / "workflows" / "bad.yml",
        "jobs:\n  t:\n    steps:\n      - uses: actions/checkout@v4\n",
    )
    assert rss.main(["--root", str(tmp_path), "static"]) == 1


def test_existing_secrets_subcommand_still_enforces(tmp_path: Path):
    secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    _write(tmp_path / "artifacts" / "scripts" / "s.py", f'token = "{secret}"\n')
    assert rss.main(["--root", str(tmp_path), "secrets"]) == 1
