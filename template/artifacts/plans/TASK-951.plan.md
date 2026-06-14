# Plan: TASK-951

## Metadata
- Task ID: TASK-951
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-11T11:10:00+08:00
- PDCA Stage: P

## Scope
- 建立一組 blocked / PDCA / resume live drill artifacts。
- 用 decision、improvement 與 verify evidence 表達 Gate E 的 applied 條件。

## Files Likely Affected
- `artifacts/decisions/TASK-951.decision.md`
- `artifacts/improvement/TASK-951.improvement.md`
- `artifacts/verify/TASK-951.verify.md`
- `artifacts/status/TASK-951.status.json`

## Proposed Changes
- 建立 research artifact，固定 Gate E 的最小條件。
- 建立 decision artifact，說明 blocked 與 resume 的合法判定。
- 建立 `Status: applied` 的 improvement artifact 與 verify evidence。

## Risks
- R1
  - Risk: verify 只寫最終 pass，沒有把 blocked 與 resume 條件寫清楚
  - Trigger: Evidence 未列 decision 與 improvement
  - Detection: 無法從 verify 重建 Gate E 何時生效
  - Mitigation: 在 Evidence 中明列 blocked condition、decision 與 applied improvement
  - Severity: blocking
- R2
  - Risk: live drill 樣本誤導讀者以為 improvement 只要存在即可
  - Trigger: improvement metadata 沒有維持 `Status: applied`
  - Detection: status validator transition check 失敗
  - Mitigation: 在 verify 與 task acceptance criteria 重複強調 `Status: applied`
  - Severity: non-blocking
- R3
  - Risk: blocked/resume 時序描述不一致，造成 Gate E 生效點難以審核
  - Trigger: verify 與 decision 對 blocked 原因或恢復條件描述不同步
  - Detection: 人工驗讀時無法一致重建事件順序
  - Mitigation: 固定以 decision 為單一事實來源，verify 僅引用對應條目
  - Severity: non-blocking

## Validation Strategy
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-951`
- 人工檢查 verify evidence 是否完整描述 blocked / resume 鏈

## Out of Scope
- 任意產品程式修改

## Ready For Coding
yes
