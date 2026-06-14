# Task: TASK-900 Validator Contract Smoke Test

## Metadata
- Task ID: TASK-900
- Artifact Type: task
- Owner: Claude
- Status: done
- Last Updated: 2026-04-11T10:00:00+08:00

## Objective
驗證內建 sample artifacts 與兩支 guard（`guard_status_validator.py`、`guard_contract_validator.py`）在 root repo 中都能正常通過。

## Background
`TASK-900` 是 bootstrap 與 template 複製後的第一個 smoke test。它的目的不是改產品程式，而是確認 workflow 契約、artifact 契約與文件同步契約都已落地。

## Inputs
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/guard_contract_validator.py`
- `AGENTS.md`
- `OBSIDIAN.md`

## Constraints
- 僅驗證 workflow / prompt / guard 契約，不涉及 app code
- 驗證結果必須可由 repo 內 sample artifacts 直接重跑
- Build Guarantee 必須明確說明本 task 沒有 build 單元變更

## Acceptance Criteria
- [x] `python artifacts/scripts/guard_status_validator.py --task-id TASK-900` 回報 `[OK] Validation passed`
- [x] `python artifacts/scripts/guard_contract_validator.py` 回報 `[OK] Contract validation passed`
- [x] `TASK-900` research artifact 符合 fact-only 契約
- [x] `TASK-900` verify artifact 含有 `## Build Guarantee`

## Dependencies
- Python 3

## Out of Scope
- 任何 `external/` 目錄修改
- 任何產品功能實作

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Built-in smoke test for validator and contract synchronization.
