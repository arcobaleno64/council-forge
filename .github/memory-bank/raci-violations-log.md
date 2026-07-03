# RACI Violations Audit Log

This is an append-only log maintained by the Gemini RACI Auditor. It tracks all structural RACI violations detected within the repository, forming the backbone of the Audit-Driven Development (ADD) and Double-Loop Learning governance lenses.

## Active Violations Log

- 2026-04-26T19:46:51+08:00 | Agent: Codex | File: docs/orchestration.md | Violation: code (實檔修改) vs code (實檔修改)
- 2026-05-03T18:29:39+08:00 | Agent: Codex CLI | File: docs/orchestration.md | Category: workflow_contract_docs

## Reconciliation Notes

- 2026-07-03 | CHG-005 (HC-7 方向 a): 上列 2 條 Codex/`docs/orchestration.md` (workflow_contract_docs) 違規之 root cause 為 routing↔RACI 矛盾——routing matrix 鼓勵 Codex 撰寫 workflow contract docs，但 `RACI_MATRIX_V2['Codex CLI']` 未授權該類。已由 CHG-005 於 `RACI_MATRIX_V2['Codex CLI']` 增列 `workflow_contract_docs` reconcile。此為承認現行實務之政策修正，**非對既有違規之追溯豁免**（歷史記錄保留不動）。
