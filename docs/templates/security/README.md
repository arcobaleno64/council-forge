# Downstream Security Scan — opt-in templates (P8-B)

This directory provides **opt-in** secret-scan + SCA (Software Composition Analysis)
templates for council-forge downstream repos. They are **reference templates, not
auto-applied workflows** — a downstream copies the jobs it needs into its own CI (or
runs them via local/pre-commit for repos without a remote). council-forge's own
`security-scan.yml` already enforces Python SCA (pip-audit) + secret/static scan.

> **Scope**: secret-scan + SCA (P8-B), **advisory SAST (P8-C)**, **SBOM (P8-C2)**,
> **vuln-disclosure intake (P8-D)**, and **release integrity (PS.2 / P8-D2)**. SSDF practices
> PW.4 (SCA), RV.1 (secret-scan/vuln-id), **PW.7 (SAST)**, **PS.3 (SBOM provenance)**, and
> **PS.2 (release integrity)** are mapped `partial`, not `covered`, in `docs/ssdf-mapping.md` —
> see the sections below. (SBOM is PS.3.2; PS.2 is release-integrity — distinct, never
> double-counted.)

## Files

- `downstream-security-scan.yml` — the opt-in multi-language workflow (secret + Node/Rust/.NET SCA).
- `downstream-sast.yml` — the opt-in SAST workflow (advisory Python SAST + native Rust clippy / .NET analyzers).
- `downstream-sbom.yml` — the opt-in SBOM workflow (CycloneDX generation per ecosystem → fail-closed `sbom_gate.py`).
- `downstream-release-integrity.yml` — the opt-in RELEASE-INTEGRITY workflow (PS.2: native signature verify + fail-closed `release_gate.py` structural pre-check).
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

> **Machine-readable SSOT**: [`enablement-matrix.json`](enablement-matrix.json) is the single
> source of truth for the per-downstream enablement states. `ssdf_conformance_dashboard.py`
> consumes it, and `test_downstream_security_template.py` lint-enforces that the **State
> matrix** token table below matches it **exactly** (per repo × dimension). The prose table
> that follows is the human-readable view; edit the JSON, not the tokens by hand.
>
> **Enablement state is *declared intent*, NOT observed runtime enforcement.** It says how a
> downstream is *expected* to cover a dimension; it does not assert the mechanism is actually
> present or running. For the actual mechanism-overlay status, run `ssdf_conformance_dashboard.py`
> (a separate, honest view — `overlaid` ≠ enforced).

### State matrix (mirrors `enablement-matrix.json` — lint-enforced)

| Repo | secret-scan | sca | sast | sbom | release-integrity | disclosure |
|---|---|---|---|---|---|---|
| council-forge | enforced-self | enforced-self | enforced-self | enforced-self | enforced-self | enforced-self |
| Sentinel | template-only-frozen | template-only-frozen | native-enforcing | template-only-frozen | template-only-frozen | template-only-frozen |
| LINE-BOT | opt-in-ci | opt-in-ci | native-enforcing | opt-in-ci | opt-in-ci | opt-in-ci |
| Verso | local-precommit | local-precommit | native-enforcing | local-precommit | local-precommit | n-a |
| Vero | local-precommit | local-precommit | native-enforcing | local-precommit | local-precommit | n-a |

### Enablement detail (prose; secret-scan + SCA focus)

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

## SBOM (P8-C2) — `downstream-sbom.yml`

