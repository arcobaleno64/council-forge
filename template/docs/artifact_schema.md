# ARTIFACT_SCHEMA

本文件定義 artifact-first workflow 的檔案命名、欄位、狀態、驗證規則與最小品質要求。

目標有三個：

1. 讓不同代理可透過固定 schema 接手工作。
2. 讓狀態可追蹤、可驗證、可重跑。
3. 避免 artifact 退化成不可機讀、不可審計的自由散文。

## 1. 通用規則

### 1.0 Artifact 為邊界物件（Boundary Objects framing）

本框架之 artifact 同時為跨代理（Claude / Gemini / Codex / subagents）之**邊界物件（Boundary Object, Star & Griesemer 1989）**：不同代理對同一 artifact 之解讀容許局部差異（如 implementer 視 code artifact 為 deliverable、verifier 視為 input），但 artifact 之嚴格欄位定義（schema）即跨代理之共同語言契約，使各代理對「任務已完成」「驗收已通過」等概念之認知對齊。

實作上之意涵：

- artifact schema 之嚴格定義不可隨意鬆動；欄位刪減須走 decision artifact 變更管制。
- 每一新增之 artifact 類型須先設 schema，再建實例；不得倒序。
- 跨代理之語義不對稱（如 implementer 假設「測試通過」與 verifier 之「驗收通過」之差異）由 schema 之欄位顯式區隔（如 `## Build Guarantee` 與 `## Acceptance Criteria Checklist` 分離）。
- PROCESS_LEDGER 與 status.json 為跨 PDCA 階段之邊界物件，承載 closure 與 next-task 入口。

### 1.1 命名規範

所有 artifacts 必須使用一致命名：

`TASK-<流水號>.<artifact-type>.<ext>`

範例：

- `TASK-001.task.md`
- `TASK-001.research.md`
- `TASK-001.plan.md`
- `TASK-001.code.md`
- `TASK-001.test.md`
- `TASK-001.verify.md`
- `TASK-001.decision.md`
- `TASK-001.status.json`

### 1.2 目錄規範

建議目錄：

```text
/artifacts
  /tasks
  /research
  /plans
  /code
  /test
  /verify
  /decisions
  /improvement
  /registry
  /metrics
  /status
```

`artifacts/status/` 只保留 `TASK-*.status.json` 與必要的狀態輔助檔；跨 task 匯總輸出應放到 `artifacts/registry/` 或 `artifacts/metrics/`。

`artifacts/test/legacy_verify_corpus/` 保留給 external legacy verify import 的共享 regression fixtures；unit tests 與 red-team drills 應優先共用這份 corpus，而不是各自維護平行樣本。

### 1.3 任務識別碼

- 任務識別碼格式：`TASK-001`、`TASK-002`。
- 一個任務可有多個關聯 artifacts，但只能有一個主 status artifact。
- 同一任務的 artifacts 必須使用相同 task id。

### 1.4 時間格式

- 所有時間使用 ISO 8601。
- 所有 workflow / template / root 長期維護 artifacts 的時間戳必須使用 `Asia/Taipei`，並帶 `+08:00`。
- 不接受只有日期或缺少時區的 `Last Updated`。
- 範例：`2026-04-09T14:30:00+08:00`

### 1.5 文件語言與風格

- artifact 以清晰、可驗證、可接手為原則。
- 用語必須具體，避免模糊詞如「可能沒問題」「應該可行」。
- 若不確定，必須明確標示 `uncertain` 或對應欄位中的未確認事項。

## 2. Artifact 類型總表

| 類型 | 副檔名 | 主要作者 | 目的 |
|---|---|---|---|
| task | `.task.md` | Claude | 定義任務目標、限制、驗收條件 |
| research | `.research.md` | Gemini | 提供規格依據、查詢結果、實作約束 |
| plan | `.plan.md` | Claude | 定義實作範圍、影響面、風險 |
| code | `.code.md` | Codex | 記錄修改內容、變更檔案、已做測試 |
| test | `.test.md` | Codex subagent 或 Claude | 記錄測試結果與失敗摘要 |
| verify | `.verify.md` | Claude 或 verifier | 對照驗收條件判定 pass/fail |
| decision | `.decision.md` | Claude | 記錄衝突、決策理由、取捨 |
| status | `.status.json` | Claude | 提供機讀狀態與下一步 |
| improvement | `.improvement.md` | Claude | PDCA 改進記錄：失敗分析、矯正與預防措施，以及 verify / done 後的輕量流程復盤 |

## 3. 必填通用欄位

所有 markdown 型 artifact 必須至少包含以下通用區段：

- `Task ID`
- `Artifact Type`
- `Owner`
- `Status`
- `Last Updated`

建議固定寫法：

```md
## Metadata
- Task ID: TASK-001
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-09T14:30:00+08:00
```

若缺少上述欄位，該 artifact 視為不合法。

## 4. 狀態值規範

### 4.1 通用狀態值

不同 artifact 可使用以下狀態值的子集合：

- `drafted`
- `in_progress`
- `ready`
- `approved`
- `blocked`
- `pass`
- `fail`
- `done`
- `superseded`

### 4.2 狀態使用原則

- task: `drafted`, `approved`, `blocked`, `done`
- research: `in_progress`, `ready`, `blocked`, `superseded`
- plan: `drafted`, `ready`, `approved`, `blocked`, `superseded`
- code: `in_progress`, `ready`, `blocked`, `superseded`
- test: `in_progress`, `pass`, `fail`, `blocked`, `superseded`
- verify: `pass`, `fail`, `blocked`, `superseded`
- decision: `done`
- improvement: `draft`, `approved`, `applied`

