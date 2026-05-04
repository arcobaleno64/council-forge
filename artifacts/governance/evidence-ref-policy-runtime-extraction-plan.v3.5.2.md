# Evidence Ref Policy Registry Runtime Extraction Plan (v3.5.2)

## Document Metadata
- Document Type: governance runtime extraction plan
- Plan Version: v3.5.2
- Created By Task: TASK-1034
- Created At: 2026-05-04T21:10:00+08:00
- Status: planning-only (no implementation authorized; no runtime registry consumption authorized)
- Companion JSON: artifacts/governance/evidence-ref-policy-runtime-extraction-plan.v3.5.2.json
- Inspection Evidence: artifacts/verify/TASK-1034/runtime-extraction-plan-inspection.json
- Builds On:
  - artifacts/governance/prototypes/evidence-ref-policy-registry.prototype.v3.5.2.json (TASK-1033)
  - artifacts/governance/evidence-ref-policy-registry-prototype-design.v3.5.2.md (TASK-1033)
  - artifacts/verify/TASK-1033/evidence-ref-policy-prototype-inspection.json (TASK-1033)
  - artifacts/governance/policy-registry-extraction-design.v3.5.1.md (TASK-1032)
  - artifacts/governance/policy-registry-extraction-decision-matrix.v3.5.1.json (TASK-1032)

---

## 1. Purpose

定義「Evidence Ref policy registry 由 design-only prototype 過渡至 runtime consumption」之**受控抽取計畫**之 schema 與內容，使任一未來授權之 runtime extraction 任務可依此計畫驗收，**不留**模糊空間。本任務為 **planning-only**：**不**修改 production PCACC runner、**不**讓 production validator 消費 prototype registry、**不**創建 runtime registry 檔、**不**創建 TASK-1035+ lifecycle artifact。

本計畫之核心立場為：

- 將「設計授權（design）」與「執行授權（implementation）」嚴格分離；TASK-1033 已給出 design 證據，TASK-1034 給出 future runtime extraction 之**驗收契約**，但**不**啟動執行；執行屬未來獨立 task 之 lifecycle。
- 對 PCACC-002 既有行為與 TASK-1030 negative test 之 `actual_reason_code` 採**字面忠實**保留為硬性錨點。
- 對 registry consumption 採**單一明示 CLI flag** 之 activation model；拒絕 automatic discovery 與 environment-variable-only activation。
- 對 registry load 與 schema validation 之失敗採 **fail-closed exit code 2**；任何 silent fallback / silent skip / 字面變體之 reason_code 均禁止。

---

## 2. Inputs

| input_id | source | role |
|---|---|---|
| IN-1 | artifacts/governance/prototypes/evidence-ref-policy-registry.prototype.v3.5.2.json | 原型 schema source；19 頂層欄位、10 prefix、5 RRC、4 ORC、9 FE、35 false key |
| IN-2 | artifacts/governance/evidence-ref-policy-registry-prototype-design.v3.5.2.md | 原型設計說明；12 sections |
| IN-3 | artifacts/verify/TASK-1033/evidence-ref-policy-prototype-inspection.json | 原型 inspection 證據；30 checks 全 pass |
| IN-4 | artifacts/governance/precommit-check-policy.v3.5.json | 現行 PCACC active surface（PCACC-001..004）；reason_code taxonomy |
| IN-5 | artifacts/scripts/run_precommit_check.py | 現行 PCACC runner；run_pcacc_002 行為錨點；sha256 prefix=5d1fcd1f96948028 |
| IN-6 | template/artifacts/scripts/run_precommit_check.py | 現行 PCACC runner template mirror；sha256 prefix=5d1fcd1f96948028（byte_identical） |
| IN-7 | artifacts/verify/TASK-1030/pcacc-negative-test-result.json | NEG-002 / NEG-003 backward compat 錨點 |
| IN-8 | artifacts/governance/policy-registry-extraction-design.v3.5.1.md | TASK-1032 之 narrower design recommendation |
| IN-9 | artifacts/governance/policy-registry-extraction-decision-matrix.v3.5.1.json | readiness gates / migration options / non-authorization 整理 |

所有 input 為 read-only；本計畫不修改任一 input。

---

## 3. Current Prototype State

