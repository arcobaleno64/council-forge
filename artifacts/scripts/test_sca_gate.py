"""Unit tests for sca_gate.py — full-coverage, fail-closed SCA gate."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import sca_gate


def _doc(packages_by_bucket=None, *, version=1, projects=None):
    """Build a dotnet --format json document. packages_by_bucket maps bucket->list."""
    if projects is None:
        framework = {"framework": "net8.0"}
        if packages_by_bucket:
            framework.update(packages_by_bucket)
        projects = [{"path": "p.csproj", "frameworks": [framework]}]
    doc = {"projects": projects}
    if version is not None:
        doc["version"] = version
    return doc


CLEAN = _doc({"topLevelPackages": [{"id": "A", "vulnerabilities": []}]})
VULN = _doc({"topLevelPackages": [{"id": "A", "vulnerabilities": [{"severity": "High"}]}]})
VULN_TRANSITIVE = _doc({"transitivePackages": [{"id": "B", "vulnerabilities": [{"severity": "Low"}]}]})


# --------------------------------------------------------------------------- #
# evaluate_dotnet — pass + every fail-closed branch
# --------------------------------------------------------------------------- #
def test_eval_clean():
    code, msg = sca_gate.evaluate_dotnet(CLEAN)
    assert code == sca_gate.EXIT_OK and "no vulnerable" in msg


def test_eval_vuln_toplevel():
    code, msg = sca_gate.evaluate_dotnet(VULN)
    assert code == sca_gate.EXIT_VULN and "A" in msg


def test_eval_vuln_transitive():
    code, msg = sca_gate.evaluate_dotnet(VULN_TRANSITIVE)
    assert code == sca_gate.EXIT_VULN and "B" in msg


def test_eval_not_object():
    assert sca_gate.evaluate_dotnet([1, 2])[0] == sca_gate.EXIT_VULN


def test_eval_missing_version():
    assert sca_gate.evaluate_dotnet({"projects": []})[0] == sca_gate.EXIT_VULN


def test_eval_unsupported_version_int():
    # version 2 with an otherwise-clean structure must STILL fail closed (silent drift guard)
    doc = _doc({"topLevelPackages": [{"id": "A", "vulnerabilities": []}]}, version=2)
    code, msg = sca_gate.evaluate_dotnet(doc)
    assert code == sca_gate.EXIT_VULN and "unsupported" in msg and "2" in msg


def test_eval_version_true_failclosed():
    # JSON `true` must NOT be accepted as version 1 via Python's True == 1
    doc = _doc({"topLevelPackages": [{"id": "A", "vulnerabilities": []}]}, version=True)
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_version_string_failclosed():
    doc = _doc({"topLevelPackages": [{"id": "A", "vulnerabilities": []}]}, version="1")
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_projects_not_list():
    assert sca_gate.evaluate_dotnet({"version": 1, "projects": {}})[0] == sca_gate.EXIT_VULN


def test_eval_empty_projects():
    code, msg = sca_gate.evaluate_dotnet({"version": 1, "projects": []})
    assert code == sca_gate.EXIT_VULN and "no projects" in msg


def test_eval_project_not_object():
    assert sca_gate.evaluate_dotnet({"version": 1, "projects": ["x"]})[0] == sca_gate.EXIT_VULN


def test_eval_frameworks_not_list():
    doc = {"version": 1, "projects": [{"frameworks": {}}]}
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_framework_not_object():
    doc = {"version": 1, "projects": [{"frameworks": ["x"]}]}
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_bucket_not_list():
    doc = {"version": 1, "projects": [{"frameworks": [{"topLevelPackages": {}}]}]}
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_package_not_object():
    doc = {"version": 1, "projects": [{"frameworks": [{"topLevelPackages": ["x"]}]}]}
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_vulnerabilities_not_list():
    doc = _doc({"topLevelPackages": [{"id": "A", "vulnerabilities": "oops"}]})
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_VULN


def test_eval_framework_without_buckets_is_clean():
    doc = {"version": 1, "projects": [{"frameworks": [{"framework": "net8.0"}]}]}
    assert sca_gate.evaluate_dotnet(doc)[0] == sca_gate.EXIT_OK


# --------------------------------------------------------------------------- #
# load_json
# --------------------------------------------------------------------------- #
def test_load_json_valid():
    payload, err = sca_gate.load_json('{"a": 1}')
    assert payload == {"a": 1} and err is None


def test_load_json_empty():
    payload, err = sca_gate.load_json("   ")
    assert payload is None and "empty" in err


def test_load_json_malformed():
    payload, err = sca_gate.load_json("{not json")
    assert payload is None and "malformed" in err


# --------------------------------------------------------------------------- #
# read_source
# --------------------------------------------------------------------------- #
def test_read_source_file(tmp_path: Path):
    p = tmp_path / "out.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    assert sca_gate.read_source(str(p)) == '{"x": 1}'


def test_read_source_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO('{"y": 2}'))
    assert sca_gate.read_source("-") == '{"y": 2}'


# --------------------------------------------------------------------------- #
# run() CLI + exit codes
# --------------------------------------------------------------------------- #
def test_run_clean_exit0(tmp_path: Path, capsys):
    p = tmp_path / "c.json"
    p.write_text(json.dumps(CLEAN), encoding="utf-8")
    assert sca_gate.run(["dotnet", "--json", str(p)]) == sca_gate.EXIT_OK
    assert "OK" in capsys.readouterr().out


def test_run_vuln_exit1(tmp_path: Path, capsys):
    p = tmp_path / "v.json"
    p.write_text(json.dumps(VULN), encoding="utf-8")
    assert sca_gate.run(["dotnet", "--json", str(p)]) == sca_gate.EXIT_VULN
    assert "FAIL" in capsys.readouterr().err


def test_run_malformed_failclosed(tmp_path: Path, capsys):
    p = tmp_path / "m.json"
    p.write_text("{bad", encoding="utf-8")
    assert sca_gate.run(["dotnet", "--json", str(p)]) == sca_gate.EXIT_VULN
    assert "failing closed" in capsys.readouterr().err


def test_run_missing_file_usage(tmp_path: Path, capsys):
    assert sca_gate.run(["dotnet", "--json", str(tmp_path / "ghost.json")]) == sca_gate.EXIT_USAGE
    assert "cannot read" in capsys.readouterr().err


def test_run_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(VULN_TRANSITIVE)))
    assert sca_gate.run(["dotnet", "--json", "-"]) == sca_gate.EXIT_VULN