## 5. 各 artifact schema

---

## 5.1 Task Artifact Schema

> PDCA Stage: P (Intake，定義階段，先於 Plan)

檔名：`artifacts/tasks/TASK-001.task.md`

用途：任務的單一權威定義。

必填區段：

```md
# Task: TASK-001

## Metadata
- Task ID:
- Artifact Type: task
- Owner:
- Status:
- Last Updated:

## Objective

## Background

## Inputs

## Constraints

## Acceptance Criteria

## Dependencies

## Out of Scope

## Assurance Level

## Project Adapter

## Current Status Summary
```

欄位規則：

- `Objective`: 一句到數句，清楚描述任務最終目標。
- `Inputs`: 指出可用檔案、模組、文件或使用者需求。
- `Constraints`: 必須明確列出不可違反條件。
- `Acceptance Criteria`: 必須條列且可驗證。
- `Out of Scope`: 避免 Codex 擴大實作範圍。
- `Assurance Level`: 目前允許 `POC`、`MVP`、`Production`；決定最低驗證強度與 required artifacts。
- `Project Adapter`: 目前允許 `generic`、`web-app`、`backend-service`、`batch-etl`、`cli-tool`、`docs-spec`、`resource-constrained-ui`；用於承接 runtime-specific 驗證規則。

最低驗收標準：

- 驗收條件不可空白。
- 至少一條 `Out of Scope` 或明確寫 `None`。
- `Constraints` 不可省略。

### Assurance / Adapter Rule Resolution

`Assurance Level` 與 `Project Adapter` 的唯一權威規則表位於 `artifacts/scripts/workflow_constants.py`。

- resolver 固定先套 `Assurance Level` baseline，再套 `Project Adapter` override，最後產生單一 resolved policy。
- `required artifacts`、verify required fields / sections、allowed `reason_code`、`verification_readiness` 都必須讀 resolved policy，不得從 artifact 偶然存在與否反推。
- `docs-spec` 是目前唯一已明確特化的 adapter：它會在 `testing / verifying / done` 移除 `test` requirement，並允許 `NOT_APPLICABLE_BY_ADAPTER`。
- 其餘 adapter 目前都明確繼承 `generic`；若未補專屬規則，表示它們暫時只共享 generic baseline，而不是已完整驗證通用性。

---

## 5.2 Research Artifact Schema

> PDCA Stage: P (Plan，規劃前之事實準備)

檔名：`artifacts/research/TASK-001.research.md`

用途：將外部知識、規格、版本差異與實作約束落地。

必填區段：

```md
# Research: TASK-001

## Metadata
- Task ID:
- Artifact Type: research
- Owner:
- Status:
- Last Updated:

## Research Questions

## Confirmed Facts

## Relevant References

## Sources

## Uncertain Items

## Constraints For Implementation
```

可選區段（research/cache draft 專用）：

```md
## Source Cache

## Tavily Cache
```

欄位規則：

- `Research Questions`: 至少一條。
- `Confirmed Facts`: 必須是可採用於規劃或實作的事實。
- `Relevant References`: 需標明來源名稱或文件名稱。
- `Sources`: 每行格式必須為 `[N] Author/Org. "Title." URL (YYYY-MM-DD retrieved)`。
- `Sources`: 至少 2 筆。
- `Source Cache`: 選填。保存 research 過程中可重用但尚未沉澱到 memory-bank 的來源摘錄；不得取代 `## Sources`。
- `Tavily Cache`: 選填。僅在 Gemini 被明確允許使用本機 Tavily CLI 時使用；每筆必須記錄實際 command、query、retrieved date、URLs 與結果摘要。
- `Sources` failure_grade:
  - `CRITICAL`: 缺少 `## Sources` 區段，或 0 筆來源。
  - `MAJOR`: 格式違規（例如缺少 URL、整體格式不符）。
  - `MINOR`: 日期缺失或只提供 partial date。
- `Uncertain Items`: 沒有時要寫 `None`。
- `Constraints For Implementation`: 要可直接被 plan 使用。
- research artifact 是 fact-only 契約，不得包含 `Recommendation`、implementation approach、PR title/body，或任何 solution 設計建議。

最低驗收標準：

- 不可只有連結或文件名，必須有整理後結論。
- 不可把推測寫進 `Confirmed Facts`。
- `Confirmed Facts` 的每一條 claim 都必須在同一條目內附上 inline citation（URL、`gh api` 指令或 artifact / doc path）。
- `Uncertain Items` 若非 `None`，每條都必須以 `UNVERIFIED:` 開頭並說明原因。
- Tavily CLI 不可用、來源擷取失敗或日期不明時，不得用未驗證內容補洞；必須寫入 `Uncertain Items`，例如 `UNVERIFIED: Tavily CLI unavailable`。
- `Source Cache` / `Tavily Cache` 只是 research artifact draft cache；Claude/Codex 篩選後才可透過 Remember Capture 流程進入 `.github/memory-bank/`。
- 至少要有一個可供 implementation 使用的約束。

---

## 5.3 Plan Artifact Schema

> PDCA Stage: P (Plan，含 premortem R1-R4+)

檔名：`artifacts/plans/TASK-001.plan.md`

用途：將需求與研究轉成可控實作範圍。

必填區段：

```md
# Plan: TASK-001

## Metadata
- Task ID:
- Artifact Type: plan
- Owner:
- Status:
- Last Updated:

## Scope

## Files Likely Affected

## Proposed Changes

## Risks

## Validation Strategy

## Verification Obligations

## Out of Scope

## Ready For Coding
```

欄位規則：

