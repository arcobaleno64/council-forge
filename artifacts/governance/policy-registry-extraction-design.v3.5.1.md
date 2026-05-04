# Policy Registry Extraction Design Decision (v3.5.1)

## Document Metadata
- Document Type: governance design decision artifact
- Plan Version: v3.5.1
- Created By Task: TASK-1032
- Created At: 2026-05-04T19:10:00+08:00
- Status: design-decision only (no implementation authorized)
- Builds On:
  - artifacts/governance/v3.5.1-gate-proving-plan.md
  - artifacts/governance/validator-test-monolith-characterization.v3.5.1.json (TASK-1031)
  - artifacts/governance/quality-baseline.v3.5.json
  - artifacts/governance/quality-gate-policy.v3.5.json
  - artifacts/governance/precommit-check-policy.v3.5.json
  - artifacts/governance/artifact-obligation-matrix.v3.5.json
- Decision Matrix Companion: artifacts/governance/policy-registry-extraction-decision-matrix.v3.5.1.json
- Authorization Scope: design-decision only; **no extraction**, **no validator split**, **no production validator/test modification**

## 1. Decision Summary

**Recommendation: `split_design_into_smaller_followups`**

理由摘要：

- TASK-1031 readiness_status=`not_ready_for_split`，9 條 RC 中 RC-1（無 golden CLI corpus）、RC-7（無 decomposition strategy）、RC-9（無 rollback plan）為 `not_satisfied`，RC-2 / RC-3 為 `partially_satisfied`，blocks_split=true 共 5 條。
- TASK-1031 之 `policy_registry_extraction_inputs.decision_questions_for_TASK_1032` 列出 8 條 design question，跨「registry 存放位置」「single vs per-domain」「RACI v1/v2 unification」「extraction 前後序」「schema 強制機制」「治理路徑」「frozenset round-trip」「rollback」八個獨立議題。單一 design decision 任務（本 TASK-1032）足以**評估**問題本身與**列舉**遷移選項，但**不足以**對 8 條議題逐一給出可實作之 design contract。
- 候選 registry 之風險梯度差距大：`workflow_constants.py` 之 `ASSURANCE_PROFILES` / `PROJECT_ADAPTER_RULES`（純資料表）為低風險候選；`RACI_MATRIX` vs `RACI_MATRIX_V2`（雙表並存）需先做 unification 設計；`guard_contract_validator.py` 之 `EXACT_SYNC_FILES` 為 source/template sync gate 自身輸入，extraction 觸發 self-reference paradox（registry 自己是否 paired？）。將 8 議題塞入單一 design 將迫使保守取最弱共識，浪費 RC-2 / RC-3 之 `partially_satisfied` 之上行空間。
- 故本 decision 推薦將 design 拆成 ≥3 條 narrower follow-up design tasks（候選 ID：TASK-1033 Schema Prototype Design / TASK-1034 Narrow Evidence Ref Policy Registry Design / TASK-1035 Status Lifecycle Policy Registry Design），每條任務各承擔 1-3 個 design question 與單一候選 registry 之 contract 草案；本 decision 提供**選項評估**與**門檻條件**，**不**創建任何 follow-up task lifecycle artifact、**不**授權任何 extraction 實作。
- v3.5.1 plan §9.2 已顯式 defer policy registry extraction implementation 至 v3.6；本 decision **沿用** 此 defer，並進一步鎖定 v3.6 implementation 之啟動條件須先有「至少一條 narrower design task done + verify pass」+「對應候選 registry 之 RC-1/RC-3/RC-7/RC-9 對該域之滿足證據」。

備選 recommendation 之拒絕依據：

- `extract_before_validator_split`：方向上理論可降 split 期間之 policy 雙寫複雜度，但本任務缺乏對「extraction 自身之 rollback 路徑」「schema validation 失敗時 runner 行為」「RACI v1/v2 是否 unify」之決策證據；單一決策直接背書會 over-claim。記為 `acceptable` 之候選 sequencing，不為 `preferred`。
- `extract_after_validator_split`：split 後再 extract 將導致 policy 須在多個新模組間遷移，反而增加 churn；與「降低 split 風險」之目的相左。記為 `rejected`。
- `defer_extraction`（單純延後到 v3.6 而不拆 design）：與 v3.5.1 plan §9.2 已 defer 之既有立場重複，無新訊息；保留 `acceptable` 但放棄之，因不能利用 TASK-1031 之 candidate listing 推進設計。
- `do_not_extract`（永不抽）：違反 TASK-1031 governance artifact `risk_register[RR-5]`「policy_constant_coupling」之既有 risk 證據；違反 v3.5.1 plan §8 之「評估 policy registry extraction 是否應先於 validator split」之題旨。記為 `rejected`。

