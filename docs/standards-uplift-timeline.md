# Standards-Uplift Timeline

> **SSOT:** the machine-readable source of truth for this timeline is
> [`standards-uplift-timeline.json`](./standards-uplift-timeline.json). This Markdown is a
> human-readable rendering of that JSON; when the two disagree, **the JSON wins**. Do not
> hand-edit the table below without updating the JSON in the same change.

## What this is (and what it is NOT)

This timeline records **WHEN** each council-forge governance standard, gate, or discipline
was introduced — evidenced by the introducing commit's committer instant
(`git log -1 --format=%cI <commit>`). It is consumed **read-only** by
`artifacts/scripts/standards_backaudit_dashboard.py` to compute, for each task, which
standards rose **after** that task completed (its *theoretical qualitative delta*).

It is **NOT** a conformance verdict. The timeline says a bar rose at instant *T*; it does
**not** claim any older task does or does not meet today's bar. Whether an older mechanism
would pass today's dual-review / SSDF / fail-closed bar is a **qualitative** judgement that
is **not machine-decidable** and stays `qualitative-review-pending` until re-judged by an
actual codex+gemini dual review. See the dashboard's `machine-green ≠ quality-met` caveat.

Same-day events are ordered by **instant**, never collapsed to a date — on 2026-06-07 alone
five standards were introduced within hours of each other, so a date-granularity comparison
would mis-order a task completed between them.

## Maintenance (this is a LIVING SSOT, not a snapshot)

**Rule:** any task that introduces a **new governance standard** — a new guard, a new
threshold, or anything in the `dual-review` / `ssdf` / `security-gate` / `fail-closed` /
`dispatch` / `lifecycle` / `write-scope` classes — **MUST append one event** to
`standards-uplift-timeline.json` in the same change. An un-recorded uplift makes every later
back-audit silently under-count the qualitative delta of earlier tasks.

**Machine-parsable entry format** (append to `events[]`; every field is required and
`category` must be one of the controlled `maintenance.categories`):

```json
{
  "introduced_at": "<ISO 8601 instant from git log -1 --format=%cI <commit>>",
  "event": "<short human label of what was uplifted>",
  "standard": "<the new bar, one sentence>",
  "ref": "TASK-XXXX",
  "commit": "<short-sha>",
  "category": "<one of: dual-review | ssdf | security-gate | fail-closed | dispatch | lifecycle | write-scope>"
}
```

The dashboard loads this file fail-closed: a bad `schema_version`, an empty `events` list, a
missing required field, an unparseable `introduced_at`, or a `category` outside the
controlled vocabulary aborts the back-audit rather than silently skipping the bad event.

## Events (rendered from the JSON SSOT, ascending by instant)

| introduced_at | event | standard (summary) | ref | commit | category |
|---|---|---|---|---|---|
| 2026-05-06T14:47:54+08:00 | sub-agent write-scope guard for dispatch wrappers | Dispatch wrappers must declare a bounded write-scope; out-of-scope sub-agent writes are guard-enforced scope-drift / RACI violations. | TASK-1057 | 7e006fe | write-scope |
| 2026-05-19T17:11:29+08:00 | dispatch prompt discipline codified | Dispatch prompts must follow the token-cost discipline: bounded, structured, no unbounded context dumping. | TASK-1064 | cdc7280 | dispatch |
| 2026-05-19T20:48:08+08:00 | wrapper prompt-size bounds-check | Dispatch wrappers enforce a prompt-size bound, rejecting oversized prompts before dispatch. | TASK-1067 | 45610cd | dispatch |
| 2026-06-05T15:29:25+08:00 | council-forge brownfield-readiness | Workflow must retrofit onto brownfield repos: a repo's own README/CLAUDE is preserved and classified brownfield-owned, not overwritten. | TASK-1074 | 4a155a8 | lifecycle |
| 2026-06-07T16:46:49+08:00 | adversarial dual-review gate established + P8 SSDLC roadmap | Every plan must pass a codex+gemini adversarial dual-review (no blocking/critical) before coding; security/crypto/auth plans add a working-tree implementation-layer dual review. | P8-roadmap | 28ab45d | dual-review |
| 2026-06-07T18:29:11+08:00 | P8-A SSDF mapping-integrity gate (NIST SP 800-218 v1.1) | Governance mechanisms are mapped to NIST SSDF practices and the mapping is integrity-gated; an unmapped / mis-mapped practice fails the gate. | TASK-1077 | fed3d5c | ssdf |
| 2026-06-07T19:19:58+08:00 | P8-B secret-scan + SCA (recognize + harden + map + downstream) | Secret-scanning and SCA gates are recognized, hardened, SSDF-mapped, and templated downstream. | TASK-1078 | 4968c14 | security-gate |
| 2026-06-07T19:34:01+08:00 | sca_gate dotnet report-version fail-closed hardening | Security gates must fail closed: a missing / unparseable report version is a hard failure, never a silent pass. | TASK-1079 | 7703b09 | fail-closed |
| 2026-06-07T21:01:22+08:00 | P8-C advisory SAST (sast_gate + PW.7 partial) | A static application security testing gate (advisory) is present and SSDF-mapped (PW.7 partial). | TASK-1080 | d8f9e7c | security-gate |
| 2026-06-08T00:24:55+08:00 | P8-C2 SBOM (sbom_gate, 4-ecosystem) | A software bill-of-materials gate (multi-ecosystem) is present and SSDF-mapped (PS.3). | TASK-1081 | 23e0692 | security-gate |
| 2026-06-08T07:56:19+08:00 | P8-D vuln-disclosure & response (security_txt_gate + SECURITY.md + IR runbook) | A vulnerability-disclosure path and an incident-response runbook are present and SSDF-mapped (RV.1). | TASK-1082 | 9cc6395 | security-gate |
| 2026-06-08T10:28:37+08:00 | P8-D2 release-integrity (release_gate + snapshot_manifest) | A release-integrity gate plus a snapshot manifest are present and SSDF-mapped (PS.2 partial). | TASK-1083 | a00173a | security-gate |
| 2026-06-08T13:35:25+08:00 | P8-D3 release-signing verification | Release-signing verification is implemented (PS.2 mechanism-implemented). | TASK-1084 | 66d1e4a | security-gate |
| 2026-06-08T17:32:13+08:00 | P8-E SSDF conformance dashboard + enablement SSOT | A per-downstream SSDF mechanism-overlay dashboard (read-only, honest non-certification) and an enablement-matrix SSOT exist; presence is never conflated with enforcement. | TASK-1085 | 8556413 | ssdf |

## Source-only

This timeline (both `.json` and `.md`) is **source-only upstream-governance** tooling: a
downstream terminal repo does not back-audit further repos, so neither file is mirrored into
`template/` nor listed in `EXACT_SYNC_FILES` — same discipline as
`standards_backaudit_dashboard.py`, `ssdf_conformance_dashboard.py`, and `drift_dashboard.py`.
