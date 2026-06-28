# Threat-Model Delta — 2026Q2 Security-Gate Hardening

> Out-of-cadence governance record. The frozen v3.4 inventory snapshot
> (`threat-model-v3.4-rerun/`) is **not** modified; proposed status changes are
> staged in `artifacts/governance/threat-findings-pending-update.v3.4.json` and
> finalized at the next quarterly threat-model exercise per
> `docs/security_cadence.md` (`.github/workflows/quarterly-threat-model.yml`).

## Decision Class

risk-acceptance + defer (finalization deferred to quarterly cadence)

## Scope

Records, against the threat model, the two CI security gates shipped in the
2026Q2 hardening engagement, and adds one previously-unenumerated threat class.

- PR #36 `d4b1d0b` — systemic ReDoS gate (`regex_safety_audit.py` / `regex-safety` job)
- PR #37 `fc81f6d` — prompt-injection gate (`prompt_injection_scan.py` / `prompt-injection` job + adversarial corpus)
- PR #38 `853b1d5` — bilingual README parity for both gates

## Findings touched

| Finding | Before | After (proposed) | Why |
|---|---|---|---|
| **FIND-23** Indirect injection through research snippets | In-Progress | **Mitigated** (with residual risk) | The runtime enforcement that FIND-23 explicitly deferred ("Status In-Progress until runtime guard implemented") is now a fail-closed CI gate over exactly the research-snippet / untrusted-capture surface. |
| **FIND-24** Memory-bank cumulative poisoning | In-Progress | **In-Progress** (unchanged) | The new detector scopes `artifacts/` only; it does **not** cover `.github/memory-bank/`. Honest no-change; extension is the next step. |
| **FIND-35** *(new)* ReDoS / catastrophic backtracking in guard validators | absent | **Mitigated** (proposed new finding) | Availability DoS class not in the v3.4 inventory; instances fixed (REDOS-01/02) and recurrence prevented by the regex-safety gate. |

## Issue

FIND-23's mitigation was, until now, **policy only** (TASK-1021 Rule-1/3/4:
external/research content is untrusted-by-default and must never be treated as
authoritative). The threat model held the finding at In-Progress pending an
actual *runtime guard*. No automated control detected an injection attempt in
committed content; ReDoS-as-availability-DoS was not enumerated at all.

## Options considered

- **A — Leave for the quarterly exercise.** Process-pure, but the tracking layer
  would misrepresent reality (a shipped mitigation recorded nowhere) for up to a
  quarter.
- **B — Hand-edit the frozen v3.4 snapshot.** Rejected: the snapshot is
  deliberately immutable; edits would corrupt the versioned baseline.
- **C — Stage proposed updates in the pending-update tracker + this memo, defer
  snapshot finalization to the quarterly exercise.** Chosen.

## Chosen option

**C.** Update `threat-findings-pending-update.v3.4.json` (the canonical, living
staging layer) and record this narrative. The frozen snapshot is untouched.

## Reasoning

The pending-update tracker is the repo's own mechanism for "findings pending
update into the next snapshot" (its existing FIND-18/23/24 entries embed
rationale + evidence the same way). Staging here is honest and non-destructive;
the quarterly exercise remains the authority that rewrites the inventory.

A full per-task lifecycle (plan/code/test/verify) was **not** created for this
bookkeeping: there is no implementation work to plan or verify beyond the already
-merged, already-CI-green PRs, and fabricating those artifacts would be dishonest.

## Implications / residual risk

- **FIND-23** is now a **detective** control (detect-and-block at commit/CI),
  not a **preventive** per-read structural trust-tagging guard. A read-time
  intake trust-boundary remains as defense-in-depth backlog. The "Mitigated"
  proposal reflects detection coverage with this residual explicitly recorded.
- **FIND-24** is genuinely unaddressed by this work (memory-bank out of scan
  scope) and stays In-Progress.
- **FIND-35**'s linter is shape-based; a novel non-shape ReDoS form could evade,
  bounded by the linear-by-construction convention and the `# redos-ok:` review.

## Expiry

Superseded when the next quarterly threat-model exercise folds these into a new
inventory snapshot.

## Linked artifacts

- `artifacts/governance/threat-findings-pending-update.v3.4.json` (staged updates)
- `artifacts/scripts/prompt_injection_scan.py`, `artifacts/red_team/prompt_injection_corpus.jsonl`, `artifacts/scripts/test_prompt_injection_scan.py`
- `artifacts/scripts/regex_safety_audit.py`, `artifacts/scripts/test_regex_safety_audit.py`
- `.github/workflows/security-deep-scan.yml` (`prompt-injection`, `regex-safety` jobs)
- `artifacts/code/TASK-1021.code.md` (Trust Policy / Rule-1/3/4 — the FIND-23/24 policy layer)

## Follow up

- Quarterly exercise: finalize FIND-23 → Mitigated and admit FIND-35 into the inventory.
- Backlog (toward FIND-24 Mitigated): extend injection detection / a structural guard to the `.github/memory-bank/` intake boundary.
- Backlog (defense-in-depth for FIND-23): a read-time intake trust-tagging guard.
