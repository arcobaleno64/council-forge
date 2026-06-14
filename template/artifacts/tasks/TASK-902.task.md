# Task: TASK-902 Blocked Resume Drill

## Metadata
- Task ID: TASK-902
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T10:15:00+08:00

## Objective
提供一組可重跑的 blocked / PDCA / resume 樣本，證明 `blocked` 任務恢復前必須有 `Status: applied` 的 improvement artifact。

## Background
workflow 新規則要求 Gate E 不只檢查 improvement 檔存在，還要檢查改善已落地。`TASK-902` 用簡單 probe 檔演練整條鏈。

## Inputs
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/drills/TASK-902.probe.txt`
- `docs/workflow_state_machine.md`

## Constraints
- 不修改任何產品程式碼
- probe 檔最終只能有兩行：`TASK-902 probe`、`resume-ok`
- improvement artifact 必須為 `Status: applied`

## Acceptance Criteria
- [x] 存在完整的 task / research / plan / code / improvement / verify / status artifacts
- [x] verify evidence 清楚說明 blocked 與 resume 的條件
- [x] `TASK-902` improvement artifact 為 `Status: applied`
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-902` 回報 `[OK] Validation passed`

## Dependencies
- Python 3

## Out of Scope
- 實際產品 build 或測試

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Built-in blocked/resume drill sample.
