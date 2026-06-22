# Red Team Suite Report

| Case | Phase | Expected | Outcome | Expected Exit | Actual Exit | Evidence | Notes |
|---|---|---|---|---:|---:|---|---|
| `RT-001` | static | fail | pass | 1 | 1 | `must not contain ## Recommendation` | [ERROR] Validation failed |
| `RT-002` | static | fail | pass | 1 | 1 | `must include an inline citation` | [ERROR] Validation failed |
| `RT-003` | static | fail | pass | 1 | 1 | `must start with UNVERIFIED:` | [ERROR] Validation failed |
| `RT-004` | static | fail | pass | 1 | 1 | `requires at least 1 blocking risks` | [ERROR] Validation failed |
| `RT-005` | static | fail | pass | 1 | 1 | `requires an improvement artifact` | [ERROR] Validation failed |
| `RT-006` | static | fail | pass | 1 | 1 | `requires an improvement artifact with Status: applied` | [ERROR] Validation failed |
| `RT-007` | static | fail | pass | 1 | 1 | `Contract drift detected` | template workflow state machine drift |
| `RT-008` | static | fail | pass | 1 | 1 | `missing required phrase: template/OBSIDIAN.md` | Obsidian GitHub/Template section lost required template mapping |
| `RT-009` | static | fail | pass | 1 | 1 | `BOOTSTRAP_PROMPT.md missing required phrase: guard_contract_validator.py` | bootstrap lost contract-guard step |
| `RT-010` | static | fail | pass | 1 | 1 | `missing required ## Sources section` | [ERROR] Validation failed |
| `RT-011` | static | pass | pass | 0 | 0 | `Mapping To Plan entry must match` | [OK] Validation passed |
| `RT-012` | static | pass | pass | 0 | 0 | `missing reviewer field` | [OK] Validation passed |
| `RT-013` | static | fail | pass | 1 | 1 | `git-backed scope check found actual changed files not listed` | [ERROR] Validation failed |
| `RT-014` | static | fail | pass | 1 | 1 | `commit-range scope check found diff files not listed` | [ERROR] Validation failed |
| `RT-015` | static | fail | pass | 1 | 1 | `--allow-scope-drift requires a decision artifact with ## Guard Exception` | [ERROR] Validation failed |
| `RT-016` | static | pass | pass | 0 | 0 | `[OK] Validation passed` | [OK] Validation passed |
| `RT-017` | static | fail | pass | 1 | 1 | `Snapshot SHA256 does not match Changed Files Snapshot` | [ERROR] Validation failed |
| `RT-018` | static | fail | pass | 1 | 1 | `github-pr scope check found diff files not listed` | [ERROR] Validation failed |
| `RT-019` | static | fail | pass | 1 | 1 | `commit-range archive fallback found diff files not listed` | [ERROR] Validation failed |
| `RT-020` | static | fail | pass | 1 | 1 | `Archive SHA256 does not match archive file` | [ERROR] Validation failed |
| `RT-021` | static | pass | pass | 0 | 0 | `lightweight candidate` | [OK] Validation passed |
| `RT-022` | static | pass | pass | 0 | 0 | `[AUTO-UPGRADE]` | auto_upgrade_log written to status.json |
| `RT-023` | static | fail | pass | 1 | 1 | `waiver expired` | [ERROR] Validation failed |
| `RT-024` | static | fail | pass | 1 | 1 | `API Base URL host '127.0.0.1' is not allowed` | [ERROR] Validation failed |
| `RT-025` | static | pass | pass | 0 | 0 | `[OK] Validation passed` | [OK] Validation passed |
| `RT-026` | static | fail | pass | 1 | 1 | `Text file too large` | [FAIL] Text file too large: /home/user/council-forge/.codex-red-team/RT-026-87dfe2d2/artifacts/plans/TASK-976.plan.md exceeds size ceiling of 524288 bytes |
| `RT-027` | static | fail | pass | 1 | 1 | `exceeds replay byte cap` | [ERROR] Validation failed |
| `RT-028` | static | fail | pass | 1 | 1 | `exceeds replay byte cap` | [ERROR] Validation failed |
| `RT-029` | static | fail | pass | 1 | 1 | `template/README.md section 'Architecture Snapshot' contains forbidden phrase: template/ + .github/ + OBSIDIAN.md + external/` | template README architecture snapshot regressed to source-only wording |
| `RT-030` | static | pass | pass | 0 | 0 | `fail-closed external legacy import confirmed` | unparseable external legacy verify stays deferred with open verification debt |
