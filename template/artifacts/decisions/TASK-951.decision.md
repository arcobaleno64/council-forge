# Decision Log: TASK-951

## Metadata
- Task ID: TASK-951
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T11:10:00+08:00

## Decision Class
scope-drift-waiver

## Affected Gate
Gate_E

## Scope
Current task artifact governance and exception handling.

## Issue
本 live drill 要驗證 blocked 任務不能只靠 decision 或 blocked_reason 恢復，必須先有合法且 `Status: applied` 的 improvement artifact。

## Options Considered
- 只保留 blocked_reason 與 decision，直接假設任務可 resume
- 建立 improvement artifact，但保留 `draft` 或 `approved`
- 停止 resume，直到存在 `Status: applied` 的 improvement artifact，再由 verify evidence 關閉事件

## Chosen Option
停止 resume，直到 improvement artifact 為 `Status: applied`，再由 verify artifact 記錄 blocked / resume 鏈。

## Reasoning
如果只靠 decision 或 blocked_reason 就恢復，會讓 Gate E 失去意義，也無法證明 PDCA 已落地。這個 live drill 的目的就是證明 applied improvement 是 resume 的硬條件，而不是附註。

## Implications
- blocked 與 resume 必須同時出現在 decision、improvement 與 verify evidence 中
- 最終樣本雖然收斂到 `done`，但必須保留完整 Gate E 證據
- `TASK-951` 可直接拿來重跑 status validator

## Expiry
None

## Linked Artifacts
- `artifacts/tasks/TASK-951.task.md`
- `artifacts/research/TASK-951.research.md`
- `artifacts/plans/TASK-951.plan.md`
- `artifacts/code/TASK-951.code.md`
- `artifacts/verify/TASK-951.verify.md`
- `artifacts/status/TASK-951.status.json`
- `artifacts/improvement/TASK-951.improvement.md`

## Follow Up
- 保留 `TASK-951` 作為 blocked / PDCA / resume live drill 樣本
- 若 Gate E 條件再收緊，更新本樣本與 runbook

## Guard Exception
- Exception Type: allow-scope-drift
- Scope Files: BOOTSTRAP_PROMPT.md, docs/artifact_schema.md, docs/orchestration.md, docs/red_team_runbook.md, docs/templates/blocking/TEMPLATE.md, docs/templates/implementer/TEMPLATE.md, docs/templates/parallel/TEMPLATE.md, docs/templates/reviewer/TEMPLATE.md, docs/templates/tester/TEMPLATE.md, docs/templates/verifier/TEMPLATE.md, obsidian/app.json, obsidian/core-plugins.json, temp_test.ps1, template/BOOTSTRAP_PROMPT.md, template/artifacts/scripts/Invoke-CodexAgent.ps1, template/artifacts/scripts/Invoke-GeminiAgent.ps1, template/artifacts/scripts/discover_templates.py, template/artifacts/scripts/guard_status_validator.py, template/artifacts/scripts/run_red_team_suite.py, template/docs/artifact_schema.md, template/docs/orchestration.md, template/docs/red_team_runbook.md, template/docs/templates/blocking/TEMPLATE.md, template/docs/templates/implementer/TEMPLATE.md, template/docs/templates/parallel/TEMPLATE.md, template/docs/templates/reviewer/TEMPLATE.md, template/docs/templates/tester/TEMPLATE.md, template/docs/templates/verifier/TEMPLATE.md, test_e2e.ps1, tmp-red-team/manual-git-test/
- Justification: 目前工作樹包含跨任務的既有與進行中變更，這些檔案不屬於 TASK-951 的 plan/code 變更範圍；本次僅為 S1 驗證窗口進行受控豁免，避免把跨任務 dirty state 誤判為 TASK-951 scope drift。
