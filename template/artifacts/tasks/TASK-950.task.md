# Task: TASK-950 Role Boundary Live Drill

## Metadata
- Task ID: TASK-950
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T11:00:00+08:00

## Objective
演練 Gemini research 越界與 Codex 超出 plan 範圍時，workflow 是否能用 decision / verify / improvement artifacts 收斂，而不是讓違規內容直接流到 `done`。

## Background
靜態 red-team case 可驗證 research contract 與 contract drift，但角色越界仍需要一組完整 live drill，證明 corrected artifacts、decision log 與 verify evidence 真的能把事件關閉。

## Inputs
- `docs/subagent_roles.md`
- `docs/artifact_schema.md`
- `docs/workflow_state_machine.md`
- `docs/red_team_runbook.md`

## Constraints
- 不修改任何產品程式碼
- 最終 research artifact 必須維持 fact-only
- verify evidence 必須同時引用 decision 與 improvement artifact

## Acceptance Criteria
- [x] 存在完整的 task / research / plan / code / decision / improvement / verify / status artifacts
- [x] decision artifact 明確記錄 research overreach 與 code-over-plan 事件
- [x] improvement artifact 將 role boundary drill 的 preventive action 落成 system-level rule
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-950` 回報 `[OK] Validation passed`

## Dependencies
- Python 3

## Out of Scope
- 任意產品功能修改
- 任意 `external/` 目錄改動

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Built-in role-boundary live drill.
