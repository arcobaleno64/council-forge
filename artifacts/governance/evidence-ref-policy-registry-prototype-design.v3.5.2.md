# Evidence Ref Policy Registry Prototype Design (v3.5.2)

## Document Metadata
- Document Type: governance prototype design note
- Plan Version: v3.5.2
- Created By Task: TASK-1033
- Created At: 2026-05-04T20:15:00+08:00
- Status: design-only (no runtime consumption authorized)
- Builds On:
  - artifacts/governance/policy-registry-extraction-design.v3.5.1.md (TASK-1032)
  - artifacts/governance/policy-registry-extraction-decision-matrix.v3.5.1.json (TASK-1032)
  - artifacts/governance/validator-test-monolith-characterization.v3.5.1.json (TASK-1031)
  - artifacts/governance/precommit-check-policy.v3.5.json (TASK-1026)
  - artifacts/verify/TASK-1030/pcacc-negative-test-result.json (TASK-1030)
- Companion Prototype JSON: artifacts/governance/prototypes/evidence-ref-policy-registry.prototype.v3.5.2.json
- Inspection Evidence: artifacts/verify/TASK-1033/evidence-ref-policy-prototype-inspection.json

---

## 1. Purpose

定義 **Evidence Ref policy** 之共用註冊表 prototype 形狀（schema），作為 v3.5.1 TASK-1032 §11 推薦之 Option E 序列中第一條 narrower follow-up 之 schema 草案。本文件**僅描述**此 prototype 之欄位、prefix、format、required/optional context 與 PCACC-002 相容性；**不**修改 production validator、PCACC runner、PCACC policy、template mirror、quality baseline、TASK-1023..TASK-1032 任一 lifecycle artifact，**亦不**將 prototype 接入 runtime 任一執行路徑。

本 prototype 之 scope 限縮在 **Evidence Ref 單一 policy 域**（policy-registry-extraction-design.v3.5.1.md §5 列表中的 RC-E `evidence-ref-policy`，範圍包含 `STRUCTURED_CHECKLIST_FIELDS` / `REQUIRED_TOPICS` / `TOPIC_PATTERN` 之 Evidence Ref 子集；本 prototype 進一步聚焦於 PCACC-002 在 verify artifact `## Evidence Refs` 章節之 ref-by-ref 解析與 prefix / 格式 / missing / malformed 行為）。

`split_design_into_smaller_followups` 之核心動機（TASK-1032.decision.md §「Chosen Option」）為：8 條 design question 跨多軸；單一 design 容量不足；narrower design tasks 須有共用 contract source。本 prototype 即為 **共用 contract source 之第一輪實例化**，但只實例化 Evidence Ref 子域，不一次性涵蓋 lifecycle enum / RACI / sync paths 等其他高風險 slice。

---

## 2. Inputs

| input_id | source | role |
|---|---|---|
| IN-1 | artifacts/governance/precommit-check-policy.v3.5.json | current PCACC active surface (PCACC-001..004); locks reason_code taxonomy |
| IN-2 | artifacts/scripts/run_precommit_check.py:run_pcacc_002 | current behavior reference; sha256 prefix=5d1fcd1f96948028 |
| IN-3 | artifacts/verify/TASK-1030/pcacc-negative-test-result.json | NEG-002 malformed_refs / NEG-003 evidence_refs_section_empty proof; backward-compat anchors |
| IN-4 | artifacts/governance/policy-registry-extraction-design.v3.5.1.md §5 RC-E | candidate slice naming; risk=medium |
| IN-5 | artifacts/governance/policy-registry-extraction-decision-matrix.v3.5.1.json | option/risk/readiness gates; future_extraction門檻 |
| IN-6 | artifacts/governance/validator-test-monolith-characterization.v3.5.1.json | RC-1/RC-3/RC-7/RC-9 readiness 立場；blocks_split=5 條 |
| IN-7 | docs/artifact_schema.md §5.6 ## Evidence Refs | verify artifact required section |

---

## 3. Prototype Scope

In scope:

- Evidence Ref `## Evidence Refs` 章節之 presence / format / prefix / missing / malformed semantics。
- Evidence Ref 與 PCACC-002 reason_code 集合之 backward compatibility surface（malformed_refs、missing_paths、evidence_refs_section_absent、evidence_refs_section_empty、evidence_refs_resolved）。
- Evidence Ref required versus optional context 之 design-level taxonomy。
- 未來 runtime 抽出之 acceptance criteria（FE-1..FE-9；條目於 prototype JSON 之 `future_extraction_acceptance_criteria`）。