---

## 2. Inputs from TASK-1031 Characterization

僅引用 TASK-1031 governance artifact 中與本決策直接相關之欄位；不複製全文（避免內容漂移）。

來源：`artifacts/governance/validator-test-monolith-characterization.v3.5.1.json`（schema_version=`validator-test-monolith-characterization/v1`、created_by_task=`TASK-1031`、generated_at=2026-05-04T18:05:00+08:00）。

### 2.1 readiness 立場

- `summary.readiness_status` = `not_ready_for_split`。
- `refactor_readiness_criteria` 9 條 RC 中：
  - `not_satisfied` = [RC-1, RC-7, RC-9]
  - `partially_satisfied` = [RC-2, RC-3]
  - `satisfied` = [RC-4, RC-5, RC-6, RC-8]
  - 對 `RC-8` 之註記：「satisfied at v3.5.1 plan level (explicit defer); becomes 'design decision completed' only after TASK-1032 done」 — 本 decision 完成後 RC-8 升至完整 satisfied。

### 2.2 候選來源模組

`policy_registry_extraction_inputs.candidate_policy_constants` 之 host_module：

- `artifacts/scripts/workflow_constants.py`（loc=636、top_funcs=10、top_classes=0、top_stmts=41、main_guard_present=false、import_candidate=true、template_mirror_status=byte_identical）：列 19 條候選常數。
- `artifacts/scripts/guard_contract_validator.py`（loc=969、top_funcs=24、top_classes=1、top_stmts=55、import_candidate=true、template_mirror_status=byte_identical）：列 16 條候選常數。

### 2.3 8 條 design question（TASK-1031 §`decision_questions_for_TASK_1032`）

```text
Q1: Where does the registry live - artifacts/scripts/ paired or artifacts/governance/ unpaired?
Q2: Does the registry use a single file or per-domain split?
Q3: Is RACI_MATRIX (legacy) deprecated outright in favor of RACI_MATRIX_V2 in the registry, or do both ship?
Q4: Does extraction precede or follow the validator module split?
Q5: How is schema validation enforced - in-runner at startup, or via a separate quality-gate?
Q6: Do registry changes require waiver/decision artifacts (governance change) or are they treated as ordinary code changes?
Q7: How is RACI_MATRIX_V2 frozenset preserved through JSON round-trip (since JSON only has arrays)?
Q8: What is the rollback plan if registry-driven runtime regresses?
```

### 2.4 風險訊號

`risk_register[RR-5]`（severity=medium、blocks_refactor_now=false）：

> policy_constant_coupling - workflow_constants drift between RACI_MATRIX and RACI_MATRIX_V2; out-of-band updates risk silent divergence; mitigation_candidate: TASK-1032 design decision must address whether registry extraction unifies both.

本 decision 採 §3 之候選列舉與 §11 之 follow-up candidate 對 RR-5 提供 design-level 回應；**不**做 unification 實作。

---

## 3. Candidate Policy Data

僅列當前 artifact / runner 已存在之 policy 形式；**不**發明新 policy data。

### 3.1 來自 `workflow_constants.py`（19 條）

| const_name | 形式 | 候選性質 |
|---|---|---|
| `REQUIRED_TOPICS` | tuple/frozenset | enum-like |
| `TOPIC_PATTERN` | regex pattern source（str） | regex string |
| `ASSURANCE_LEVELS` | frozenset | enum |
| `PROJECT_ADAPTERS` | frozenset | enum |
| `WORKFLOW_STATES` | frozenset | enum |
| `ARTIFACT_TYPES` | frozenset | enum |
| `STRUCTURED_CHECKLIST_FIELDS` | tuple/frozenset | enum |
| `ASSURANCE_PROFILES` | dict-of-rules | rule table |
| `PROJECT_ADAPTER_RULES` | dict-of-rules | rule table |
| `RACI_MATRIX` | dict（set-valued） | rule table（legacy） |
| `RACI_MATRIX_V2` | dict（frozenset-valued） | rule table（current） |
| `VERIFICATION_ITEM_RESULTS` | frozenset | enum |
| `VERIFICATION_REASON_CODES` | frozenset | enum |
| `VERIFICATION_READINESS_STATES` | frozenset | enum |
| `DECISION_CLASSES` | frozenset | enum |
| `IMPROVEMENT_PROFILES` | dict | rule table |
| `_PATH_PREFIX_RULES` | tuple-of-tuples（precedence-ordered） | precedence rule table |
| `_WORKFLOW_ENTRY_FILES` | frozenset | enum |
| `_AGENT_PROMPT_FILES` | frozenset | enum |

