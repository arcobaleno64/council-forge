# Decision Log: TASK-900

## Metadata
- Task ID: TASK-900
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
S1 驗證期間，`guard_status_validator.py` 啟用 git-backed scope check 後，將工作樹中與 TASK-900 無關的跨任務 dirty files 視為 scope drift，導致 TASK-900 驗證被阻擋。

## Options Considered
- 立即清空工作樹後再驗證
- 把所有 dirty files 寫入 TASK-900 plan/code scope
- 以受控 guard exception 豁免本次 scope drift，保留可審計軌跡

## Chosen Option
採用受控 guard exception，僅在 `--allow-scope-drift` 模式下針對明確檔案集合豁免 scope drift。

## Reasoning
目前工作樹同時承載多個任務中的變更，直接將其納入 TASK-900 會造成 plan/code 失真；清空工作樹則會中斷當前整體開發節奏。使用 decision artifact 的顯式豁免可保留審計性，並把風險限制在已列出的檔案範圍內。

## Implications
- TASK-900 在 `--allow-scope-drift` 下可降級處理此批 drift files
- 必須保留明確 Scope Files 與 Justification，避免無邊界放寬
- 後續若工作樹清理完成，應移除此 guard exception

## Expiry
None

## Linked Artifacts
- `artifacts/tasks/TASK-900.task.md`
- `artifacts/research/TASK-900.research.md`
- `artifacts/plans/TASK-900.plan.md`
- `artifacts/code/TASK-900.code.md`
- `artifacts/verify/TASK-900.verify.md`
- `artifacts/status/TASK-900.status.json`

## Follow Up
- 在完成跨任務整併後，移除本 decision 的 guard exception
- 保持 TASK-900 的 plan/code scope 定義不被跨任務檔案污染

## Guard Exception
- Exception Type: allow-scope-drift
- Scope Files: BOOTSTRAP_PROMPT.md, docs/artifact_schema.md, docs/orchestration.md, docs/red_team_runbook.md, docs/templates/blocking/TEMPLATE.md, docs/templates/implementer/TEMPLATE.md, docs/templates/parallel/TEMPLATE.md, docs/templates/reviewer/TEMPLATE.md, docs/templates/tester/TEMPLATE.md, docs/templates/verifier/TEMPLATE.md, obsidian/app.json, obsidian/core-plugins.json, temp_test.ps1, template/BOOTSTRAP_PROMPT.md, template/artifacts/scripts/Invoke-CodexAgent.ps1, template/artifacts/scripts/Invoke-GeminiAgent.ps1, template/artifacts/scripts/discover_templates.py, template/artifacts/scripts/guard_status_validator.py, template/artifacts/scripts/run_red_team_suite.py, template/docs/artifact_schema.md, template/docs/orchestration.md, template/docs/red_team_runbook.md, template/docs/templates/blocking/TEMPLATE.md, template/docs/templates/implementer/TEMPLATE.md, template/docs/templates/parallel/TEMPLATE.md, template/docs/templates/reviewer/TEMPLATE.md, template/docs/templates/tester/TEMPLATE.md, template/docs/templates/verifier/TEMPLATE.md, test_e2e.ps1, tmp-red-team/manual-git-test/
- Justification: 目前工作樹包含跨任務的既有與進行中變更，這些檔案不屬於 TASK-900 的 plan/code 變更範圍；本次僅為 S1 驗證窗口進行受控豁免，避免把跨任務 dirty state 誤判為 TASK-900 scope drift。