SBOM is a CycloneDX **provenance** mechanism — SSDF **PS.3.2** (`Collect ... provenance data
... in a software bill of materials`), NOT PS.2. (PS.2 is release-integrity / hashes / code
signing, deferred to P8-D; council-forge's earlier "PS.2 (SBOM)" was a misattribution, now
corrected in `docs/ssdf-mapping.md` and `docs/ssdf-roadmap.md` §8.) Every ecosystem generator
emits CycloneDX JSON, validated by the single tested **`sbom_gate.py`** (one gate, many
generators — the same shape as `sast_gate.py` consuming any analyzer's SARIF).

> council-forge runs the Python SBOM on **itself** in `.github/workflows/security-scan.yml`
> (the `sbom` job). That operational job is the `evidence` for **PS.3** `partial` in
> `docs/ssdf-mapping.md`.

| Repo | Stack | SBOM generator | Enablement |
|---|---|---|---|
| council-forge | Python | `cyclonedx-py environment` (resolved venv) → `sbom_gate.py` | already operational in its own `security-scan.yml` (`sbom` job) |
| Sentinel | .NET (frozen) | `dotnet-CycloneDX` → `sbom_gate.py` | **template-only while frozen — do NOT wire into CI; do NOT touch azure-pipelines.yml** |
| LINE-BOT | .NET (active GitHub remote) | `dotnet-CycloneDX` → `sbom_gate.py` | opt-in: copy the `dotnet-sbom` job |
| Verso | Tauri (Rust + pnpm, no remote) | `cargo-cyclonedx` (all members) + `@cyclonedx/cdxgen -t pnpm` → `sbom_gate.py` | local / pre-commit |
| Vero | Tauri (Rust + pnpm, no remote) | `cargo-cyclonedx` (all members) + `@cyclonedx/cdxgen -t pnpm` → `sbom_gate.py` | local / pre-commit |

**What the gate enforces (fail-closed)**: well-formedness (`bomFormat` const, supported
`specVersion`, per-specVersion component-type allowlist, BOM `version`), **presence**
(`--min-components`, default 1 — an empty SBOM fails), and **direct-dependency identity**
(`--require-components`: the manifest's direct dependency names must be present — a count-only
floor can be satisfied by unrelated components, so identity is checked). Each job derives the
names from its manifest and `test -n "$REQ"` guards against a parser failure degrading to a
count-only check. Name matching: `pep503` for PyPI; `exact` for npm / Cargo / NuGet
(punctuation is part of identity).

**Accepted risk — transitive completeness**: the gate verifies form + presence + DIRECT-dep
identity. **Exhaustive transitive completeness vs the true dependency graph is an explicitly
ACCEPTED RISK** — no gate can verify it without re-deriving the graph or trusting another
enumerator whose own completeness is unverifiable (infinite regress). It is mitigated by
**resolved-source generation recipes** (Python resolved-env captures transitive by
construction; Rust validates ALL workspace members; Node uses `cdxgen` which reads
`pnpm-lock.yaml` where `cyclonedx-npm` cannot), the gate's **unmissable advisory**, and a
**non-blocking periodic audit** (a defined follow-up: compare the SBOM against an independent
enumerator — `pipdeptree` / `cargo tree` / `pnpm list` — as a generator-efficacy feedback
loop, observation not a hard gate). This is why **PS.3 is `partial`, not `covered`**, and why
the advisory SBOM is not falsely claimed to be a complete bill of materials.

## Vulnerability disclosure (P8-D) — `security.txt` + `SECURITY.md`

council-forge ships a fail-closed RFC 9116 gate (`artifacts/scripts/security_txt_gate.py`,
EXACT_SYNC so downstreams get it) and runs it on **itself** via the `security-txt` job in
`.github/workflows/security-scan.yml` (validating its own `.well-known/security.txt`). The job is
**step-level presence-conditional** (`if: hashFiles('.well-known/security.txt') != ''`), so a
downstream that copied `template/` but has **not** authored a `security.txt` simply skips it — it
does **not** fail CI. The workflow also runs on a weekly `schedule` so an expired `Expires` is
caught even with no code change.

A downstream that wants a disclosure program:
1. Author `SECURITY.md` (GitHub surfaces it under the Security tab) — a CVD policy: a private
   intake channel, a best-effort acknowledgement (don't over-promise an SLA), a coordinated
   disclosure window, and safe-harbor language. (council-forge's own `SECURITY.md` is a model.)
2. Author `.well-known/security.txt` (RFC 9116): a `Contact:` (https/mailto) and a **non-expired**
   `Expires:` (RFC 3339, < 1 year out) are required; `Policy:`/`Canonical:` etc. are optional URIs.
3. Enable GitHub **private vulnerability reporting** (Settings → Advanced Security).

The gate validates **syntax + URI structure + https-for-web + a non-expired Expires**. It does
**not** verify that the Contact reaches a monitored party, that URLs resolve, or that a signature
is valid — that is human review. SSDF mapping: this is the **RV.1.3** disclosure dimension (it
stays `partial`, policy + verifiable intake). Release-integrity signing (PS.2) is **P8-D2** (below).

## Release integrity (PS.2 / P8-D2) — `downstream-release-integrity.yml`

Release integrity (SSDF **PS.2** — "Provide a Mechanism for Verifying Software Release
Integrity": make integrity-verification info available to acquirers via cryptographic hashes /
code signing) is **distinct from PS.3.2 provenance (SBOM)** and must never be double-counted.

**Map-don't-recreate**: each stack's **native** tool is the REAL cryptographic check —
`signtool verify` / `dotnet nuget verify` (.NET Authenticode / NuGet), `cosign verify` +
`gh attestation verify` (Sigstore / GitHub build provenance), `minisign -V` (Tauri updater).
council-forge does NOT re-implement signature verification. `release_gate.py` is an **offline
STRUCTURAL pre-check** of a published checksums manifest only (schema / digest shape / no
placeholders / coverage); it explicitly does **not** verify signatures, certificate trust, or
that digests match the real bytes — that is the native tools' job and an accepted residual risk
(printed as an advisory on every run). in-toto/Sigstore/Tauri structural validation is left to
the native tools, NOT re-implemented in `release_gate`.

> council-forge applies PS.2 to **its own** release surface — the propagated `template/` SSOT
> snapshot it ships to downstreams — via `snapshot_manifest.py` (a content-addressed,
> reproducible manifest published at `.well-known/release-manifest.json`) + the `release-integrity`
> job in `security-scan.yml` (regenerate-diff + `release_gate`), and a durable
> `.council-forge/release-snapshot.json` record written into each downstream on `propagate --apply`.
> That moves PS.2 from `gap` to **`partial`** in `docs/ssdf-mapping.md`.

| Repo | Stack | Native verify (REAL check) | Enablement |
|---|---|---|---|
| council-forge | Python (SSOT snapshot) | `snapshot_manifest.py` reproducible manifest + `release_gate` structural | already operational (`release-integrity` job; PS.2 `partial`) |
| Sentinel | .NET (frozen) | `signtool verify` / `dotnet nuget verify` | **template-only while frozen — do NOT wire into CI; do NOT touch azure-pipelines.yml** |
| LINE-BOT | .NET (active GitHub remote, container) | `cosign verify` + `gh attestation verify` (build provenance) | opt-in: copy `dotnet-release-integrity`; sign in the build job (`actions/attest-build-provenance`, pin it) |
| Verso | Tauri (Rust + pnpm, no remote) | `minisign -V` (updater signature) | local / pre-commit (no CI) — run `tauri-release-integrity` commands locally |
| Vero | Tauri (Rust + pnpm, no remote) | `minisign -V` (updater signature) | local / pre-commit (evidence-zip model makes integrity especially relevant) |

**`partial`, not `covered`** (honest ceiling): council-forge publishes a **reproducible** hash
manifest of its release surface (NIST PS.2.1 Example 1) — an acquirer can independently
recompute and compare. Full `covered` needs actual **signing** of the manifest/tag plus a key
rotation/revocation/review process (Example 2/3); that is a **defined follow-up**, not claimed
now. PS.2 ≠ PS.3.2 (SBOM): `release_gate` validates integrity manifests, `sbom_gate` validates
SBOMs — different mechanisms, no double-count.

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
