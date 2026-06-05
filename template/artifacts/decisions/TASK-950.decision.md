# Decision Log: TASK-950

## Metadata
- Task ID: TASK-950
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T11:00:00+08:00

## Decision Class
scope-drift-waiver

## Affected Gate
Gate_B

## Scope
Current task artifact governance and exception handling.

## Issue
本 live drill 模擬兩個角色邊界事件：一是 Gemini research 草稿夾帶 solution design；二是 Codex 提議擴大到未列入 plan 的額外修改。

## Options Considered
- 接受越界內容，直接讓任務往下推進
- 只在對話中口頭修正，不留下 artifact 證據
- 停止推進、記錄 decision，改以 corrected artifacts + verify evidence 收斂

## Chosen Option
停止推進、記錄 decision，並要求最終 artifacts 只保留 fact-only research 與 plan-scoped code 結果。

## Reasoning
若接受越界內容，會讓 research 與 implementation 的責任邊界失真，也無法證明 workflow 真正有能力收斂這類事件。用 decision artifact 固定記錄事件，再由 verify artifact 指向 corrected artifacts，才能證明最終 `done` 狀態不是靠口頭宣告取得。

## Implications
- 最終 research artifact 必須維持 fact-only
- code artifact 只能描述 plan 內的 live drill 產物
- verify evidence 必須同時指向 decision 與 improvement artifact

## Expiry
None

## Linked Artifacts
- `artifacts/tasks/TASK-950.task.md`
- `artifacts/research/TASK-950.research.md`
- `artifacts/plans/TASK-950.plan.md`
- `artifacts/code/TASK-950.code.md`
- `artifacts/verify/TASK-950.verify.md`
- `artifacts/status/TASK-950.status.json`
- `artifacts/improvement/TASK-950.improvement.md`

## Follow Up
- 保留 `TASK-950` 作為 role boundary live drill 樣本
- 若未來新增自動化 diff-to-plan guard，更新 `docs/red_team_backlog.md`

## Guard Exception
- Exception Type: allow-scope-drift
- Scope Files: BOOTSTRAP_PROMPT.md, docs/artifact_schema.md, docs/orchestration.md, docs/red_team_runbook.md, docs/templates/blocking/TEMPLATE.md, docs/templates/implementer/TEMPLATE.md, docs/templates/parallel/TEMPLATE.md, docs/templates/reviewer/TEMPLATE.md, docs/templates/tester/TEMPLATE.md, docs/templates/verifier/TEMPLATE.md, obsidian/app.json, obsidian/core-plugins.json, temp_test.ps1, template/BOOTSTRAP_PROMPT.md, template/artifacts/scripts/Invoke-CodexAgent.ps1, template/artifacts/scripts/Invoke-GeminiAgent.ps1, template/artifacts/scripts/discover_templates.py, template/artifacts/scripts/guard_status_validator.py, template/artifacts/scripts/run_red_team_suite.py, template/docs/artifact_schema.md, template/docs/orchestration.md, template/docs/red_team_runbook.md, template/docs/templates/blocking/TEMPLATE.md, template/docs/templates/implementer/TEMPLATE.md, template/docs/templates/parallel/TEMPLATE.md, template/docs/templates/reviewer/TEMPLATE.md, template/docs/templates/tester/TEMPLATE.md, template/docs/templates/verifier/TEMPLATE.md, test_e2e.ps1, tmp-red-team/manual-git-test/
- Justification: 目前工作樹包含跨任務的既有與進行中變更，這些檔案不屬於 TASK-950 的 plan/code 變更範圍；本次僅為 S1 驗證窗口進行受控豁免，避免把跨任務 dirty state 誤判為 TASK-950 scope drift。