- `Scope`: 明確描述此次計畫包含哪些內容。
- `Files Likely Affected`: 至少列出模組、目錄或檔案群。若 task 專屬 artifact 仍位於 dirty git worktree 中，`guard_status_validator.py` 也會用實際 git changed files 自動比對這個欄位。
- `Proposed Changes`: 條列具體改動。
- `Risks`: 不可省略。必須執行 premortem 分析（見 `docs/premortem_rules.md`）。每條風險必須包含 R 編號 + Risk / Trigger / Detection / Mitigation / Severity 五欄位。Severity 只能填 `blocking` 或 `non-blocking`。一般任務至少 2 條風險；安全性 / 依賴升級 / upstream PR 至少 4 條且至少 1 條 blocking。品質規則見 `docs/premortem_rules.md` §4。`guard_status_validator.py` 在 `planned → coding` 時會自動檢查。
- `Validation Strategy`: 必須說明如何驗證成功。
- `Verification Obligations`: 明列這個 task 在 `verify` 與 `status.open_verification_debts` 層需要結清或明示 deferred 的驗證責任。
- `Ready For Coding`: 只能填 `yes` 或 `no`。

最低驗收標準：

- 未列影響範圍的 plan 不可進 coding。
- `Ready For Coding` 為 `yes` 前，必須已有對應 task artifact。
- 若 task 需要 research，則 plan 建立前必須已有 research artifact。

---

## 5.4 Code Artifact Schema

> PDCA Stage: D (Do，實作執行)

檔名：`artifacts/code/TASK-001.code.md`

用途：記錄實作結果，避免主 thread 被 diff 與 log 淹沒。

必填區段：

```md
# Code Result: TASK-001

## Metadata
- Task ID:
- Artifact Type: code
- Owner:
- Status:
- Last Updated:

## Files Changed

## Execution Profile

## Subagent Plan

## Summary Of Changes

## Mapping To Plan

## Tests Added Or Updated

## Known Risks

## TAO Trace

## Blockers
```

可選區段（若需支援 historical diff reconstruction）：

```md
## Diff Evidence
- Evidence Type: commit-range
- Base Ref:
- Head Ref:
- Base Commit:
- Head Commit:
- Diff Command:
- Changed Files Snapshot:
- Snapshot SHA256:
- Archive Path:
- Archive SHA256:

## Diff Evidence
- Evidence Type: github-pr
- Repository:
- PR Number:
- API Base URL:
- Changed Files Snapshot:
- Snapshot SHA256:
```

欄位規則：

- `Files Changed`: 至少列出實際修改檔案，沒有修改時不可建立 code artifact。若 task 專屬 artifact 仍位於 dirty git worktree 中，`guard_status_validator.py` 會用實際 git changed files 自動驗證這個欄位；若為 clean task 且存在合法 diff evidence，也會在 historical replay 中驗證這個欄位。
- `Execution Profile`: 記錄實際使用的 Codex task scale、model policy、model 與 reasoning effort；若由 Claude 直接實作，必須記錄 routing override reason。
- `Subagent Plan`: 記錄 Codex 是否使用 subagent；未使用時寫 `None` 並說明理由，使用時列出各 subagent 的責任、write scope 與驗證分工。
- `Mapping To Plan`: 每行格式必須為 `- plan_item: {N.N}, status: done|partial|skipped, evidence: "{short description}"`。
- `Mapping To Plan`: 每個 plan item 都必須有對應一行；若無計畫對應則必須寫 `status: skipped, evidence: "not required by plan"`。
- `Tests Added Or Updated`: 沒有時寫 `None`。
- `Known Risks`: 沒有時寫 `None`。
- `TAO Trace`: risk ≥ 3（plan `## Risks` 任一條 `Severity: blocking`）之 implementer / verifier dispatch **必填**；risk ≤ 2 或 lightweight / docs-only 任務可寫 `None`。schema 與必填欄位見 [docs/agentic_execution_layer.md §2](agentic_execution_layer.md)。回填既有 artifact 時須以 `Reconstructed from artifact history` 開頭，不偽造當時即時思考。
- `Blockers`: 沒有時寫 `None`。
- `Diff Evidence`: 沒有時可省略或寫 `None`。目前 `guard_status_validator.py` 支援 `Evidence Type: commit-range` 與 `Evidence Type: github-pr`。
- `commit-range`: 要求 immutable commit pinning：`Base Commit` 與 `Head Commit` 必須是完整 40 字元 git commit SHA；`Base Ref` 與 `Head Ref` 是可選便利欄位，只用於偵測 ref drift。`Diff Command` 應對應實際 replay 命令。若擔心長期 git objects retention 不足，可額外提供 `Archive Path` 與 `Archive SHA256`；兩者必須一起出現，`Archive Path` 必須是 repo-relative、UTF-8、每行一個 normalized relative path、排序後、LF 換行的 text file，`Archive SHA256` 則是該 archive file 原始 bytes 的 SHA-256。guard 只會在 local git replay 失敗時改用 archive fallback，且 archive 內容仍必須與 `Changed Files Snapshot` 完全一致。
- `github-pr`: `Repository` 必須是 `owner/repo`，`PR Number` 必須是正整數；`API Base URL` 可省略，省略時預設 `https://api.github.com`，若使用 GitHub Enterprise Server 或本地 fixture，可覆寫成其他 http(s) endpoint。guard 會透過 GitHub PR files API 逐頁抓取 changed files，public repo 可不帶 token；private repo 或 rate-limited 環境則應提供 `GITHUB_TOKEN` 或 `GH_TOKEN`。
- `Changed Files Snapshot`: 必須列出 replayed diff 或 provider response 的完整檔案清單（以逗號分隔）。
- `Snapshot SHA256`: 必須是 `Changed Files Snapshot` 排序後以換行串接所得內容的 SHA-256。

