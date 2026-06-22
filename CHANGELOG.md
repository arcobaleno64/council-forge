# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Dates use the `Asia/Taipei` timezone.

## [0.4.0] - 2026-06-22

This release turns Council Forge from a single-repo governance workflow into a
propagatable governance platform: a one-command downstream generator, a
steady-state drift/propagation loop, a supply-chain security tooling layer, and a
NIST SSDF *mapping-integrity* layer (a structural, honesty check of the SSDF
coverage map — explicitly not an SSDLC conformance certification). It also
formalizes the two-layer (PDCA × TAO/ReAct) execution model and substantially
raises validator/automation test coverage (CI gate at 90%; current CI-equivalent
aggregate ≈ 95.82%).

### Added

- **Downstream project generator** — `artifacts/scripts/scaffold_downstream.py`
  bootstraps a new project from `template/` (greenfield) or layers governance
  onto an existing repository with `--retrofit` (brownfield, additive
  copy-missing-only overlay). Brownfield-readiness mode lets source-repo guards
  skip greenfield-only README/bilingual assumptions on adopted repos.
- **Steady-state propagation** — `drift_dashboard.py` reports per-downstream
  drift (in-sync / drifted / missing / instantiated / brownfield-owned), and
  `propagate_downstream.py` refreshes downstream-owned files toward the
  `template/` source of truth (dry-run by default, `--apply` to write).
- **NIST SSDF mapping-integrity layer** — `ssdf_mapping_validator.py` +
  `docs/ssdf-mapping.md` map the workflow's mechanisms onto SP 800-218 v1.1
  (19 practices) with a fail-closed gate that verifies the map is structurally
  complete and honest and never reports bare "conformant" with open gaps (this is
  not a conformance certification); plus `ssdf_conformance_dashboard.py`,
  `docs/ssdf-roadmap.md`, `standards_backaudit_dashboard.py`, and
  `docs/standards-uplift-timeline.md`.
- **Supply-chain & security gates** — `sca_gate.py` (fail-closed dependency-scan
  gate), `sast_gate.py` (advisory SARIF gate), `sbom_gate.py` (fail-closed
  CycloneDX SBOM validation), `security_txt_gate.py` (RFC 9116 `security.txt`
  gate), and `release_gate.py` + `snapshot_manifest.py` for release integrity. A
  `SECURITY.md`, `docs/incident-response-runbook.md`, `docs/security/release-signing.md`,
  and `docs/security_cadence.md` document the disclosure, response, signing, and
  cadence processes.
- **Two-layer governance model** — PDCA (cross-task project layer) × TAO/ReAct
  (single-dispatch agentic execution layer), documented in
  `docs/agentic_execution_layer.md`. A dedicated `test` artifact type (§5.5) is
  now split from the `code` artifact, bringing the schema set to **9 artifact
  types** (§5.1–§5.9).
- **Verify floor & assurance levels** — required artifacts and verification
  intensity are now profiled by `Assurance Level` and `Project Adapter`, backed
  by a verify-floor baseline manifest.
- **RACI auditor v2** with `guard_contract_validator.py --audit-raci <file> <agent>`,
  and an emit-only mode for the Architecture Synthesizer role.
- **Onboarding & authoring** — `START_HERE.md` three-file onboarding,
  GitHub Wiki content under `wiki/` with `push-wiki.ps1`, a standalone repo
  keyword glossary, document templates (SRS / RTM / ADR / Bug / Feature / Debug),
  and the `bootstrap-prompt-builder` skill.
- **Quality-gate runners** — `run_quality_gates.py` runs the baseline-aware P0
  quality gates (QC-SYNC / QC-SCHEMA / QC-IMPORT / QC-GOLDEN, advisory QC-RUFF);
  `run_precommit_check.py` runs the PCACC pre-commit checks.

### Changed

- **EXACT_SYNC twin enforcement** — root ↔ `template/` synchronized files are
  guarded by byte-identical twin checks and a `snapshot_manifest` integrity
  digest.
- **`workflow_state_machine.md`** — added the `superseded-via-reconciliation`
  terminal disposition so reconciled tasks resolve cleanly instead of lingering
  as stuck.
- **`repo_security_scan.py`** — converted from fail-open to fail-closed,
  consistent with the gate discipline.
- **Test coverage** — validator/automation coverage raised from a ~51% baseline
  (core validator modules reach 100%); the CI gate enforces 90% and the current
  CI-equivalent aggregate is ≈ 95.82% (`.coveragerc` omits the two gate runners).

### Fixed

- **`run_quality_gates.py` / `run_precommit_check.py`** — `detect_repo_root` no
  longer keys on a marker file that was never tracked; it now uses the
  `.council-forge-source-repo` sentinel.
- **`run_quality_gates.py --self-check`** — `missing_template` over-report scoped
  to `EXACT_SYNC` authority, so intentionally source-only scripts no longer fail
  the self-check.

### Security

- All GitHub Actions in `.github/workflows/` are pinned to full 40-character
  commit SHAs; Dependabot proposes weekly `github-actions` and `pip` updates.
- `.github/workflows/security-scan.yml` runs `pip-audit` plus repo-local secret
  and static control-plane scans on every PR, push to `master`, and manual
  dispatch.
- Wiki and release publish scripts (`push-wiki.ps1`, `publish-release.ps1`)
  enforce mandatory preflight checks (auth probing, remote reachability,
  tag/release existence) and support `-WhatIf` dry runs.

## [0.3.1] - 2026-04-16

### Added

- Getting Started, Repository Structure, Validator Commands, Context System,
  Contributing, and License sections across all READMEs.

## [0.3.0] - 2026-04-16

### Added

- Context-stack enhancements and the initial public documentation set.

[0.4.0]: https://github.com/arcobaleno64/council-forge/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/arcobaleno64/council-forge/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/arcobaleno64/council-forge/releases/tag/v0.3.0