- prototype JSON：`artifacts/governance/prototypes/evidence-ref-policy-registry.prototype.v3.5.2.json`，刻意落於 `prototypes/` 子目錄以隔離 PCACC runner 之候選 load 路徑。
- prototype 之 `prototype_status=design_only`、`runtime_consumption_authorized=false`；TASK-1033 inspection JSON 30 checks 全 pass。
- prototype 之 `pcacc_compatibility` 顯示 `prototype_introduces_pcacc_005=false`、`prototype_changes_pcacc_active_count=false`、`prototype_changes_pcacc_result_schema=false`、`ac_to_verify_coverage_activated=false`、`ac_to_verify_coverage_remains_excluded=true`。
- prototype 之 `non_authorization` 列 35 條 false key（含 5 條核心：implementation / runtime_consumption / validator_split / production_validator_modification / task_1034_plus）。

本計畫**不**修改 prototype；只**讀**之為 future runtime extraction 之契約來源。

---

## 4. Future Production Change Points

下列 change points 為 future 之**設計位點**，本任務**不**動。詳細 surface / current_behavior / future_planned_behavior / risk / evidence_ref 見 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `future_change_points`。

| change_point_id | surface | summary |
|---|---|---|
| CP-1 | `artifacts/scripts/run_precommit_check.py:run_pcacc_002`（line 292 之函式入口） | 預先（optional）讀取 CLI flag 提供之 registry 路徑；不提供時行為與當前一致 |
| CP-2 | `parse_evidence_refs`（line 156）與 `run_pcacc_002` 內 per-ref 分支 | registry 啟動時依 registry 之 `allowed_ref_prefixes`；未啟動時與當前一致 |
| CP-3 | 計畫新增之 `load_evidence_ref_registry` 輔助函式（runner 內、純標準庫） | 讀檔、parse、schema validate、failed close；無 silent fallback |
| CP-4 | `load_evidence_ref_registry` 內之 schema validation 段 | 嚴格 enum / required / unknown field 檢查；exit 2 fail-closed |
| CP-5 | `run_pcacc_002` 內 reason_code 聚合段（lines 357-359） | 字面保留 `missing_paths:` / `malformed_refs:`；不引入新 key |
| CP-6 | runner 模組頂層 exit code surface | 0/1/2 三段不變；exit 2 用於 registry load / schema 驗證失敗 |

若上列任一函式名 / 行號於未來 runner 改動後失準，必須在 future runtime extraction task 之 plan / verify 中重新錨定，再啟動實作。**不可**以 stale change point 為基礎執行抽取。

由於本任務為 static inspection，無法保證 future runner refactor 後函式名仍存在；此限制顯式記於 §13。

---

## 5. Backward-Compatible Default Behavior

| condition | required future behavior |
|---|---|
| registry 路徑未提供 | 等同當前 in-module PCACC-002 邏輯；無任何 behavioural delta |
| registry 路徑提供且檔案 valid | 行為等價於 prototype 語意；TASK-1030 NEG-002 / NEG-003 reason_code 字面不變 |
| registry 路徑提供但檔案 invalid（malformed JSON / schema mismatch / forbidden pattern） | fail-closed；exit code 2；machine-readable failure 記錄寫入 `artifacts/verify/<task>/precommit-check-result.json` |
| registry 檔案缺失且**顯式請求** | fail-closed；exit code 2 |
| registry 檔案缺失且**未請求** | 走 default in-module 路徑；不報錯 |

硬性錨點：

- `task_1030_neg_002_actual_reason_code_anchor=malformed_refs:garbage_token_not_a_known_prefix`
- `task_1030_neg_003_actual_reason_code_anchor=evidence_refs_section_empty`
- `pcacc_active_check_count_must_remain_4=true`
- `pcacc_active_check_surface_must_remain=[PCACC-001, PCACC-002, PCACC-003, PCACC-004]`
- `pcacc_005_must_not_be_introduced=true`
- `ac_to_verify_coverage_must_remain_excluded=true`
- `result_schema_must_remain_unchanged=true`
- `reason_code_surface_must_be_string_identical_for_existing_fixtures=true`

---

## 6. Registry Path and Activation Model

### 6.1 Preferred activation

採**單一明示 CLI flag**：

```text
python artifacts/scripts/run_precommit_check.py <task_id> --evidence-ref-policy=artifacts/governance/evidence-ref-policy.v1.json
```

特性：

- flag 必為**選用**；未提供時走 in-module default；提供時走 registry path。
- flag 值為**單一檔案路徑**；不接受 directory；不接受 glob；不接受 URL。
- flag 不設 boolean default-on；不接受 env-var fallback；不接受 cwd-implicit detection。

### 6.2 Rejected activation models