Out of scope:

- task / plan / decision / verify / status lifecycle artifact set existence（屬 PCACC-001 surface）。
- canonical owner / reviewer set（屬 PCACC-003 surface；對應 RACI policy registry，留予 TASK-1036 候選）。
- review_timestamp 與 evidence_generated_at 排序（屬 PCACC-004 surface）。
- AC-to-verify coverage（v3.5.1 顯式 deferred）。
- reasoning faithfulness / belief-state / model self-confidence / free-text rationale / SAVeR markdown（v3.5.0 forbidden）。
- 任一 production validator/test 檔之修改（與 TASK-1032 prompt §2 hard non-goals 一致）。
- 任一 PCACC runner / policy 修改。
- 任一 template mirror / EXACT_SYNC_FILES 擴張。
- 任一 TASK-1034+ lifecycle artifact 創建。

---

## 4. Evidence Ref Policy Surface

Evidence Ref 之 policy 表面落於 verify artifact 之 `## Evidence Refs` 章節，每行一條 ref，由 `parse_evidence_refs(text)` 抽取後逐條判斷。current PCACC-002 之 ref-by-ref 判斷分支可整理為以下決策序列：

```
1. ref 含 '://' or 以 '/' 起始 or len>=2 且 ref[1]==':'
   -> 若 startswith('HEAD') 或 match scheme prefix 則 resolved
   -> 否則 malformed
2. ref 以 'HEAD' 起始 or 含 '=' or 以 'commit' 起始
   -> resolved
3. ref 以 {artifacts/, template/, docs/, consilium-fabri-, governance-repair-, .github/} 起始
   -> 對 disk 存在性檢查；存在則 resolved；不存在則 missing
4. ref lower starts 'commit ' 或 match ^[0-9a-f]{7,40}$
   -> resolved
5. 否則 malformed
```

本 prototype 之 `allowed_ref_prefixes`、`ref_format_rules`、`local_artifact_constraints`、`malformed_ref_behavior`、`missing_ref_behavior` 五條欄位**精確映射**至上列分支，不擴張、不縮限，以保證 backward compatibility（§6）。

required vs optional context 之 design-level taxonomy（RRC-1..RRC-5 vs ORC-1..ORC-4）為**新增**設計，但僅供未來 runtime 抽出時之 mapping 設計參考；當前 PCACC-002 不消費此 taxonomy，實際行為仍為「section absent / empty / malformed / missing 一律 fail」。

---

## 5. Prototype Registry Schema

prototype JSON top-level fields:

```text
schema_version                                 -> "evidence-ref-policy-registry-prototype/v1"
plan_version                                   -> "v3.5.2"
created_by_task                                -> "TASK-1033"
generated_at                                   -> "2026-05-04T20:10:00+08:00"
prototype_status                               -> "design_only"
runtime_consumption_authorized                 -> false
source_policy_refs                             -> 9 source 引用
policy_surface                                 -> domain / consumed_by_check / 10 items_governed / 9 items_explicitly_out_of_scope
allowed_ref_prefixes                           -> 10 條（6 local + 3 git scheme + 1 inline metadata）
ref_format_rules                               -> encoding / 路徑分隔 / 標準化規則
local_artifact_constraints                     -> 13 條布林 + 9 條 forbidden_root + 7 條 forbidden_url_schemes
required_ref_contexts                          -> RRC-1..RRC-5
optional_ref_contexts                          -> ORC-1..ORC-4
malformed_ref_behavior                         -> default_action=fail；TASK-1030 NEG-002 對齊
missing_ref_behavior                           -> section_absent / section_empty / missing_path 各自 reason_code
pcacc_compatibility                            -> 與 PCACC-002 結構/輸出/exit code 相容
future_extraction_acceptance_criteria          -> FE-1..FE-9
non_authorization                              -> 35 條 false key
limitations                                    -> 10 條
```

設計選擇：

