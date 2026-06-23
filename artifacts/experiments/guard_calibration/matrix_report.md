# Guard Calibration Matrix Report

- Generated: 2026-06-23T00:58:53+08:00
- Repo root: `/home/user/council-forge`
- Sample size (requested): 18
- Total cases run: 40
- Runtime: 14.2s

## Headline Result

No false positives and no false negatives detected across the sampled corpora. Within this sample the guards are neither over-strict nor over-loose.

## Labeling Convention

Positive class = "artifact SHOULD be rejected" (a real defect exists).

| | guard rejected (fail) | guard accepted (pass) |
|---|---|---|
| **defect present (SHOULD_FAIL)** | TP | FN (too loose) |
| **valid artifact (SHOULD_PASS)** | FP (too strict) | TN |

## Per-Guard Confusion Matrix

| Guard | TP | TN | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|
| `guard_contract_validator` | 1 | 1 | 0 | 0 | 1.000 | 1.000 |
| `guard_status_validator` | 20 | 18 | 0 | 0 | 1.000 | 1.000 |

## False Positives (over-strict — valid artifacts wrongly rejected)

_None._

## False Negatives (over-loose — defects wrongly accepted)

_None._

## Corruption Coverage (SHOULD_FAIL)

| Corruption class | cases | caught (TP) | missed (FN) |
|---|---|---|---|
| `delete_required_metadata_field` | 4 | 4 | 0 |
| `illegal_state` | 4 | 4 | 0 |
| `malformed_timestamp` | 4 | 4 | 0 |
| `missing_lifecycle_artifact` | 4 | 4 | 0 |
| `oversize_artifact` | 4 | 4 | 0 |
| `root_template_divergence` | 1 | 1 | 0 |

## Method

1. **SHOULD_PASS** — `guard_status_validator` is run IN PLACE against a sample of real tasks that are currently green in the repo; each is expected to pass. A pristine contract-fixture copy is run through `guard_contract_validator` and is expected to pass. Any failure here is a false positive (over-strict).
2. **SHOULD_FAIL** — for each sampled task the artifact tree is copied to an isolated temp root (via the red_team `copy_task_fixture` helper), exactly ONE labeled corruption is applied, and the guard is run against the temp copy; each is expected to fail. Any pass is a false negative (over-loose). A root/template divergence is injected for the contract guard.
3. All mutation happens on temp copies; the real repo tree is never modified. Guards are invoked as real subprocesses and exit codes are the ground truth (0 = pass).

Corruption classes exercised:

- `delete_required_metadata_field` — remove the `- Status:` line from task ## Metadata
- `malformed_timestamp` — strip `+08:00` from the task `Last Updated` field
- `illegal_state` — set status.json `state` to an unreachable/invalid value
- `oversize_artifact` — pad an artifact past 512KB (MAX_ARTIFACT_FILE_BYTES)
- `missing_lifecycle_artifact` — delete the plan for a plan-requiring task
- `root_template_divergence` — diverge a synced file's template copy (contract guard)

## Honest Limitations

- This is a **sample-based** measurement, not exhaustive. Confusion-matrix counts are only valid within the sampled tasks and the specific corruption classes listed; absence of FP/FN here does not prove the guards are perfectly calibrated in general.
- Each SHOULD_FAIL case applies a single, deliberately-detectable corruption. Subtle or compound defects (e.g. semantically-wrong-but-well-formed content) are out of scope.
- The SHOULD_PASS corpus is biased toward already-green tasks (selected BY passing the guard), so the FP measurement specifically tests whether re-running the guard on known-good input ever flips to reject — it cannot detect valid artifacts that were never committed because the guard rejected them historically.
- `precision`/`recall` are computed from positive-class = should-be-rejected; with zero FP/FN both are 1.0, which reflects the sample, not a formal guarantee.
- The contract guard contributes a single SHOULD_PASS and single SHOULD_FAIL case (one divergence class), so its matrix is illustrative rather than statistically robust.