最低驗收標準：

- 不能只寫「已完成修改」。
- 必須能看出改了哪裡、為何而改。
- 若超出 plan，必須明確標示並阻止 closure；在 task 專屬 dirty worktree 中，status guard 會直接用 git changed files 攔截未宣告 drift；在 clean task 且存在合法 diff evidence 時，status guard 會先驗證 `Changed Files Snapshot` 與 `Snapshot SHA256`，再用 pinned `commit-range`、archive fallback 或 `github-pr` provider response 重建 changed files 後攔截未宣告 drift。`--allow-scope-drift` 只可降級真正的 scope drift，不能覆蓋 diff evidence 損毀、archive 損毀或 provider evidence 錯誤。

---

## 5.5 Test Artifact Schema

> PDCA Stage: C (Check，測試輸出)

檔名：`artifacts/test/TASK-001.test.md`

用途：承接測試與驗證輸出，不把原始 log 丟進主 thread。

必填區段：

```md
# Test Report: TASK-001

## Metadata
- Task ID:
- Artifact Type: test
- Owner:
- Status:
- Last Updated:

## Test Scope

## Commands Executed

## Result Summary

## Failures

## Evidence Files

## Recommendation
```

欄位規則：

- `Commands Executed`: 至少列出實際命令或測試類型。
- `Result Summary`: 必須有總結，不可只貼 log。
- `Failures`: 沒有時寫 `None`。
- `Evidence Files`: 若完整 log 落地到其他檔案，需在此列出。

最低驗收標準：

- 不可只貼 raw output。
- 必須明確指出是 pass、fail 或 blocked。

---

## 5.6 Verify Artifact Schema

> PDCA Stage: C (Check，含 Build Guarantee)

檔名：`artifacts/verify/TASK-001.verify.md`

用途：對照 acceptance criteria 做最終驗收。

必填區段：

```md
# Verification: TASK-001

## Metadata
- Task ID:
- Artifact Type: verify
- Owner:
- Status:
- Last Updated:

## Verification Summary

## Acceptance Criteria Checklist

## Overall Maturity

## Deferred Items

## Evidence

## Evidence Refs

## Decision Refs

## Build Guarantee

## TAO Trace

## Pass Fail Result

## Remaining Gaps

## Recommendation
```

欄位規則：

- `Acceptance Criteria Checklist`: 必須逐條對照 task artifact。
- `Acceptance Criteria Checklist` item schema: `required_fields_by_assurance`
  - `POC`: `criterion`, `method`, `evidence`, `result`
  - `MVP`: `criterion`, `method`, `evidence`, `result`
  - `Production`: `criterion`, `method`, `evidence`, `result`, `reviewer`, `timestamp`
- `Acceptance Criteria Checklist` item `result` 必須使用：`verified`、`unverified`、`unverifiable`、`deferred`。
- 若 `result` 為 `unverified`、`unverifiable` 或 `deferred`，必須同時記錄 `decision_ref` 或 `reason_code`。
- `Acceptance Criteria Checklist` item `reason_code` 與 disallowed results 必須讀 resolved policy，不得在 validator / migration script 各自維護另一套清單。
- `Acceptance Criteria Checklist` item schema: `timestamp` 必須為 `Asia/Taipei` 的 ISO 8601 並帶 `+08:00`。
- `Verification Summary`: 用一段短文交代本次 verify 的覆蓋範圍與主要限制。
- `Overall Maturity`: 目前允許 `poc`、`mvp`、`production-blocked`、`production-ready`。
- `Deferred Items`: 沒有時寫 `None`；若有 deferred/unverifiable 項目，需與 checklist / decision refs 對應。
- `Deferred Items` 與 `status.open_verification_debts` 必須能由 checklist item 中落在 `status_debt_results` 的 `result` 推導；不得再用 `Remaining Gaps` 承載正式 debt 狀態。
- `Evidence`: 指向 code/test/research/decision artifacts。
- `Evidence Refs`: 列 repo-relative artifact path，方便機器檢查存在性。
- `Decision Refs`: 列 repo-relative decision path；沒有時寫 `None`。
- `Build Guarantee` (FUP-2)：針對本 task 修改過的**每一個** build 單元，明列 build 指令、exit code、與 output tail。
  - .NET 任務：對每個被修改的 `.csproj` 執行 `dotnet build <csproj> -c Debug` 並貼出結尾段落（含「建置成功/錯誤」或等價 summary）。
  - 非 .NET 任務（python / node / etc.）：列對應 build / type-check / lint 指令與結果。
  - 若本 task 未修改任何 `.csproj` 或等價 build 單元，寫 `None (no .csproj modified)` 並簡述原因（例如純文件變更、python-only 任務）。
  - **禁止**以「測試專案 build 成功」替代「被測專案 build 成功」—— 兩者不等價。若發生此類事故，應建立 decision artifact 記錄根因與修正。
