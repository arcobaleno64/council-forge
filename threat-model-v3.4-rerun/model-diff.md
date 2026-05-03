# Model Diff: threat-model-20260417-124620 → threat-model-v3.4-rerun

## Diff Metadata

| Field | Value |
|---|---|
| Source snapshot | `threat-model-20260417-124620` |
| Source commit | `4090bce` |
| Rerun snapshot | `threat-model-v3.4-rerun` |
| Rerun task | TASK-1012 (Prompt 6f) |
| Rerun commit | `ad99a980888a4b6fc40f856c60373cd3ae79fe64` |
| Plan version | v3.4 |
| Generated at | 2026-05-03T22:00:00+08:00 |
| Source finding count | 12 (FIND-01..FIND-12) |
| Rerun finding count | 34 (FIND-01..FIND-34) |

---

## Finding Status Changes

| Finding ID | Old Status | New Status | Evidence Ref | Decision Ref | Rationale | Requires Revalidation |
|---|---|---|---|---|---|---|
| FIND-01 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot; no mitigation in v3.4 scope | No |
| FIND-02 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-03 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-04 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-05 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-06 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-07 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-08 | Open | Open | artifacts/governance/red-team-execution-results.v3.4.json#RT-ALIAS-CHAIN-001 | artifacts/decisions/TASK-1007.decision.md | Alias rejection guard active (RT-ALIAS-CHAIN-001 PASS); underlying credential trust scope unresolved | No |
| FIND-09 | Open | Open | artifacts/governance/red-team-execution-results.v3.4.json#RT-WAIVER-CHAIN-001 | artifacts/decisions/TASK-1007.decision.md | Waiver chain non-transitivity confirmed (RT-WAIVER-CHAIN-001 PASS); sandbox gap unresolved | No |
| FIND-10 | Open | Open | threat-model-20260417-124620/threat-inventory.json | — | Retained from source snapshot | No |
| FIND-11 | Mitigated | Mitigated | threat-model-20260417-124620/threat-inventory.json | — | No change; already Mitigated at source snapshot | No |
| FIND-12 | Mitigated | Mitigated | threat-model-20260417-124620/threat-inventory.json | — | No change; already Mitigated at source snapshot | No |

---

## New Findings (FIND-13..FIND-34)

