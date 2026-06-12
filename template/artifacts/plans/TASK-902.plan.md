# Plan: TASK-902

## Metadata
- Task ID: TASK-902
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-11T10:15:00+08:00
- PDCA Stage: P

## Scope
- 建立 `TASK-902` 的 blocked / resume drill artifacts 與 probe 檔。
- 用 improvement artifact 展示 Gate E 的 applied 條件。

## Files Likely Affected
- `artifacts/scripts/drills/TASK-902.probe.txt`
- `artifacts/improvement/TASK-902.improvement.md`
- `artifacts/verify/TASK-902.verify.md`
- `artifacts/status/TASK-902.status.json`

## Proposed Changes
- 建立靜態 probe 檔，最終內容為兩行。
- 建立 improvement artifact，說明 blocked 未被預防的原因與 system-level action。
- 產出 verify artifact，記錄 blocked/resume 證據與最終狀態。

## Risks
- R1
  - Risk: drill sample 只有 improvement 檔存在，但沒有反映 applied 條件，導致 Gate E 樣本失真
  - Trigger: improvement artifact 仍停在 `draft` 或 `approved`
  - Detection: `python artifacts/scripts/guard_status_validator.py --task-id TASK-902`
  - Mitigation: 直接將 sample improvement artifact 寫成 `Status: applied`
  - Severity: blocking
- R2
  - Risk: verify artifact 沒有清楚解釋 blocked 與 resume 關係，讓樣本失去教學價值
  - Trigger: verify 只寫最終 pass，沒有記錄 blocked 條件
  - Detection: 人工閱讀 verify artifact 時無法重建 flow
  - Mitigation: 在 Evidence 中明列 blocked reason、improvement applied 與 probe 最終狀態
  - Severity: non-blocking
- R3
  - Risk: probe 檔內容被後續測試覆蓋，造成 blocked/resume 範例不可重現
  - Trigger: drill 腳本或手動測試誤寫 `TASK-902.probe.txt`
  - Detection: verify evidence 與 probe 實際內容不一致
  - Mitigation: 驗證時固定比對 probe 兩行最終內容並寫入 verify evidence
  - Severity: non-blocking

## Validation Strategy
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-902`
- 人工檢查 `TASK-902.improvement.md` 是否為 `Status: applied`

## Out of Scope
- 任何 app 層 build / test

## Ready For Coding
yes
