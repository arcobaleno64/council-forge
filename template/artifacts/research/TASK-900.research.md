# Research: TASK-900

## Metadata
- Task ID: TASK-900
- Artifact Type: research
- Owner: Gemini
- Status: ready
- Last Updated: 2026-04-11T10:00:00+08:00

## Research Questions
- `guard_status_validator.py` 與 `guard_contract_validator.py` 各自負責什麼驗證邊界？
- bootstrap smoke test 需要哪些 sample artifacts 才能重跑？

## Confirmed Facts
- `guard_status_validator.py` 專責 task / artifact / state 驗證，會檢查 metadata、research fact-only 契約、premortem 與 Gate E（source: `artifacts/scripts/guard_status_validator.py`).
- `guard_contract_validator.py` 專責 workflow 文件、bootstrap、template 與 Obsidian 同步契約（source: `artifacts/scripts/guard_contract_validator.py`).
- `BOOTSTRAP_PROMPT.md` 要求初始化後同時執行 `guard_status_validator.py --task-id TASK-900` 與 `guard_contract_validator.py`（source: `BOOTSTRAP_PROMPT.md`).

## Relevant References
- `artifacts/scripts/guard_status_validator.py`
- `artifacts/scripts/guard_contract_validator.py`
- `BOOTSTRAP_PROMPT.md`

## Sources
[1] Arcobaleno64. "guard_status_validator.py." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/guard_status_validator.py (2026-04-15 retrieved)
[2] Arcobaleno64. "guard_contract_validator.py." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/guard_contract_validator.py (2026-04-15 retrieved)
[3] Arcobaleno64. "BOOTSTRAP_PROMPT.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/BOOTSTRAP_PROMPT.md (2026-04-15 retrieved)

## Uncertain Items
None

## Constraints For Implementation
- Smoke sample 必須只依賴 repo 內現有文件與 scripts。
- Research artifact 必須保持 fact-only，不得包含 `Recommendation`。