| Finding ID | Old Status | New Status | Evidence Ref | Decision Ref | Rationale | Requires Revalidation |
|---|---|---|---|---|---|---|
| FIND-13 | (not in source) | Mitigated | artifacts/verify/TASK-1007.verify.md | artifacts/decisions/TASK-1007.decision.md | classify_path() now fail-closed for unknown paths (RACI_MATRIX_V2 has no 'unknown' category → VIOLATION) | No |
| FIND-14 | (not in source) | Mitigated | artifacts/verify/TASK-1007.verify.md | artifacts/decisions/TASK-1007.decision.md | resolve_identity() raises AliasRejectedError for non-canonical aliases in strict mode; RT-ALIAS-CHAIN-001 PASS | No |
| FIND-15 | (not in source) | In-Progress | artifacts/governance/red-team-execution-results.v3.4.json#RT-PATH-001, RT-PATH-002, RT-SYMLINK-001 | artifacts/decisions/TASK-1012.decision.md | Unicode homoglyph mitigated (RT-PATH-001 PASS); dotdot normalization absent (RT-PATH-002 FAIL → FIND-26 backlog); symlink realpath absent (RT-SYMLINK-001 ESCALATED → FIND-27 backlog) | Yes — when FIND-26 and FIND-27 resolved |
| FIND-16 | (not in source) | Mitigated | artifacts/verify/TASK-1008.verify.md | artifacts/decisions/TASK-1008.decision.md | validate_assurance_level_strict() rejects 'high'; TASK-964 corrected to 'mvp' | No |
| FIND-17 | (not in source) | Mitigated | artifacts/verify/TASK-1008.verify.md | artifacts/decisions/TASK-1008.decision.md | guard_status_validator mismatch check between task.md and status.json | No |
| FIND-18 | (not in source) | In-Progress | artifacts/verify/TASK-1006.verify.md; artifacts/verify/TASK-1019.verify.md; artifacts/governance/red-team-execution-results.v3.4.json#RT-SOURCE-TEMPLATE-001, RT-RACI-COLLISION-001 | artifacts/decisions/TASK-1012.decision.md | Drift detection guard active (EXACT_SYNC_FILES, RT-SOURCE-TEMPLATE-001 PASS); template mirror classification correct (RT-RACI-COLLISION-001 PASS). Remaining for Mitigated: (1) CI exact-sync guard absent; (2) drift regression case absent. Both deferred. | Yes — when CI guard and regression case implemented |
| FIND-19 | (not in source) | In-Progress | artifacts/verify/TASK-1009.verify.md; artifacts/verify/TASK-1015.verify.md; artifacts/governance/red-team-execution-results.v3.4.json#RT-VERIFY-STUFFING-001 | artifacts/decisions/TASK-1012.decision.md | Strict enforcement for post-baseline verify artifacts (RT-VERIFY-STUFFING-001 PASS). Semantic validator gap (FIND-25) and HITL validator gap (FIND-28) remain. | Yes — when FIND-25 and FIND-28 resolved |
| FIND-20 | (not in source) | Mitigated | artifacts/verify/TASK-1010.verify.md | artifacts/decisions/TASK-1010.decision.md | TASK-964 reclassified as limited evidence; is_historical_limited_evidence_exception() guard active; production canonical drill created as TASK-1010 | No |
| FIND-21 | (not in source) | Mitigated | artifacts/verify/TASK-1011.verify.md | artifacts/decisions/TASK-1011.decision.md | superseded_by formal schema (v3.4 §5.0) adopted; TASK-1001 reconciliation uses validated schema | No |
| FIND-22 | (not in source) | In-Progress | artifacts/governance/red-team-execution-results.v3.4.json#RT-HITL-ATTESTATION-001 | artifacts/decisions/TASK-1012.decision.md | RT-HITL-ATTESTATION-001 FAIL: evidence_timestamp_source not validated; reviewer_id presence alone passes; HITL validator not implemented. Deferred to backlog (FIND-28). | Yes — when FIND-28 resolved |
| FIND-23 | (not in source) | In-Progress | artifacts/verify/TASK-1021.verify.md; artifacts/governance/red-team-execution-results.v3.4.json#RT-INJECTION-004; artifacts/governance/threat-findings-pending-update.v3.4.json#FIND-23 | artifacts/decisions/TASK-1012.decision.md | Policy layer established (untrusted-by-default, Rule-1/3/4); RT-INJECTION-004 PASS (RACI_MATRIX_V2 not overridable by research content). Runtime guard at intake boundary deferred to Prompt 1+ (not implemented in v3.4). finalized_by=TASK-1012. | Yes — when runtime guard implemented |
| FIND-24 | (not in source) | In-Progress | artifacts/verify/TASK-1021.verify.md; artifacts/governance/red-team-execution-results.v3.4.json#RT-MEMORY-POISON-001; artifacts/governance/threat-findings-pending-update.v3.4.json#FIND-24 | artifacts/decisions/TASK-1012.decision.md | Policy layer established (source-ref-required authority, Rule-2/4); RT-MEMORY-POISON-001 PASS (memory-bank not read by RACI_MATRIX_V2 validator). Runtime guard at memory-bank intake boundary deferred. finalized_by=TASK-1012. | Yes — when runtime guard implemented |
| FIND-25 | (not in source) | Backlog | artifacts/governance/red-team-execution-results.v3.4.json#RT-THREAT-SEMANTIC-001; artifacts/governance/threat-finding-backlog.v3.4.json#FIND-25 | artifacts/decisions/TASK-1012.decision.md | RT-THREAT-SEMANTIC-001 ESCALATED_BY_DESIGN: json.loads() does not detect duplicate finding_id; no semantic validator exists. Semantic validator not yet implemented; gap documented. | Yes — when semantic validator implemented |
| FIND-26 | (not in source) | Backlog | artifacts/governance/red-team-execution-results.v3.4.json#RT-PATH-002; artifacts/governance/threat-finding-backlog.v3.4.json#FIND-26 | artifacts/decisions/TASK-1012.decision.md | RT-PATH-002 FAIL gap: classify_path() lacks os.path.normpath(); dotdot traversal misclassified. Fix deferred per TASK-1019 hardening_note. | Yes — when normpath fix + regression test implemented |
| FIND-27 | (not in source) | Backlog | artifacts/governance/red-team-execution-results.v3.4.json#RT-SYMLINK-001; artifacts/governance/threat-finding-backlog.v3.4.json#FIND-27 | artifacts/decisions/TASK-1012.decision.md | RT-SYMLINK-001 ESCALATED by design: realpath resolution absent; lexical classification only. Architectural gap. | Yes — when realpath-aware audit policy implemented |
| FIND-28 | (not in source) | Backlog | artifacts/governance/red-team-execution-results.v3.4.json#RT-HITL-ATTESTATION-001; artifacts/governance/threat-finding-backlog.v3.4.json#FIND-28 | artifacts/decisions/TASK-1012.decision.md | RT-HITL-ATTESTATION-001 FAIL gap: HITL attestation validator not implemented; evidence_timestamp_source not validated. | Yes — when HITL validator implemented |
| FIND-29 | (not in source) | Mitigated | artifacts/verify/TASK-1013.verify.md | artifacts/decisions/TASK-1013.decision.md | validate_context_stack import side-effect removed; explicit init function with stream injection; unit test confirms clean import | No |
| FIND-30 | (not in source) | Mitigated | artifacts/verify/TASK-1014.verify.md | artifacts/decisions/TASK-1014.decision.md | per-case (60s) and per-suite (600s) timeouts implemented; TIMEOUT case marking and CI strict-run failure | No |
| FIND-31 | (not in source) | Mitigated | artifacts/verify/TASK-1015.verify.md; artifacts/governance/verify-floor-baseline.v3.4.json | artifacts/decisions/TASK-1015.decision.md | verify-floor-baseline.v3.4.json snapshots 32 historical artifacts (advisory); post-baseline new/modified artifacts strict; --verify-floor-enforce passes 0 failures as of TASK-1019 | No |
| FIND-32 | (not in source) | Mitigated | artifacts/verify/TASK-1019.verify.md; artifacts/governance/red-team-execution-results.v3.4.json | artifacts/decisions/TASK-1019.decision.md | 9/12 red-team cases promoted to regression (regression_promoted=true); execution results JSON serves as regression corpus | No |
| FIND-33 | (not in source) | Mitigated | artifacts/verify/TASK-1020.verify.md | artifacts/decisions/TASK-1020.decision.md | v3.4 plan enforces consistent self-assertion; governance-repair-manifest.v3.4.json as authoritative task ID registry | No |
| FIND-34 | (not in source) | Mitigated | artifacts/verify/TASK-1020.verify.md; artifacts/governance/governance-repair-manifest.v3.4.json | artifacts/decisions/TASK-1020.decision.md | governance-repair-manifest.v3.4.json defines reserved_task_range and execution_order; preflight confirmed ID uniqueness; hard-coded task ID checks replaced | No |