### 3.2 來自 `guard_contract_validator.py`（16 條）

| const_name | 形式 | 候選性質 |
|---|---|---|
| `EXACT_SYNC_FILES` | tuple-of-paths（28 paths） | path enum（self-referential） |
| `COMMON_REQUIRED_PHRASES` | tuple/frozenset | phrase enum |
| `SOURCE_REQUIRED_PHRASES` | tuple/frozenset | phrase enum |
| `DOWNSTREAM_REQUIRED_PHRASES` | tuple/frozenset | phrase enum |
| `PROMPT_ENTRY_FILES` | tuple/frozenset | path enum |
| `PROMPT_REGRESSION_FILES` | tuple/frozenset | path enum |
| `REPOSITORY_PROFILE_FILES` | tuple/frozenset | path enum |
| `ACTIVE_GEMINI_POLICY_FILES` | tuple/frozenset | path enum |
| `ALLOWED_GEMINI_MODELS` | frozenset | enum |
| `DISALLOWED_GEMINI_FRAGMENTS` | frozenset | phrase enum |
| `README_HEADERS_EN` | tuple | header enum |
| `README_HEADERS_ZH` | tuple | header enum |
| `OBSIDIAN_HEADERS` | tuple | header enum |
| `README_CONTRACTS` | dict-of-rules | contract table |
| `OBSIDIAN_CONTRACTS` | dict-of-rules | contract table |
| `PLACEHOLDER_PATTERNS` | tuple-of-regex | regex table |

### 3.3 候選分類

按 extraction 風險梯度（低 → 高）：

- **Low-risk slice（純 enum）**：`ASSURANCE_LEVELS`, `PROJECT_ADAPTERS`, `WORKFLOW_STATES`, `ARTIFACT_TYPES`, `VERIFICATION_ITEM_RESULTS`, `VERIFICATION_REASON_CODES`, `VERIFICATION_READINESS_STATES`, `DECISION_CLASSES`, `ALLOWED_GEMINI_MODELS`。
- **Medium-risk slice（rule table，無 cross-table 一致性）**：`ASSURANCE_PROFILES`, `PROJECT_ADAPTER_RULES`, `IMPROVEMENT_PROFILES`, `README_CONTRACTS`, `OBSIDIAN_CONTRACTS`。
- **High-risk slice（self-referential / cross-table consistency / 雙表並存）**：`EXACT_SYNC_FILES`（self-ref）、`RACI_MATRIX` + `RACI_MATRIX_V2`（雙表並存）、`_PATH_PREFIX_RULES`（precedence-ordered）、`TOPIC_PATTERN`（regex 含 capture group 之語意）。

---

## 4. Execution Logic that Must Remain in Python

下列控制流 / I/O / 算法不得移入 JSON：

- `validate_workflow_rule_tables`（control flow + cross-table consistency check；仰賴 `ASSURANCE_PROFILES` 與 `PROJECT_ADAPTER_RULES` 之 cross-validation）。
- `resolve_verification_policy`（resolution algorithm + adapter inheritance chain）。
- `_resolve_adapter_chain`（cycle detection；圖論演算法）。
- `classify_path`（precedence-ordered prefix matching；演算法非資料）。
- `validate_raci_hybrid_sync`（markdown table parsing；structural parsing）。
- `validate_section_contract`（markdown section traversal；structural parsing）。
- 全部 argparse / subprocess / urllib / file I/O 路徑（boundary I/O；不可表為靜態 policy）。
- `_run_raci_audit_v2`（130+ LOC，含 JSON output formatting / alias resolution / waiver application；混合 I/O 與算法）。
- `validate_exact_sync` 之 walking 邏輯（FS 走查；只有「allowed paths set」屬 policy data）。
- `detect_repo_mode`（執行期 mode 偵測；不可靜態化）。

---

