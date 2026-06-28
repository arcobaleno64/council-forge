"""Unit tests for sast_gate.py — full-coverage, fail-closed-on-garbage SARIF SAST gate."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import sast_gate


# --------------------------------------------------------------------------- #
# SARIF fixture builders
# --------------------------------------------------------------------------- #
def _result(rule_id="R1", level="warning", uri="a.py", line=10, text="msg"):
    result = {
        "ruleId": rule_id,
        "message": {"text": text},
        "locations": [
            {"physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": line}}}
        ],
    }
    if level is not None:
        result["level"] = level
    return result


def _sarif(results=None, *, version="2.1.0", runs=None):
    if runs is None:
        runs = [{"results": results if results is not None else []}]
    doc = {"runs": runs}
    if version is not None:
        doc["version"] = version
    return doc


# --------------------------------------------------------------------------- #
# extract_findings — happy path + every fail-closed branch
# --------------------------------------------------------------------------- #
def test_extract_clean():
    findings, err = sast_gate.extract_findings(_sarif([]))
    assert err is None and findings == []


def test_extract_with_findings():
    findings, err = sast_gate.extract_findings(_sarif([_result(level="error")]))
    assert err is None and len(findings) == 1
    assert findings[0].level == "error" and findings[0].location == "a.py:10"


def test_extract_not_object():
    findings, err = sast_gate.extract_findings([1, 2])
    assert findings is None and "top-level" in err


def test_extract_missing_version():
    findings, err = sast_gate.extract_findings(_sarif([], version=None))
    assert findings is None and "unsupported SARIF version" in err


def test_extract_version_non_string():
    findings, err = sast_gate.extract_findings(_sarif([], version=2))
    assert findings is None and "unsupported SARIF version" in err


def test_extract_version_unknown_string():
    findings, err = sast_gate.extract_findings(_sarif([], version="3.0.0"))
    assert findings is None and "3.0.0" in err


def test_extract_runs_not_list():
    findings, err = sast_gate.extract_findings({"version": "2.1.0", "runs": {}})
    assert findings is None and "'runs' is not a list" in err


def test_extract_run_not_object():
    findings, err = sast_gate.extract_findings({"version": "2.1.0", "runs": ["x"]})
    assert findings is None and "run entry" in err


def test_extract_results_absent_is_clean():
    # a run with no `results` key -> treated as no findings
    findings, err = sast_gate.extract_findings({"version": "2.1.0", "runs": [{}]})
    assert err is None and findings == []


def test_extract_results_null_is_clean():
    findings, err = sast_gate.extract_findings({"version": "2.1.0", "runs": [{"results": None}]})
    assert err is None and findings == []


def test_extract_results_not_list():
    findings, err = sast_gate.extract_findings({"version": "2.1.0", "runs": [{"results": {}}]})
    assert findings is None and "'results' is not a list" in err


def test_extract_result_not_object():
    findings, err = sast_gate.extract_findings(_sarif(["x"]))
    assert findings is None and "result entry" in err


def test_extract_rule_id_not_string():
    findings, err = sast_gate.extract_findings(_sarif([{"ruleId": 5}]))
    assert findings is None and "'ruleId' is not a string" in err


def test_extract_unknown_level_failclosed():
    findings, err = sast_gate.extract_findings(_sarif([_result(level="catastrophic")]))
    assert findings is None and "unknown SARIF result level" in err


def test_extract_level_non_string_failclosed():
    findings, err = sast_gate.extract_findings(_sarif([_result(level=3)]))
    assert findings is None and "unknown SARIF result level" in err


def test_extract_default_level_when_absent():
    findings, err = sast_gate.extract_findings(_sarif([_result(level=None)]))
    assert err is None and findings[0].level == sast_gate.DEFAULT_LEVEL


# --------------------------------------------------------------------------- #
# _message_text / _location best-effort branches
# --------------------------------------------------------------------------- #
def test_message_text_variants():
    assert sast_gate._message_text({"message": {"text": "hi"}}) == "hi"
    assert sast_gate._message_text({"message": {"text": 5}}) == ""
    assert sast_gate._message_text({"message": {}}) == ""
    assert sast_gate._message_text({"message": "nope"}) == ""
    assert sast_gate._message_text({}) == ""


def test_location_full():
    r = {"locations": [{"physicalLocation": {"artifactLocation": {"uri": "f.py"}, "region": {"startLine": 7}}}]}
    assert sast_gate._location(r) == "f.py:7"


def test_location_uri_only_when_no_line():
    r = {"locations": [{"physicalLocation": {"artifactLocation": {"uri": "f.py"}}}]}
    assert sast_gate._location(r) == "f.py"


def test_location_bool_line_is_not_treated_as_int():
    r = {"locations": [{"physicalLocation": {"artifactLocation": {"uri": "f.py"}, "region": {"startLine": True}}}]}
    assert sast_gate._location(r) == "f.py"


def test_location_missing_uri():
    r = {"locations": [{"physicalLocation": {"region": {"startLine": 7}}}]}
    assert sast_gate._location(r) == "<unknown>"


def test_location_physical_not_dict():
    assert sast_gate._location({"locations": [{"physicalLocation": "x"}]}) == "<unknown>"


def test_location_first_not_dict():
    assert sast_gate._location({"locations": ["x"]}) == "<unknown>"


def test_location_absent_or_empty():
    assert sast_gate._location({}) == "<unknown>"
    assert sast_gate._location({"locations": []}) == "<unknown>"


# --------------------------------------------------------------------------- #
# summarize / decide
# --------------------------------------------------------------------------- #
def test_summarize_empty_and_nonempty():
    assert sast_gate.summarize([]) == "no SARIF findings"
    findings = [sast_gate.Finding("R", "note", "m", "a:1"), sast_gate.Finding("R", "error", "m", "a:2")]
    assert "highest level: error" in sast_gate.summarize(findings)


def test_decide_advisory_passes_with_findings():
    findings = [sast_gate.Finding("R", "error", "m", "a:1")]
    code, msg = sast_gate.decide(findings, enforce=False, min_level="error")
    assert code == sast_gate.EXIT_OK and "1 SARIF finding" in msg


def test_decide_enforce_blocks_at_threshold():
    findings = [sast_gate.Finding("R", "error", "m", "a:1")]
    code, msg = sast_gate.decide(findings, enforce=True, min_level="error")
    assert code == sast_gate.EXIT_FAIL and "at or above 'error'" in msg


def test_decide_enforce_passes_below_threshold():
    findings = [sast_gate.Finding("R", "note", "m", "a:1")]
    code, msg = sast_gate.decide(findings, enforce=True, min_level="error")
    assert code == sast_gate.EXIT_OK and "no findings at or above 'error'" in msg


def test_decide_enforce_warning_threshold_catches_warning():
    findings = [sast_gate.Finding("R", "warning", "m", "a:1")]
    code, _ = sast_gate.decide(findings, enforce=True, min_level="warning")
    assert code == sast_gate.EXIT_FAIL


# --------------------------------------------------------------------------- #
# render_summary_markdown / append_summary
# --------------------------------------------------------------------------- #
def test_render_summary_empty():
    out = sast_gate.render_summary_markdown([])
    assert "No SARIF findings." in out


def test_render_summary_escapes_pipe():
    findings = [sast_gate.Finding("R", "error", "a | b\nc", "a:1")]
    out = sast_gate.render_summary_markdown(findings)
    assert "a \\| b c" in out and "| error | R |" in out


def test_append_summary_appends(tmp_path: Path):
    target = tmp_path / "summary.md"
    target.write_text("pre\n", encoding="utf-8")
    sast_gate.append_summary(str(target), [sast_gate.Finding("R", "note", "m", "a:1")])
    text = target.read_text(encoding="utf-8")
    assert text.startswith("pre\n") and "SAST (SARIF) findings" in text


# --------------------------------------------------------------------------- #
# load_json / read_source
# --------------------------------------------------------------------------- #
def test_load_json_valid():
    payload, err = sast_gate.load_json('{"a": 1}')
    assert payload == {"a": 1} and err is None


def test_load_json_empty():
    payload, err = sast_gate.load_json("   ")
    assert payload is None and "empty" in err


def test_load_json_malformed():
    payload, err = sast_gate.load_json("{nope")
    assert payload is None and "malformed" in err


def test_read_source_file(tmp_path: Path):
    p = tmp_path / "x.sarif"
    p.write_text("{}", encoding="utf-8")
    assert sast_gate.read_source(str(p)) == "{}"


def test_read_source_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert sast_gate.read_source("-") == "{}"


# --------------------------------------------------------------------------- #
# run() — CLI + exit codes + durable summary
# --------------------------------------------------------------------------- #
def test_run_advisory_clean_exit0(tmp_path: Path, capsys):
    p = tmp_path / "c.sarif"
    p.write_text(json.dumps(_sarif([])), encoding="utf-8")
    assert sast_gate.run(["--sarif", str(p)]) == sast_gate.EXIT_OK
    assert "OK" in capsys.readouterr().out


def test_run_advisory_with_findings_exit0(tmp_path: Path, capsys):
    p = tmp_path / "f.sarif"
    p.write_text(json.dumps(_sarif([_result(level="error")])), encoding="utf-8")
    assert sast_gate.run(["--sarif", str(p)]) == sast_gate.EXIT_OK
    assert "ADVISORY" in capsys.readouterr().out


def test_run_enforce_fails_exit1(tmp_path: Path, capsys):
    p = tmp_path / "f.sarif"
    p.write_text(json.dumps(_sarif([_result(level="error")])), encoding="utf-8")
    assert sast_gate.run(["--sarif", str(p), "--enforce", "--min-level", "error"]) == sast_gate.EXIT_FAIL
    assert "FAIL" in capsys.readouterr().err


def test_run_enforce_passes_below_threshold(tmp_path: Path):
    p = tmp_path / "f.sarif"
    p.write_text(json.dumps(_sarif([_result(level="note")])), encoding="utf-8")
    assert sast_gate.run(["--sarif", str(p), "--enforce", "--min-level", "error"]) == sast_gate.EXIT_OK


def test_run_malformed_failclosed(tmp_path: Path, capsys):
    p = tmp_path / "m.sarif"
    p.write_text("{bad", encoding="utf-8")
    assert sast_gate.run(["--sarif", str(p)]) == sast_gate.EXIT_FAIL
    assert "failing closed" in capsys.readouterr().err


def test_run_unknown_version_failclosed(tmp_path: Path, capsys):
    p = tmp_path / "v.sarif"
    p.write_text(json.dumps(_sarif([], version="9.9.9")), encoding="utf-8")
    assert sast_gate.run(["--sarif", str(p)]) == sast_gate.EXIT_FAIL
    assert "failing closed" in capsys.readouterr().err


def test_run_missing_file_usage(tmp_path: Path, capsys):
    assert sast_gate.run(["--sarif", str(tmp_path / "ghost.sarif")]) == sast_gate.EXIT_USAGE
    assert "cannot read" in capsys.readouterr().err


def test_run_summary_file_written(tmp_path: Path):
    p = tmp_path / "f.sarif"
    p.write_text(json.dumps(_sarif([_result(level="warning")])), encoding="utf-8")
    summary = tmp_path / "step-summary.md"
    assert sast_gate.run(["--sarif", str(p), "--summary-file", str(summary)]) == sast_gate.EXIT_OK
    assert "SAST (SARIF) findings" in summary.read_text(encoding="utf-8")


def test_run_summary_file_unwritable_usage(tmp_path: Path, capsys):
    p = tmp_path / "f.sarif"
    p.write_text(json.dumps(_sarif([])), encoding="utf-8")
    bad_summary = tmp_path / "no-such-dir" / "summary.md"
    assert sast_gate.run(["--sarif", str(p), "--summary-file", str(bad_summary)]) == sast_gate.EXIT_USAGE
    assert "cannot write summary" in capsys.readouterr().err


def test_run_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_sarif([]))))
    assert sast_gate.run(["--sarif", "-"]) == sast_gate.EXIT_OK


# Mutation-kill: pin the exit-code contract and required CLI args (survived mutants).
def test_exit_code_contract():
    assert (sast_gate.EXIT_OK, sast_gate.EXIT_FAIL, sast_gate.EXIT_USAGE) == (0, 1, 2)


def test_sarif_arg_is_required():
    with pytest.raises(SystemExit):
        sast_gate.parse_args([])