---

## Red-Team Gap Findings Summary

| Case ID | Result | Gap Type | Finding ID | Disposition |
|---|---|---|---|---|
| RT-PATH-002 | FAIL | dotdot normalization absent in classify_path() | FIND-26 | Backlog — next_task_id=TBD |
| RT-HITL-ATTESTATION-001 | FAIL | HITL attestation validator not implemented | FIND-28 | Backlog — next_task_id=TBD |
| RT-THREAT-SEMANTIC-001 | ESCALATED_BY_DESIGN | semantic validator for threat findings JSON not implemented | FIND-25 | Backlog — regression_candidate=false per design; semantic validator not yet implemented; not pretending mitigated |

---

## Pending Update Integration

| Finding ID | Source | finalized_by | Proposed → Final Status |
|---|---|---|---|
| FIND-18 | TASK-1006 / TASK-1019 | TASK-1012 | In-Progress → In-Progress (conditions 1+2 unmet) |
| FIND-23 | TASK-1021 / TASK-1019 | TASK-1012 | In-Progress → In-Progress (runtime guard deferred) |
| FIND-24 | TASK-1021 / TASK-1019 | TASK-1012 | In-Progress → In-Progress (runtime guard deferred) |

---

## Historical / Frozen Classifications

| Task | Classification | Rationale |
|---|---|---|
| TASK-964 | historical limited evidence (mvp) | Right-answer-for-wrong-reason; not retroactively upgraded by TASK-1010 production canonical drill. is_historical_limited_evidence_exception() guard active. |
| TASK-1001 | blocked (partial supersession) | AC-5b (GEMINI.md Architecture Synthesizer) unimplemented; blocked_reason.reason_code=external_dependency_unavailable; no v3.4 prompt authorized to change. |

---

## Status Summary

| Status | FIND-01..FIND-12 (retained) | FIND-13..FIND-34 (new) | Total |
|---|---|---|---|
| Open | 10 | 2 | 12 |
| Mitigated | 2 | 10 | 12 |
| In-Progress | 0 | 6 | 6 |
| Backlog | 0 | 4 | 4 |
| **Total** | **12** | **22** | **34** |