## 5. JSON Registry Candidates

以**目的**為單位列舉 candidate registry；**不**創建 runtime registry。

| candidate_id | name | source const | scope | risk |
|---|---|---|---|---|
| RC-A | `assurance-profile-policy` | `ASSURANCE_PROFILES`, `PROJECT_ADAPTER_RULES`, `IMPROVEMENT_PROFILES` | verify policy 解析 | medium |
| RC-B | `lifecycle-enum-policy` | `ASSURANCE_LEVELS`, `PROJECT_ADAPTERS`, `WORKFLOW_STATES`, `ARTIFACT_TYPES`, `VERIFICATION_*` 三 enum, `DECISION_CLASSES` | enum 集合 | low |
| RC-C | `raci-policy` | `RACI_MATRIX`, `RACI_MATRIX_V2` | RACI 規則 | high（需 unification 設計） |
| RC-D | `path-classification-policy` | `_PATH_PREFIX_RULES`, `_WORKFLOW_ENTRY_FILES`, `_AGENT_PROMPT_FILES` | path classification | medium（含 precedence） |
| RC-E | `evidence-ref-policy` | `STRUCTURED_CHECKLIST_FIELDS`, `REQUIRED_TOPICS`, `TOPIC_PATTERN` | evidence/topic 規則 | medium（含 regex） |
| RC-F | `sync-paths-policy` | `EXACT_SYNC_FILES`, `PROMPT_ENTRY_FILES`, `PROMPT_REGRESSION_FILES`, `REPOSITORY_PROFILE_FILES`, `ACTIVE_GEMINI_POLICY_FILES` | sync gate input | high（self-ref） |
| RC-G | `phrase-contract-policy` | `COMMON_REQUIRED_PHRASES`, `SOURCE_REQUIRED_PHRASES`, `DOWNSTREAM_REQUIRED_PHRASES`, `DISALLOWED_GEMINI_FRAGMENTS`, `ALLOWED_GEMINI_MODELS` | 文本片段約定 | low |
| RC-H | `markdown-contract-policy` | `README_HEADERS_EN`, `README_HEADERS_ZH`, `OBSIDIAN_HEADERS`, `README_CONTRACTS`, `OBSIDIAN_CONTRACTS` | markdown 結構 | medium |
| RC-I | `placeholder-pattern-policy` | `PLACEHOLDER_PATTERNS` | regex enum | medium |

候選 registry 切片可在 follow-up design task 中重組；本 decision 不釘定切分粒度。

---

## 6. Schema Validation Requirements

任一未來 extraction 須滿足：

- **schema_version 必填**：每 registry file 之 root JSON object 第一欄為 `schema_version`，採 `<registry-id>/v<n>` 字串模式（與既有 `quality-gate-policy/v1` 等 v3.5.0 命名對齊）。
- **plan_version 相容**：registry file 含 `plan_version` 欄位，與消費端 runner 之 expected plan_version 匹配；不匹配時 runner 拒絕載入並 exit≠0。
- **enum 強制**：每 enum 候選欄位以 JSON array of string 表，runner 載入時須將其轉為 frozenset；非陣列 / 非字串型別觸發載入失敗。
- **必填頂層欄位拒缺**：缺一即 fail；不採 default fallback（避免 silent degradation）。
- **未知欄位處理**：採 `reject_unknown_fields = true`（fail-closed），與 v3.5.0 governance policy 之保守風格一致；如允許未知欄位將打開向前相容性後門，違反 PCACC 之 strict 精神。
- **migration / versioning 行為**：跨 schema_version 升級須採 `supersedes` 鏈（與 plan / manifest 之 supersedes 模式對齊）；不允許 in-place 升級；舊版 registry 須保留至 supersession decision 過期。
- **validation 失敗行為**：runner 以 fail-closed 拒絕啟動；exit code ≠ 0；錯誤訊息含 schema_version / plan_version / 失敗欄位 / repo-relative path 四項；**不**採 silent skip 或 fallback to embedded default。
- **source/template mirror 行為**：若 registry file 落在 `artifacts/scripts/` 之 source/template paired 區，須加入 `EXACT_SYNC_FILES` 並維持 byte_identical；若落在 `artifacts/governance/` 之 unpaired 區，無需 mirror。
- **跨 registry consistency 規則**：當多個 registry 共用 enum（如 `ASSURANCE_LEVELS` 出現在 RC-A 與 RC-B），應透過 `references` 欄位顯式引用而非複製；任何複製須由 schema validator 偵測為 violation。

