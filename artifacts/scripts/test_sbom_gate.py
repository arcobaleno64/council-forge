"""Unit tests for sbom_gate.py — full-coverage, fail-closed CycloneDX SBOM gate."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import sbom_gate


# --------------------------------------------------------------------------- #
# CycloneDX fixture builder
# --------------------------------------------------------------------------- #
def _sbom(components="__default__", *, bom_format="CycloneDX", spec="1.6", version=1):
    doc = {}
    if bom_format is not None:
        doc["bomFormat"] = bom_format
    if spec is not None:
        doc["specVersion"] = spec
    if version is not None:
        doc["version"] = version
    if components != "__drop__":
        doc["components"] = [{"name": "PyYAML", "type": "library"}] if components == "__default__" else components
    return doc


def _eval(doc, min_components=1, required=frozenset(), normalization="exact"):
    return sbom_gate.evaluate(doc, min_components=min_components, required=required, normalization=normalization)


# --------------------------------------------------------------------------- #
# normalize_name
# --------------------------------------------------------------------------- #
def test_normalize_pep503():
    assert sbom_gate.normalize_name("PyYAML", "pep503") == "pyyaml"
    assert sbom_gate.normalize_name("foo_.-bar", "pep503") == "foo-bar"


def test_normalize_exact_preserves():
    assert sbom_gate.normalize_name("Foo_Bar", "exact") == "Foo_Bar"


# --------------------------------------------------------------------------- #
# parse_required
# --------------------------------------------------------------------------- #
def test_parse_required_none_skips():
    result, err = sbom_gate.parse_required(None, "exact")
    assert result == frozenset() and err is None


def test_parse_required_valid_multi():
    result, err = sbom_gate.parse_required("a, b ,c", "exact")
    assert err is None and result == {"a", "b", "c"}


def test_parse_required_pep503_normalizes():
    result, _ = sbom_gate.parse_required("PyYAML", "pep503")
    assert result == {"pyyaml"}


def test_parse_required_empty_string_errors():
    result, err = sbom_gate.parse_required("", "exact")
    assert result is None and "no names" in err


def test_parse_required_comma_only_errors():
    result, err = sbom_gate.parse_required(", , ", "exact")
    assert result is None and err is not None


# --------------------------------------------------------------------------- #
# evaluate — well-formedness
# --------------------------------------------------------------------------- #
def test_eval_valid():
    code, msg = _eval(_sbom())
    assert code == sbom_gate.EXIT_OK and "identity satisfied" in msg


def test_eval_not_object():
    assert _eval([1, 2])[0] == sbom_gate.EXIT_FAIL


def test_eval_bomformat_wrong_case_failclosed():
    assert _eval(_sbom(bom_format="cyclonedx"))[0] == sbom_gate.EXIT_FAIL


def test_eval_bomformat_missing_failclosed():
    assert _eval(_sbom(bom_format=None))[0] == sbom_gate.EXIT_FAIL


def test_eval_specversion_missing_failclosed():
    assert _eval(_sbom(spec=None))[0] == sbom_gate.EXIT_FAIL


def test_eval_specversion_unknown_failclosed():
    code, msg = _eval(_sbom(spec="9.9"))
    assert code == sbom_gate.EXIT_FAIL and "unsupported" in msg


def test_eval_specversion_non_string_failclosed():
    assert _eval(_sbom(spec=1.6))[0] == sbom_gate.EXIT_FAIL


def test_eval_all_supported_versions_ok():
    for spec in ("1.2", "1.3", "1.4", "1.5", "1.6", "1.7"):
        assert _eval(_sbom(spec=spec))[0] == sbom_gate.EXIT_OK


def test_eval_version_zero_failclosed():
    assert _eval(_sbom(version=0))[0] == sbom_gate.EXIT_FAIL


def test_eval_version_bool_failclosed():
    assert _eval(_sbom(version=True))[0] == sbom_gate.EXIT_FAIL


def test_eval_version_string_failclosed():
    assert _eval(_sbom(version="1"))[0] == sbom_gate.EXIT_FAIL


def test_eval_version_absent_ok():
    assert _eval(_sbom(version=None))[0] == sbom_gate.EXIT_OK


# --------------------------------------------------------------------------- #
# evaluate — components shape + per-version type allowlist
# --------------------------------------------------------------------------- #
def test_eval_components_null_is_empty_min0_ok():
    doc = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "components": None}
    assert _eval(doc, min_components=0)[0] == sbom_gate.EXIT_OK


def test_eval_components_not_list_failclosed():
    assert _eval(_sbom(components={}))[0] == sbom_gate.EXIT_FAIL


def test_eval_component_not_object_failclosed():
    assert _eval(_sbom(components=["x"]))[0] == sbom_gate.EXIT_FAIL


def test_eval_component_name_missing_failclosed():
    assert _eval(_sbom(components=[{"type": "library"}]))[0] == sbom_gate.EXIT_FAIL


def test_eval_component_name_empty_failclosed():
    assert _eval(_sbom(components=[{"name": "", "type": "library"}]))[0] == sbom_gate.EXIT_FAIL


def test_eval_component_type_not_string_failclosed():
    assert _eval(_sbom(components=[{"name": "A", "type": 5}]))[0] == sbom_gate.EXIT_FAIL


def test_eval_base8_type_ok_any_version():
    assert _eval(_sbom(components=[{"name": "A", "type": "library"}], spec="1.2"))[0] == sbom_gate.EXIT_OK


def test_eval_crypto_asset_ok_on_17_failclosed_on_14():
    crypto = [{"name": "A", "type": "cryptographic-asset"}]
    assert _eval(_sbom(components=crypto, spec="1.7"))[0] == sbom_gate.EXIT_OK
    code, msg = _eval(_sbom(components=crypto, spec="1.4"))
    assert code == sbom_gate.EXIT_FAIL and "not valid for CycloneDX 1.4" in msg


def test_eval_v15_type_ok_on_15_failclosed_on_14():
    data = [{"name": "A", "type": "data"}]
    assert _eval(_sbom(components=data, spec="1.5"))[0] == sbom_gate.EXIT_OK
    assert _eval(_sbom(components=data, spec="1.4"))[0] == sbom_gate.EXIT_FAIL


# --------------------------------------------------------------------------- #
# evaluate — min-components + require-components identity
# --------------------------------------------------------------------------- #
def test_eval_empty_components_failclosed_default_min():
    assert _eval(_sbom(components=[]))[0] == sbom_gate.EXIT_FAIL


def test_eval_missing_components_failclosed_default_min():
    code, msg = _eval(_sbom(components="__drop__"))
    assert code == sbom_gate.EXIT_FAIL and "min-components" in msg


def test_eval_min_zero_allows_empty():
    assert _eval(_sbom(components=[]), min_components=0)[0] == sbom_gate.EXIT_OK


def test_eval_required_present_ok():
    code, _ = _eval(_sbom(), required=frozenset({"pyyaml"}), normalization="pep503")
    assert code == sbom_gate.EXIT_OK


def test_eval_required_missing_failclosed():
    code, msg = _eval(_sbom(), required=frozenset({"requests"}), normalization="pep503")
    assert code == sbom_gate.EXIT_FAIL and "requests" in msg


def test_eval_required_not_satisfied_by_unrelated_count():
    # count alone would pass min=1, but the required direct dep is absent -> fail-closed
    doc = _sbom(components=[{"name": "unrelated", "type": "library"}])
    assert _eval(doc, required=frozenset({"pyyaml"}), normalization="pep503")[0] == sbom_gate.EXIT_FAIL


def test_eval_exact_normalization_does_not_fold_punctuation():
    doc = _sbom(components=[{"name": "foo_bar", "type": "library"}])
    assert _eval(doc, required=frozenset({"foo-bar"}), normalization="exact")[0] == sbom_gate.EXIT_FAIL


# --------------------------------------------------------------------------- #
# render_summary_markdown / append_summary
# --------------------------------------------------------------------------- #
def test_summary_with_components():
    out = sbom_gate.render_summary_markdown(_sbom())
    assert "specVersion: `1.6`" in out and "PyYAML" in out and "ADVISORY" in out


def test_summary_empty_components():
    out = sbom_gate.render_summary_markdown(_sbom(components=[]))
    assert "components: 0" in out and "| Name | Type |" not in out and "ADVISORY" in out


def test_summary_non_dict_payload():
    out = sbom_gate.render_summary_markdown([1, 2])
    assert "components: 0" in out and "ADVISORY" in out


def test_summary_escapes_pipe():
    out = sbom_gate.render_summary_markdown(_sbom(components=[{"name": "a|b", "type": "library"}]))
    assert "a\\|b" in out


def test_append_summary_appends(tmp_path: Path):
    target = tmp_path / "summary.md"
    target.write_text("pre\n", encoding="utf-8")
    sbom_gate.append_summary(str(target), _sbom())
    text = target.read_text(encoding="utf-8")
    assert text.startswith("pre\n") and "SBOM (CycloneDX)" in text


# --------------------------------------------------------------------------- #
# load_json / read_source
# --------------------------------------------------------------------------- #
def test_load_json_valid():
    payload, err = sbom_gate.load_json('{"a": 1}')
    assert payload == {"a": 1} and err is None


def test_load_json_empty():
    payload, err = sbom_gate.load_json("   ")
    assert payload is None and "empty" in err


def test_load_json_malformed():
    payload, err = sbom_gate.load_json("{nope")
    assert payload is None and "malformed" in err


def test_read_source_file(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    assert sbom_gate.read_source(str(p)) == "{}"


def test_read_source_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert sbom_gate.read_source("-") == "{}"


# --------------------------------------------------------------------------- #
# run() — CLI, exit codes, standing advisory
# --------------------------------------------------------------------------- #
def test_run_pass_exit0_advisory_on_stdout(tmp_path: Path, capsys):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom()), encoding="utf-8")
    assert sbom_gate.run(["--sbom", str(p)]) == sbom_gate.EXIT_OK
    out = capsys.readouterr().out
    assert "[OK]" in out and "ADVISORY" in out


def test_run_schema_fail_exit1_advisory_on_stderr(tmp_path: Path, capsys):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom(bom_format="cyclonedx")), encoding="utf-8")
    assert sbom_gate.run(["--sbom", str(p)]) == sbom_gate.EXIT_FAIL
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "ADVISORY" in err


def test_run_malformed_failclosed(tmp_path: Path, capsys):
    p = tmp_path / "m.json"
    p.write_text("{bad", encoding="utf-8")
    assert sbom_gate.run(["--sbom", str(p)]) == sbom_gate.EXIT_FAIL
    assert "failing closed" in capsys.readouterr().err


def test_run_require_empty_exit2(tmp_path: Path, capsys):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom()), encoding="utf-8")
    assert sbom_gate.run(["--sbom", str(p), "--require-components", ""]) == sbom_gate.EXIT_USAGE
    assert "degrade" in capsys.readouterr().err


def test_run_require_present_pep503_pass(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom()), encoding="utf-8")
    code = sbom_gate.run(["--sbom", str(p), "--require-components", "PyYAML", "--name-normalization", "pep503"])
    assert code == sbom_gate.EXIT_OK


def test_run_require_missing_fail(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom()), encoding="utf-8")
    assert sbom_gate.run(["--sbom", str(p), "--require-components", "requests", "--name-normalization", "pep503"]) == sbom_gate.EXIT_FAIL


def test_run_missing_file_usage(tmp_path: Path, capsys):
    assert sbom_gate.run(["--sbom", str(tmp_path / "ghost.json")]) == sbom_gate.EXIT_USAGE
    assert "cannot read" in capsys.readouterr().err


def test_run_min_components_zero_allows_empty(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom(components=[])), encoding="utf-8")
    assert sbom_gate.run(["--sbom", str(p), "--min-components", "0"]) == sbom_gate.EXIT_OK


def test_run_summary_file_written(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom()), encoding="utf-8")
    summary = tmp_path / "step-summary.md"
    assert sbom_gate.run(["--sbom", str(p), "--summary-file", str(summary)]) == sbom_gate.EXIT_OK
    text = summary.read_text(encoding="utf-8")
    assert "SBOM (CycloneDX)" in text and "ADVISORY" in text


def test_run_summary_file_unwritable_usage(tmp_path: Path, capsys):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_sbom()), encoding="utf-8")
    bad_summary = tmp_path / "no-such-dir" / "summary.md"
    assert sbom_gate.run(["--sbom", str(p), "--summary-file", str(bad_summary)]) == sbom_gate.EXIT_USAGE
    assert "cannot write summary" in capsys.readouterr().err


def test_run_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_sbom())))
    assert sbom_gate.run(["--sbom", "-"]) == sbom_gate.EXIT_OK
