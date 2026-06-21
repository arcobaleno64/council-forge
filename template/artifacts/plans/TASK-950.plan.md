# Plan: TASK-950

## Metadata
- Task ID: TASK-950
- Artifact Type: plan
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-11T11:00:00+08:00
- PDCA Stage: P

## Scope
- 建立一組可重跑的 role boundary live drill artifacts。
- 用 decision / improvement / verify artifacts 表達研究越界與 code-over-plan 的收斂流程。

## Files Likely Affected
- `artifacts/decisions/TASK-950.decision.md`
- `artifacts/improvement/TASK-950.improvement.md`
- `artifacts/verify/TASK-950.verify.md`
- `artifacts/status/TASK-950.status.json`

## Proposed Changes
- 建立 fact-only research artifact，僅描述角色邊界與收斂要求。
- 建立 decision artifact，記錄 research overreach 與 code-over-plan 事件。
- 建立 improvement artifact，將 role boundary drill 轉成 system-level rule。
- 建立 verify artifact，證明 corrected artifacts 才能進入 `done`。

## Risks
- R1
  - Risk: verify evidence 沒有清楚指出哪一段屬於越界事件、哪一段屬於最終合法輸出
  - Trigger: verify 只寫「已修正」但未指向 decision artifact
  - Detection: 驗讀 verify 無法重建事件順序
  - Mitigation: 在 Evidence 中固定列 decision 與 improvement artifact
  - Severity: blocking
- R2
  - Risk: live drill 被誤讀為產品程式修改案例
  - Trigger: code artifact 未明說沒有產品 code 變更
  - Detection: Build Guarantee 與 Files Changed 描述互相矛盾
  - Mitigation: 在 code / verify 明確寫 `None (no .csproj modified)`
  - Severity: non-blocking
- R3
  - Risk: decision artifact 未跟 verify 證據保持一致，導致 drill 結論可追溯性下降
  - Trigger: 更新 decision 後未同步 verify 的 Evidence 區段
  - Detection: verify 無法對應到正確 decision 條目
  - Mitigation: 每次變更 decision 同步更新 verify 的證據引用
  - Severity: non-blocking

## Validation Strategy
- 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-950`
- 人工檢查 `TASK-950.verify.md` 是否同時引用 decision 與 improvement

## Out of Scope
- 任意產品程式修改

## Ready For Coding
yes
