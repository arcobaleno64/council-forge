# Downstream Security Scan — opt-in templates (P8-B)

This directory provides **opt-in** secret-scan + SCA (Software Composition Analysis)
templates for council-forge downstream repos. They are **reference templates, not
auto-applied workflows** — a downstream copies the jobs it needs into its own CI (or
runs them via local/pre-commit for repos without a remote). council-forge's own
`security-scan.yml` already enforces Python SCA (pip-audit) + secret/static scan.

> **Scope (P8-B)**: secret-scan + SCA only. SAST + SBOM are P8-C; vuln-disclosure
> intake + release/IR are P8-D. This is why SSDF practices PW.4 (SCA) and RV.1
> (secret-scan/vuln-id) are mapped `partial`, not `covered`, in `docs/ssdf-mapping.md`.

## Files

- `downstream-security-scan.yml` — the opt-in multi-language workflow (secret + Node/Rust/.NET SCA).
- `action-pins.json` — manifest of approved GitHub Actions (identity → version + resolved SHA). Lint-enforced.

## Fail-closed & supply-chain guarantees (lint-enforced)

`artifacts/scripts/test_downstream_security_template.py` parses the security workflows and asserts:
- **Supply chain**: every `uses:` in `.github/workflows/security-scan.yml`,
  `template/.github/workflows/security-scan.yml`, and `downstream-security-scan.yml`
  matches `action-pins.json` by **owner/repo identity AND exact 40-hex SHA** (unknown
  action, wrong owner with a coincidental SHA, or SHA drift all fail the lint).
- **No exit-masking**: no scan/gate/audit step (or its job) may use `continue-on-error: true`,
  `|| true`, `; true`, `set +e`, or any other exit-code masking. A vulnerability or
  scanner error must fail the job.
- **Tested .NET gate**: the .NET job pipes `dotnet list package --vulnerable --format json`
  into the tested `sca_gate.py` (because `dotnet list` exits 0 even with vulnerabilities;
  a raw text grep would silently pass). `sca_gate.py` is fail-closed on vulnerabilities,
  malformed/empty output, missing projects, and unexpected JSON schema.

## Per-downstream enablement matrix

| Repo | Stack | Enablement | Jobs to keep |
|---|---|---|---|
| council-forge | Python | already enforced in its own `security-scan.yml` (pip-audit + secret/static) | n/a (this dir is for downstreams) |
| Sentinel | .NET (frozen) | **template-only — do NOT wire into CI while frozen; do NOT touch azure-pipelines.yml.** After thaw, its Azure DevOps pipeline can run the `dotnet-sca` + `secret-scan` equivalents | secret-scan, dotnet-sca |
| LINE-BOT | .NET (active GitHub remote) | opt-in: copy into `.github/workflows/`. Most valuable here (AI provider keys, LINE channel secret) | secret-scan, dotnet-sca |
| Verso | Tauri (Rust + Node, no remote) | local / pre-commit (no CI) — run the audit commands locally | secret-scan, node-sca, rust-sca |
| Vero | Tauri (Rust + Node, no remote) | local / pre-commit (evidence-zip security model makes SCA especially relevant) | secret-scan, node-sca, rust-sca |

## Adoption

1. Copy `downstream-security-scan.yml` into `.github/workflows/` (or run its `run:` commands locally for no-CI repos).
2. Delete the jobs that don't match your stack (keep the column above).
3. Ensure `artifacts/scripts/repo_security_scan.py` and `artifacts/scripts/sca_gate.py` are present (they are, for council-forge retrofitted repos).
4. Do not add exit-masking; do not unpin tools/actions.

## Keeping pins fresh (bump cadence)

Pinned versions go stale — an old pinned `pip-audit` / `cargo-audit` / `pnpm` or action
SHA can miss newer advisories. Keep them current:
- **GitHub Actions**: enable Dependabot (`.github/dependabot.yml` with `package-ecosystem: "github-actions"`) so action SHAs are bump-PR'd; update `action-pins.json` in the same PR (the lint enforces they stay in sync).
- **Scanner tools** (`pip-audit==`, `cargo-audit --version`, `pnpm@`): review on a recurring cadence (e.g. monthly) and bump to the current stable release.
- council-forge's own `security-scan.yml` pins `pip-audit==2.7.3`; bump it on the same cadence.
