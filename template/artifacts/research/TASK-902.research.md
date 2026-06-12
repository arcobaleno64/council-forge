# Research: TASK-902

## Metadata
- Task ID: TASK-902
- Artifact Type: research
- Owner: Gemini
- Status: ready
- Last Updated: 2026-04-11T10:15:00+08:00

## Research Questions
- Gate E 在 blocked resume 時需要什麼條件？
- improvement artifact 需要哪些最小欄位才算合法？

## Confirmed Facts
- `blocked -> *` transition 會檢查對應 task 是否存在 improvement artifact，且該 artifact 必須為 `Status: applied`（source: `artifacts/scripts/guard_status_validator.py`).
- improvement artifact 至少要有 `Trigger Type`、`Preventive Action (System Level)`、`Validation`、`Final Rule` 與 `## 9. Status`（source: `docs/artifact_schema.md`).
- `blocked` 恢復前的 improvement artifact 是 workflow 契約的一部分，不屬於 Obsidian-only 或 README-only 規範（source: `docs/workflow_state_machine.md`).

## Relevant References
- `artifacts/scripts/guard_status_validator.py`
- `docs/artifact_schema.md`
- `docs/workflow_state_machine.md`

## Sources
[1] Arcobaleno64. "guard_status_validator.py." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/guard_status_validator.py (2026-04-15 retrieved)
[2] Arcobaleno64. "artifact_schema.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/artifact_schema.md (2026-04-15 retrieved)
[3] Arcobaleno64. "workflow_state_machine.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/workflow_state_machine.md (2026-04-15 retrieved)

## Uncertain Items
None

## Constraints For Implementation
- Drill sample 必須以靜態 artifacts 表達 blocked / resume，而不是依賴臨時手動步驟。
- improvement artifact 必須寫出可驗證的 preventive action 與 final rule。
