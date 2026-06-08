"""Unit tests for snapshot_manifest.py — source-only release-integrity manifest generator.

Covers determinism, cruft exclusion, POSIX path normalisation, diff/verify, content-address
regression (a snapshot manifest still verifies its tree after the live tree advances), and the
generate/verify CLI orchestration.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import snapshot_manifest as sm


def make_tree(root: Path) -> Path:
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    sub = root / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("beta", encoding="utf-8")
    return root


# --- is_excluded --------------------------------------------------------------------------

def test_is_excluded_ds_store():
    assert sm.is_excluded(".DS_Store", ".DS_Store") is True


def test_is_excluded_tilde():
    assert sm.is_excluded("c.txt~", "c.txt~") is True


def test_is_excluded_pyc_suffix():
    assert sm.is_excluded("d.pyc", "d.pyc") is True


def test_is_excluded_dir_component():
    assert sm.is_excluded("__pycache__/x.bin", "x.bin") is True


def test_is_excluded_regular():
    assert sm.is_excluded("sub/b.txt", "b.txt") is False


# --- sha256_file / compute_manifest -------------------------------------------------------

def test_sha256_file(tmp_path):
    path = tmp_path / "f"
    path.write_text("alpha", encoding="utf-8")
    import hashlib
    assert sm.sha256_file(path) == hashlib.sha256(b"alpha").hexdigest()


def test_compute_manifest_basic(tmp_path):
    make_tree(tmp_path)
    manifest = sm.compute_manifest(tmp_path)
    assert manifest["schema"] == sm.SCHEMA
    assert manifest["algorithm"] == "sha256"
    paths = [entry["path"] for entry in manifest["entries"]]
    assert paths == ["a.txt", "sub/b.txt"]  # sorted + POSIX separators


def test_compute_manifest_deterministic(tmp_path):
    make_tree(tmp_path)
    assert sm.compute_manifest(tmp_path) == sm.compute_manifest(tmp_path)


def test_compute_manifest_excludes_cruft(tmp_path):
    make_tree(tmp_path)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_text("", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("", encoding="utf-8")
    (tmp_path / "note.txt~").write_text("", encoding="utf-8")
    (tmp_path / "mod.pyc").write_text("", encoding="utf-8")
    paths = [entry["path"] for entry in sm.compute_manifest(tmp_path)["entries"]]
    assert paths == ["a.txt", "sub/b.txt"]


def test_compute_manifest_root_changes_with_content(tmp_path):
    make_tree(tmp_path)
    root_before = sm.compute_manifest(tmp_path)["root"]
    (tmp_path / "a.txt").write_text("ALPHA-changed", encoding="utf-8")
    assert sm.compute_manifest(tmp_path)["root"] != root_before


# --- diff_manifest ------------------------------------------------------------------------

def test_diff_manifest_identical(tmp_path):
    make_tree(tmp_path)
    manifest = sm.compute_manifest(tmp_path)
    assert sm.diff_manifest(manifest, manifest) == []


def test_diff_manifest_all_kinds():
    expected = {
        "entries": [{"path": "keep", "sha256": "x"}, {"path": "gone", "sha256": "y"}, {"path": "chg", "sha256": "1"}],
        "root": "R1",
    }
    actual = {
        "entries": [{"path": "keep", "sha256": "x"}, {"path": "new", "sha256": "z"}, {"path": "chg", "sha256": "2"}],
        "root": "R2",
    }
    diffs = sm.diff_manifest(expected, actual)
    assert any("in manifest but not in tree: gone" in d for d in diffs)
    assert any("in tree but not in manifest: new" in d for d in diffs)
    assert any("digest changed: chg" in d for d in diffs)
    assert "root digest mismatch" in diffs


# --- write_manifest -----------------------------------------------------------------------

def test_write_manifest(tmp_path):
    make_tree(tmp_path)
    manifest = sm.compute_manifest(tmp_path)
    out = tmp_path / "m.json"
    sm.write_manifest(str(out), manifest)
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n") and json.loads(text) == manifest


def test_default_template_root():
    assert sm.default_template_root().name == "template"


# --- run: generate ------------------------------------------------------------------------

def test_run_generate_ok(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    out = tmp_path / "manifest.json"
    rc = sm.run(["generate", "--template-root", str(src), "--output", str(out)])
    assert rc == sm.EXIT_OK
    assert "wrote manifest" in capsys.readouterr().out
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == sm.SCHEMA


def test_run_generate_requires_output(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    rc = sm.run(["generate", "--template-root", str(src)])
    assert rc == sm.EXIT_ERROR and "requires --output" in capsys.readouterr().err


def test_run_generate_write_error(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    bad = tmp_path / "missing" / "manifest.json"  # parent does not exist
    rc = sm.run(["generate", "--template-root", str(src), "--output", str(bad)])
    assert rc == sm.EXIT_ERROR and "cannot write manifest" in capsys.readouterr().err


def test_run_template_root_missing(tmp_path, capsys):
    rc = sm.run(["generate", "--template-root", str(tmp_path / "nope"), "--output", str(tmp_path / "m.json")])
    assert rc == sm.EXIT_ERROR and "template root does not exist" in capsys.readouterr().err


# --- run: verify --------------------------------------------------------------------------

def test_run_verify_ok(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    manifest_path = tmp_path / "m.json"
    sm.write_manifest(str(manifest_path), sm.compute_manifest(src))
    rc = sm.run(["verify", "--template-root", str(src), "--manifest", str(manifest_path)])
    assert rc == sm.EXIT_OK and "matches the template snapshot" in capsys.readouterr().out


def test_run_verify_requires_manifest(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    rc = sm.run(["verify", "--template-root", str(src)])
    assert rc == sm.EXIT_ERROR and "requires --manifest" in capsys.readouterr().err


def test_run_verify_read_error(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    rc = sm.run(["verify", "--template-root", str(src), "--manifest", str(tmp_path / "nope.json")])
    assert rc == sm.EXIT_ERROR and "cannot read manifest" in capsys.readouterr().err


def test_run_verify_malformed(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    rc = sm.run(["verify", "--template-root", str(src), "--manifest", str(bad)])
    assert rc == sm.EXIT_ERROR and "malformed manifest JSON" in capsys.readouterr().err


def test_run_verify_non_dict(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    arr = tmp_path / "arr.json"
    arr.write_text("[]", encoding="utf-8")
    rc = sm.run(["verify", "--template-root", str(src), "--manifest", str(arr)])
    assert rc == sm.EXIT_ERROR and "not a JSON object" in capsys.readouterr().err


def test_run_verify_mismatch(tmp_path, capsys):
    src = tmp_path / "tpl"
    src.mkdir()
    make_tree(src)
    manifest_path = tmp_path / "m.json"
    sm.write_manifest(str(manifest_path), sm.compute_manifest(src))
    (src / "a.txt").write_text("tampered", encoding="utf-8")  # tree advances
    rc = sm.run(["verify", "--template-root", str(src), "--manifest", str(manifest_path)])
    assert rc == sm.EXIT_ERROR
    assert "does not match" in capsys.readouterr().err


def test_content_address_regression(tmp_path, capsys):
    """A snapshot-A manifest still verifies tree-A even after the live tree advances to B."""
    tree_a = tmp_path / "a"
    tree_a.mkdir()
    make_tree(tree_a)
    manifest_a = tmp_path / "manifest_a.json"
    sm.write_manifest(str(manifest_a), sm.compute_manifest(tree_a))

    # council-forge HEAD advances: a different snapshot B (different content).
    tree_b = tmp_path / "b"
    tree_b.mkdir()
    make_tree(tree_b)
    (tree_b / "a.txt").write_text("B-snapshot-content", encoding="utf-8")

    # manifest_A still verifies tree-A (content-address binds to A's bytes, not to HEAD).
    assert sm.run(["verify", "--template-root", str(tree_a), "--manifest", str(manifest_a)]) == sm.EXIT_OK
    # ...and does NOT verify the advanced snapshot B.
    assert sm.run(["verify", "--template-root", str(tree_b), "--manifest", str(manifest_a)]) == sm.EXIT_ERROR
