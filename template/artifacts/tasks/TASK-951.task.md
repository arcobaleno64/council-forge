# Task: TASK-951 Blocked Resume Live Drill

## Metadata
- Task ID: TASK-951
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T11:10:00+08:00

## Objective
驗證 blocked 任務只有在 decision、improvement 與 verify evidence 都完整，且 improvement 為 `Status: applied` 時，才能合法恢復並收斂到 `done`。

## Background
`TASK-902` 已是靜態 blocked / resume 樣本；`TASK-951` 則提供 live drill 版本，讓紅隊演練可以直接驗證 Gate E、PDCA 與 final verify 鏈。

## Inputs
- `docs/workflow_state_machine.md`
- `docs/artifact_schema.md`
- `docs/red_team_runbook.md`

## Constraints
- 不修改任何產品程式碼
- verify evidence 必須說明 blocked condition、decision 與 applied improvement 的關係
- 最終樣本必須能被 `guard_status_validator.py` 重跑

## Acceptance Criteria
- [x] 存在完整的 task / research / plan / code / decision / improvement / verify / status artifacts
- [x] decision artifact 說明 blocked 與 resume 的判定
- [x] improvement artifact 為 `Status: applied`
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-951` 回報 `[OK] Validation passed`

## Dependencies
- Python 3

## Out of Scope
- 任意產品程式修改

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Built-in blocked / PDCA / resume live drill.