- `prototype_status: "design_only"` 為 prototype JSON 之第一級可機讀標記，其值僅 `design_only` 一種；未來 runtime 抽出時須以另一個 schema_version 之 registry file 取代，**不得**就地將此值改為 `runtime_consumed`。
- `runtime_consumption_authorized: false` 為配套之第二級保護，亦為 prototype 之強約束；若有任一 runner 嘗試 load 時讀到 `false`，必須立即 fail-closed exit≠0。
- prototype 落於 `artifacts/governance/prototypes/` 而非 `artifacts/governance/`，刻意將其與 PCACC runner 之候選 load 路徑隔離；EXACT_SYNC_FILES 不擴張、template mirror 不創建、quality baseline 不變更。
- prefix 列表採**現行 PCACC-002 已接受集合之忠實寫照**；不擴張為更鬆（如 HTTP URL）亦不縮限為更嚴（如取消 `.github/`）；任何擴張須由獨立 decision artifact 授權。

---

## 6. PCACC-002 Compatibility

current PCACC-002 之 contract（自 `run_precommit_check.py:run_pcacc_002` 抽出）：

- **input**: verify artifact path = `artifacts/verify/<task_id>.verify.md`。
- **section parsing**: `parse_evidence_refs(text)`；section absent → None；section 全 `- None` → []；其餘逐條歸納為 ref。
- **per-ref classification**: malformed / missing / resolved 三歸。
- **output**: PCACC-002 check entry 含 check_id / target / expected / actual / evidence_ref / status / reason_code 七欄；status ∈ {pass, fail, skipped_with_reason_code}。
- **reason_code surface**: 
  - `evidence_refs_section_absent`
  - `evidence_refs_section_empty`
  - `missing_paths:<first_offending_token>`
  - `malformed_refs:<first_offending_token>`
  - 兩者並見：`missing_paths:...;malformed_refs:...`
  - resolved：`evidence_refs_resolved`
  - verify 不存在：`verify_artifact_missing`（status=skipped_with_reason_code）

prototype 對 PCACC-002 之契約：

- prototype 不擴張上述任一 reason_code；不新增 PCACC-005 等新 check id。
- prototype 不修改 PCACC-002 之 check entry 結構（仍 7 欄）。
- prototype 不引入 free-text rationale 欄位（v3.5.0 forbidden）。
- prototype 不改 PCACC runner 之 exit code 語意（0 pass / 1 violations / 2 hard guard error）。
- prototype 不引入新的 status 值（status ∈ {pass, fail, skipped_with_reason_code} 維持不變）。
- TASK-1030 之 PCACC-NEG-002（malformed_refs）+ PCACC-NEG-003（evidence_refs_section_empty）之 actual_reason_code 須由未來 runtime 實作完整保留；任一 reason_code 字面值改變即 backward compat 破裂。

---

## 7. Malformed and Missing Ref Semantics

| scenario | section state | per-ref state | result | reason_code |
|---|---|---|---|---|
| section 存在且至少一條 resolved ref，無 missing 無 malformed | non-empty | all resolved | pass | evidence_refs_resolved |
| section 不存在 | absent | n/a | fail | evidence_refs_section_absent |
| section 存在但只含 `- None` | none-only | empty list | fail（required context）／ skipped_with_reason_code（optional context） | evidence_refs_section_empty 或 evidence_refs_optional_per_orc_<id> |
| section 存在但含 0 條 ref（純空白） | empty | empty list | fail | evidence_refs_section_empty |
| 至少一條 ref 通過 path-prefix 檢查但 disk 上不存在 | non-empty | missing | fail | missing_paths:<token> |
| 至少一條 ref 不在 allowed prefix／scheme 集合內 | non-empty | malformed | fail | malformed_refs:<token> |
| 同時含 missing 與 malformed | non-empty | mixed | fail | missing_paths:<token>;malformed_refs:<token> |
| verify 檔本身不存在 | n/a | n/a | skipped_with_reason_code | verify_artifact_missing |

required vs optional context 之 dispatch 規則（design-level；當前 PCACC-002 不實作）：

- 預設視為 required context；除非 verify artifact metadata 顯式宣告 ORC-1..ORC-4 任一情境且附 reason_code，否則一律走 required path。
- 任何 fail-closed 無法以 ORC-1..ORC-4 任一情境降級；僅 `## Evidence Refs` 全 `- None` 且任一 ORC 條件成立時方可降為 skipped_with_reason_code。
- silent fallback to in-module default 永遠禁止；任何 ambiguity 走 fail-closed。

---

## 8. Local Artifact Safety Constraints