---

## 7. Source/Template Sync Implications

對 QC-SYNC-001（TASK-1025 deliverable，TASK-1029 negative-test 證實）之影響：

### 7.1 若 registry 落在 `artifacts/scripts/`（paired）

- 須擴 `EXACT_SYNC_FILES` 加入新 JSON path；同時須建立 `template/artifacts/scripts/<registry>.json` mirror。
- baseline `quality-baseline.v3.5.json` 之 `source_template_pairs` 須擴張；屬 governance policy modification，本 decision 不授權。
- 任一 mirror 漏建即觸發 QC-SYNC-001 之 `post_baseline_new_pair` violation（TASK-1029 NEG-001/NEG-002 已 prove）。
- registry 內容修改須 root + template lockstep；任一不同步即 drift violation（TASK-1029 NEG-003 已 prove）。
- Waiver 機制（六欄齊備 + 未過期 expires_at）依舊適用。

### 7.2 若 registry 落在 `artifacts/governance/`（unpaired）

- 不觸發 source/template paired baseline；無 mirror 義務。
- 但仍須符合 `quality-gate-policy/v1` 之 schema_version 命名規範（與 quality-gate-policy.v3.5.json 等 v3.5.0 既有 governance JSON 一致）。
- baseline 不擴張；QC-SYNC-001 不啟用對該檔之檢查。
- 治理變更（registry content 修改）仍須走 decision-artifact + verify-pass 路徑（與 quality-baseline / quality-gate-policy 變更同級）。

### 7.3 對 baseline 之影響

- 任何 extraction 須由獨立 v3.6 task 處理 baseline 變更；本 decision **不**授權變更 `quality-baseline.v3.5.json`。
- baseline 之 `source_template_pairs` 與 `existing_drift_entries` 若不擴張，則 §7.1 之 paired 路徑不可行，registry 必須落在 `artifacts/governance/`。
- 若選 paired 路徑，須先以獨立 task 補 baseline；該 task 之 plan 須含 R/B 計畫與 PCACC 影響評估。

### 7.4 post-baseline drift detection

- 對 paired registry，drift 檢測沿襲 QC-SYNC-001 之 `post_baseline_drift` 路徑（已被 TASK-1029 NEG-003 驗證）。
- 對 unpaired registry，無 drift 檢測義務；但 schema validation 失敗仍 fail-closed。

---

## 8. Backward Compatibility Concerns

### 8.1 既有 CLI 行為

- 現行 `guard_status_validator.py` / `guard_contract_validator.py` 之 stdout shape（[OK]/[FAIL]/[WARN] stanzas、`raci-audit/v2` JSON object）不得因 extraction 改變。任一變更須觸發 user-facing change escalation（AOM-011）。
- 任一 extraction 須採 import-time fallback：runner 啟動時先 load registry，失敗則 fail-closed；不採「load fail → 退回 in-module default」。

### 8.2 既有 evidence 格式

- TASK-1023..1031 之 verify artifact `Evidence Refs` 與 helper output JSON shape 不得因 extraction 改變；屬 PCACC-002 之 strict 範圍（TASK-1030 NEG-002/003 已驗證 strict 行為）。

### 8.3 既有 task / status JSON shape

- `artifacts/status/TASK-XXXX.status.json` 之 schema 不得因 extraction 改變；任一新欄位須走 separate decision artifact。

### 8.4 v3.5.0 / v3.5.1 artifact 相容性

- TASK-1023..1027（v3.5.0 closure chain）+ TASK-1028..1031（v3.5.1 chain）+ 本 TASK-1032 之既有 artifact **絕對不可** 因未來 extraction 而 retroactively 修改；屬 immutability 約束。
- 任一新 v3.6 extraction 任務若需引用既有 const，採 reference-by-name；不得修改 v3.5.x lifecycle artifact。

### 8.5 失敗模式相容

- runner 之 exit code 語意（0 pass / 1 violations / 2 hard guard error）不得改變。
- registry load 失敗應映射至 exit code 2（hard guard），與既有 GuardError 路徑一致。
- silent fallback 行為被禁止；任何 extraction 設計含「load 失敗回退 in-module default」即 reject。

---

## 9. Migration Sequencing Options

每選項含 pros / cons / risks / preconditions / recommended_followup 五欄。所有 implementation 屬 v3.6，本 decision **不**授權。

