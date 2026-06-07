# Security Policy

council-forge is an artifact-first multi-agent governance template (a single source of truth
that propagates to downstream repos). This policy covers **how to report a vulnerability**, how
we triage and remediate, and the good-faith terms for security researchers. It implements SSDF
**RV.1.3** (a documented vulnerability-disclosure-and-remediation policy) and the intake side of
**RV.1.1**. The machine-checkable intake file lives at
[`.well-known/security.txt`](.well-known/security.txt) and is validated in CI by
`artifacts/scripts/security_txt_gate.py` (per-PR and on a schedule, so it cannot silently lapse).

## Reporting a vulnerability

Please report privately — do **not** open a public issue for a suspected vulnerability.

1. **Preferred:** GitHub private vulnerability reporting —
   <https://github.com/arcobaleno64/council-forge/security/advisories/new> (the "Report a
   vulnerability" button). This opens a private draft advisory only the maintainers can see.
2. **Alternative:** email the contact listed in
   [`.well-known/security.txt`](.well-known/security.txt).

Please include: affected file/script/workflow, a description of the issue and its impact, and
reproduction steps or a proof of concept where possible.

## What to expect (best effort, not a contractual SLA)

council-forge is maintained on a best-effort basis. We do not promise a fixed response time we
cannot reliably meet (see the OWASP Vulnerability Disclosure guidance and GitHub's coordinated
disclosure guidance, which deliberately set no hard deadline). Our intent:

- **Acknowledgement:** we aim to acknowledge a report promptly (best effort).
- **Coordinated disclosure:** we ask that you give us a reasonable window — by default up to
  **90 days** — to remediate before any public disclosure, and we will coordinate timing with
  you. This window is a convention (cf. ISO/IEC 29147 coordinated disclosure), not a guarantee.
- **Credit:** with your consent, we will credit you in the advisory / release notes.

## Remediation prioritization (self-imposed targets — NOT a NIST SP 800-218 requirement)

NIST SSDF SP 800-218 v1.1 (RV.2) requires *risk-based* assessment and prioritization but does
**not** define numeric remediation deadlines. The targets below are **council-forge's own
self-imposed conventions**, derived from common industry practice (CVSS severity bands) and are
explicitly **not** mandated by SSDF:

| Severity (CVSS v3.1/v4) | Target remediation window (best effort) |
|---|---|
| Critical (9.0–10.0) | ~7 days |
| High (7.0–8.9) | ~30 days |
| Medium (4.0–6.9) | ~90 days |
| Low (0.1–3.9) | next routine maintenance |

**KEV override:** a vulnerability listed in the CISA Known Exploited Vulnerabilities catalog (or
otherwise observed exploited in the wild) is treated as Critical regardless of CVSS score, per
the spirit of CISA BOD 22-01.

## Handling an incident

When a confirmed vulnerability becomes an incident (e.g. exploitation, exposure of a downstream),
we follow the [incident-response runbook](docs/incident-response-runbook.md) (a NIST SP 800-61
shaped detect → triage → contain → eradicate → recover → post-incident/root-cause flow). The
root-cause / post-incident analysis feeds `artifacts/improvement/PROCESS_LEDGER.md`.

## Safe harbor (good-faith research)

We support good-faith security research. If you make a good-faith effort to comply with this
policy — accessing only your own accounts/data or test data, avoiding privacy violations,
service degradation, and data destruction, and giving us reasonable time to remediate before
disclosure — we will not pursue or support legal action against you for that research, and we
will work with you to understand and resolve the issue quickly. (Adapted from the open
disclose.io / dioterms conventions. **This is not legal advice;** per OWASP, consult a lawyer for
binding terms.)

## Scope

This policy covers the council-forge repository itself (its scripts, workflows, governance
artifacts, and templates). Downstream terminal repos generated from `template/` maintain their
own security policies; this repo's `docs/templates/security/` directory provides reusable
templates (SCA / SAST / SBOM / security.txt) for them to adopt.

## Cadence

See [`docs/security_cadence.md`](docs/security_cadence.md) for how disclosure intake, the weekly
Codex Council audit, the quarterly threat model, and the continuous SAST/SCA/SBOM/secret scans
fit together.