- 必為 repo-relative path；禁止絕對路徑、Windows drive letter、parent traversal。
- 必為 forward-slash 規範路徑；Windows backslash 必須先 normalize 才比對。
- 禁止指向 `.obsidian` / `.omc` / `.tmp` / `.pytest-basetemp` / `__pycache__` / `.pytest_cache` / `node_modules` / `.venv` / `.git` 任一目錄（這些目錄之內容非 committed authoritative evidence）。
- 禁止 URL scheme（`http://` / `https://` / `ftp://` / `file://` / `ssh://` / `git://` / `git+ssh://`）；遠端引用須改以 commit SHA 或 git scheme token 表達。
- 必為 committed 或 task-authorized 之 evidence；scratch / draft / temp 路徑一律 malformed。
- ref 之 trailing anchor `#section` 允許，但 anchor 部分不對 disk 驗證。
- ref 之 trailing query `?key=value` 不允許；視為 malformed。
- ref 不得跨行；一行一條 ref。

constraint 對齊 PCACC-002 第 1 步分支（current_pcacc_002_malformed_branch），不擴張新規則。

---

## 9. Future Runtime Extraction Criteria

prototype JSON `future_extraction_acceptance_criteria` 列 FE-1..FE-9。摘要：

| id | 描述 | 對應證據要求 |
|---|---|---|
| FE-1 | 須由獨立後續 task 顯式授權 runtime consumption | 後續 task plan 引此 prototype 路徑 + 該 task decision 把 runtime_consumption_authorized 設 true |
| FE-2 | 預設行為 backward 相容於 PCACC-002 | 後續 task verify 重跑 TASK-1030 NEG-002/003 fixture（或等價）回報 reason_code 一致 |
| FE-3 | 不新增 active PCACC check | 後續 task plan 不引入 PCACC-005 等 |
| FE-4 | runner load 時 schema validation 為 fail-closed | reject unknown / missing / 非 string enum；exit code 2 |
| FE-5 | source/template sync policy 顯式 | paired vs unpaired 路徑各自治理；EXACT_SYNC_FILES 擴張須獨立 decision |
| FE-6 | rollback 路徑文檔化 | registry 移除 / runner 還原 / sha256 重置 / 重跑 fixture |
| FE-7 | Codex post-commit verification PASS | Codex 對未來 runtime task 之 verify 與 fixture rerun 結果 PASS |
| FE-8 | paired path 須有 QC-SYNC-001 對應 negative test | 沿 TASK-1029 模式新建 negative test |
| FE-9 | 未動 v3.5.x lifecycle | 後續 task verify 紀錄 TASK-1023..TASK-1033 sha256 不變 |

FE-* 為**前提門檻**，非授權；本 task 不滿足任一 FE-* 即足以使 runtime 抽出不被啟動，但本 task 之 PASS 並不等於授權執行 runtime 抽出。

---

## 10. Risks and Limitations

DR-1：prototype 被誤讀為授權 runtime consumption。

- mitigation: `prototype_status="design_only"`、`runtime_consumption_authorized=false`、35 條 false `non_authorization`、設計文件多處顯式宣告。

DR-2：prototype JSON 被誤放至 `artifacts/governance/`（與 quality-gate-policy 並列），可能被誤掃為 runtime registry。

- mitigation: prototype 強制落於 `artifacts/governance/prototypes/`；任何移動須由獨立 decision artifact 授權；prototype 路徑名含 `prototype` 字面以利 grep 排除。

DR-3：prefix 集合與 PCACC-002 實作分歧（prototype 寬於或嚴於 runner）。

- mitigation: §4 / §6 明列 current PCACC-002 行為；inspection helper 對 prototype 之 allowed_ref_prefixes 與 PCACC-002 分支邏輯做一致性檢查；任何分歧由 inspection evidence 之 check 標 fail。

DR-4：未來 runtime 抽出時忽略 TASK-1030 之 reason_code 字面值（如改為 `EVIDENCE_REFS_EMPTY` 大寫）導致 backward compat 破裂。

- mitigation: prototype 明列 reason_code 字面值；FE-2 + FE-7 共同守住；TASK-1030 fixture 必跑於未來 runtime task verify。

DR-5：prototype 之 ORC-1..ORC-4 設計被未來 runtime 不慎當成 silent skip 後門。

