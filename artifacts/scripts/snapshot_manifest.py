#!/usr/bin/env python3
"""snapshot_manifest.py — generate/verify a content-addressed integrity manifest over the
council-forge ``template/`` SSOT snapshot (the real release surface propagated to downstreams).

This is the producer-side complement of release_gate.py (the structural validator): it WALKS
the template tree and emits / re-derives a checksums manifest. council-forge publishes the
generated manifest at ``.well-known/release-manifest.json`` as PS.2.1 "integrity verification
information available to acquirers"; an acquirer can independently recompute and compare.

Determinism (byte-reproducibility is the whole point — a hash nobody can reproduce is theater):
  - paths are normalised to POSIX (``/``) so a Windows-generated manifest verifies on Linux CI,
  - TEXT file line endings are normalised (CRLF/CR -> LF) BEFORE hashing, so a manifest generated
    on a CRLF working tree (e.g. Windows, autocrlf) is byte-identical to one generated on LF
    (Linux CI). A file is treated as text iff it decodes as UTF-8 AND contains no NUL byte;
    otherwise it is binary and hashed raw (fail-closed — line endings are never touched). The
    manifest DECLARES this in ``digest_canonicalization`` so an acquirer can reproduce it; the
    schema is ``@2`` (``@1`` was raw-byte and is NOT cross-platform reproducible for text).
  - a fixed cruft exclusion set (VCS / editor / OS noise) keeps the file SET stable,
  - entries are sorted by path and there is NO wall-clock field; the ``root`` is a Merkle-ish
    digest over the sorted ``path\\0digest`` lines and is the snapshot's content-address.

Source-only (a downstream terminal repo does not own the release-integrity program), so this
file is NOT mirrored into ``template/`` and is NOT in EXACT_SYNC_FILES — same discipline as
scaffold_downstream.py / drift_dashboard.py / propagate_downstream.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Sequence

EXIT_OK = 0
EXIT_ERROR = 1

SCHEMA = "council-forge/release-manifest@2"
ALGORITHM = "sha256"
# Declares HOW digests are canonicalised so an acquirer can reproduce them independently.
# "text-eol-lf-v1": text files (UTF-8-decodable AND no NUL) are LF-normalised before hashing;
# binary files are hashed raw. Bump this token if the canonicalisation rule ever changes.
DIGEST_CANONICALIZATION = "text-eol-lf-v1"

# Cruft excluded so the manifest is byte-reproducible across environments (no .DS_Store on a
# Mac, no __pycache__ from a test run, etc.). Directory NAMES pruned anywhere in the path;
# file SUFFIXES and exact NAMES skipped.
EXCLUDE_DIRS = frozenset({".git", "__pycache__", ".mypy_cache", ".pytest_cache"})
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".swp")
EXCLUDE_NAMES = frozenset({".DS_Store", "Thumbs.db"})


def is_excluded(rel_posix: str, name: str) -> bool:
    """True if a file should be excluded from the manifest (cruft / editor / VCS noise)."""
    if name in EXCLUDE_NAMES or name.endswith("~"):
        return True
    if name.endswith(EXCLUDE_SUFFIXES):
        return True
    return any(part in EXCLUDE_DIRS for part in PurePosixPath(rel_posix).parts)


def is_text(data: bytes) -> bool:
    """True iff ``data`` is text: decodes as UTF-8 AND contains no NUL byte.

    Fail-closed for the binary path: anything not provably UTF-8-and-NUL-free (incl. binaries
    without an early NUL) is treated as binary and hashed raw, so its bytes are never mutated.
    """
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def canonicalize_text(data: bytes) -> bytes:
    """Normalise text line endings to LF: CRLF -> LF first, then any lone CR -> LF."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_file(path: Path) -> str:
    # Whole-file read (not chunked): a chunked CRLF/CR->LF replace could split a ``\r\n`` that
    # straddles a chunk boundary into ``\n\n`` and break determinism. template files are small.
    data = path.read_bytes()
    if is_text(data):
        data = canonicalize_text(data)
    return hashlib.sha256(data).hexdigest()


