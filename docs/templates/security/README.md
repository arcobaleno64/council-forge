# Downstream Security Scan — opt-in templates (P8-B)

This directory provides **opt-in** secret-scan + SCA (Software Composition Analysis)
templates for council-forge downstream repos. They are **reference templates, not
auto-applied workflows** — a downstream copies the jobs it needs into its own CI (or
runs them via local/pre-commit for repos without a remote). council-forge's own
`security-scan.yml` already enforces Python SCA (pip-audit) + secret/static scan.

> **Scope**: secret-scan + SCA (P8-B) and **advisory SAST (P8-C)**. SBOM is P8-C2;
> vuln-disclosure intake + release/IR are P8-D. This is why SSDF practices PW.4 (SCA),
> RV.1 (secret-scan/vuln-id), and **PW.7 (SAST)** are mapped `partial`, not `covered`, in
> `docs/ssdf-mapping.md` — see the **SAST** section below for why PW.7 is advisory, not enforced.

## Files

- `downstream-security-scan.yml` — the opt-in multi-language workflow (secret + Node/Rust/.NET SCA).
- `downstream-sast.yml` — the opt-in SAST workflow (advisory Python SAST + native Rust clippy / .NET analyzers).
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

## SAST (P8-C) — `downstream-sast.yml`

SAST (SSDF **PW.7**) is **advisory-first**: the Python path runs `repo_security_scan.py sast`
(curated, low-false-positive rules) → SARIF → the fail-closed `sast_gate.py`, which is
**advisory by default** (exit 0 even with findings) so a false-positive avalanche cannot
wedge CI. Findings are not dropped — they are durably appended to `$GITHUB_STEP_SUMMARY`.
Rust and .NET need no new scanner: their **native, build-enforcing analyzers** (clippy
`-D warnings`; Roslyn analyzers via `TreatWarningsAsErrors`) ARE the SAST mechanism.

> council-forge runs the Python advisory SAST on **itself** in `.github/workflows/security-scan.yml`
> (the `python-sast` job). That operational job — not this opt-in template — is the `evidence`
> for PW.7 `partial` in `docs/ssdf-mapping.md`.

| Repo | Stack | SAST mechanism | Enablement |
|---|---|---|---|
| council-forge | Python | `repo_security_scan.py sast` → `sast_gate.py` (advisory) | already operational in its own `security-scan.yml` (`python-sast` job) |
| Sentinel | .NET (frozen) | Roslyn analyzers, `TreatWarningsAsErrors` (native, **enforcing**) | native build already enforces; **template-only while frozen — do NOT wire `dotnet-analyzers` into CI; do NOT touch azure-pipelines.yml** |
| LINE-BOT | .NET (active GitHub remote) | Roslyn analyzers (native) + opt-in workflow | opt-in: copy `dotnet-analyzers` (and `python-sast` if any tooling scripts are Python) |
| Verso | Tauri (Rust + Node, no remote) | `cargo clippy -- -D warnings` (native, **enforcing**) | local / pre-commit (clippy already in package.json scripts) |
| Vero | Tauri (Rust + Node, no remote) | `cargo clippy -- -D warnings` (native, **enforcing**) | local / pre-commit |

**Advisory → enforce transition.** The Python SAST is advisory on purpose; raising PW.7 from
`partial` to `covered` is a **future governed task** (must pass the dual adversarial-review
gate), not a flag flip. It requires: (1) triaging the advisory findings surfaced in the job
summary; (2) a baseline + waiver schema (rule_id / path / reason / owner / expires, reusing
the TASK-1042 runtime-waiver pattern) so the first enforcing run does not thrash; (3) a
per-language order — the low-FP native analyzers (.NET, clippy) are already enforcing, so the
Python regex SAST is enforced last via `sast_gate.py --enforce --min-level error` once a
baseline exists. PW.7 becomes `covered` only when council-forge **and** the critical downstreams
all enforce.

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
