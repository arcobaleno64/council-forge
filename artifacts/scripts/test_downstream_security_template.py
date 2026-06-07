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
MANIFEST = ROOT / "docs" / "templates" / "security" / "action-pins.json"
MAPPING_DOC = ROOT / "docs" / "ssdf-mapping.md"

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
@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF, DOWNSTREAM_WF, DOWNSTREAM_SAST_WF])
def test_real_workflow_action_pins_clean(wf_path: Path):
    manifest = load_manifest(MANIFEST)
    wf = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert check_action_pins(wf, manifest) == []


@pytest.mark.parametrize("wf_path", [ROOT_WF, TEMPLATE_WF, DOWNSTREAM_WF, DOWNSTREAM_SAST_WF])
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
