# Research: TASK-951

## Metadata
- Task ID: TASK-951
- Artifact Type: research
- Owner: Gemini
- Status: ready
- Last Updated: 2026-04-11T11:10:00+08:00

## Research Questions
- blocked 任務恢復前，最少要滿足哪些 artifact 與 metadata 條件？
- Gate E 與 status validator 在這條鏈上各自負責什麼？

## Confirmed Facts
- `blocked -> *` transition 會檢查 improvement artifact 是否存在，且至少有一份 improvement 的 metadata `Status` 必須為 `applied`（source: `artifacts/scripts/guard_status_validator.py`).
- blocked state 進入時必須記錄 `blocked_reason`，恢復前則需要 improvement artifact 與合法的 resume 條件（source: `docs/workflow_state_machine.md`).
- improvement artifact 至少要有 `Trigger Type`、`Preventive Action (System Level)`、`Validation`、`Final Rule` 與 `## 9. Status`，否則不算合法 PDCA 輸出（source: `docs/artifact_schema.md`).

## Relevant References
- `artifacts/scripts/guard_status_validator.py`
- `docs/workflow_state_machine.md`
- `docs/artifact_schema.md`

## Sources
[1] Arcobaleno64. "guard_status_validator.py." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/guard_status_validator.py (2026-04-15 retrieved)
[2] Arcobaleno64. "workflow_state_machine.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/workflow_state_machine.md (2026-04-15 retrieved)
[3] Arcobaleno64. "artifact_schema.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/artifact_schema.md (2026-04-15 retrieved)

## Uncertain Items
None

## Constraints For Implementation
- live drill 要保留 blocked / resume 證據，但最終樣本必須是可重跑的合法完成狀態。
- improvement artifact 必須明確說明 preventive action 與 validation。
