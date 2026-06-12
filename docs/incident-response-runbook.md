# Incident Response Runbook

> Shape: NIST SP 800-61 (Computer Security Incident Handling). Scope: a security **incident**
> affecting council-forge (the governance SSOT) — e.g. a confirmed vulnerability under
> exploitation, a leaked secret, a compromised dependency, a malicious commit/PR, or an exposure
> that reaches a downstream terminal repo. This runbook operationalizes SSDF **RV.3** (analyze
> vulnerabilities to identify root causes) and feeds the disclosure flow in
> [`../SECURITY.md`](../SECURITY.md). It is a process document (a "partial" governance control):
> it states *how* we respond; it does not itself enforce response.

## 0. Roles

- **Incident lead** — the maintainer who owns the incident end-to-end (single writer, per the
  council-forge orchestration model).
- **Reporter** — whoever raised it (a researcher via [`SECURITY.md`](../SECURITY.md), a CI gate,
  the weekly Codex Council audit, or the quarterly threat model).

## 1. Preparation

- Intake channels exist and are validated: [`.well-known/security.txt`](../.well-known/security.txt)
  (RFC 9116, gated by `security_txt_gate.py`) + GitHub private vulnerability reporting.
- Detection controls run in CI: secret-scan, SCA (pip-audit / dotnet / cargo / pnpm), advisory
  SAST, SBOM provenance, and the weekly Codex Council audit (see
  [`security_cadence.md`](security_cadence.md)).
- This runbook + `SECURITY.md` are kept current (doc-yml drift is monitored by the weekly audit).

## 2. Detection & Analysis

- **Record** the report as a private GitHub security advisory (draft). Do not discuss a live
  vulnerability in a public issue/PR.
- **Confirm** it is a real incident (reproduce; rule out false positive).
- **Assess severity** using CVSS v3.1/v4; apply the **KEV override** (treat as Critical if listed
  in CISA KEV or observed exploited). Severity drives the remediation window in
  [`SECURITY.md`](../SECURITY.md) (self-imposed targets, not a NIST mandate).
- **Scope** the blast radius: which scripts/workflows/artifacts, and **which downstreams** (the
  `template/` propagation means a flaw can have been copied to Sentinel / Verso / Vero / LINE-BOT).

## 3. Containment

- Short-term: revoke/rotate any exposed credential immediately; disable a compromised workflow or
  token; if a malicious commit/PR is involved, block merge and protect the branch.
- For a downstream-reaching flaw: notify the affected downstream owners (do not push fixes into a
  frozen or active downstream CI without their coordination — see the retrofit constraints).
- Preserve evidence (logs, the offending diff, CI run URLs) before changing state.

## 4. Eradication

- Fix the root cause in the SSOT; if the flaw is in `template/`, fix root **and** template
  (EXACT_SYNC / sync discipline) so it does not re-propagate.
- Re-run the relevant fail-closed gate(s) to prove the fix (no exit-masking).
- Add or extend a test that reproduces the issue and now passes (regression guard).

## 5. Recovery

- Merge the fix via PR (single writer; review required). Cut/annotate a release/tag if applicable.
- Update [`.well-known/security.txt`](../.well-known/security.txt) Expires if renewing intake.
- Coordinate disclosure timing with the reporter (default up to 90 days; sooner once a fix ships).
- Publish the GitHub security advisory; credit the reporter with consent.

## 6. Post-Incident (Root-Cause)

- Write a root-cause analysis (what failed, why, what control would have caught it earlier) and
  record it in `artifacts/improvement/PROCESS_LEDGER.md` (RV.3 — premortem/improvement loop).
- File follow-up governed tasks for any new control the analysis surfaced (each through the normal
  lifecycle + the dual adversarial-review gate for plans).
- Verify the fix propagated to downstreams where relevant (drift dashboard / propagate).

## Honest limits

This runbook is a **process control**, not an enforced one: CI can validate that the intake file
and policy *exist and are well-formed*, but whether an incident is actually handled within any
window — and whether the root-cause loop is run — depends on the maintainers. That is why the
related SSDF practices (RV.1/RV.2) are mapped `partial`, not `covered`, in
[`ssdf-mapping.md`](ssdf-mapping.md).