- mitigation: prototype 明文「silent_skip_forbidden=true」「fallback_to_in_module_default_forbidden=true」；ORC-* 之 missing_behavior 一律為 `skipped_with_reason_code`，**必須**附 reason_code，**不得**降至 silent pass。

DR-6：未來 runtime 抽出落入 paired path（artifacts/scripts/）但忘記擴 EXACT_SYNC_FILES 與 template mirror。

- mitigation: FE-5 顯式要求；TASK-1029 NEG 模式之 negative test 為 FE-8 必要條件。

限制：

- 本 prototype 僅涵蓋 Evidence Ref 子域；其他 RC-A / RC-B / RC-C / RC-D / RC-F / RC-G / RC-H / RC-I 之 prototype 未一同產出。
- 本 prototype 不對 verify artifact 之 `## Decision Refs` / `## Build Guarantee` / `## Acceptance Criteria Checklist` 任一其他 section 做 schema 約束；其他 section 之 schema 由 docs/artifact_schema.md §5.6 維護。
- 本 prototype 不對 helper script invocation pattern 做約束；任何未來 runtime task 須自行設計 invocation 介面。
- inspection evidence JSON 為**靜態 inspection** 結果；不含 PCACC-002 之 fixture rerun（fixture rerun 屬未來 runtime task）。

---

## 11. Follow-up Task Candidates

TASK-1033 不創建 TASK-1034+ 任一 lifecycle artifact。下列為**候選描述**（指引而非授權）：

| candidate_id | proposed_name | scope | depends_on | sequencing |
|---|---|---|---|---|
| TASK-1034 | Evidence Ref Policy Registry Runtime Extraction Plan | 設計 runtime extraction plan / 含 rollback / EXACT_SYNC_FILES 擴張政策 | TASK-1033 | step 1 (plan only) |
| TASK-1035 | Evidence Ref Policy Registry Controlled Runtime Extraction | 落實 runtime extraction（registry 落地、runner 改寫、template mirror 同步） | TASK-1034 | step 2 (implementation) |
| TASK-1036 | Evidence Ref Registry Negative Regression Tests | 對 runtime extraction 加 NEG-002/003 等價 fixture + QC-SYNC-001 negative test | TASK-1035 | step 3 (regression) |

候選 ID 為**指引**，實際 ID 由未來 task allocation 任務決定。

---

## 12. Explicit Non-authorization

This prototype is not consumed by production validators.

This task does not authorize production policy registry extraction.

This task does not authorize validator split.

完整未授權清單見 prototype JSON 之 `non_authorization` 欄位（35 條 false key）。摘要：

- TASK-1033 不授權執行 policy registry extraction implementation。
- TASK-1033 不授權創建任一 runtime policy registry JSON 並接入 production runner。
- TASK-1033 不授權執行 validator module split。
- TASK-1033 不授權修改 5 件 production validator/test 檔（guard_status_validator.py / guard_contract_validator.py / workflow_constants.py / run_red_team_suite.py / test_guard_units.py）任一檔。
- TASK-1033 不授權修改 PCACC runner（run_precommit_check.py）或 PCACC policy（precommit-check-policy.v3.5.json）。
- TASK-1033 不授權修改 quality baseline / quality gate policy / artifact obligation matrix。
- TASK-1033 不授權擴張 EXACT_SYNC_FILES。
- TASK-1033 不授權新增 PCACC-005 或任一 active PCACC check。
- TASK-1033 不授權啟用 AC-to-verify coverage。
- TASK-1033 不授權修改 v3.5 / v3.5.1 plan 與 manifest。
- TASK-1033 不授權修改 TASK-1023..TASK-1032 任一 lifecycle artifact。
- TASK-1033 不授權創建 TASK-1034 及更後之 lifecycle artifact。
- TASK-1033 不授權執行 reasoning faithfulness audit / belief-state audit / model self-confidence audit / free-text rationale 添加 / SAVeR markdown report。
- TASK-1033 不授權生成 SRS / RTM / design spec / threat model / release note / migration note / user guide / runbook 任一**內容**。
- TASK-1033 不授權執行 ruff / mypy / pyright / coverage / pylint / bandit / safety / formatter / package manager 任一執行。
- TASK-1033 不授權執行 pytest。
- TASK-1033 不授權執行 5 件 target file 任一之 CLI 或 main()。

任何未來 runtime extraction implementation 須由獨立後續 task 顯式授權；本 prototype 之存在不構成授權。