- `Pass Fail Result`: 只能填 `pass` 或 `fail`。
- `TAO Trace`: risk ≥ 3 之 verifier dispatch **必填**；其他可寫 `None`。schema 與必填欄位見 [docs/agentic_execution_layer.md §2](agentic_execution_layer.md)。回填既有 verify artifact 時須以 `Reconstructed from artifact history` 開頭。
- `Remaining Gaps`: 沒有時寫 `None`。
- `status.verification_readiness` 與 `status.open_verification_debts` 必須能由 verify artifact 的 structured checklist 推導，不可脫鉤。
- root repo tracked artifacts 不得依賴 legacy verify/status compatibility fallback；fallback 只保留給外部或歷史輸入。
- `artifacts/scripts/migrate_artifact_schema.py` 預設以 `--input-mode root-tracked` 執行；此模式只允許對 root tracked artifacts 做 deterministic normalization，不得把 heuristic import 當成日常治理路徑。
- 若要匯入外部 legacy artifact，必須顯式使用 `--input-mode external-legacy`。此模式允許 heuristic mapping，但 migration report 必須揭露 strategy / confidence / unresolved fields。
- `external-legacy` 模式下，只有已具 structured checklist 的 verify artifact 可直接保留原結果；heading block、checkbox list 與無法辨識的 legacy verify 一律必須降為 manual-review / deferred 路徑，不得直接升成 authoritative `pass`。

最低驗收標準：

- 未逐條對照 acceptance criteria 的 verify artifact 不合法。
- 若有未完成條件，不可標 `pass`。
- 缺少 `## Build Guarantee` 區段的 verify artifact 不合法；`guard_status_validator.py` 會在 `required_markers["verify"]` 擋下。

---

## 5.7 Decision Artifact Schema

> PDCA Stage: 跨層橫切（cross-cutting；可承接任一階段之衝突、取捨或 routing override）

檔名：`artifacts/decisions/TASK-001.decision.md`

用途：處理衝突、取捨、補查決策與流程分歧。

必填區段：

```md
# Decision Log: TASK-001

## Metadata
- Task ID:
- Artifact Type: decision
- Owner:
- Status: done
- Last Updated:

## Decision Class

## Affected Gate

## Scope

## Issue

## Options Considered

## Chosen Option

## Reasoning

## Implications

## Expiry

## Linked Artifacts

## Follow Up
```

若 decision 用於 guard waiver，需額外提供：

```md
## Guard Exception
- Exception Type:
- Scope Files:
- Justification:
- Override_Reason:
```

何時必須建立 decision artifact：

- 研究結果互相衝突
- 計畫需做取捨
- Codex 提出超出原計畫的必要修改
- 驗收未通過，需決定回退或補改
- 對話內容與 artifact 衝突
- 使用 `--allow-scope-drift` 將 drift 降級為 warning

`Decision Class` 目前固定 taxonomy：

- `scope-drift-waiver`
- `risk-acceptance`
- `defer`
- `reject`
- `conflict-resolution`

`## Guard Exception` 規則：

- `Exception Type: allow-scope-drift` 代表此 decision 是 scope drift 的顯式豁免。
- `Scope Files`: 必須明列此次豁免涵蓋的 drift files，使用逗號分隔；不可只寫 `all` 或留白。
- `Justification`: 必須說明為何這次 drift 可以被受控接受。若 `guard_status_validator.py` 在 `--allow-scope-drift` 模式下找不到對應 waiver，仍會 fail。
- `Override_Reason`: 當使用 `guard_status_validator.py --override ... --override-approver ...` 時，decision artifact 應同步記錄人工核准的 override 理由；此欄位不得只寫 `test` 或空泛字眼，必須能對應 override log 中的 `reason`。

---

## 5.8 Status Artifact Schema

> PDCA Stage: meta（meta-state，承載各階段機器可讀狀態，不屬任一單一階段）

檔名：`artifacts/status/TASK-001.status.json`

用途：提供機器可讀狀態，作為流程主控依據。

JSON schema 範例：

```json
{
  "task_id": "TASK-001",
  "state": "planned",
  "current_owner": "Claude",
  "next_agent": "Codex",
  "required_artifacts": ["task", "research", "plan"],
  "available_artifacts": ["task", "research", "plan"],
  "missing_artifacts": [],
  "assurance_level": "mvp",
  "project_adapter": "generic",
  "open_verification_debts": [],
  "blocked_reason": "",
  "last_updated": "2026-04-09T14:30:00+08:00"
}
```

### state 合法值

- `drafted`
- `researched`
- `planned`
- `coding`
- `testing`
- `verifying`
- `done`
- `blocked`

### 欄位規則

- `task_id`: 必須對應既有 task artifact。
- `state`: 必須符合 workflow state machine。
- `required_artifacts`: 此狀態進入下一步所需類型。
- `missing_artifacts`: 實際缺件清單。
- `assurance_level`: `poc`、`mvp`、`production` 之一。status guard 依此決定最低 required artifacts。
- `project_adapter`: `generic`、`web-app`、`backend-service`、`batch-etl`、`cli-tool`、`docs-spec`、`resource-constrained-ui` 之一。
- `open_verification_debts`: 尚未結清的 verify obligations；沒有時填 `[]`。
- `blocked_reason`: 若 state 為 `blocked`，不可空白。
- `Gate_E_passed` (新增)：Gate E 驗證是否通過。只有 state 為 `done` 且曾經歷 blocked 時才填寫。值為 `true` 或 `false`。
- `Gate_E_evidence` (新增)：proof of Gate E；當 `Gate_E_passed: true` 時必填。格式為 array of paths / artifact IDs（例如 `["artifacts/decisions/TASK-001.decision.md", "artifacts/improvement/TASK-001.improvement.md"]`）。
- `Gate_E_timestamp` (新增)：Gate E 驗證通過時間戳，採 ISO 8601+08:00 格式。當 `Gate_E_passed: true` 時必填。

### 完整範例（包含 Gate E）