def compute_manifest(template_root: Path) -> dict:
    """Compute a deterministic content-addressed manifest over ``template_root``."""
    entries: List[Dict[str, str]] = []
    for path in template_root.rglob("*"):
        if not path.is_file():
            continue
        rel_posix = path.relative_to(template_root).as_posix()
        if is_excluded(rel_posix, path.name):
            continue
        entries.append({"path": rel_posix, ALGORITHM: sha256_file(path)})
    entries.sort(key=lambda entry: entry["path"])
    root = hashlib.sha256(
        "".join(f"{entry['path']}\0{entry[ALGORITHM]}\n" for entry in entries).encode("utf-8")
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "algorithm": ALGORITHM,
        "digest_canonicalization": DIGEST_CANONICALIZATION,
        "entries": entries,
        "root": root,
    }


def diff_manifest(expected: dict, actual: dict) -> List[str]:
    """Human-readable differences (entries + root) between a published and a recomputed manifest."""
    diffs: List[str] = []
    exp = {entry.get("path"): entry.get(ALGORITHM) for entry in expected.get("entries", [])}
    act = {entry.get("path"): entry.get(ALGORITHM) for entry in actual.get("entries", [])}
    for path in sorted(set(exp) - set(act)):
        diffs.append(f"in manifest but not in tree: {path}")
    for path in sorted(set(act) - set(exp)):
        diffs.append(f"in tree but not in manifest: {path}")
    for path in sorted(set(exp) & set(act)):
        if exp[path] != act[path]:
            diffs.append(f"digest changed: {path}")
    if expected.get("root") != actual.get("root"):
        diffs.append("root digest mismatch")
    return diffs


def write_manifest(path: str, manifest: dict) -> None:
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def default_template_root() -> Path:
    # snapshot_manifest.py lives at <root>/artifacts/scripts/snapshot_manifest.py
    return Path(__file__).resolve().parents[2] / "template"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate/verify the council-forge release-integrity manifest over template/."
    )
    parser.add_argument("command", choices=["generate", "verify"], help="generate a manifest or verify a tree against one.")
    parser.add_argument("--template-root", default="", help="Override the template/ source dir.")
    parser.add_argument("--output", help="(generate) Path to write the manifest JSON.")
    parser.add_argument("--manifest", help="(verify) Path to the published manifest to compare against.")
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    template_root = Path(args.template_root) if args.template_root else default_template_root()
    if not template_root.is_dir():
        print(f"[FAIL] template root does not exist: {template_root}", file=sys.stderr)
        return EXIT_ERROR

    if args.command == "generate":
        if not args.output:
            print("[FAIL] generate requires --output", file=sys.stderr)
            return EXIT_ERROR
        manifest = compute_manifest(template_root)
        try:
            write_manifest(args.output, manifest)
        except OSError as exc:
            print(f"[FAIL] cannot write manifest: {exc}", file=sys.stderr)
            return EXIT_ERROR
        print(f"[OK] wrote manifest: {len(manifest['entries'])} entr(y/ies); root {manifest['root'][:12]}")
        return EXIT_OK

    if not args.manifest:
        print("[FAIL] verify requires --manifest", file=sys.stderr)
        return EXIT_ERROR
    try:
        published = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"[FAIL] cannot read manifest: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except json.JSONDecodeError as exc:
        print(f"[FAIL] malformed manifest JSON: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if not isinstance(published, dict):
        print("[FAIL] manifest is not a JSON object", file=sys.stderr)
        return EXIT_ERROR
    pub_canon = published.get("digest_canonicalization")
    if pub_canon != DIGEST_CANONICALIZATION:
        print(
            f"[FAIL] manifest digest_canonicalization mismatch: expected "
            f"{DIGEST_CANONICALIZATION!r}, got {pub_canon!r} (fail-closed)",
            file=sys.stderr,
        )
        return EXIT_ERROR
    actual = compute_manifest(template_root)
    diffs = diff_manifest(published, actual)
    if diffs:
        print("[FAIL] published manifest does not match the template snapshot:", file=sys.stderr)
        for diff in diffs:
            print(f"  - {diff}", file=sys.stderr)
        return EXIT_ERROR
    print(f"[OK] manifest matches the template snapshot ({len(actual['entries'])} entr(y/ies))")
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
