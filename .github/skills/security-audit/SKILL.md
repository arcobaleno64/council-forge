---
name: security-audit
description: "Generative vulnerability-discovery harness for an entire codebase, driven by parallel sub-agents and adversarial validation. Unlike the deterministic CI gates (repo_security_scan, regex_safety_audit, prompt_injection_scan) which prevent KNOWN bad patterns from recurring, this skill DISCOVERS unknown, exploitable vulnerabilities through a six-phase pipeline: recon, multi-angle hunting, adversarial validation, reporting, structured findings, and independent verification. Use this skill when asked to run a deep security audit, hunt for exploitable vulnerabilities, perform the quarterly threat-model discovery exercise, or find security bugs that pattern matching misses. Outputs findings.json conforming to report-schema.json and hands confirmed findings into the threat-model staging layer. Trigger on 'security audit', 'vulnerability hunt', 'quarterly threat model exercise', 'find exploitable bugs', or /security-audit."
license: MIT — adapted from cloudflare/security-audit-skill. See NOTICE.
metadata:
  version: 0.1.0
  adapted_from: https://github.com/cloudflare/security-audit-skill
  upstream_license: MIT (Copyright (c) 2025-2026 Cloudflare, Inc.)
---

# Security Audit (generative vulnerability discovery)

**When this skill starts, display this banner before doing anything else:**

```
Security Audit v0.1.0 — adapted from cloudflare/security-audit-skill (MIT)
https://github.com/cloudflare/security-audit-skill
```

This skill is council-forge's **discovery** engine. It complements — does not replace —
the deterministic, fail-closed CI gates:

| Layer | Job | Tool |
|---|---|---|
| **Prevent recurrence** (known bad patterns) | CI gates, fail-closed | `repo_security_scan.py`, `regex_safety_audit.py`, `prompt_injection_scan.py`, `sca/sbom/sast/security_txt` |
| **Discover the unknown** (novel exploitable bugs) | this skill | parallel sub-agents + adversarial validation |
| **Track over time** | threat model | `threat-model-*/threat-inventory.json` + `artifacts/governance/threat-findings-pending-update.*.json` |

It is the automated realization of `docs/red_team_runbook.md`'s discovery half: where the
runbook drives *static workflow-integrity* cases (`run_red_team_suite.py`), this skill drives
*generative product/code* vulnerability hunting.

## Core principles (from the upstream methodology)

1. **Only report what you can exploit.** A deviation from best practice is not a finding
   unless you can describe a concrete attacker, payload, and observable result.
2. **Severity is likelihood × impact**, not checklist conformance. Score impact by what an
   attacker actually gains.
3. **Discovery and validation are different agents.** The agent that finds a bug must not be
   the agent that confirms it — separate, adversarial review kills false positives.
4. **Verify every factual claim against source.** A finding's trace (file:line) must be
   re-checked by a fresh agent reading the actual code, not the finding text.
5. **Iterate.** Each independent run finds materially more; run ≥2 rounds for a real audit.

## Inputs

- Target: a repo path (default: repo root). For council-forge itself, also include
  `artifacts/scripts/` (the guard/gate control plane) as a high-value target.
- Output dir: `artifacts/red_team/audit/run-<N>/` (kept out of the prompt-injection scan
  scope; see `prompt_injection_scan.py` SCAN_EXCLUDE_PREFIXES).

## Pipeline

### Phase 1 — Recon
Spawn parallel `Explore` sub-agents to map architecture, entrypoints, trust boundaries,
auth model, external I/O, and the control plane (guards/gates). Write `architecture.md`.
One agent per subsystem; each returns a structured map, not file dumps.

### Phase 2 — Hunt
Spawn one sub-agent **per attack class**, each blind to the others, each told to produce
concrete exploit traces (entrypoint → propagation → sink). Attack classes:

1. **Injection** — command/SQL/template/path/argument injection; deserialization.
2. **Access control** — authn/authz bypass, IDOR, privilege escalation, missing checks.
3. **Cryptography** — weak primitives, predictable randomness, secret handling.
4. **Business logic** — state-machine abuse, race conditions, TOCTOU, invariant breaks.
5. **Feature abuse** — using a feature as intended for unintended damage (quota, cost, DoS).
6. **Chained** — low-severity primitives composed into a high-severity exploit.
7. **Wildcard** — anything unconventional the other lenses would miss.

For council-forge specifically, add a workflow-integrity lens: can crafted artifact content
subvert a guard/gate, launder scope drift, poison authority, or DoS a validator (ReDoS)?
(Cross-check against existing findings FIND-18/23/24/35 — do not re-report mitigated ones.)

### Phase 3 — Validate (adversarial)
For each candidate finding, spawn a **different** sub-agent whose job is to **refute** it:
prove the code path doesn't exist, a mitigation prevents it, or the trace is wrong. Default
to `rejected` under uncertainty. Survivors only proceed.

### Phase 4 — Report
Write `REPORT.md` (human triage: ranked by severity, one paragraph each) and
`FINDINGS-DETAIL.md` (full trace + reproduction per finding).

### Phase 5 — Structured output
Write `findings.json` — an array of objects each conforming to `report-schema.json`
(`output_schema.oneOf`: a `confirmed` object with the full required fields, or a `rejected`
object with a reason). Then validate it:

```
python .github/skills/security-audit/scripts/validate_findings.py \
  --findings artifacts/red_team/audit/run-<N>/findings.json
```

The validator is fail-closed (exit 1 on any schema violation): trace must start with an
`entrypoint` and end with a `sink`; enums and required fields are enforced from the schema.

### Phase 6 — Independent verification
Spawn fresh sub-agents that re-read the cited source for each `confirmed` finding and confirm
every `trace` step and `execution.payload`. Downgrade or reject anything that doesn't hold.

### Phase 7 — Governance handoff (council-forge integration)
Confirmed findings are staged into the threat model — they do **not** edit the frozen
inventory snapshot. For each `confirmed` finding, append an entry to
`artifacts/governance/threat-findings-pending-update.<plan>.json` (`entries[]`) using this
mapping; finalization into a new inventory snapshot is the quarterly exercise's job:

| pending-update field | from findings.json |
|---|---|
| `finding_id` | `AUDIT-<run>-NN` (canonical FIND-NN assigned at the next snapshot) |
| `title` | `title` |
| `proposed_status` | `"Open"` (newly discovered) |
| `severity` | `severity.overall_severity` |
| `evidence_refs` | the `findings.json` path + each `trace[].file:line` |
| `rationale` | `root_cause` + `intended_behavior` + `execution.expected_result` |
| `source_task_id` | the audit run id (e.g. `security-audit-run-<N>`) |
| `red_team_execution_ref` | `<findings.json path>#<title>` |
| `residual_risk` | `remediation.strategy` (the fix that would close it) |

Rejected findings are retained in `findings.json` for audit-trail completeness but are not staged.

## Requirements
- A coding agent with tool use and parallel sub-agents (Claude Code: `Agent` / `Workflow`).
- Python 3 (stdlib only) for `validate_findings.py`. No Node dependency (the upstream
  `validate-findings.cjs` was reimplemented in stdlib Python to match the repo's CLI-first,
  dependency-light convention).

## Attribution
Methodology, phase structure, and `report-schema.json` are adapted from
`cloudflare/security-audit-skill` (MIT). See `NOTICE` for the full license and copyright.