```json
{
  "task_id": "TASK-001",
  "state": "done",
  "current_owner": "Claude",
  "next_agent": "Claude",
  "required_artifacts": ["code", "research", "status", "task", "verify"],
  "available_artifacts": ["code", "decision", "improvement", "plan", "research", "status", "task", "verify"],
  "missing_artifacts": [],
  "blocked_reason": "",
  "last_updated": "2026-04-11T11:10:00+08:00",
  "Gate_E_passed": true,
  "Gate_E_evidence": ["artifacts/decisions/TASK-001.decision.md", "artifacts/improvement/TASK-001.improvement.md"],
  "Gate_E_timestamp": "2026-04-11T11:10:00+08:00"
}
```

---

## 5.9 Improvement Artifact Schema (PDCA Act + Double-Loop Learning)

> PDCA Stage: A (Act，Gate E 之核心 artifact，回灌至下一輪 Plan)

**Double-Loop Learning framing（Argyris 1977）**：本 artifact 為 Argyris 雙迴路學習之具體落地。單迴路（Single-Loop）為「失敗 → 修 code」，僅在行為層調整；雙迴路（Double-Loop）為「失敗 → 檢討產生此錯誤之系統規則 → 修運作層邏輯」。本 schema 之 `## Why It Was Not Prevented`（為何既有 guard / schema / prompt 未阻擋此錯誤）與 `## Preventive Action (System Level)`（修 prompt-patterns / guard / template / workflow）即雙迴路之強制欄位；single-loop 之即時修正則於 code artifact 與本 artifact 之 `## Corrective Action` 承接。此區隔使 improvement artifact 不退化為「只記症狀」。

檔名：`artifacts/improvement/TASK-001.improvement.md`

用途：`improvement` artifact 同時承接兩種場景：

1. **Gate E / PDCA**：任務發生 failure、blocked、或流程缺陷後，分析根因、執行矯正、提出系統層級預防措施。
2. **Post-run review**：任務已跑到 `verify` 或 `done` 後，用 human-first 方式快速記錄流程實際怎麼走、哪些步驟浪費、哪些地方最容易重犯。

命名規則：

- 主要改進：`TASK-001.improvement.md`
- 同一任務多次改進：`TASK-001-IMP-002.improvement.md`

必填區段（Gate E / validator-compatible profile）：

```md
# Process Improvement

## Metadata
- Task ID:
- Artifact Type: improvement
- Source Task:
- Trigger Type: (failure / blocked / inefficiency / guard miss)
- Improvement Profile: (gate-e / retrospective)
- Owner: Claude
- Status: draft
- Last Updated:

## Risk Analysis (新增)
- Predicted Risks: [R1, R2, ...]  # 來自 plan artifact 的 premortem 預測
- Realized Risks: [R1]             # 此次 blocked/failure 中實際發生的
- Missed Risks: []                 # plan 未預測但實際發生的（若無填 None）

## 1. What Happened

## 2. Why It Was Not Prevented

## 3. Failure Classification

## 4. Corrective Action (Immediate)

## 5. Preventive Action (System Level)

## 6. Validation

## 7. Impact Scope

## 8. Final Rule

## 9. Status
```

欄位規則：

- `Trigger Type`: 必須為 `failure`、`blocked`、`inefficiency` 或 `guard miss` 之一。
- `Improvement Profile`: `gate-e` 用於 blocked/failure 後的恢復治理；`retrospective` 用於 verify/done 後的常規復盤。
- `## Risk Analysis` (新增)：追蹤 premortem 預測與實際風險的映射。
  - `Predicted Risks`: 從 plan artifact 中的 `## Risks` 區段複製所有 R 編號（例如 `[R1, R2, R3]`）。
  - `Realized Risks`: 此次故障中實際觸發的風險編號。必須是 Predicted Risks 的子集或超集。若為超集，說明是 missed risk。
  - `Missed Risks`: 若有未在 plan 預測但實際發生的風險，在此列舉；若無填 `None`。此欄用於評估 premortem 品質。
- `## 1. What Happened`: 必須具體描述發生在哪個階段（Plan / Do / Check / Act）、哪個 agent、哪個 artifact，並用編號指出是哪條 Realized Risk。
- `## 2. Why It Was Not Prevented`: 必須指出哪條規則缺失、哪個 guard 沒覆蓋、哪個 prompt 太寬鬆。
- `## 3. Failure Classification`: 至少勾選一個分類（G1–G6、Premortem failure、Unknown gap）。
- `## 5. Preventive Action (System Level)`: **最重要區段**。必須至少包含一項：Prompt 修正、Guard 規則補強、Template 修正、或 Workflow 調整。
- `## 8. Final Rule`: 將改進轉成一句可執行規則。
- `## 9. Status`: `draft` → `approved` → `applied`。

輕量復盤區段（post-run review profile）：

```md
## What Actually Happened

## Steps That Felt Redundant

## Error-Prone Steps

## Surprises / Mismatches

## Template / Workflow Fix Candidates

## Next Time Default
```

使用原則：

- 任務完成到 `verify` 或 `done` 後，建議補一份短 improvement artifact，即使該任務沒有進入 `blocked`。
- 若 improvement artifact 需要同時滿足 **Gate E** 與 **日常復盤**，請保留上方 validator-compatible 區段，並在 `## 9. Status` 後追加上述 6 個 human-first 區段。
- `## What Actually Happened` 應描述實際流程，而不是理想流程。
- `## Steps That Felt Redundant` 應只寫真正造成浪費的步驟，不列無關背景。
- `## Error-Prone Steps` 應指出最可能重犯的操作、判斷或 handoff。
- `## Surprises / Mismatches` 用於記錄「文件寫的流程」與「實際跑出來的流程」之間的落差。
- `## Template / Workflow Fix Candidates` 應明確標示該改 template、prompt、guard、還是單純操作說明。
- `## Next Time Default` 應把本次學到的更佳預設寫成一句可直接重用的操作準則。

