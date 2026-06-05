# Process Improvement

## Metadata
- Task ID: TASK-950
- Artifact Type: improvement
- Source Task: TASK-950
- Trigger Type: guard miss
- Owner: Claude
- Status: applied
- Last Updated: 2026-04-11T11:00:00+08:00
- Improvement Profile: retrospective

## Risk Analysis (新增)
None

## 1. What Happened
這個 live drill 刻意模擬 research overreach 與 code-over-plan。前者可透過 research fact-only guard 收斂，後者則主要依賴 decision artifact、verify evidence 與人工 review。

## 2. Why It Was Not Prevented
目前 workflow 對 research 越界已有明確 contract，但對「Codex 提出超出 plan 的必要修改」仍以 decision / verify 為主，尚未有專門的 diff-to-plan 自動 guard。

## 3. Failure Classification
- G4 Guard coverage gap
- Unknown gap

## 4. Corrective Action (Immediate)
- 建立 `TASK-950` live drill，固定記錄 decision、improvement 與 verify evidence
- 在 verify 中要求同時引用 decision 與 improvement artifact

## 5. Preventive Action (System Level)
- 將 role boundary 演練納入 `docs/red_team_runbook.md` 與 `run_red_team_suite.py`
- 在 backlog 中明列 diff-to-plan 自動 guard 為後續補強項

## 6. Validation
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-950` 應通過
- `TASK-950.verify.md` 應可重建 research overreach 與 code-over-plan 的收斂順序

## 7. Impact Scope
- `docs/red_team_runbook.md`
- `docs/red_team_scorecard.md`
- `docs/red_team_backlog.md`
- `artifacts/scripts/run_red_team_suite.py`

## 8. Final Rule
Role boundary live drills 必須以 decision artifact 記錄越界事件，並以 verify evidence 證明 corrected artifacts 才能收斂到 `done`。

## 9. Status
applied
