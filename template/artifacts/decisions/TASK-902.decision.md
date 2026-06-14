# Decision Log: TASK-902

## Metadata
- Task ID: TASK-902
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-15T00:00:00+08:00

## Decision Class
scope-drift-waiver

## Affected Gate
Gate_B

## Scope
Current task artifact governance and exception handling.

## Issue
S2 驗證時，`guard_status_validator.py` 的 git-backed scope check 將跨任務 dirty files 視為 TASK-902 的 scope drift，導致回放驗證失敗。

## Options Considered
- 清空工作樹後再重跑 S2
- 把跨任務 dirty files 寫入 TASK-902 的 plan/code scope
- 使用 decision-based guard exception 在 `--allow-scope-drift` 下受控豁免

## Chosen Option
使用 decision-based guard exception，僅在 `--allow-scope-drift` 下豁免明確列出的 drift files。

## Reasoning
跨任務 dirty files 並非 TASK-902 的實際交付內容，若直接寫入 plan/code 會污染任務邊界；以 decision artifact 的結構化豁免可保留審計軌跡且控制風險範圍。

## Implications
- TASK-902 在 `--allow-scope-drift` 下可完成回放驗證
- Guard Exception 必須維持 Scope Files 與實際 drift 同步
- 後續工作樹清理後應移除本豁免

## Expiry
None

## Linked Artifacts
- `artifacts/tasks/TASK-902.task.md`
- `artifacts/research/TASK-902.research.md`
- `artifacts/plans/TASK-902.plan.md`
- `artifacts/code/TASK-902.code.md`
- `artifacts/verify/TASK-902.verify.md`
- `artifacts/status/TASK-902.status.json`
- `artifacts/improvement/TASK-902.improvement.md`

## Follow Up
- 整理跨任務工作樹變更後，移除此 guard exception
- 保持 TASK-902 的 plan/code 範圍純粹

## Guard Exception
- Exception Type: allow-scope-drift
- Scope Files: BOOTSTRAP_PROMPT.md, docs/artifact_schema.md, docs/orchestration.md, docs/red_team_runbook.md, docs/templates/blocking/TEMPLATE.md, docs/templates/implementer/TEMPLATE.md, docs/templates/parallel/TEMPLATE.md, docs/templates/reviewer/TEMPLATE.md, docs/templates/tester/TEMPLATE.md, docs/templates/verifier/TEMPLATE.md, obsidian/app.json, obsidian/core-plugins.json, temp_test.ps1, template/BOOTSTRAP_PROMPT.md, template/artifacts/scripts/Invoke-CodexAgent.ps1, template/artifacts/scripts/Invoke-GeminiAgent.ps1, template/artifacts/scripts/discover_templates.py, template/artifacts/scripts/guard_status_validator.py, template/artifacts/scripts/run_red_team_suite.py, template/docs/artifact_schema.md, template/docs/orchestration.md, template/docs/red_team_runbook.md, template/docs/templates/blocking/TEMPLATE.md, template/docs/templates/implementer/TEMPLATE.md, template/docs/templates/parallel/TEMPLATE.md, template/docs/templates/reviewer/TEMPLATE.md, template/docs/templates/tester/TEMPLATE.md, template/docs/templates/verifier/TEMPLATE.md, test_e2e.ps1, tmp-red-team/manual-git-test/
- Justification: 目前工作樹包含跨任務的既有與進行中變更，這些檔案不屬於 TASK-902 的 plan/code 變更範圍；本次僅為 S2 驗證窗口進行受控豁免，避免把跨任務 dirty state 誤判為 TASK-902 scope drift。
