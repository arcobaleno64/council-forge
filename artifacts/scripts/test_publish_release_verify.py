"""TASK-1089 / FB-2: tests for the release-integrity + release-signing verification coupled
into publish-release.ps1 (logic lives in github_publish_common.ps1 testable functions).

Driven through pwsh: each test dot-sources github_publish_common.ps1, calls a function, and
reports OK:<state> / THREW via stdout so the Python side asserts on the verification outcome.

The gpg signer-binding tests MIRROR the CI release-integrity job semantics (capture-then-check,
VALIDSIG exact-fingerprint binding) and are gpg-gated (skipped wholesale if gpg is unavailable or
key generation fails in this environment) — same honesty discipline as test_release_signing.py.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
COMMON = SCRIPTS_DIR / "github_publish_common.ps1"
PUBLISH = SCRIPTS_DIR / "publish-release.ps1"


def _pwsh_exe() -> str:
    exe = shutil.which("pwsh") or (shutil.which("powershell.exe") if os.name == "nt" else None)
    if not exe:
        pytest.skip("pwsh/powershell unavailable")
    return exe


def _ps(p: Path) -> str:
    return str(p).replace("\\", "/")


def _call(body: str, *, env: dict | None = None) -> subprocess.CompletedProcess:
    """Dot-source the helpers and run `body`, surfacing OK:<state> or THREW:<msg> on stdout."""
    script = (
        f". '{_ps(COMMON)}'\n"
        "try {\n"
        f"{body}\n"
        "  Write-Output \"OK:$result\"\n"
        "} catch { Write-Output \"THREW:$($_.Exception.Message)\" }\n"
    )
    run_env = os.environ.copy()
    # default: signing UNprovisioned unless a test sets the pin
    run_env.pop("EXPECTED_SIGNING_FINGERPRINT", None)
    if env:
        run_env.update(env)
    return subprocess.run(
        [_pwsh_exe(), "-NoProfile", "-Command", script],
        capture_output=True, text=True, env=run_env,
    )


# --------------------------------------------------------------------------- #
# Helpers to build a minimal valid release surface (template/ + generated manifest)
# --------------------------------------------------------------------------- #
def _make_release_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "template").mkdir(parents=True)
    (root / "template" / "keep.txt").write_text("content\n", encoding="utf-8")
    (root / ".well-known").mkdir()
    manifest = root / ".well-known" / "release-manifest.json"
    res = subprocess.run(
        ["python", str(SCRIPTS_DIR / "snapshot_manifest.py"), "generate",
         "--template-root", str(root / "template"), "--output", str(manifest)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    return root


# --------------------------------------------------------------------------- #
# Get-RepoRoot
# --------------------------------------------------------------------------- #
def test_get_repo_root_resolves_true_root():
    out = _call(f"$result = Get-RepoRoot -StartDir '{_ps(SCRIPTS_DIR)}'").stdout
    assert "OK:" in out
    assert out.strip().endswith("council-forge")  # the TRUE root, not artifacts/


def test_publish_release_script_binds_params_and_starts():
    """Regression for the -WhatIf parameter collision (a CmdletBinding(SupportsShouldProcess) +
    explicit [switch]$WhatIf throws a MetadataError at binding, so the gates never run). The
    script must BIND its params and REACH preflight, exiting via a handled code — not crash."""
    env = os.environ.copy()
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    res = subprocess.run(
        [_pwsh_exe(), "-NoProfile", "-File", str(PUBLISH), "-Tag", "v0.0.0-cf-nonexistent", "-WhatIf"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    combined = res.stdout + res.stderr
    assert "defined multiple times" not in combined, combined
    assert "MetadataError" not in combined, combined
    # params bound and the script REACHED preflight (it did not crash at parameter binding),
    # then failed-closed (non-zero) at the nonexistent-tag precondition.
    assert "=== Preflight ===" in combined, combined
    assert res.returncode != 0, f"rc={res.returncode}\n{combined}"


# --------------------------------------------------------------------------- #
# Invoke-ReleaseIntegrityGate (snapshot_manifest verify + release_gate, fail-closed)
# --------------------------------------------------------------------------- #
def test_integrity_gate_passes_on_valid_repo():
    out = _call(
        f"Invoke-ReleaseIntegrityGate -RepoRoot '{_ps(REPO_ROOT)}' -ScriptDir '{_ps(SCRIPTS_DIR)}'; $result='pass'"
    ).stdout
    assert "OK:pass" in out, out


def test_integrity_gate_throws_on_missing_manifest(tmp_path: Path):
    root = tmp_path / "empty"
    (root / ".well-known").mkdir(parents=True)
    out = _call(
        f"Invoke-ReleaseIntegrityGate -RepoRoot '{_ps(root)}' -ScriptDir '{_ps(SCRIPTS_DIR)}'; $result='pass'"
    ).stdout
    assert "THREW:" in out and "manifest not found" in out


def test_integrity_gate_throws_on_tampered_manifest(tmp_path: Path):
    root = _make_release_repo(tmp_path)
    manifest = root / ".well-known" / "release-manifest.json"
    # corrupt a digest -> snapshot_manifest verify (tree<->manifest) fails -> fail-closed
    manifest.write_text(manifest.read_text(encoding="utf-8").replace('"sha256": "', '"sha256": "0', 1), encoding="utf-8")
    out = _call(
        f"Invoke-ReleaseIntegrityGate -RepoRoot '{_ps(root)}' -ScriptDir '{_ps(SCRIPTS_DIR)}'; $result='pass'"
    ).stdout
    assert "THREW:" in out and "release-integrity" in out


# --------------------------------------------------------------------------- #
# Signing triad — armed-vs-unprovisioned (no gpg needed)
# --------------------------------------------------------------------------- #
def test_signature_unprovisioned_when_triad_empty(tmp_path: Path):
    root = _make_release_repo(tmp_path)
    out = _call(f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'").stdout
    assert "OK:unprovisioned" in out, out


def test_signature_armed_incomplete_fails_closed(tmp_path: Path):
    root = _make_release_repo(tmp_path)
    # only the detached signature is present (no pin, no pubkey) -> ARMED -> fail closed
    (root / ".well-known" / "release-manifest.json.asc").write_text("-----BEGIN PGP SIGNATURE-----\n", encoding="utf-8")
    out = _call(f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'").stdout
    assert "THREW:" in out and "ARMED" in out


def test_signature_armed_with_bad_pin_fails_closed(tmp_path: Path):
    root = _make_release_repo(tmp_path)
    (root / ".well-known" / "release-manifest.json.asc").write_text("sig\n", encoding="utf-8")
    (root / ".well-known" / "release-signing.pub").write_text("pub\n", encoding="utf-8")
    # full triad present but a non-40-hex (regex-metachar) pin must be rejected before any gpg call
    out = _call(
        f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'",
        env={"EXPECTED_SIGNING_FINGERPRINT": ".*"},
    ).stdout
    assert "THREW:" in out and "40-hex" in out


# --------------------------------------------------------------------------- #
# Signer binding (Test-PinnedValidSig) — deterministic, no gpg, runs everywhere.
# This is the security-critical exact-fingerprint match (the pwsh port of the CI awk).
# --------------------------------------------------------------------------- #
def _validsig_line(sign_fpr: str, primary_fpr: str) -> str:
    # [GNUPG:] VALIDSIG <signing-key-fpr> <date> <ts> <exp> <ver> <algo> <hash> <class> <primary-fpr>
    return f"[GNUPG:] VALIDSIG {sign_fpr} 2026-01-01 0 0 4 0 22 0 01 {primary_fpr}"


def _pin_match(lines: list[str], want: str) -> str:
    arr = ",".join("'" + l.replace("'", "''") + "'" for l in lines)
    body = (
        f"  $lines = @({arr})\n"
        f"  $result = if (Test-PinnedValidSig -StatusLines $lines -Want '{want}') {{ 'true' }} else {{ 'false' }}"
    )
    return _call(body).stdout


def test_pinned_validsig_exact_binding():
    A, B, C = "A" * 40, "B" * 40, "C" * 40
    assert "OK:true" in _pin_match([_validsig_line(A, B)], A)            # $3 (signing key) == want
    assert "OK:true" in _pin_match([_validsig_line(C, A)], A)            # $NF (primary key) == want
    assert "OK:false" in _pin_match([_validsig_line(B, C)], A)           # attacker fp: neither == want
    assert "OK:false" in _pin_match(["[GNUPG:] GOODSIG " + A + " x"], A)  # not a VALIDSIG line
    assert "OK:false" in _pin_match([], A)                              # no status lines
    assert "OK:false" in _pin_match(["XX VALIDSIG " + A], A)            # wrong prefix (not [GNUPG:])


# --------------------------------------------------------------------------- #
# gpg-gated: real sign -> verify (signer binding), tamper, wrong-fp, attacker-key
# --------------------------------------------------------------------------- #
GPG = shutil.which("gpg")
gpg_gated = pytest.mark.skipif(GPG is None, reason="gpg unavailable; release-signing is a native-tool mechanism")


def _short_gnupghome(tmp_path: Path, name: str) -> Path:
    # gpg-agent binds a unix-domain socket whose path must be short; keep GNUPGHOME tiny.
    home = Path(os.environ.get("RUNNER_TEMP", tmp_path)) / name
    home.mkdir(parents=True, exist_ok=True)
    return home


def _gpg(args, home: Path, *, check=True):
    return subprocess.run([GPG, "--batch", "--yes", "--homedir", _ps(home), *args],
                          capture_output=True, text=True, check=check)


def _gen_key(home: Path, uid: str) -> str:
    try:
        _gpg(["--pinentry-mode", "loopback", "--passphrase", "", "--quick-generate-key", uid, "ed25519", "sign", "0"], home)
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"gpg key generation failed in this environment: {exc.stderr or exc}")
    listing = _gpg(["--with-colons", "--list-keys", uid], home).stdout
    for line in listing.splitlines():
        if line.startswith("fpr:"):
            return line.split(":")[9]
    raise AssertionError("no fingerprint")  # pragma: no cover


@gpg_gated
def test_signature_verified_then_tamper_then_wrong_fp(tmp_path: Path):
    root = _make_release_repo(tmp_path)
    manifest = root / ".well-known" / "release-manifest.json"
    sig = root / ".well-known" / "release-manifest.json.asc"
    pub = root / ".well-known" / "release-signing.pub"
    home = _short_gnupghome(tmp_path, "g1")
    try:
        fpr = _gen_key(home, "Release Signer <rel@example.invalid>")
        pub.write_text(_gpg(["--armor", "--export", fpr], home).stdout, encoding="utf-8")
        _gpg(["--pinentry-mode", "loopback", "--passphrase", "", "-u", fpr,
              "--detach-sign", "--armor", "-o", _ps(sig), _ps(manifest)], home)

        # (a) correct pin + good signature -> verified
        out = _call(f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'",
                    env={"EXPECTED_SIGNING_FINGERPRINT": fpr}).stdout
        assert "OK:verified" in out, out

        # (b) wrong pinned fingerprint -> signer mismatch fail-closed (exact binding, not substring)
        wrong = "0" * 40
        out = _call(f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'",
                    env={"EXPECTED_SIGNING_FINGERPRINT": wrong}).stdout
        assert "THREW:" in out and ("signer mismatch" in out or "VALIDSIG" in out), out

        # (c) tamper the manifest after signing -> gpg --verify fails -> fail-closed
        manifest.write_text(manifest.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        out = _call(f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'",
                    env={"EXPECTED_SIGNING_FINGERPRINT": fpr}).stdout
        assert "THREW:" in out, out
    finally:
        gpgconf = shutil.which("gpgconf")
        if gpgconf:
            subprocess.run([gpgconf, "--homedir", _ps(home), "--kill", "gpg-agent"], capture_output=True)


@gpg_gated
def test_signature_attacker_key_in_bundle_rejected(tmp_path: Path):
    """An attacker key appended to the imported bundle must NOT let an attacker signature pass when
    the pin is the LEGIT signer (gpg --verify exits 0 on any good sig; exact binding rejects it)."""
    root = _make_release_repo(tmp_path)
    manifest = root / ".well-known" / "release-manifest.json"
    sig = root / ".well-known" / "release-manifest.json.asc"
    pub = root / ".well-known" / "release-signing.pub"
    home = _short_gnupghome(tmp_path, "g2")
    try:
        legit_fpr = _gen_key(home, "Legit <legit@example.invalid>")
        attacker_fpr = _gen_key(home, "Attacker <atk@example.invalid>")
        # publish BOTH public keys (attacker appended to the bundle) ...
        pub.write_text(_gpg(["--armor", "--export", legit_fpr, attacker_fpr], home).stdout, encoding="utf-8")
        # ... but the manifest is signed by the ATTACKER
        _gpg(["--pinentry-mode", "loopback", "--passphrase", "", "-u", attacker_fpr,
              "--detach-sign", "--armor", "-o", _ps(sig), _ps(manifest)], home)
        # pin is the LEGIT signer -> the attacker's good signature must be REJECTED (exact binding)
        out = _call(f"$result = Assert-ReleaseSignature -RepoRoot '{_ps(root)}'",
                    env={"EXPECTED_SIGNING_FINGERPRINT": legit_fpr}).stdout
        assert "THREW:" in out and ("signer mismatch" in out or "VALIDSIG" in out), out
    finally:
        gpgconf = shutil.which("gpgconf")
        if gpgconf:
            subprocess.run([gpgconf, "--homedir", _ps(home), "--kill", "gpg-agent"], capture_output=True)