Repo-level quick index：

- `artifacts/improvement/PROCESS_LEDGER.md` 是 repo-level operational note，不屬於 validator 強制 artifact。
- 用途：作為冷啟動入口，快速回顧最近流程實際做了什麼、哪裡浪費、哪裡容易出錯。
- 欄位固定為 `Date`、`Task`、`Outcome`、`Top Waste`、`Top Risk`、`Fix Candidate`、`Applied?`。
- 建議閱讀順序：先看 `PROCESS_LEDGER.md`，再看最近 3 份 `TASK-XXX.improvement.md`，需要細節時再回跳 `verify` / `decision` / `status`。

工作流規則：

- **Gate E (PDCA)**：任何任務從 `blocked` 恢復前，必須先建立且通過驗證的 improvement artifact。`guard_status_validator.py` 在 `blocked → *` 轉移時自動檢查。
- 恢復前的 improvement artifact 必須為 `Status: applied`。`draft` 或 `approved` 不足以解除 blocked。
- **Routine review**：任務完成 `verify` 或 `done` 後，建議追加一份短 improvement artifact 並更新 `PROCESS_LEDGER.md`，但這不會改變 Gate E 的 validator 規則。

最低驗收標準：

- 不可只描述問題而無預防措施。
- 不可把整份 command log 或 raw terminal output 直接貼進 improvement artifact；應只保留短結論與必要 artifact path。
- Preventive Action 不可只寫「注意一下」，必須是可被 guard / prompt / template 執行的具體改動。
- Final Rule 必須是一句可直接加入 CLAUDE.md 或 guard script 的規則。
- `Validation` 不可空白，必須說明如何驗證該改善已落地。

---

## 5.10 Artifact Lineage MVP

用途：定義 artifact 間最小可查的 lineage 關係，供 registry 與後續自動化擴充使用。

最小 schema：

```yaml
lineage_entry:
  source_file: "artifacts/code/{task}.code.md"
  plan_item: "N.N"
  decision_refs:
    - "artifacts/decisions/{task}.decision.md"
  research_refs:
    - "artifacts/research/{task}.research.md"
  scope: "file-level only"
  generated_by: "build_decision_registry.py"
```

規則：

- `source_file`: 指向單一 code artifact，使用 repo-relative path。
- `plan_item`: 對應 code artifact `## Mapping To Plan` 的 `N.N` 項目。
- `decision_refs`: 指向相關 decision artifacts，使用 repo-relative path array。
- `research_refs`: 指向相關 research artifacts，使用 repo-relative path array。
- `scope`: 目前只支援 file-level only，不含行號、不含 commit hash。
- `generated_by`: 目前由 `build_decision_registry.py` 作為最小生成入口；未來可擴充其他 producer，但不得改變 MVP 的 file-level 邊界。

---

## 5.11 Assurance Resolver Pipeline（TASK-1008 schema clarification）

> Authoritative since: 2026-04-29 (TASK-1008). Decision ref: artifacts/decisions/TASK-1008.decision.md

### 5.11.1 Allowed Assurance Levels

Exactly three values are valid:

| Level | Meaning |
|---|---|
| `poc` | Proof-of-concept; minimal artifact requirements |
| `mvp` | Minimum viable product; standard governance gates |
| `production` | Full governance; requires manual review, build guarantee, and reviewer attestation |

`high` is **not** a valid assurance level and must be rejected by validators.

### 5.11.2 Resolver Pipeline

The assurance resolution follows this pipeline:

```
assurance baseline (task.md ## Assurance Level)
  → adapter override (PROJECT_ADAPTER_RULES artifact_overrides_by_state)
  → resolved policy (resolve_verification_policy)
```

Validators MUST read the **resolved policy** returned by `resolve_verification_policy(assurance_level, project_adapter)`, not re-derive requirements from artifact heuristics.

### 5.11.3 Strict Mode (root default)

Root strict mode applies to all new and modified artifacts after TASK-1008 baseline:

- **Missing assurance_level**: error (not warning). No silent default.
- **Unknown assurance_level**: explicit schema error. `high` and any value outside `{poc, mvp, production}` are schema violations.
- **task.md and status.json mismatch**: error. Both must declare the same value.
- **Forbidden**: silently defaulting unknown values to `poc`.

Implemented in:
- `guard_status_validator.py` → `validate_status_schema`: missing or invalid → error
- `guard_status_validator.py` → `validate_markdown_artifact` (task type): missing section → error; invalid raw value → error; mismatch with status.json → error
- `workflow_constants.py` → `validate_assurance_level_strict(value)`: raises `ValueError` on unknown or empty

### 5.11.4 Legacy Compatibility Mode (explicit invocation only)

Legacy mode exists only for historical or downstream artifacts that predate strict enforcement:

- **Invocation**: must call `workflow_constants.warn_and_default_assurance_level(value)` explicitly.
- **Silent default is forbidden**: code must never call this implicitly as a fallback.
- **Warning structure** (returned dict when defaulting occurs):
  - `defaulted_from`: the original invalid value
  - `selected_default`: the level that was substituted (`poc`)
  - `migration_debt`: human-readable message describing the required correction
- If the value is already valid, returns `(value, {})` with empty warning dict.

### 5.11.5 TASK-964 Policy Clarification

The historical TASK-964 governance drill is permanently classified as:

- **maturity**: `mvp + limited evidence`
- **reason**: the drill was correct in conclusion but was produced under a lower evidence floor than production-grade attestation requires.

Repaired future evidence MUST NOT retroactively upgrade TASK-964's historical maturity. Production-grade canonical drill ownership belongs to TASK-1010 (Prompt 4) or the manifest-designated equivalent.

