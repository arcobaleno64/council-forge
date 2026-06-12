"""Unit tests for release_gate.py — fail-closed release-integrity (checksums manifest) gate.

Targets 100% line coverage of the source module (CLI plumbing excluded via .coveragerc).
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

import release_gate as rg

D1 = hashlib.sha256(b"one").hexdigest()
D2 = hashlib.sha256(b"two").hexdigest()
ROOT = hashlib.sha256(b"root").hexdigest()
ALLZERO = "0" * 64


def manifest(entries=None, **over):
    doc = {
        "schema": "council-forge/release-manifest@1",
        "algorithm": "sha256",
        "entries": [{"path": "a.py", "sha256": D1}] if entries is None else entries,
        "root": ROOT,
    }
    doc.update(over)
    return doc


def write(tmp_path: Path, obj) -> str:
    path = tmp_path / "m.json"
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


# --- reject_placeholder / validate_digest -------------------------------------------------

def test_reject_placeholder_empty():
    assert rg.reject_placeholder("") is True


def test_reject_placeholder_sentinel():
    assert rg.reject_placeholder("todo" + "a" * 60) is True


def test_reject_placeholder_all_same():
    assert rg.reject_placeholder(ALLZERO) is True


def test_reject_placeholder_real():
    assert rg.reject_placeholder(D1) is False


def test_validate_digest_not_str():
    assert "not a string" in rg.validate_digest("sha256", 123)


def test_validate_digest_bool_not_str():
    # bool is an int subclass; type(x) is str must reject it
    assert rg.validate_digest("sha256", True) is not None


def test_validate_digest_wrong_length():
    assert "64 lowercase-hex" in rg.validate_digest("sha256", "abc")


def test_validate_digest_not_hex():
    assert "not lowercase hex" in rg.validate_digest("sha256", "g" * 64)


def test_validate_digest_placeholder():
    assert "placeholder" in rg.validate_digest("sha256", ALLZERO)


def test_validate_digest_valid_sha256():
    assert rg.validate_digest("sha256", D1) is None


def test_validate_digest_valid_sha512():
    d = hashlib.sha512(b"x").hexdigest()
    assert rg.validate_digest("sha512", d) is None


# --- parse_require_paths ------------------------------------------------------------------

def test_parse_require_paths_none():
    result, error = rg.parse_require_paths(None)
    assert result == frozenset() and error is None


def test_parse_require_paths_valid():
    result, error = rg.parse_require_paths("a.py, b.py")
    assert result == frozenset({"a.py", "b.py"}) and error is None


def test_parse_require_paths_empty():
    result, error = rg.parse_require_paths(" , ")
    assert result is None and "refusing to degrade" in error


# --- evaluate_checksums -------------------------------------------------------------------

def test_evaluate_valid():
    code, msg = rg.evaluate_checksums(manifest(), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_OK and "valid release manifest" in msg


def test_evaluate_top_level_not_dict():
    code, msg = rg.evaluate_checksums([], require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "top-level is not an object" in msg


def test_evaluate_schema_missing():
    doc = manifest()
    del doc["schema"]
    code, msg = rg.evaluate_checksums(doc, require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "unsupported manifest schema" in msg


def test_evaluate_schema_non_str():
    code, msg = rg.evaluate_checksums(manifest(schema=1), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "unsupported manifest schema" in msg


def test_evaluate_schema_unknown():
    code, msg = rg.evaluate_checksums(manifest(schema="other@1"), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL


# --- schema @2 digest_canonicalization (structural presence) ------------------------------

def test_evaluate_schema_v1_no_canonicalization_passes():
    # @1 (legacy raw-byte) does NOT require digest_canonicalization -> backward compatible.
    doc = manifest()
    assert "digest_canonicalization" not in doc
    code, msg = rg.evaluate_checksums(doc, require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_OK


def test_evaluate_schema_v2_with_canonicalization_passes():
    doc = manifest(schema=rg.SCHEMA_V2, digest_canonicalization="text-eol-lf-v1")
    code, msg = rg.evaluate_checksums(doc, require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_OK and "valid release manifest" in msg


def test_evaluate_schema_v2_missing_canonicalization_fails_closed():
    doc = manifest(schema=rg.SCHEMA_V2)  # @2 but no digest_canonicalization
    code, msg = rg.evaluate_checksums(doc, require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "digest_canonicalization" in msg


def test_evaluate_schema_v2_empty_canonicalization_fails_closed():
    doc = manifest(schema=rg.SCHEMA_V2, digest_canonicalization="")
    code, msg = rg.evaluate_checksums(doc, require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "digest_canonicalization" in msg


def test_evaluate_schema_v2_nonstring_canonicalization_fails_closed():
    doc = manifest(schema=rg.SCHEMA_V2, digest_canonicalization=1)
    code, msg = rg.evaluate_checksums(doc, require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "digest_canonicalization" in msg


def test_evaluate_algorithm_unknown():
    code, msg = rg.evaluate_checksums(manifest(algorithm="md5"), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "unsupported algorithm" in msg


def test_evaluate_entries_not_list():
    code, msg = rg.evaluate_checksums(manifest(entries={}), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "'entries' is not a list" in msg


def test_evaluate_entry_not_object():
    code, msg = rg.evaluate_checksums(manifest(entries=["x"]), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "an entry is not an object" in msg


def test_evaluate_entry_no_path():
    code, msg = rg.evaluate_checksums(
        manifest(entries=[{"sha256": D1}]), require_paths=frozenset(), min_entries=1
    )
    assert code == rg.EXIT_FAIL and "no non-empty string path" in msg


def test_evaluate_entry_empty_path():
    code, msg = rg.evaluate_checksums(
        manifest(entries=[{"path": "", "sha256": D1}]), require_paths=frozenset(), min_entries=1
    )
    assert code == rg.EXIT_FAIL and "no non-empty string path" in msg


def test_evaluate_duplicate_path():
    entries = [{"path": "a.py", "sha256": D1}, {"path": "a.py", "sha256": D2}]
    code, msg = rg.evaluate_checksums(manifest(entries=entries), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "duplicate entry path" in msg


def test_evaluate_entry_bad_digest():
    entries = [{"path": "a.py", "sha256": ALLZERO}]
    code, msg = rg.evaluate_checksums(manifest(entries=entries), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "entry 'a.py'" in msg


def test_evaluate_below_min_entries():
    code, msg = rg.evaluate_checksums(manifest(entries=[]), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and "< --min-entries 1" in msg


def test_evaluate_min_entries_zero_empty_ok():
    code, msg = rg.evaluate_checksums(manifest(entries=[]), require_paths=frozenset(), min_entries=0)
    assert code == rg.EXIT_OK


def test_evaluate_root_bad():
    code, msg = rg.evaluate_checksums(manifest(root=ALLZERO), require_paths=frozenset(), min_entries=1)
    assert code == rg.EXIT_FAIL and msg.startswith("root:")


def test_evaluate_require_paths_missing():
    code, msg = rg.evaluate_checksums(
        manifest(), require_paths=frozenset({"missing.py"}), min_entries=1
    )
    assert code == rg.EXIT_FAIL and "required paths absent" in msg


def test_evaluate_require_paths_present():
    code, msg = rg.evaluate_checksums(
        manifest(), require_paths=frozenset({"a.py"}), min_entries=1
    )
    assert code == rg.EXIT_OK


# --- render_summary_markdown --------------------------------------------------------------

def test_render_summary_valid():
    out = rg.render_summary_markdown(manifest())
    assert "release_gate" in out and "[ADVISORY]" in out


def test_render_summary_non_dict():
    out = rg.render_summary_markdown([])
    assert "schema: `None`" in out and "entries: 0" in out


def test_render_summary_entries_not_list():
    out = rg.render_summary_markdown(manifest(entries={}))
    assert "entries: 0" in out


# --- load_json / read_source --------------------------------------------------------------

def test_load_json_empty():
    payload, error = rg.load_json("   ")
    assert payload is None and error == "empty output"


def test_load_json_malformed():
    payload, error = rg.load_json("{bad")
    assert payload is None and "malformed JSON" in error


def test_load_json_valid():
    payload, error = rg.load_json('{"a": 1}')
    assert payload == {"a": 1} and error is None


def test_read_source_file(tmp_path):
    path = write(tmp_path, manifest())
    assert "schema" in rg.read_source(path)


def test_read_source_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("hello"))
    assert rg.read_source("-") == "hello"


# --- run (orchestration) ------------------------------------------------------------------

def test_run_ok(tmp_path, capsys):
    path = write(tmp_path, manifest())
    assert rg.run(["--format", "checksums", "--file", path]) == rg.EXIT_OK
    out = capsys.readouterr().out
    assert "[OK] release_gate" in out and "[ADVISORY]" in out


def test_run_require_paths_empty(tmp_path, capsys):
    path = write(tmp_path, manifest())
    rc = rg.run(["--format", "checksums", "--file", path, "--require-paths", " , "])
    assert rc == rg.EXIT_USAGE
    assert "refusing to degrade" in capsys.readouterr().err


def test_run_missing_file(tmp_path, capsys):
    rc = rg.run(["--format", "checksums", "--file", str(tmp_path / "nope.json")])
    assert rc == rg.EXIT_USAGE
    assert "cannot read manifest" in capsys.readouterr().err


def test_run_malformed_json(tmp_path, capsys):
    path = write(tmp_path, "{bad")
    rc = rg.run(["--format", "checksums", "--file", path])
    assert rc == rg.EXIT_FAIL
    assert "failing closed" in capsys.readouterr().err


def test_run_evaluate_fail(tmp_path, capsys):
    path = write(tmp_path, manifest(algorithm="md5"))
    rc = rg.run(["--format", "checksums", "--file", path])
    assert rc == rg.EXIT_FAIL
    assert "[FAIL] release_gate" in capsys.readouterr().err


def test_run_summary_ok(tmp_path):
    path = write(tmp_path, manifest())
    summary = tmp_path / "summary.md"
    rc = rg.run(["--format", "checksums", "--file", path, "--summary-file", str(summary)])
    assert rc == rg.EXIT_OK
    assert "[ADVISORY]" in summary.read_text(encoding="utf-8")


def test_run_summary_unwritable(tmp_path, capsys):
    path = write(tmp_path, manifest())
    bad = tmp_path / "nope" / "summary.md"  # parent dir does not exist -> OSError
    rc = rg.run(["--format", "checksums", "--file", path, "--summary-file", str(bad)])
    assert rc == rg.EXIT_USAGE
    assert "cannot write summary file" in capsys.readouterr().err


def test_run_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(manifest())))
    assert rg.run(["--format", "checksums", "--file", "-"]) == rg.EXIT_OK
