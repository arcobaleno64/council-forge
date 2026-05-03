# Threat Model — v3.4 Rerun Snapshot

## Purpose

This directory is the final v3.4 threat model snapshot produced by TASK-1012 (Prompt 6f — Final Threat Model Rebuild).

It supersedes no prior snapshot. The original `threat-model-20260417-124620/` remains intact and unchanged as the historical source reference.

## Snapshot Metadata

| Field | Value |
|---|---|
| Folder | `threat-model-v3.4-rerun` |
| Folder pattern | `threat-model-*-rerun` (year-free per v3.4 plan §4.6f) |
| Plan version | v3.4 |
| Source snapshot | `threat-model-20260417-124620` (commit `4090bce`) |
| Rerun task | TASK-1012 |
| Rerun commit | `ad99a980888a4b6fc40f856c60373cd3ae79fe64` |
| Generated at | 2026-05-03T22:00:00+08:00 |

## Contents

| File | Description |
|---|---|
| `threat-inventory.json` | Full v3.4 threat inventory: FIND-01..FIND-34 with status, evidence_refs, decision_refs |
| `model-diff.md` | Status diff from source snapshot to this rerun; covers all required findings |
| `README.md` | This file |

## Finding Counts

| Status | Count |
|---|---|
| Open | 12 |
| Mitigated | 12 |
| In-Progress | 6 |
| Backlog | 4 |
| **Total** | **34** |

## Sources Consumed

| Source | Purpose |
|---|---|
| `threat-model-20260417-124620/threat-inventory.json` | FIND-01..FIND-12 base; retained as-is |
| `artifacts/governance/threat-findings-pending-update.v3.4.json` | FIND-18, FIND-23, FIND-24 pending status updates; finalized by TASK-1012 |
| `artifacts/governance/red-team-execution-results.v3.4.json` | RT-PATH-002, RT-HITL-ATTESTATION-001, RT-THREAT-SEMANTIC-001 gap findings |
| `artifacts/governance/threat-finding-backlog.v3.4.json` | FIND-25..FIND-28 deferred backlog entries |
| `artifacts/verify/TASK-1006..TASK-1019.verify.md` | Evidence for FIND-13..FIND-32 status assignments |
| `artifacts/verify/TASK-964.verify.md` | Historical limited evidence classification (frozen) |
| `artifacts/decisions/TASK-1001.decision.md` | TASK-1001 partial supersession / AC-5b blocked context |

## Key Constraints Satisfied

- FIND-01..FIND-34: exact 34-finding list (no `>= 33` threshold)
- `threat-model-*-rerun` folder pattern (year-free)
- FIND-18 = In-Progress (CI exact-sync guard and drift regression case absent)
- FIND-23 / FIND-24 = In-Progress (runtime guard deferred)
- RT-PATH-002 gap → FIND-26 Backlog (not absorbed into summary)
- RT-HITL-ATTESTATION-001 gap → FIND-28 Backlog (not absorbed)
- RT-THREAT-SEMANTIC-001 escalated_by_design → FIND-25 Backlog with semantic validator noted as not implemented
- TASK-964 maturity unchanged (historical limited evidence)
- Original `threat-model-20260417-124620/` not modified

## Relationship to Prompt 7 Smoke Test

Prompt 7 (TASK-1016 End-to-End Smoke Test) depends_on TASK-1012 (this task). It is not executed as part of TASK-1012. See TASK-1012.verify.md for deferral rationale.