| model | rationale |
|---|---|
| automatic discovery | scanning `artifacts/governance/` 會誤掃 prototype 與任何 draft；破壞 design-only 隔離 |
| environment-variable-only activation | env-var 不出現在 git diff 與 verify artifact；違反 RACI-PDCA-SECI 可稽核紀律 |
| 將 registry 路徑寫入 `precommit-check-policy.v3.5.json` | 修改 v3.5.0 policy 屬獨立 decision；本計畫不開此口；可由 future v3.5.x successor policy 透過獨立 decision 啟動 |

### 6.3 Default vs explicit request

- default：未提供 flag → in-module behavior。
- explicit：提供 flag → registry path；任何失敗 fail-closed exit 2；不退回 in-module default。

---

## 7. Fallback and Failure Semantics

下列 8 case 之 condition / future_status / reason_code / exit_code / machine_readable_evidence 詳列於 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `fallback_and_failure_semantics`。摘要：

| case | condition | future_status | reason_code | exit |
|---|---|---|---|---|
| FS-1 | missing_registry_explicit | fail | `evidence_ref_registry_missing:<path>` | 2 |
| FS-2 | malformed_json | fail | `evidence_ref_registry_malformed_json` | 2 |
| FS-3 | schema_version_mismatch | fail | `evidence_ref_registry_schema_version_mismatch:<actual>` | 2 |
| FS-4 | unknown_required_field | fail | `evidence_ref_registry_missing_required_field:<field>` | 2 |
| FS-5 | unknown_enum_value | fail | `evidence_ref_registry_unknown_enum_value:<field>=<value>` | 2 |
| FS-6 | forbidden_ref_pattern | fail | `evidence_ref_registry_forbidden_pattern:<pattern>` | 2 |
| FS-7 | invalid_local_artifact_constraint | fail | `evidence_ref_registry_invalid_local_artifact_constraint:<key>` | 2 |
| FS-8 | policy_conflict_with_pcacc_002 | fail | `evidence_ref_registry_pcacc_002_conflict:<fixture>` | 2 |

通則：

- 所有 reason_code 為**新增** key，且僅在 registry 啟動時可能出現；不影響 PCACC-002 既有 reason_code。
- 失敗皆走 exit code 2（hard guard error），與 PCACC violation 之 exit code 1 區隔。
- machine-readable evidence 統一寫至 `artifacts/verify/<task>/precommit-check-result.json` 之 check entry；不另開 markdown 副通道。
- silent fallback 永遠禁止；silent skip 永遠禁止。

---

## 8. Schema Validation Plan

詳細欄位見 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `schema_validation_plan`。摘要：

- 必填頂層欄位 13 條（schema_version / plan_version / created_by_task / generated_at / policy_surface / allowed_ref_prefixes / ref_format_rules / local_artifact_constraints / required_ref_contexts / optional_ref_contexts / malformed_ref_behavior / missing_ref_behavior / pcacc_compatibility）。
- 必填巢狀欄位涵蓋 allowed_ref_prefixes entry / required / optional context entry / malformed / missing behavior。
- 允許 enum 限定 5 條 prefix kind 之集合、required missing_behavior=fail、optional missing_behavior_with_reason_code=skipped_with_reason_code、malformed default_action=fail。
- unknown field 行為：load 階段直接 reject。
- 版本相容：runtime load 採 exact match；supersedes 鏈須由獨立 decision artifact 文檔化。
- error message：必含 offending field path 與 observed value；不可 silent。
- exit code：schema 驗證失敗 → 2；PCACC-002 違規（registry 已 valid）→ 1；clean → 0。
- machine-readable evidence：單一 JSON record 寫入 verify artifact path；無 markdown side-channel。

---

## 9. Regression Cases for Future Extraction

11 條 future regression case 詳列於 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `regression_cases`。摘要：

| case | title | blocks_runtime_extraction |
|---|---|---|
| EVREF-REG-001 | TASK-1030 NEG-002 malformed_refs anchor remains fail | true |
| EVREF-REG-002 | TASK-1030 NEG-003 evidence_refs_section_empty anchor remains fail or explicit skip | true |
| EVREF-REG-003 | Valid local artifact ref passes | true |
| EVREF-REG-004 | Absolute path fails | true |
| EVREF-REG-005 | Parent traversal fails | true |
| EVREF-REG-006 | Remote URL fails | true |
| EVREF-REG-007 | Shell command token fails | true |
| EVREF-REG-008 | Wildcard-only ref fails | true |
| EVREF-REG-009 | Missing optional ref with reason_code is skipped_with_reason_code | true |
| EVREF-REG-010 | Missing optional ref without reason_code fails | true |
| EVREF-REG-011 | Registry load failure fails closed with exit code 2 when explicitly requested | true |

