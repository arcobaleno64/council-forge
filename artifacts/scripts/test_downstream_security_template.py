"""Lint tests for the P8-B security workflows + downstream template.

Asserts (per the adversarial-review hardening of TASK-1078):
- supply chain: every `uses:` in the security workflows matches action-pins.json by
  owner/repo identity AND exact 40-hex SHA;
- fail-closed: no step/job uses any exit-masking (continue-on-error / || true / ; true /
  set +e) in the security workflows;
- the downstream template wires the tested gates (sca_gate.py for .NET,
  repo_security_scan.py for secrets) and pins scanner tool versions.

The lint helpers are defined here (this is a test, not a coverage-counted module) and are
exercised both on the REAL files (positive) and on synthetic inputs (negative).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
ROOT_WF = ROOT / ".github" / "workflows" / "security-scan.yml"
TEMPLATE_WF = ROOT / "template" / ".github" / "workflows" / "security-scan.yml"
DOWNSTREAM_WF = ROOT / "docs" / "templates" / "security" / "downstream-security-scan.yml"
DOWNSTREAM_SAST_WF = ROOT / "docs" / "templates" / "security" / "downstream-sast.yml"
DOWNSTREAM_SBOM_WF = ROOT / "docs" / "templates" / "security" / "downstream-sbom.yml"
DOWNSTREAM_RELEASE_WF = ROOT / "docs" / "templates" / "security" / "downstream-release-integrity.yml"
MANIFEST = ROOT / "docs" / "templates" / "security" / "action-pins.json"
MAPPING_DOC = ROOT / "docs" / "ssdf-mapping.md"
ROADMAP_DOC = ROOT / "docs" / "ssdf-roadmap.md"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MASKING_SUBSTRINGS = ("|| true", "|| :", "; true", "; :", "set +e", "set +o errexit")


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["actions"]


def _jobs(wf: dict) -> dict:
    return wf.get("jobs", {}) or {}


def iter_steps(wf: dict):
    """Yield (job_name, job, step) for every step."""
    for job_name, job in _jobs(wf).items():
        for step in job.get("steps", []) or []:
            yield job_name, job, step


def check_action_pins(wf: dict, manifest: dict) -> list:
    """Violations where a `uses:` is not an approved action@exact-SHA."""
    violations = []
    for job_name, _job, step in iter_steps(wf):
        uses = step.get("uses")
        if not uses:
            continue
        identity, _, ref = uses.partition("@")
        if identity not in manifest:
            violations.append(f"{job_name}: unknown action '{identity}' (not in manifest)")
            continue
        if not SHA_RE.match(ref):
            violations.append(f"{job_name}: '{identity}' not pinned to a 40-hex SHA: '{ref}'")
            continue
        if ref != manifest[identity]["sha"]:
            violations.append(f"{job_name}: '{identity}' SHA drift (got {ref}, manifest {manifest[identity]['sha']})")
    return violations


def check_no_masking(wf: dict) -> list:
    """Violations where any step/job masks exit codes."""
    violations = []
    for job_name, job, step in iter_steps(wf):
        if job.get("continue-on-error") is True:
            violations.append(f"{job_name}: job has continue-on-error: true")
        if step.get("continue-on-error") is True:
            violations.append(f"{job_name}: a step has continue-on-error: true")
        run = step.get("run")
        if isinstance(run, str):
            for bad in MASKING_SUBSTRINGS:
                if bad in run:
                    violations.append(f"{job_name}: step run masks exit code with '{bad}'")
    return violations


def _all_run_text(wf: dict) -> str:
    return "\n".join(
        step.get("run", "") for _j, _job, step in iter_steps(wf) if isinstance(step.get("run"), str)
    )


# --------------------------------------------------------------------------- #
# POSITIVE: the real shipped workflows must lint clean
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF, DOWNSTREAM_WF, DOWNSTREAM_SAST_WF, DOWNSTREAM_SBOM_WF, DOWNSTREAM_RELEASE_WF])
def test_real_workflow_action_pins_clean(wf_path: Path):
    manifest = load_manifest(MANIFEST)
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert check_action_pins(wf, manifest) == []


@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF, DOWNSTREAM_WF, DOWNSTREAM_SAST_WF, DOWNSTREAM_SBOM_WF, DOWNSTREAM_RELEASE_WF])
def test_real_workflow_no_masking(wf_path: Path):
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert check_no_masking(wf) == []


def test_downstream_wires_tested_gates():
    text = DOWNSTREAM_WF.read_text(encoding="utf-8")
    assert "sca_gate.py dotnet" in text  # .NET via tested gate, not raw grep
    assert "repo_security_scan.py --root . secrets" in text  # reuse home-grown secret scan
    assert "has the following vulnerable" not in text  # no fragile string heuristic


def test_downstream_pins_scanner_tool_versions():
    text = DOWNSTREAM_WF.read_text(encoding="utf-8")
    assert re.search(r"corepack prepare pnpm@\d+\.\d+\.\d+", text)
    assert re.search(r"cargo-audit --version \d+\.\d+\.\d+", text)


def test_root_security_scan_pins_pip_audit():
    text = ROOT_WF.read_text(encoding="utf-8")
    assert re.search(r"pip install pip-audit==\d+\.\d+\.\d+", text)
    assert "|| true" not in text  # enforcing, not advisory


# --------------------------------------------------------------------------- #
# NEGATIVE: the lint must catch each supply-chain / masking defect
# --------------------------------------------------------------------------- #
def _wf_with_step(step: dict, job_extra=None) -> dict:
    job = {"steps": [step]}
    if job_extra:
        job.update(job_extra)
    return {"jobs": {"j": job}}


def test_lint_catches_unknown_action():
    manifest = load_manifest(MANIFEST)
    wf = _wf_with_step({"uses": "evil/action@" + "a" * 40})
    assert check_action_pins(wf, manifest)


def test_lint_catches_sha_drift():
    manifest = load_manifest(MANIFEST)
    wf = _wf_with_step({"uses": "actions/checkout@" + "b" * 40})
    assert any("SHA drift" in v for v in check_action_pins(wf, manifest))


def test_lint_catches_wrong_owner_same_sha():
    manifest = load_manifest(MANIFEST)
    real_sha = manifest["actions/checkout"]["sha"]
    wf = _wf_with_step({"uses": f"evil/checkout@{real_sha}"})  # same SHA, wrong identity
    assert any("unknown action" in v for v in check_action_pins(wf, manifest))


def test_lint_catches_non_sha_ref():
    manifest = load_manifest(MANIFEST)
    wf = _wf_with_step({"uses": "actions/checkout@v6"})  # floating tag, not SHA
    assert any("not pinned to a 40-hex SHA" in v for v in check_action_pins(wf, manifest))


def test_lint_catches_step_continue_on_error():
    wf = _wf_with_step({"run": "pnpm audit", "continue-on-error": True})
    assert any("step has continue-on-error" in v for v in check_no_masking(wf))


def test_lint_catches_job_continue_on_error():
    wf = _wf_with_step({"run": "pnpm audit"}, job_extra={"continue-on-error": True})
    assert any("job has continue-on-error" in v for v in check_no_masking(wf))


@pytest.mark.parametrize("masked", ["pnpm audit || true", "cargo audit ; true", "set +e\npnpm audit"])
def test_lint_catches_run_masking(masked: str):
    wf = _wf_with_step({"run": masked})
    assert check_no_masking(wf)


def test_lint_clean_step_has_no_violation():
    wf = _wf_with_step({"run": "pnpm audit --audit-level=high"})
    assert check_no_masking(wf) == []


# --------------------------------------------------------------------------- #
# P8-C SAST: operational evidence + durable advisory exposure
# --------------------------------------------------------------------------- #
def _mapping_row(practice_id: str) -> list:
    for line in MAPPING_DOC.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"| {practice_id} |"):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError(f"{practice_id} row not found in ssdf-mapping.md")


def _job_run_text(wf: dict, job_name: str) -> str:
    job = _jobs(wf).get(job_name, {})
    return "\n".join(
        step.get("run", "") for step in job.get("steps", []) or [] if isinstance(step.get("run"), str)
    )


def test_pw7_evidence_is_operational_workflow_not_template():
    """PW.7 evidence must be the RUNNING council-forge workflow (operational control), and
    that workflow must actually invoke the advisory scanner + the tested gate — so an opt-in
    template can never be mistaken for the operational evidence (codex v2/v3)."""
    cells = _mapping_row("PW.7")  # [Practice, Title, Status, Mechanism, Evidence, Gap/Waiver]
    assert cells[2] == "partial"
    assert cells[3] == "artifacts/scripts/sast_gate.py"
    evidence = cells[4]
    assert evidence == ".github/workflows/security-scan.yml"
    wf = yaml.safe_load((ROOT / evidence).read_text(encoding="utf-8"))
    assert "python-sast" in _jobs(wf), "operational evidence workflow lacks the python-sast job"
    run_text = _job_run_text(wf, "python-sast")
    assert "repo_security_scan.py --root . sast" in run_text
    assert "sast_gate.py" in run_text


def _sast_gate_invocations(wf: dict) -> list:
    lines = []
    for _job_name, _job, step in iter_steps(wf):
        run = step.get("run")
        if isinstance(run, str):
            lines.extend(line for line in run.splitlines() if "sast_gate.py" in line)
    return lines


@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF, DOWNSTREAM_SAST_WF])
def test_advisory_sast_gate_durably_exposes_findings(wf_path: Path):
    """Every advisory sast_gate invocation — in council-forge's own workflow AND the
    downstream template — must bind --summary-file "$GITHUB_STEP_SUMMARY", so advisory
    findings are durably surfaced rather than silently dropped (codex v4/v5)."""
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    invocations = _sast_gate_invocations(wf)
    assert invocations, f"{wf_path.name} has no sast_gate invocation to check"
    for line in invocations:
        assert '--summary-file "$GITHUB_STEP_SUMMARY"' in line, (
            f"advisory sast_gate must durably surface findings: {line!r}"
        )


def test_downstream_sast_wires_tested_gate_and_recognizes_native():
    text = DOWNSTREAM_SAST_WF.read_text(encoding="utf-8")
    assert "repo_security_scan.py --root . sast --format sarif" in text  # advisory scanner -> SARIF
    assert "sast_gate.py --sarif" in text  # gated via the tested sast_gate, not raw output
    assert "clippy" in text and "-D warnings" in text  # recognize Rust native analyzer
    assert "warnaserror" in text  # recognize .NET native analyzer (TreatWarningsAsErrors)


# --------------------------------------------------------------------------- #
# P8-C2 SBOM: PS.2 misattribution correction, PS.3 evidence, identity/parser-fail invariant
# --------------------------------------------------------------------------- #
def test_ps2_release_integrity_raised_to_partial_by_p8d2():
    """PS.2 keeps its verbatim NIST title (release-integrity, NOT the P8-A '(SBOM)' misattribution)
    and is raised from gap to PARTIAL by P8-D2 — the under-claim correction (council-forge's
    propagated template/ snapshot IS a real release artifact). Mechanism = release_gate.py; the
    gap-waiver is WITHDRAWN (no longer a gap)."""
    cells = _mapping_row("PS.2")  # [Practice, Title, Status, Mechanism, Evidence, Gap/Waiver]
    assert "Verifying Software Release Integrity" in cells[1]
    assert "(SBOM)" not in cells[1]
    assert cells[2] == "partial"
    assert cells[3] == "artifacts/scripts/release_gate.py"
    assert cells[4] == ".github/workflows/security-scan.yml"
    # gap-waiver withdrawn: PS.2 is no longer a gap, so no SSDF-Gap-Waiver marker for it.
    assert "SSDF-Gap-Waiver: PS.2" not in ROADMAP_DOC.read_text(encoding="utf-8")


def test_ps3_evidence_is_operational_sbom_job():
    """PS.3 (SBOM provenance, PS.3.2) is strengthened by the RUNNING council-forge sbom job,
    which must actually generate (cyclonedx-py) + gate (sbom_gate) — not an opt-in template."""
    cells = _mapping_row("PS.3")
    assert cells[2] == "partial"
    assert cells[3] == "artifacts/scripts/sbom_gate.py"
    evidence = cells[4]
    assert evidence == ".github/workflows/security-scan.yml"
    wf = yaml.safe_load((ROOT / evidence).read_text(encoding="utf-8"))
    assert "sbom" in _jobs(wf), "operational evidence workflow lacks the sbom job"
    run_text = _job_run_text(wf, "sbom")
    assert "cyclonedx_py environment" in run_text  # resolved-environment generation
    assert "sbom_gate.py" in run_text


def test_sbom_completeness_accepted_risk_documented():
    """The transitive-completeness limit must be documented as an explicit ACCEPTED RISK in
    the mapping footnote (no over-claim of full completeness)."""
    text = MAPPING_DOC.read_text(encoding="utf-8")
    assert "ACCEPTED RISK" in text
    assert "transitive completeness" in text and "well-formedness" in text


def _sbom_gate_steps(wf: dict) -> list:
    """Yield (job_name, step_run) for every step whose run invokes sbom_gate.py."""
    out = []
    for job_name, _job, step in iter_steps(wf):
        run = step.get("run")
        if isinstance(run, str) and "sbom_gate.py" in run:
            out.append((job_name, run))
    return out


@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF, DOWNSTREAM_SBOM_WF])
def test_sbom_gate_invocations_enforce_identity_and_parser_fail_guard(wf_path: Path):
    """Every sbom_gate invocation — council-forge's own job AND every downstream stack — must
    pass --require-components (identity, never a bare count-only --sbom), and its run block must
    guard with `test -n` so a non-empty manifest yielding zero names fails BEFORE the gate
    (no silent degrade to count-only). codex v6/v7/v8/v9."""
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    steps = _sbom_gate_steps(wf)
    assert steps, f"{wf_path.name} has no sbom_gate invocation to check"
    for job_name, run in steps:
        for line in run.splitlines():
            if "sbom_gate.py" in line:
                assert "--require-components" in line, f"{wf_path.name}:{job_name} bare sbom_gate (count-only): {line!r}"
        assert "test -n" in run, f"{wf_path.name}:{job_name} lacks a REQ-non-empty guard"


def test_downstream_sbom_recipes_per_ecosystem():
    text = DOWNSTREAM_SBOM_WF.read_text(encoding="utf-8")
    assert "cyclonedx_py environment" in text  # Python: resolved environment (captures transitive)
    assert "find . -name bom.json" in text  # Rust: validate ALL workspace members
    assert "cdxgen -t pnpm" in text  # Node: pnpm via cdxgen (cyclonedx-npm cannot read pnpm-lock)
    assert "-spv 1.6" not in text  # no forced spec-version downgrade (gate allows 1.2-1.7)


def test_downstream_sbom_pins_generator_tools():
    text = DOWNSTREAM_SBOM_WF.read_text(encoding="utf-8")
    assert "cyclonedx-bom==7.3.0" in text
    assert re.search(r"cargo-cyclonedx --version \d+\.\d+\.\d+", text)
    assert re.search(r"@cyclonedx/cdxgen@\d+\.\d+\.\d+", text)
    assert re.search(r"CycloneDX --version \d+\.\d+\.\d+", text)


def test_council_forge_sbom_job_uses_resolved_recipe():
    """The council-forge self sbom job must generate from a RESOLVED environment (captures
    transitive), NOT from the unfrozen requirements manifest (codex v1 [high])."""
    wf = yaml.safe_load(ROOT_WF.read_text(encoding="utf-8"))
    run_text = _job_run_text(wf, "sbom")
    assert "cyclonedx_py environment" in run_text
    assert "cyclonedx_py requirements requirements.txt" not in run_text  # not the top-level-only path


def test_sbom_generation_captures_transitive(tmp_path: Path):
    """Generation-path regression (not just the gate parser, codex v2 [high]): generating from
    a resolved environment must capture TRANSITIVE dependencies. The guard lane installs
    cyclonedx-bom==7.3.0 so this runs (not skipped) in CI; importorskip is a local fallback."""
    import subprocess
    import sys

    pytest.importorskip("cyclonedx_py")
    out = tmp_path / "sbom.cdx.json"
    result = subprocess.run(
        [sys.executable, "-m", "cyclonedx_py", "environment", "--output-format", "JSON", "--output-file", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    names = {component.get("name", "").lower() for component in doc.get("components", [])}
    assert "pluggy" in names, "resolved-env generation must capture pluggy (a transitive dep of pytest)"

    import sbom_gate

    code, _ = sbom_gate.evaluate(doc, min_components=1, required=frozenset(), normalization="exact")
    assert code == sbom_gate.EXIT_OK


# --------------------------------------------------------------------------- #
# P8-D vuln-disclosure & response: RFC 9116 security.txt + operational job + honest mapping
# --------------------------------------------------------------------------- #
SECURITY_TXT = ROOT / ".well-known" / "security.txt"


def test_council_forge_security_txt_is_valid():
    """council-forge's own committed security.txt must pass the fail-closed RFC 9116 gate
    (evaluated with a fixed now, so the test is deterministic regardless of the date)."""
    import security_txt_gate
    from datetime import datetime, timezone

    text = SECURITY_TXT.read_text(encoding="utf-8")
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    code, message = security_txt_gate.evaluate(text, now=now, max_validity_days=365)
    assert code == security_txt_gate.EXIT_OK, message


def test_security_txt_job_is_operational_and_scheduled():
    """The security-txt job must invoke the gate, be guarded at STEP level by hashFiles (so a
    downstream without the file skips rather than fails — codex v2), and the workflow must run on
    a schedule so an expired security.txt is caught even with no code change."""
    wf = yaml.safe_load(ROOT_WF.read_text(encoding="utf-8"))
    assert "security-txt" in _jobs(wf), "security-scan.yml lacks the security-txt job"
    steps = _jobs(wf)["security-txt"].get("steps", [])
    gate_steps = [s for s in steps if isinstance(s.get("run"), str) and "security_txt_gate.py" in s["run"]]
    assert gate_steps, "security-txt job does not invoke security_txt_gate.py"
    for step in gate_steps:
        cond = str(step.get("if", ""))
        assert "hashFiles" in cond and ".well-known/security.txt" in cond, (
            "gate step must be step-level presence-conditional on the security.txt"
        )
    # yaml.safe_load may parse the `on:` key as the boolean True (YAML 1.1)
    on_block = wf.get("on", wf.get(True, {}))
    assert on_block.get("schedule"), "security-scan.yml must run on a schedule (catch Expires lapse)"


def test_rv_disclosure_mapping_is_honest():
    """The RV footnote must document the disclosure intake + IR runbook; RV.1/RV.2 stay partial.
    PS.2 is now partial (raised by P8-D2) with the gap-waiver withdrawn (no over-claim)."""
    mapping = MAPPING_DOC.read_text(encoding="utf-8")
    assert "SECURITY.md" in mapping and ".well-known/security.txt" in mapping
    assert "incident-response-runbook" in mapping
    assert _mapping_row("RV.1")[2] == "partial"
    assert _mapping_row("RV.2")[2] == "partial"
    assert _mapping_row("PS.2")[2] == "partial"
    assert "SSDF-Gap-Waiver: PS.2" not in ROADMAP_DOC.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# P8-D2 release integrity (PS.2): source-repo-guarded job, native-verify template, honesty
# --------------------------------------------------------------------------- #
def test_release_integrity_job_is_source_repo_guarded():
    """The release-integrity job's BASE structural steps must be STEP-level guarded on the
    SOURCE-REPO IDENTITY sentinel (.council-forge-source-repo) — NOT on the manifest (which would
    mask a missing-manifest regression as a skip) and NOT on a script path (which a downstream
    could coincidentally carry). They must invoke snapshot_manifest verify + release_gate. The
    P8-D3 native-verify step is INDEPENDENT (also sentinel-only; it decides signing-artifact
    presence inside bash via the armed-triad, asserted separately) — the base gates must stay
    manifest-free so an unsigned/missing-manifest state still fails them closed (codex v1 [H1])."""
    wf = yaml.safe_load(ROOT_WF.read_text(encoding="utf-8"))
    assert "release-integrity" in _jobs(wf), "security-scan.yml lacks the release-integrity job"
    run_steps = [s for s in _jobs(wf)["release-integrity"].get("steps", []) if isinstance(s.get("run"), str)]
    assert any("snapshot_manifest.py verify" in s["run"] for s in run_steps)
    assert any("release_gate.py --format checksums" in s["run"] for s in run_steps)
    base_steps = [s for s in run_steps if "snapshot_manifest.py verify" in s["run"] or "release_gate.py" in s["run"]]
    for step in base_steps:
        cond = str(step.get("if", ""))
        assert "hashFiles('.council-forge-source-repo')" in cond, "base gate must guard on the source-repo sentinel"
        assert "release-manifest.json" not in cond, "base gate guard must NOT key on the manifest/.asc (would mask a missing-manifest regression)"


def test_release_integrity_job_present_in_template():
    """The release-integrity job must be mirrored into template/ (security-scan.yml is synced),
    so a retrofitted downstream inherits it — and it cleanly skips there (no source-repo sentinel)."""
    wf = yaml.safe_load(TEMPLATE_WF.read_text(encoding="utf-8"))
    assert "release-integrity" in _jobs(wf)


def test_downstream_release_integrity_uses_native_verify_not_reimplemented():
    """map-don't-recreate: the downstream template invokes each stack's NATIVE crypto verify (the
    REAL check) and uses release_gate ONLY as a checksums structural pre-check — it does NOT
    re-implement in-toto/Sigstore/Tauri validation in release_gate."""
    text = DOWNSTREAM_RELEASE_WF.read_text(encoding="utf-8")
    assert "dotnet nuget verify" in text  # .NET NuGet signing (native)
    assert "signtool verify" in text or "Authenticode" in text  # .NET Authenticode (native)
    assert "gh attestation verify" in text  # Sigstore / GitHub build provenance (native)
    assert "minisign -V" in text  # Tauri updater signature (native)
    assert "release_gate.py --format checksums" in text  # structural pre-check only
    assert "--format intoto" not in text and "--format sigstore" not in text and "--format tauri" not in text


def test_release_gate_only_supports_checksums_format():
    """release_gate must validate ONLY the checksums manifest format (in-toto/Sigstore/Tauri are
    delegated to native tools, map-don't-recreate, per the commander's v1 adjudication)."""
    import release_gate

    args = release_gate.parse_args(["--format", "checksums", "--file", "x"])
    assert args.format == "checksums"
    with pytest.raises(SystemExit):
        release_gate.parse_args(["--format", "sigstore", "--file", "x"])  # not a valid choice


def test_council_forge_release_manifest_published_and_gate_passes():
    """council-forge's own published release manifest must exist and pass the structural gate
    (end-to-end PS.2.1: published, reproducible integrity-verification info)."""
    import release_gate

    manifest_path = ROOT / ".well-known" / "release-manifest.json"
    assert manifest_path.is_file(), "council-forge must publish .well-known/release-manifest.json"
    assert release_gate.run(["--format", "checksums", "--file", str(manifest_path)]) == release_gate.EXIT_OK


def test_council_forge_release_manifest_matches_template_snapshot():
    """The published manifest must match the current template/ tree (regenerate-diff) — the same
    HEAD-consistency check the CI release-integrity job runs, proving the manifest is not stale."""
    import snapshot_manifest

    manifest_path = ROOT / ".well-known" / "release-manifest.json"
    rc = snapshot_manifest.run(["verify", "--template-root", str(ROOT / "template"), "--manifest", str(manifest_path)])
    assert rc == snapshot_manifest.EXIT_OK


def test_snapshot_manifest_is_source_only_never_propagated():
    """The CI guard's correctness rests on snapshot_manifest.py being source-only: it must NOT be
    in template/ nor in EXACT_SYNC_FILES, so it is structurally impossible to propagate it
    downstream (gemini v3/v4 invariant). Same for the source-repo sentinel."""
    assert not (ROOT / "template" / "artifacts" / "scripts" / "snapshot_manifest.py").exists()
    guard = (ROOT / "artifacts" / "scripts" / "guard_contract_validator.py").read_text(encoding="utf-8")
    assert "snapshot_manifest.py" not in guard  # not in EXACT_SYNC_FILES
    assert not (ROOT / "template" / ".council-forge-source-repo").exists()


def test_ps2_release_integrity_honesty_footnote():
    """The mapping footnote must keep PS.2 honest: partial-not-covered (Example-1 reproducible
    hashes), signing as path-to-covered, and PS.2 != PS.3.2 (no double-count with SBOM)."""
    mapping = MAPPING_DOC.read_text(encoding="utf-8")
    assert "under-claim" in mapping
    assert "path-to-covered" in mapping
    assert "PS.2 ≠ PS.3.2" in mapping or "PS.2≠PS.3.2" in mapping


def test_readme_has_release_integrity_section():
    text = (ROOT / "docs" / "templates" / "security" / "README.md").read_text(encoding="utf-8")
    assert "Release integrity (PS.2 / P8-D2)" in text
    assert "minisign -V" in text and "gh attestation verify" in text  # native verify in the matrix


# --------------------------------------------------------------------------- #
# P8-D3 release SIGNING (PS.2): native gpg --verify w/ VALIDSIG signer-binding, honest partial
# --------------------------------------------------------------------------- #
RELEASE_SIGNING_DOC = ROOT / "docs" / "security" / "release-signing.md"
SECURITY_MD = ROOT / "SECURITY.md"
# A REAL private key is a full armor block: BEGIN, a base64 BODY (>=64 chars), then END. This
# distinguishes an actual committed key from prose/regex that merely names the armor line (e.g. a
# secret-detection rule's example), so the invariant has no false positives on documentation.
PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----"
    r"[\r\n]+[A-Za-z0-9+/=\r\n]{64,}?"
    r"-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----"
)


def _release_integrity_steps(wf: dict) -> list:
    return [s for s in _jobs(wf).get("release-integrity", {}).get("steps", []) if isinstance(s.get("run"), str)]


def _native_verify_step(wf: dict):
    for step in _release_integrity_steps(wf):
        if "gpg" in step["run"] and "--verify" in step["run"]:
            return step
    return None


@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF])
def test_release_signing_native_verify_binds_signer(wf_path: Path):
    """The native-verify step must do a REAL gpg --verify bound to the PINNED SIGNER via VALIDSIG
    (NOT the pubkey file's first key), refuse an unpinned key, isolate the keyring, and be
    pipefail-safe with capture-then-grep — so a degraded signature or an attacker-key-in-bundle
    substitution fails closed (codex v1 [H2] / v2 [H2] / v3 pipefail-masking)."""
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    step = _native_verify_step(wf)
    assert step is not None, f"{wf_path.name} release-integrity job lacks a native gpg --verify step"
    run = step["run"]
    # VALIDSIG signer-binding (NOT a naive file-first --show-keys compare)
    assert "--status-fd" in run and "VALIDSIG" in run, "must parse VALIDSIG from the gpg status stream"
    assert "EXPECTED_SIGNING_FINGERPRINT" in run, "must bind to the pinned fingerprint"
    assert "--show-keys" not in run, "must bind via VALIDSIG, not a file-first --show-keys compare"
    # EXACT field equality (codex/gemini impl-review): the pin must be format-validated as a full
    # 40-hex fingerprint and compared as a fixed field token via awk — NOT interpolated into a regex
    # / substring match (which a weak pin like ".*" would defeat by matching any valid signature).
    assert "[0-9A-F]{40}" in run, "must STRICTLY validate the pin as a full 40-hex fingerprint"
    assert "awk" in run and '$2=="VALIDSIG"' in run, "must exact-match the VALIDSIG field via awk"
    assert "($3==want || $NF==want)" in run, "must compare exact signing/primary key fingerprint fields"
    assert ".*${EXPECTED_SIGNING_FINGERPRINT}" not in run, "must NOT use a substring/regex pin match"
    # refuse-unpinned + isolated keyring
    assert "test -n" in run, "must refuse an unpinned key (test -n)"
    assert "GNUPGHOME=" in run and "mktemp" in run, "must use an isolated mktemp GNUPGHOME"
    # pipefail-safe + capture-then-check (gpg rc checked at the assignment, not masked by a pipe)
    assert step.get("shell") == "bash", "must pin shell: bash (not rely on the runner default)"
    assert "set -eo pipefail" in run, "must set -eo pipefail explicitly"
    assert 'STATUS="$(gpg' in run, "must capture-then-check (gpg rc checked directly), not pipe gpg | matcher"
    # no exit-masking
    assert check_no_masking(wf) == []


@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF])
def test_release_signing_native_verify_arms_on_full_triad(wf_path: Path):
    """The native-verify step is keyed ONLY on the source-repo sentinel (always runs in
    council-forge, skips downstream); the signing-artifact presence is decided INSIDE bash, NOT in
    the `if`. Keying the `if` on the .asc/pubkey would let DELETING a signature SKIP enforcement
    once signing is provisioned — a fail-open (codex impl-review). Instead: no-op ONLY when the
    whole triad (pin + .asc + pubkey) is absent, else ALL must be present or it FAILS CLOSED."""
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    step = _native_verify_step(wf)
    cond = str(step.get("if", ""))
    assert "hashFiles('.council-forge-source-repo')" in cond
    assert ".asc" not in cond and "release-signing.pub" not in cond, (
        "artifact presence must be decided in bash, not the `if` (else deleting a signature skips enforcement)"
    )
    run = step["run"]
    # armed-triad: count present members; no-op ONLY when zero; else require all three present.
    assert "present=0" in run and "-eq 0" in run, "must no-op ONLY when the whole triad is unprovisioned"
    assert 'test -f "$SIG"' in run and 'test -f "$PUB"' in run, "armed state must require the signature AND pubkey"
    assert ".well-known/release-manifest.json.asc" in run and ".well-known/release-signing.pub" in run


def test_release_signing_doc_documents_lifecycle_and_residual():
    """release-signing.md must document the Example 2/3 key lifecycle (rotation / revocation /
    review), the same-repo-pin RESIDUAL (true trust is out-of-band), the mechanism-implemented
    (operator-action-dependent) ceiling, and the no-committed-key invariant."""
    assert RELEASE_SIGNING_DOC.is_file(), "docs/security/release-signing.md must exist"
    text = RELEASE_SIGNING_DOC.read_text(encoding="utf-8")
    low = text.lower()
    for token in ("rotation", "revocation", "review", "out-of-band", "expected_signing_fingerprint",
                  "release-signing.pub", "gpg --detach-sign", "gpg --verify"):
        assert token in low, f"release-signing.md missing {token!r}"
    assert "mechanism-implemented" in text and "operator-action-dependent" in text
    assert "repo integrity" in low or "repo's own integrity" in low, "must state the same-repo-pin residual"
    assert "private key" in low and "never" in low, "must state no private key is committed"


def test_release_signing_discovery_pointers_consistent():
    """SECURITY.md and security.txt must point to the single source of truth (release-signing.md /
    the pubkey + fingerprint pin) — consistent discovery, no conflicting pointers (premortem R8)."""
    security_md = SECURITY_MD.read_text(encoding="utf-8")
    assert "docs/security/release-signing.md" in security_md
    assert "release-signing.pub" in security_md and "EXPECTED_SIGNING_FINGERPRINT" in security_md
    sec_txt = SECURITY_TXT.read_text(encoding="utf-8")
    assert "release-signing" in sec_txt  # RFC 9116 comment pointer (does not affect the gate)


def test_ps2_stays_partial_mechanism_implemented_not_flipped():
    """P8-D3 builds + tests the signing mechanism but PS.2 MUST stay partial (covered is
    operator-gated: real key + real signature + out-of-band-published trust anchor). The mapping
    footnote must say so in the unambiguous 'mechanism-implemented (operator-action-dependent)'
    wording, not flip; the roadmap records P8-D3; PS.2 is not a re-added gap-waiver."""
    assert _mapping_row("PS.2")[2] == "partial"
    mapping = MAPPING_DOC.read_text(encoding="utf-8")
    assert "mechanism-implemented" in mapping
    assert "operator-action-dependent" in mapping
    assert "out-of-band" in mapping
    assert "不 flip" in mapping
    roadmap = ROADMAP_DOC.read_text(encoding="utf-8")
    assert "P8-D3" in roadmap
    assert "SSDF-Gap-Waiver: PS.2" not in roadmap


def test_no_signing_key_committed_anywhere():
    """Zero-theater invariant: NO private key material is ever committed. Scan for PEM/PGP
    'PRIVATE KEY' armor (not prose) across the tracked tree, and for private-key files under
    .well-known/ (the publication slot holds only the PUBLIC key + a fingerprint pin). The
    end-to-end test uses throwaway tmp keys only."""
    wk = ROOT / ".well-known"
    if wk.is_dir():
        for p in wk.iterdir():
            assert not p.name.endswith((".key", ".sec", ".gpg")), f"private-key-like file in .well-known/: {p.name}"
    # external/ holds third-party repos (off-limits to council-forge governance); skip VCS / venvs
    # / caches / build output too.
    skip_dirs = {".git", ".sbom-venv", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules",
                 "coverage-report", ".pytest-basetemp", "external"}
    skip_suffix = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".zip", ".gz", ".whl"}
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in skip_suffix:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PRIVATE_KEY_BLOCK.search(content):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == [], f"committed PEM/PGP PRIVATE KEY armor found: {offenders}"