### Option A — `do_not_extract_in_v3_5_1`

- **pros**：
  - 與 v3.5.1 plan §9.2 既有立場一致；零風險。
  - 不擴 baseline；不擴 PCACC；不擴 AOM。
  - 不創新 governance plane。
- **cons**：
  - 不利用 TASK-1031 之 candidate listing 推進設計；validator split 之 v3.6 啟動條件之一（policy 邊界明確）仍懸而未決。
  - RR-5（RACI v1/v2 drift risk）長期未處理。
- **risks**：
  - 若 v3.6 split 啟動時仍無 extraction 設計，split 期間政策雙寫會成為風險源。
- **preconditions**：無（已是 v3.5.1 默認狀態）。
- **recommended_followup**：在 v3.6 啟動前以新 design task 重新評估；不得直接跳至實作。

### Option B — `extract_before_validator_split`

- **pros**：
  - split 期間 module 邊界較清晰（policy 已外部化）；split decision 只需處理控制流。
  - 提早暴露 schema validation / migration 風險。
- **cons**：
  - extraction 自身複雜度高（高風險 slice 含 EXACT_SYNC_FILES self-ref / RACI v1/v2 unification）。
  - 須先解 8 條 design question；單一 design task 容量不足。
  - 對 baseline / EXACT_SYNC_FILES 之擴張須先以獨立 task 完成。
- **risks**：
  - 若 extraction 自身 introduce regression（如 frozenset round-trip 喪失型別），split 將被進一步推遲。
  - extraction 之 rollback 路徑未定義。
- **preconditions**：
  - 8 條 design question 全部以 narrower design tasks 結案。
  - schema prototype 經 PCACC strict scope 驗證。
  - rollback plan（含 sha256 restoration / runner re-baseline）形式化。
- **recommended_followup**：先做 Option D（schema prototype），再決定是否選 B。

### Option C — `extract_after_validator_split`

- **pros**：
  - split 後每個新 module 之 policy 邊界天然較窄；extraction 可逐 module 進行。
- **cons**：
  - split 期間 policy 雙寫複雜度 = 兩種變化（split + extract）疊加。
  - split 之 RC-7（decomposition strategy）未滿足之下 split 不可啟動；extract 因此被連帶推遲。
  - 多模組擴 baseline 須多次 governance 變更，churn 高。
- **risks**：
  - split 期間若 policy 因「未 extract」而被複寫到多個新 module，會引入 silent divergence（與 RR-5 同型別）。
- **preconditions**：
  - validator split 已完成且 verify pass 並維持綠至少一個 release cycle（v3.5 plan §5.6 / version_split_rule）。
- **recommended_followup**：record_only；本 decision 將其 `rejected`。

### Option D — `schema_prototype_design_first_implementation_later`

- **pros**：
  - 風險最低之前進路徑；只設計 schema 與 contract，**不**改 runner / validator / template。
  - 為 §11 之 narrower follow-up tasks 提供共用 contract。
  - 不擴 baseline；不擴 PCACC；不擴 AOM。
- **cons**：
  - 不直接降低 split-time 風險；仍須跟一個 implementation task。
- **risks**：
  - schema prototype 若選錯（如 single file vs per-domain split），下游 follow-up 須整體返工。
- **preconditions**：
  - TASK-1031 readiness gate 文檔可引用（已 done）。
  - 8 design question 中至少 Q1（registry 位置）+ Q2（single vs per-domain）+ Q5（schema validation 強制）有暫定回答。
- **recommended_followup**：先以 narrower design task 對 Q1/Q2/Q5 給出 contract 草案；再決定是否進入 Option B。

### Option E — `split_design_into_smaller_followups`

- **pros**：
  - 最直接回應 TASK-1031 之 8 design question 之多元複雜度。
  - 對 Q3（RACI unification）/ Q7（frozenset round-trip）/ Q8（rollback）等深度問題保留專任設計空間。
  - 與 §11 之 follow-up candidates 對齊。
  - 可與 Option D 串接：narrower design tasks 之第一條即 schema prototype。
- **cons**：
  - 序列化會延長 v3.6 extraction implementation 啟動時間。
  - 多個 design task 之 closure 條件須額外設計。
- **risks**：
  - 若 narrower design tasks 之間無共用 contract（schema prototype 缺席），可能 introduce design drift。Mitigation：將 schema prototype 列為 narrower design tasks 之第一條前置依賴。