通則：

- `blocks_runtime_extraction=true` 之意：未來 runtime extraction task 任一 case fail 即不得 commit；不開 deferred verification debt。
- 本計畫**不**撰寫對應 fixture 與 driver；fixture 撰寫屬 future task。
- 若未來 task 改用 prototype JSON 之 ORC-1..ORC-4 任一情境，必須同步在 future task verify artifact 中**顯式**記錄 reason_code，否則仍歸 EVREF-REG-010 之 fail。

---

## 10. Rollback Strategy

詳列於 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `rollback_strategy`。摘要：

1. 移除 PCACC runner 之 `--evidence-ref-policy` CLI argument 使用。
2. `git revert` 引入 runtime registry consumption 之 commit。
3. 復原 `artifacts/scripts/run_precommit_check.py` 與其 mirror 至 sha256 prefix=`5d1fcd1f96948028`。
4. 退回 in-module PCACC-002 行為；無任何 behavioural delta。
5. 保留 `artifacts/governance/prototypes/` 之 prototype registry**不**刪除（仍為 design 證據）。
6. 重跑 TASK-1030 NEG-002 / NEG-003 fixture，驗證 reason_code 字面不變。
7. Codex 對 rollback verify artifact 報 PASS。

rollback 之 evidence 須包含：post-rollback sha256 prefix 比對、TASK-1030 NEG-002 / NEG-003 reason_code 字面。rollback 執行屬 future task 之 lifecycle；**TASK-1034 不授權 rollback 執行**（理由：尚無 extraction）。

---

## 11. Source/Template Sync Implications

| 議題 | 結論 |
|---|---|
| future runtime registry 是否需要 template mirror | 若落於 `artifacts/governance/`（unpaired），無 mirror 義務；若 future task 改放 `artifacts/scripts/`，必須由獨立 decision 擴 EXACT_SYNC_FILES 並建 mirror |
| production runner 改動是否需要 template mirror | 是；`artifacts/scripts/run_precommit_check.py` 與 `template/artifacts/scripts/run_precommit_check.py` 為 paired source；任一 byte 變動須 lockstep |
| registry 改動是否觸發 QC-SYNC-001 | 否；QC-SYNC-001 只對 EXACT_SYNC_FILES 路徑生效；若 registry 留在 `artifacts/governance/`，無觸發；除非未來 decision 將之改為 paired |
| baseline 是否須刷新 | 是；改 runner 即改 sha256，`quality-baseline.v3.5.json` 可能須由獨立 decision 刷新；TASK-1034 不授權刷新 |
| waiver 適用 | 任一 drift 須由 remediation 或獨立 decision 之 waiver 處理；TASK-1034 不簽 waiver |
| post-baseline drift detection | future runtime extraction 須沿 TASK-1029 model 加 QC-SYNC-001 negative regression test，證明 paired files 仍 byte_identical；屬 FE-8 之延伸 |

---

## 12. Future TASK-1035 Acceptance Criteria

11 條 future task acceptance criteria（FTA-1..FTA-11）詳列於 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `future_task_acceptance_criteria`。摘要：

| id | description |
|---|---|
| FTA-1 | runner 修改最小化、限於 `run_pcacc_002` 與新增 load 輔助；其他 function 不動 |
| FTA-2 | runner 與其 mirror byte-identical |
| FTA-3 | 預設行為（無 flag）不變；TASK-1030 NEG-002 / NEG-003 reason_code 字面一致 |
| FTA-4 | registry-driven 行為對齊 prototype 語意；通過全 11 條 EVREF-REG-* |
| FTA-5 | TASK-1030 NEG-002 / NEG-003 fixture 仍 pass，reason_code 不變 |
| FTA-6 | 新增 FS-1..FS-8 對應之 registry-specific negative test 全 pass |
| FTA-7 | PCACC active surface 嚴限 PCACC-001..PCACC-004；不引入 PCACC-005 |
| FTA-8 | AC-to-verify coverage 仍排除；reasoning faithfulness / belief-state / model self-confidence / free-text rationale / SAVeR 仍禁 |
| FTA-9 | 不拆 validator 模組；5 件 production validator/test 不動 |
| FTA-10 | rollback path 文檔化於 future task plan / decision，並已預演 |
| FTA-11 | Codex post-commit verification 對 future runtime extraction task verify artifact 報 PASS |

候選 task 命名：`TASK-1035 Evidence Ref Policy Registry Controlled Runtime Extraction`（**指引** ID；實際 ID 由未來 task allocation 任務決定）。**TASK-1034 不創建 TASK-1035 lifecycle artifact**。