## 5.12 Verify Floor Baseline Schema（TASK-1009 schema clarification）

> Authoritative since: 2026-05-03 (TASK-1009). Decision ref: artifacts/decisions/TASK-1009.decision.md

### 5.12.1 Purpose

`artifacts/governance/verify-floor-baseline.v3.4.json` is an **immutable snapshot** of all verify artifacts that existed **before** the TASK-1009 baseline was created. It classifies each entry by floor policy and enables split enforcement: historical artifacts remain advisory, while new and modified artifacts are immediately strict.

**Baseline semantics (critical)**:

- `baseline_verify_files` covers only verify artifacts that existed at baseline creation time.
- Verify artifacts created or modified **after** the baseline snapshot are **not** included in `baseline_verify_files`.
- `artifacts/verify/TASK-1009.verify.md` is intentionally absent from the baseline because it was created as part of TASK-1009 itself — after the baseline snapshot. It is classified as `strict` by `classify_verify_floor_policy`.
- Adding a post-baseline artifact to `baseline_verify_files` would incorrectly downgrade it from `strict` to `advisory_until_6d` — this MUST NOT be done.
- The baseline entry count (32) and the current total artifact count (33+) will diverge as new verify artifacts are created. This divergence is correct and expected.

### 5.12.2 Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | Must be `"verify-floor-baseline/v1"` |
| `plan_version` | string | yes | Must be `"v3.4"` |
| `created_at` | string | yes | Taipei timestamp; MUST come from a deterministic source |
| `created_at_source` | string | yes | Identifies the deterministic source (e.g. `"git:<sha>"`) |
| `created_by` | string | yes | Task ID that created this baseline |
| `sha256_method` | string | yes | Describes how sha256 was computed |
| `baseline_task_count` | integer | yes | Count of entries in `baseline_verify_files` |
| `policy` | object | yes | Policy constants (see §5.12.3) |
| `baseline_verify_files` | array | yes | One entry per baseline verify artifact |

### 5.12.3 Policy Object

| Field | Type | Description |
|---|---|---|
| `historical_unchanged` | string | Value: `"advisory_until_6d"` — baseline files with matching sha256 are advisory |
| `new_or_modified_after_baseline` | string | Value: `"strict"` — absent or sha256-changed files are strict |
| `full_enforcement_task` | string | Task ID for full repo enforcement (TASK-1015) |
| `full_enforcement_prompt` | string | Prompt label for full enforcement (`"6d"`) |

### 5.12.4 Baseline Entry Fields

Each object in `baseline_verify_files`:

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Posix-style relative path from repo root |
| `sha256` | string | yes | SHA256 hex digest of raw file bytes at baseline time |
| `floor_status` | string | yes | One of: `"advisory_until_6d"`, `"strict"` |
| `baseline_known_debt` | string | no | Present when baseline entry carries known debt (e.g. `"limited_evidence"`) |
| `baseline_known_debt_ref` | string | no | Reference to artifact section documenting the debt |
| `baseline_known_debt_note` | string | no | Human-readable explanation of the debt |

### 5.12.5 Classification Logic

Implemented in `guard_status_validator.py` → `classify_verify_floor_policy(verify_path, baseline)`:

1. Search `baseline_verify_files` for entry whose `path` matches the verify artifact's posix path.
2. If not found → `strict` (new artifact after baseline).
3. If found, compute `sha256` of current file bytes.
4. If sha256 matches → `advisory_until_6d` (historical unchanged).
5. If sha256 differs → `strict` (modified after baseline).

Dry-run support: `guard_status_validator.py --verify-floor-dry-run` classifies and prints the policy without failing. Full enforcement is deferred to Prompt 6d / TASK-1015.

### 5.12.6 TASK-964 Baseline-Known-Debt Pattern

TASK-964 is the canonical example of a `baseline_known_debt` entry:

- `floor_status` remains `"advisory_until_6d"` (it is a historical unchanged artifact).
- `baseline_known_debt = "limited_evidence"` records the known evidence debt for traceability.
- This annotation does NOT modify TASK-964.verify.md or upgrade its maturity.
- Production canonical drill for TASK-964 scope belongs to TASK-1010 (Prompt 4).

---

## 6. 合法性檢查規則

artifact 合法需同時符合：

1. 命名正確
2. 放在正確目錄
3. 包含必填欄位
4. 使用合法狀態值
5. 與上游 artifacts 的 task id 一致
6. 內容與角色責任一致
7. 沒有以模糊語句取代可驗證結論

若不合法，應：

- 視為缺件
- 不可作為下一步輸入
- 於 status artifact 記錄缺失

## 7. 版本與覆寫規則

- 同一 task 同一類型 artifact 原則上維持單一最新版本。
- 若需保留舊版，可另存備份，但主流程只認最新合法版本。
- 被新版本取代的 artifact，狀態應標記為 `superseded`。

## 8. 最小可用原則

對極小型任務可採 lightweight mode，但最少仍需：

- task artifact
- code artifact
- status artifact

若任務涉及外部知識，仍不可跳過 research artifact。
若任務需要驗收，仍不可跳過 verify artifact。

## 9. 禁止事項

以下 artifact 一律視為品質不合格：

- 只有標題沒有實質內容
- 用大量原始 log 取代摘要
- 把推測當成 confirmed fact
- 未列出 acceptance criteria
- 未列出 files changed
- 未列出風險或直接省略風險欄位
- status 與實際 artifacts 不一致

## 10. 最終原則

Artifact 的目的不是存檔，而是作為下一個代理的可用契約。

若某份 artifact 不能讓下一位代理不靠猜測就接手，那它就還不夠好。