- **preconditions**：
  - TASK-1031 done + verify pass（已滿足）。
  - 本 TASK-1032 done + verify pass（將於本任務 commit 後滿足）。
- **recommended_followup**：序列為 schema prototype → low-risk slice extraction design → medium-risk slice extraction design → high-risk slice extraction design + RACI unification。

### Option recommendation status 摘要

| option_id | recommendation_status |
|---|---|
| A `do_not_extract_in_v3_5_1` | acceptable（已是默認） |
| B `extract_before_validator_split` | acceptable（待 narrower design 收口後重評） |
| C `extract_after_validator_split` | rejected |
| D `schema_prototype_design_first_implementation_later` | acceptable（為 E 之第一步） |
| E `split_design_into_smaller_followups` | **preferred** |

---

## 10. Risks and Trade-offs

| risk_id | description | mitigation |
|---|---|---|
| DR-1 | 本 design 過度切細，narrower design tasks 之間無共用 contract，引入 design drift | 將 Option D 列為 Option E 之第一步；schema prototype 為共用 contract source |
| DR-2 | narrower design 拖延 v3.6 implementation 啟動，validator split readiness 因 policy 邊界懸而未決 | 將 8 design question 對應到 ≤4 個 narrower task，控制 narrowness 粒度 |
| DR-3 | 在 design 階段意外提及實作細節而被誤讀為授權 | 本 design 與 decision matrix 多處 explicit non-authorization；verify artifact 顯式檢查 |
| DR-4 | RACI v1/v2 unification 設計遭草率延後，導致 RR-5 長期 latent | 將 Q3 + Q7 列為 narrower design task 之必選議題；不允許「全延後到 v3.6 implementation」 |
| DR-5 | EXACT_SYNC_FILES 之 self-reference paradox 設計失誤（registry 自己是否 paired？） | 將 Q1（registry 位置）列為前置議題；schema prototype 必須先給出此問題之 contract |
| DR-6 | schema validation 失敗時 fallback 行為被誤設為「retain in-module default」 | §6 / §8 顯式禁止 silent fallback；narrower design task 之 acceptance 條件須含此項 |

trade-offs：

- 「拆 design」之代價是節奏放緩；換得每條議題之深度。在 v3.5.1 plan §9.2 已 defer implementation 之前提下，節奏代價可吸收。
- 「不直接背書 Option B」之代價是失去最直觀 sequencing；換得對 8 design question 之深度回應；TASK-1031 readiness gate 之保守立場已支持此 trade。

---

## 11. Recommendation

採 **Option E — `split_design_into_smaller_followups`** 為本 decision 之 recommendation。

實作門檻（須由 v3.6 implementation 任務之 plan 顯式滿足，本 decision 不授權）：

1. narrower design tasks 之第一條須是 **schema prototype design**（對應 Option D）；其餘 narrower design tasks 引用 schema prototype 為前置依賴。
2. 每條 narrower design task 對應 ≤3 個 §2.3 之 design question；以「Q-id 集合」明示其 scope。
3. 每條 narrower design task 須回答對應 candidate registry slice（§5）之：位置（§7）、schema requirement（§6）、backward compatibility（§8）、rollback（§10）。
4. RC-1（golden CLI corpus）/ RC-3（test_guard_units.py drift）/ RC-7（decomposition strategy）/ RC-9（rollback plan）之滿足狀態，每條 narrower design task 須引用 TASK-1031 之最新 status 並聲明該 task 之啟動是否受其阻擋。
5. v3.6 extraction implementation 啟動須等齊：
   - schema prototype design done + verify pass。
   - 至少一條 narrower domain design done + verify pass。
   - 對應 candidate registry slice 之 R/B 計畫納入 plan artifact。
   - baseline / EXACT_SYNC_FILES 擴張之治理 task（若 paired 路徑）已 done。
   - QC-SYNC-001 對該 slice 之 negative test 證據已存在（沿襲 TASK-1029 模式）。

若上述任一門檻未滿足，**v3.6 extraction implementation 不得啟動**。

---

## 12. Follow-up Task Candidates

候選清單（**僅描述**；本 decision **不**創建任一 lifecycle artifact）：

