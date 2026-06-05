# Process Improvement

## Metadata
- Task ID: TASK-951
- Artifact Type: improvement
- Source Task: TASK-951
- Trigger Type: blocked
- Owner: Claude
- Status: applied
- Last Updated: 2026-04-11T11:10:00+08:00
- Improvement Profile: gate-e

## Risk Analysis (新增)
- Predicted Risks: [R1, R2]  # 來自 TASK-951.plan.md 的 premortem 
- Realized Risks: [R1]        # 此次 live drill 中實際觸發的是 R1 (缺少 applied improvement)
- Missed Risks: []             # 沒有未預測的新風險

## 1. What Happened
這個 live drill 模擬 blocked 任務若只補 decision 而不補 improvement，就可能讓流程錯誤地恢復。事件焦點不是 blocked 本身，而是 resume 條件是否真的依附在 PDCA。

## 2. Why It Was Not Prevented
若沒有把 Gate E 明確寫成 applied improvement 條件，blocked_reason 與 decision 很容易被誤當成足夠的恢復證據。

## 3. Failure Classification
- G4 Guard coverage gap
- Premortem failure

## 4. Corrective Action (Immediate)
- 建立 `TASK-951` 的 applied improvement artifact
- 在 verify evidence 中明列 blocked condition、decision 與 applied improvement 的順序

## 5. Preventive Action (System Level)
- 將 blocked / PDCA / resume 演練納入 `docs/red_team_runbook.md` 與 `run_red_team_suite.py`
- 保留 live drill 樣本，避免未來只剩文件描述而沒有可重跑案例

## 6. Validation
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-951` 應通過
- 以 `--from-state blocked --to-state planned` 檢查時，只有 applied improvement 才能恢復

## 7. Impact Scope
- `docs/red_team_runbook.md`
- `docs/red_team_scorecard.md`
- `artifacts/scripts/run_red_team_suite.py`
- `artifacts/improvement/TASK-951.improvement.md`

## 8. Final Rule
Blocked live drills 必須用 `Status: applied` 的 improvement artifact 證明 Gate E 已落地；只有 decision 或 blocked_reason 不足以 resume。

## 9. Status
applied