---

## 13. Risks and Limitations

| risk_id | risk | mitigation |
|---|---|---|
| RL-1 | future change points 之函式名 / 行號於 runner 改動後失準 | future runtime extraction task 須在 plan / verify 中重新錨定；不可以 stale change point 啟動 |
| RL-2 | 本計畫被誤讀為 implementation 授權 | `plan_status=planning_only`、`implementation_authorized=false`、`runtime_registry_consumption_authorized=false`；38 條 false key non_authorization |
| RL-3 | activation model 採 env-var 或 automatic discovery | activation_model.rejected_activation_models 顯式列且附 rationale |
| RL-4 | reason_code 字面值漂移破壞 TASK-1030 backward compat | EVREF-REG-001 + EVREF-REG-002 為硬性 anchor；FTA-3 + FTA-5 雙錨 |
| RL-5 | registry 改放 `artifacts/scripts/` 而漏擴 EXACT_SYNC_FILES / template mirror | source_template_sync_implications 顯式列；FTA-2 雙路徑 byte_identical |
| RL-6 | rollback 路徑未事先預演 | rollback_strategy 列 7 步 + 4 條 evidence；FTA-10 強制 future task 預演 |

限制：

- 本計畫僅涵蓋 Evidence Ref policy 子域；其他 RC slice 不在範圍。
- 本計畫不創建 fixture / driver；fixture 由 future task 撰寫。
- 本計畫不執行任何 helper / pytest / formatter / package manager；inspection 為靜態。
- 本計畫不刷新 baseline、不擴 EXACT_SYNC_FILES、不簽 waiver。
- 本計畫不創建 SRS / RTM / design spec / threat model / release note / migration note / user guide / runbook 之**內容**。
- 本計畫不創建 TASK-1035 及更後之 lifecycle artifact；候選 ID 為**指引**。

---

## 14. Explicit Non-authorization

This plan does not authorize implementation.

This plan does not authorize runtime registry extraction.

This plan does not authorize production PCACC runner modification.

This plan does not authorize validator split.

This plan does not authorize production validator/test modification.

This plan does not authorize TASK-1035+ execution.

完整未授權清單見 [companion JSON](evidence-ref-policy-runtime-extraction-plan.v3.5.2.json) `non_authorization`（38 條 false key）。摘要：

- TASK-1034 不授權執行 policy registry extraction implementation。
- TASK-1034 不授權創建任一 runtime policy registry JSON 並接入 production runner。
- TASK-1034 不授權執行 validator module split。
- TASK-1034 不授權修改 5 件 production validator/test 檔（guard_status_validator.py / guard_contract_validator.py / workflow_constants.py / run_red_team_suite.py / test_guard_units.py）任一檔。
- TASK-1034 不授權修改 PCACC runner（run_precommit_check.py）或其 mirror。
- TASK-1034 不授權修改 PCACC policy（precommit-check-policy.v3.5.json）。
- TASK-1034 不授權修改 quality gate runner / policy / baseline / artifact obligation matrix。
- TASK-1034 不授權擴 EXACT_SYNC_FILES。
- TASK-1034 不授權新增 PCACC-005 或任一 active PCACC check。
- TASK-1034 不授權啟用 AC-to-verify coverage。
- TASK-1034 不授權修改 v3.5 / v3.5.1 plan / manifest。
- TASK-1034 不授權修改 TASK-1023..TASK-1033 任一 lifecycle artifact。
- TASK-1034 不授權修改 TASK-1031 / TASK-1032 / TASK-1033 之 governance artifact。
- TASK-1034 不授權創建 TASK-1035 及更後之 lifecycle artifact。
- TASK-1034 不授權執行 reasoning faithfulness audit / belief-state audit / model self-confidence audit / free-text rationale 添加 / SAVeR markdown report。
- TASK-1034 不授權執行 ruff / mypy / pyright / coverage / pylint / bandit / safety / formatter / package manager 任一執行。
- TASK-1034 不授權執行 pytest。
- TASK-1034 不授權執行 PCACC runner 或 quality gate runner 之 CLI / main()。
- TASK-1034 不授權對 QB-DRIFT-0001 做 remediation 或 waiver 簽發。
- TASK-1034 不授權升級 FIND-18 status。
- TASK-1034 不授權修改 Bootstrap Prompt Skill artifact 或 `.obsidian/` / `.omc/` / `.tmp/` / `.pytest-basetemp/`。

任何未來 runtime extraction implementation 須由獨立 task lifecycle 顯式授權；本計畫之存在不構成授權。