| candidate_id | proposed_name | scope | depends_on | sequencing |
|---|---|---|---|---|
| TASK-1033 | Policy Registry Schema Prototype Design | §2.3 之 Q1 / Q2 / Q5；schema_version naming；fail-closed contract | TASK-1032 | step 1（前置） |
| TASK-1034 | Narrow Evidence Ref Policy Registry Design | RC-E（evidence-ref-policy）；§2.3 之 Q4 / Q6；low-risk slice | TASK-1033 | step 2 |
| TASK-1035 | Status Lifecycle Policy Registry Design | RC-B（lifecycle-enum-policy）+ RC-A（assurance-profile-policy）；§2.3 之 Q4 / Q6 | TASK-1033 | step 2 |
| TASK-1036 | RACI Policy Registry Design with v1/v2 Unification | RC-C（raci-policy）；§2.3 之 Q3 / Q7 | TASK-1033 | step 3 |
| TASK-1037 | Sync Paths Policy Registry Self-reference Design | RC-F（sync-paths-policy）；§2.3 之 Q1 細化 | TASK-1033, TASK-1034 | step 3 |
| TASK-1038 | Validator Module Split Candidate Plan | TASK-1031 RC-7 / RC-9 之滿足；含 rollback plan / decomposition strategy | TASK-1031, TASK-1032 + ≥1 narrower design | v3.6 prerequisite |

候選順序與 ID 為**指引**；實際 ID 由 v3.6 task allocation 任務決定。本 decision 不釘定。

---

## 13. Explicit Non-authorization

本 decision 顯式聲明下列**未授權**項目（與 TASK-1032 prompt §2 一致）：

- TASK-1032 不授權執行 policy registry extraction implementation。
- TASK-1032 不授權創建任一 runtime policy registry JSON（即使是 §5 之候選 RC-A..RC-I 任一）。
- TASK-1032 不授權修改 `artifacts/scripts/workflow_constants.py`、`artifacts/scripts/guard_status_validator.py`、`artifacts/scripts/guard_contract_validator.py`、`artifacts/scripts/run_red_team_suite.py`、`artifacts/scripts/test_guard_units.py` 任一檔。
- TASK-1032 不授權修改前述五檔之 template mirror。
- TASK-1032 不授權修改 PCACC runner（`run_precommit_check.py`）或其 mirror。
- TASK-1032 不授權修改 quality gate runner（`run_quality_gates.py`）或其 mirror。
- TASK-1032 不授權修改 `quality-gate-policy.v3.5.json`、`quality-baseline.v3.5.json`、`precommit-check-policy.v3.5.json`、`artifact-obligation-matrix.v3.5.json`。
- TASK-1032 不授權修改 v3.5 plan / v3.5 manifest / v3.5.1 plan / v3.5.1 manifest。
- TASK-1032 不授權修改 TASK-1023..TASK-1031 任一 lifecycle artifact。
- TASK-1032 不授權執行 validator module split。
- TASK-1032 不授權重組 test monolith。
- TASK-1032 不授權執行 ruff / mypy / pyright / coverage / pylint / bandit / safety / formatters / package managers。
- TASK-1032 不授權執行 pytest。
- TASK-1032 不授權執行 5 件 target file 任一檔之 CLI 或 main()。
- TASK-1032 不授權生成 SRS / RTM / design spec / threat model / release note / migration note / user guide / operation runbook 之任何**內容**。
- TASK-1032 不授權創建 standalone waiver registry / style debt registry / runtime policy registry。
- TASK-1032 不授權對 QB-DRIFT-0001 做 remediation 或 waiver 簽發。
- TASK-1032 不授權升級 FIND-18 status。
- TASK-1032 不授權啟動 P0 quality gate 之 Phase 2 或 Phase 3。
- TASK-1032 不授權修改 Bootstrap Prompt Skill artifact。
- TASK-1032 不授權修改 `.obsidian/core-plugins.json` / `.obsidian/workspace.json` / `.omc/` / `.pytest-basetemp/` / `.tmp/`。
- TASK-1032 不授權創建 TASK-1033 及更後之任一 lifecycle artifact。
- TASK-1032 不授權擴張 P0 quality gates / PCACC active checks / AOM matrix。
- TASK-1032 不授權擴張 assurance_level taxonomy 加入 `high`。
- TASK-1032 不授權新增 agent role 或建立全域 model-brand-to-role binding。

任何未來 extraction implementation 須由獨立 v3.6 task 顯式授權；本 decision 之 §11 之門檻條件為**前提**而非**授權**。
