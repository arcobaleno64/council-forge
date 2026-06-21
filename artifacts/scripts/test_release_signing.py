"""End-to-end functional test for the release-signing mechanism (SSDF PS.2, P8-D3).

This proves the CI `release-integrity` native-verify step is NOT merely theoretical: it exercises
the real `gpg` sign -> verify -> tamper sequence and the VALIDSIG **signer-binding** logic that the
workflow uses, against EPHEMERAL throwaway keys generated in a temporary GNUPGHOME.

Honesty invariants (the whole point of P8-D3):
- gpg-gated: skipped wholesale if `gpg` is unavailable, or if key generation fails in the test
  environment (no entropy / sandbox) — it is a functional check, not a blocker.
- The keys are THROWAWAY: generated in a tmp GNUPGHOME, used, and discarded. They are never a
  publisher identity and NEVER committed (no key or signature is written into the repo tree).
- The verify helper MIRRORS the CI step's semantics exactly: capture-then-grep (the gpg return
  code is checked directly, so a degraded/bad signature is never masked by a status stream that
  merely contains a matching VALIDSIG line) + VALIDSIG signer binding (the ACTUAL signing/primary
  key fingerprint must equal the pinned anchor, NOT the pubkey file's first key).

The negative multi-key case is the load-bearing one: an attacker key appended to the published
bundle, with the attacker signing the manifest, must FAIL verification when the PINNED fingerprint
is the expected anchor — even though `gpg --verify` exits 0 (the attacker's signature is "good"
against its own key, which is present in the bundle). Binding to VALIDSIG, not to the file's first
key, is what defeats that substitution.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

GPG = shutil.which("gpg")
BASH = shutil.which("bash")
ROOT_DIR = Path(__file__).resolve().parents[2]
FINGERPRINT_RE = re.compile(r"^[0-9A-F]{40}$")  # a full 40-hex OpenPGP v4 fingerprint (normalized upper)


def _native_verify_run_block() -> str:
    """Extract the SHIPPED native-verify run script from the real workflow, so the gating below is
    tested against exactly what CI runs (not a paraphrase)."""
    yaml = pytest.importorskip("yaml")
    wf = yaml.safe_load((ROOT_DIR / ".github" / "workflows" / "security-scan.yml").read_text(encoding="utf-8"))
    for job in (wf.get("jobs") or {}).values():
        for step in job.get("steps", []) or []:
            run = step.get("run")
            if isinstance(run, str) and "VALIDSIG" in run and "--verify" in run:
                return run
    raise AssertionError("native-verify run block not found in security-scan.yml")  # pragma: no cover

pytestmark = pytest.mark.skipif(GPG is None, reason="gpg not available; release-signing is a native-tool mechanism")

# A fixed test manifest (the signing logic is format-agnostic; this is NOT the real release
# manifest, and nothing here is written into the repo tree — everything lives under tmp dirs).
TEST_MANIFEST_BYTES = b'{"schema": "council-forge/release-manifest@1", "algorithm": "sha256", "entries": [], "root": "0"*64}\n'


def _gpgpath(p) -> str:
    """Render a filesystem path for a gpg argument. On Linux CI (where this gate actually runs)
    this is a plain ``str()`` no-op. On Windows it POSIX-normalizes (``C:\\x`` -> ``/c/x``) because
    a Git-bash/MSYS gpg mis-joins a native Windows path; a native-Windows gpg would then skip via
    the keygen-failure guard rather than mis-verify (gpg-gated honesty, never a false pass)."""
    s = str(p)
    if os.name == "nt":
        s = s.replace("\\", "/")
        if len(s) >= 2 and s[1] == ":":
            s = "/" + s[0].lower() + s[2:]
    return s


@pytest.fixture
def gnupghome():
    """Factory for isolated GNUPGHOMEs on a SHORT path. gpg-agent binds a unix-domain socket
    inside the homedir; pytest's deeply-nested tmp paths can exceed the AF_UNIX ~108-char limit
    (on Linux runners and the Git-bash gpg alike), which makes the agent fail to start. Keyrings
    therefore live under a short system-temp dir; each is killed + removed at teardown."""
    homes: list[Path] = []

    def make() -> Path:
        return Path(tempfile.mkdtemp(prefix="cfk-")).resolve()

    def _make_tracked() -> Path:
        home = make()
        homes.append(home)
        return home

    yield _make_tracked

    gpgconf = shutil.which("gpgconf")
    for home in homes:
        if gpgconf:  # release the agent's handle on the homedir before removing it
            subprocess.run([gpgconf, "--homedir", _gpgpath(home), "--kill", "gpg-agent"],
                           capture_output=True, text=True, check=False)
        shutil.rmtree(home, ignore_errors=True)


def _gpg(args, home: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    """Run gpg with an isolated GNUPGHOME (no ambient keyring / trust)."""
    return subprocess.run(
        [GPG, "--batch", "--yes", "--homedir", _gpgpath(home), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _gen_key(home: Path, uid: str) -> str:
    """Generate a throwaway ed25519 signing key in `home`; return its 40-hex fingerprint.

    Skips (not fails) if the environment cannot generate a key (no entropy / sandbox)."""
    try:
        _gpg(
            ["--pinentry-mode", "loopback", "--passphrase", "", "--quick-generate-key", uid, "ed25519", "sign", "0"],
            home,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"gpg key generation failed in this environment: {exc.stderr or exc}")
    listing = _gpg(["--with-colons", "--list-keys", uid], home).stdout
    for line in listing.splitlines():
        if line.startswith("fpr:"):
            return line.split(":")[9]
    raise AssertionError("could not parse a fingerprint from gpg --list-keys")  # pragma: no cover


def _export_pub(home: Path, uid: str, out: Path) -> Path:
    out.write_text(_gpg(["--armor", "--export", uid], home).stdout, encoding="utf-8")
    return out


def _detach_sign(home: Path, signer_fpr: str, manifest: Path, sig: Path) -> Path:
    _gpg(["--pinentry-mode", "loopback", "--passphrase", "", "-u", signer_fpr,
          "--detach-sign", "--armor", "-o", _gpgpath(sig), _gpgpath(manifest)], home)
    return sig


def verify_signature(*, pubkey: Path, sig: Path, manifest: Path, expected_fingerprint: str, home: Path) -> bool:
    """Mirror the CI native-verify step: import the published pubkey into an ISOLATED keyring,
    capture-then-grep (gpg rc checked directly -> a non-zero gpg fails closed, never masked), and
    bind the VALIDSIG fingerprint to the pinned anchor. Returns True iff BOTH hold.

    This is the test analogue of:
        test -n "$EXPECTED" ; printf '%s' "$EXPECTED" | grep -Eq '^[0-9A-F]{40}$'   # validate pin
        STATUS="$(gpg --status-fd 1 --verify sig manifest)"                          # set -e: gpg!=0 -> fail
        printf '%s\\n' "$STATUS" | awk -v want="$EXPECTED" \
          '$1=="[GNUPG:]" && $2=="VALIDSIG" && ($3==want || $NF==want){ok=1} END{exit(ok?0:1)}'
    """
    # Normalize + STRICTLY validate the pin as a full 40-hex fingerprint. A weak/mistyped pin
    # (empty, a short key-id, or a regex metacharacter such as ".*" / "0") fails closed here — it is
    # never used as a regex, only as a fixed string compared for EXACT field equality below.
    want = expected_fingerprint.upper()
    if not FINGERPRINT_RE.match(want):
        return False
    _gpg(["--import", _gpgpath(pubkey)], home)
    proc = _gpg(["--status-fd", "1", "--verify", _gpgpath(sig), _gpgpath(manifest)], home, check=False)
    if proc.returncode != 0:
        return False  # degraded / bad signature: gpg non-zero -> fail-closed (not masked)
    for line in proc.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[0] == "[GNUPG:]" and fields[1] == "VALIDSIG":
            # field 3 (index 2) = signing-key fpr; last field = primary-key fpr (GnuPG DETAILS).
            # EXACT equality on a whole field, NOT a substring of the line.
            if fields[2] == want or fields[-1] == want:
                return True  # signer-bound: the ACTUAL signing/primary key fingerprint == pinned
    return False


# --------------------------------------------------------------------------- #
# POSITIVE: the pinned key signs; verifying against its pubkey + pinned fingerprint passes.
# --------------------------------------------------------------------------- #
def test_pinned_signature_verifies(tmp_path: Path, gnupghome):
    home = gnupghome()
    pinned_fpr = _gen_key(home, "pinned-test <pinned@example.invalid>")
    pub = _export_pub(home, pinned_fpr, tmp_path / "release-signing.pub")
    manifest = tmp_path / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    sig = _detach_sign(home, pinned_fpr, manifest, tmp_path / "release-manifest.json.asc")

    assert verify_signature(
        pubkey=pub, sig=sig, manifest=manifest,
        expected_fingerprint=pinned_fpr, home=gnupghome(),
    ) is True


# --------------------------------------------------------------------------- #
# TAMPER: mutating the manifest after signing makes gpg --verify fail (non-zero), so the
# capture-then-grep fails closed — a matching VALIDSIG line cannot rescue a bad signature.
# --------------------------------------------------------------------------- #
def test_tampered_manifest_fails(tmp_path: Path, gnupghome):
    home = gnupghome()
    pinned_fpr = _gen_key(home, "pinned-test <pinned@example.invalid>")
    pub = _export_pub(home, pinned_fpr, tmp_path / "release-signing.pub")
    manifest = tmp_path / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    sig = _detach_sign(home, pinned_fpr, manifest, tmp_path / "release-manifest.json.asc")

    manifest.write_bytes(TEST_MANIFEST_BYTES + b"tampered\n")  # mutate AFTER signing

    assert verify_signature(
        pubkey=pub, sig=sig, manifest=manifest,
        expected_fingerprint=pinned_fpr, home=gnupghome(),
    ) is False


# --------------------------------------------------------------------------- #
# NEGATIVE multi-key (the load-bearing case, codex v2 [H2]): an attacker key appended to the
# published bundle, with the attacker signing the manifest. `gpg --verify` exits 0 (the sig is
# good against the attacker key, which IS in the bundle), but the PINNED fingerprint is the
# expected anchor — VALIDSIG carries the attacker's fingerprint, so binding to the signer (not the
# file's first key) FAILS verification. A file-first-fingerprint check would have WRONGLY passed.
# --------------------------------------------------------------------------- #
def test_attacker_key_in_bundle_fails(tmp_path: Path, gnupghome):
    pinned_home = gnupghome()
    attacker_home = gnupghome()
    pinned_fpr = _gen_key(pinned_home, "pinned-test <pinned@example.invalid>")
    attacker_fpr = _gen_key(attacker_home, "attacker-test <attacker@example.invalid>")
    assert pinned_fpr != attacker_fpr

    # Published bundle: PINNED key first, attacker key appended (the substitution attack).
    pinned_pub = _export_pub(pinned_home, pinned_fpr, tmp_path / "pinned.pub")
    attacker_pub = _export_pub(attacker_home, attacker_fpr, tmp_path / "attacker.pub")
    bundle = tmp_path / "release-signing.pub"
    bundle.write_text(pinned_pub.read_text(encoding="utf-8") + attacker_pub.read_text(encoding="utf-8"), encoding="utf-8")

    # The attacker signs the manifest with the ATTACKER key.
    manifest = tmp_path / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    attacker_sig = _detach_sign(attacker_home, attacker_fpr, manifest, tmp_path / "release-manifest.json.asc")

    # Verifying with the PINNED fingerprint as the expected anchor must FAIL (VALIDSIG == attacker).
    assert verify_signature(
        pubkey=bundle, sig=attacker_sig, manifest=manifest,
        expected_fingerprint=pinned_fpr, home=gnupghome(),
    ) is False

    # Sanity: gpg itself accepts the attacker's signature (exit 0) — proving the failure above is
    # the signer-binding, not gpg rejecting the signature.
    sanity_home = gnupghome()
    _gpg(["--import", _gpgpath(bundle)], sanity_home)
    sanity = _gpg(["--status-fd", "1", "--verify", _gpgpath(attacker_sig), _gpgpath(manifest)], sanity_home, check=False)
    assert sanity.returncode == 0
    assert any(line.startswith("[GNUPG:] VALIDSIG ") and attacker_fpr in line for line in sanity.stdout.splitlines())


# --------------------------------------------------------------------------- #
# REFUSE-UNPINNED: an empty expected fingerprint must fail closed (the CI `test -n` guard).
# --------------------------------------------------------------------------- #
def test_unpinned_fingerprint_refused(tmp_path: Path, gnupghome):
    home = gnupghome()
    pinned_fpr = _gen_key(home, "pinned-test <pinned@example.invalid>")
    pub = _export_pub(home, pinned_fpr, tmp_path / "release-signing.pub")
    manifest = tmp_path / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    sig = _detach_sign(home, pinned_fpr, manifest, tmp_path / "release-manifest.json.asc")

    assert verify_signature(
        pubkey=pub, sig=sig, manifest=manifest,
        expected_fingerprint="", home=gnupghome(),
    ) is False


# --------------------------------------------------------------------------- #
# WEAK-PIN: a VALID signature must STILL fail verification when the pin is not a full 40-hex
# fingerprint — a regex metacharacter (".*", "0") or a short key-id. Without the format validation +
# exact field equality, a substring/regex match would accept any valid signature (codex [high]).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("weak_pin", [".*", "0", "AAAA", "FF", "not-a-fingerprint", "{40}"])
def test_weak_or_regex_pin_refused(tmp_path: Path, gnupghome, weak_pin: str):
    home = gnupghome()
    pinned_fpr = _gen_key(home, "pinned-test <pinned@example.invalid>")
    pub = _export_pub(home, pinned_fpr, tmp_path / "release-signing.pub")
    manifest = tmp_path / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    sig = _detach_sign(home, pinned_fpr, manifest, tmp_path / "release-manifest.json.asc")

    # The signature itself is good; the PIN is weak -> must fail closed (no signer binding).
    assert verify_signature(
        pubkey=pub, sig=sig, manifest=manifest,
        expected_fingerprint=weak_pin, home=gnupghome(),
    ) is False


def test_short_keyid_pin_refused(tmp_path: Path, gnupghome):
    """A short key-id (a real SUBSTRING of the genuine fingerprint) must be refused: it is not a
    full 40-hex fingerprint, so the format guard rejects it before any field comparison."""
    home = gnupghome()
    pinned_fpr = _gen_key(home, "pinned-test <pinned@example.invalid>")
    pub = _export_pub(home, pinned_fpr, tmp_path / "release-signing.pub")
    manifest = tmp_path / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    sig = _detach_sign(home, pinned_fpr, manifest, tmp_path / "release-manifest.json.asc")

    short_keyid = pinned_fpr[-16:]  # the long key-id: a genuine substring of the fingerprint
    assert verify_signature(
        pubkey=pub, sig=sig, manifest=manifest,
        expected_fingerprint=short_keyid, home=gnupghome(),
    ) is False


# --------------------------------------------------------------------------- #
# TRIAD GATING (codex impl-review): execute the SHIPPED workflow run block. Enforcement must arm as
# soon as ANY member of the signing triad (pin / .asc / pubkey) is present, and a missing member
# must FAIL CLOSED — so deleting a signature/pubkey after provisioning cannot silently disable it.
# The armed-but-partial cases fail BEFORE gpg, so they need only bash (no key).
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(BASH is None, reason="bash required to execute the shipped workflow run block")
@pytest.mark.parametrize(
    "pin, make_sig, make_pub, expect_zero",
    [
        ("", False, False, True),         # fully unprovisioned -> honest no-op (exit 0)
        ("A" * 40, False, False, False),  # pin set, artifacts deleted -> armed -> FAIL CLOSED
        ("", True, True, False),          # both artifacts present, pin unset -> armed -> FAIL CLOSED
        ("", True, False, False),         # signature present, pubkey deleted -> armed -> FAIL CLOSED
        ("", False, True, False),         # pubkey present, signature deleted -> armed -> FAIL CLOSED
    ],
)
def test_signing_triad_gating_fails_closed(tmp_path: Path, pin, make_sig, make_pub, expect_zero):
    wk = tmp_path / ".well-known"
    wk.mkdir()
    (wk / "release-manifest.json").write_bytes(TEST_MANIFEST_BYTES)
    if make_sig:
        (wk / "release-manifest.json.asc").write_text("dummy", encoding="utf-8")
    if make_pub:
        (wk / "release-signing.pub").write_text("dummy", encoding="utf-8")
    script = _native_verify_run_block()
    env = {**os.environ, "EXPECTED_SIGNING_FINGERPRINT": pin}
    proc = subprocess.run([BASH, "-c", script], cwd=str(tmp_path), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if expect_zero:
        assert proc.returncode == 0, f"unprovisioned state must no-op cleanly: {proc.stderr}"
    else:
        assert proc.returncode != 0, f"armed-but-partial state must FAIL CLOSED; stdout={proc.stdout!r} stderr={proc.stderr!r}"


@pytest.mark.skipif(BASH is None, reason="bash required to execute the shipped workflow run block")
def test_shipped_run_block_verifies_real_signature(tmp_path: Path, gnupghome):
    """End-to-end through the ACTUAL shipped YAML run block (not the Python mirror): a fully
    provisioned triad with a real signature verifies (exit 0); a tampered manifest fails closed."""
    keyhome = gnupghome()
    fpr = _gen_key(keyhome, "pinned-test <pinned@example.invalid>")
    wk = tmp_path / ".well-known"
    wk.mkdir()
    manifest = wk / "release-manifest.json"
    manifest.write_bytes(TEST_MANIFEST_BYTES)
    _export_pub(keyhome, fpr, wk / "release-signing.pub")
    _detach_sign(keyhome, fpr, manifest, wk / "release-manifest.json.asc")

    script = _native_verify_run_block()
    env = {**os.environ, "EXPECTED_SIGNING_FINGERPRINT": fpr}
    ok = subprocess.run([BASH, "-c", script], cwd=str(tmp_path), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert ok.returncode == 0, f"shipped run block must verify a real signature: {ok.stderr}"

    manifest.write_bytes(TEST_MANIFEST_BYTES + b"tampered\n")  # mutate AFTER signing
    bad = subprocess.run([BASH, "-c", script], cwd=str(tmp_path), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert bad.returncode != 0, "shipped run block must FAIL CLOSED on a tampered manifest"
