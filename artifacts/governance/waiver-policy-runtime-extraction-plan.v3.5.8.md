# Waiver Policy Runtime Extraction Plan (v3.5.8)

## Document Metadata
- Document Type: governance runtime extraction plan
- Plan Version: v3.5.8
- Created By Task: TASK-1040
- Created At: 2026-05-05T23:15:00+08:00
- Plan Status: planning_only (no implementation authorized; no runtime consumption authorized)
- Builds On:
  - artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json (TASK-1039)
  - artifacts/governance/waiver-policy-registry-prototype-design.v3.5.7.md (TASK-1039)
  - artifacts/governance/evidence-ref-policy.v3.5.3.json (TASK-1035)
  - artifacts/verify/TASK-1037/golden-cli-coverage-result.json (TASK-1037)
  - artifacts/governance/v3.5.x-governance-closure-index.json (TASK-1038)
- Companion Plan JSON: artifacts/governance/waiver-policy-runtime-extraction-plan.v3.5.8.json
- Inspection Evidence: artifacts/verify/TASK-1040/waiver-runtime-extraction-plan-inspection.json

---

## 1. Purpose

本文件為 **waiver policy runtime extraction plan** 之共用 contract
source。其作用為將 TASK-1039 waiver policy registry prototype 之
runtime 抽出路徑寫成可讀、可審、可重複驗證之 plan，**僅描述**
未來 runtime 抽出之 activation model、loading model、fail-closed
matrix、selection 與 matching semantics、Evidence Ref 整合需求、
golden CLI 覆蓋需求、production runner / template mirror 保留需求、
backward compatibility、rollback 策略與 future TASK-1041 acceptance
criteria，**不**修改 prototype registry、production runner、
validator、PCACC policy、quality-gate policy、AOM、Evidence Ref
policy、template mirror、quality baseline、TASK-1023..TASK-1039 任
一 lifecycle artifact，**亦不**將 prototype 接入 runtime 任一執行
路徑。

本 plan 鏡像 TASK-1034/TASK-1035 模式（先寫 Evidence Ref runtime
extraction plan，再以 explicit `--evidence-ref-policy` flag 抽出
runtime）以利 future TASK-1041 之 controlled implementation 在已
紀錄之 contract 上落地，而非在實作壓力下才設計 contract。

`implementation_authorized=false` 與
`runtime_consumption_authorized=false` 為 plan JSON 之雙級保護；
任何 runner 嘗試以本 plan 為授權 trigger runtime 抽出時讀到
`false` 必須立即 fail-closed。

---

## 2. Source of truth and limitations

本 plan 之每一條主張均可追溯至下列 committed 來源：

| input_id | source | role |
|---|---|---|
| IN-1 | artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json | waiver schema (10 required + 7 optional fields)、6 lifecycle states、9 registry_load_failure_reason_codes、QC-SYNC-001 reason_code alignment、41 條 non_authorization |
| IN-2 | artifacts/governance/waiver-policy-registry-prototype-design.v3.5.7.md | prototype 設計敘述（16 sections）、interaction notes、risks |
| IN-3 | artifacts/governance/evidence-ref-policy.v3.5.3.json | runtime-active Evidence Ref registry；future waiver runtime 須沿用其 allowed prefixes / forbidden directories / forbidden URL schemes |
| IN-4 | artifacts/verify/TASK-1037/golden-cli-coverage-result.json | 24 已實作 golden CLI cases；TASK-1037 repair schema（split actual_status / observed_cli_status）為 future waiver golden CLI 模板 |
| IN-5 | artifacts/verify/TASK-1037/golden-cli-case-manifest.json | 已記錄 GCLI-QUALITY-SYNC-005/006 為 implementation_authorized=false 之 candidate cases |
| IN-6 | artifacts/governance/v3.5.x-governance-closure-index.json | TASK-1038 closure 之 non-authorization 邊界，含 new_runtime_registry_extraction_authorized=false |
| IN-7 | artifacts/verify/TASK-1035/evidence-ref-runtime-extraction-result.json | TASK-1035 controlled runtime extraction 已驗證模式（RTX-001..RTX-016）；future waiver runtime 須沿用 |
| IN-8 | artifacts/verify/TASK-1035/registry-regression-result.json | TASK-1030 NEG-002 / NEG-003 anchor 透過 EVREF-REG-001/002 保留之模式；future waiver runtime 須以同等模式保留 TASK-1029 QC-SYNC-001 anchor |

限制：

- 本 plan 為 **planning_only**；不執行 runtime 抽出；不創 fixture；
  不執行 production runner；不修改 EXACT_SYNC_FILES。
- 本 plan 對 verify artifact 之 `## Decision Refs` /
  `## Build Guarantee` / `## Acceptance Criteria Checklist` 任一
  其他 section 不做 schema 約束；其他 section 由
  `docs/artifact_schema.md §5.6` 維護。
- inspection evidence JSON 為**靜態 inspection** 結果；不含
  QC-SYNC-001 fixture rerun（fixture rerun 屬未來 TASK-1041
  task obligation）。
- 本 plan 之 `future_task_acceptance_criteria` 為**前提門檻**，
  非授權；本 task 之 PASS 並不等於授權 TASK-1041 執行 runtime
  抽出。
- 本 plan 不修改 prototype 之 `runtime_consumption_authorized=false`
  flag；prototype 仍為 design-only。
- 本 plan 不創建任何 production waiver registry；future runtime
  抽出時是否將 registry 推為 production 由 TASK-1041 之 plan 決定。

---

## 3. Preconditions

執行未來 waiver runtime 抽出（TASK-1041）之前提：

| precondition_id | description | current_state |
|---|---|---|
| PC-1 | TASK-1039 waiver policy registry prototype JSON 存在且 prototype_status=design_only | satisfied |
| PC-2 | TASK-1039 prototype design note 存在且涵蓋 16 sections | satisfied |
| PC-3 | TASK-1039 inspection JSON 存在且 overall_status=pass | satisfied |
| PC-4 | TASK-1038 v3.5.x closure snapshot 與 closure index 已記錄 | satisfied |
| PC-5 | TASK-1037 golden CLI repair schema（actual_status / observed_cli_status 分離）已驗證 | satisfied |
| PC-6 | TASK-1035 Evidence Ref runtime extraction 已落地（PCACC-002 registry-driven mode）為 future waiver runtime 之 reference 模板 | satisfied |
| PC-7 | TASK-1029 QC-SYNC-001 negative-test fixture set 存在；future waiver runtime 必保留其 reason_code 字面值 | satisfied |
| PC-8 | quality-gate-policy.v3.5.json#waiver_policy.discovery.mode=explicit_policy_waivers_array 仍為 default discovery mode；future runtime 抽出僅在 explicit CLI flag 下生效 | satisfied |
| PC-9 | 5 件 production validator/test 檔之 sha256 prefix 與 TASK-1038 closure index 紀錄一致 | satisfied |
| PC-10 | TASK-1040 lifecycle artifacts 存在；plan markdown 與 plan JSON 存在；inspection JSON overall_status=pass | satisfied (本 task 落地後) |
| PC-11 | TASK-1041+ lifecycle artifacts **不**存在 | satisfied |
| PC-12 | 顯式人類授權（`arcobaleno`）方可啟動 TASK-1041 | not satisfied |

PC-1..PC-11 在 TASK-1040 commit 時即可滿足；PC-12 為 TASK-1041
啟動之硬性前提，本 plan 不滿足。

---

## 4. Non-authorization boundary

本 plan 為 planning-only；**不授權**任一以下行為：

- runtime consumption（含以本 plan 為依據觸發 runtime 抽出）
- production runner 修改（`run_precommit_check.py` /
  `run_quality_gates.py` 任一檔或其 template mirror）
- production validator / test 修改（5 件 .py 檔任一檔或其 template
  mirror）
- production governance policy 修改（`precommit-check-policy.v3.5.json`
  / `quality-gate-policy.v3.5.json` /
  `quality-baseline.v3.5.json` /
  `artifact-obligation-matrix.v3.5.json` /
  `evidence-ref-policy.v3.5.3.json`）
- waiver prototype registry 修改（
  `artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json`
  與其 design note）
- 新建 production waiver registry 於 `artifacts/governance/`
  active runtime path 下
- 新增 PCACC-005 或任何 active PCACC check
- 啟用 AC-to-verify coverage
- validator module split
- function 跨檔搬移、rename
- production test 重整
- 新測試實作
- TASK-1023..TASK-1039 lifecycle artifact 修改（含 TASK-1037
  repair evidence、TASK-1038 closure evidence、TASK-1039
  prototype evidence）
- TASK-1041+ lifecycle artifact 創建
- pytest / ruff / formatter / package manager 執行
- production runner CLI / `main()` 執行
- SRS / RTM / design spec / threat model / release note /
  migration note / user guide / runbook 內容生成
- `.obsidian/` / `.omc/` / `.tmp/` / `.pytest-basetemp/` 修改
- v3.5 / v3.5.1 plan / manifest 修改

完整 41 條 false key 見 plan JSON `non_authorization` 欄位（見 §10
與 plan JSON 文件）。

---

## 5. Proposed activation model

未來 runtime 抽出之 activation 必為 **explicit CLI-only**：

```text
--waiver-policy <path>
```

### 5.1 Activation constraints

| constraint_id | constraint |
|---|---|
| AM-1 | default behavior unchanged without explicit waiver registry path |
| AM-2 | no automatic discovery（runner 不掃描任何預設路徑） |
| AM-3 | no environment-variable-only activation（不接受 `WAIVER_POLICY=...` 環境變數作為觸發） |
| AM-4 | no implicit consumption from prototype path（`artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json` 不得被 runner 隱式 load） |
| AM-5 | explicit path required（必為 CLI argument） |
| AM-6 | missing explicit file fails closed（exit_code=2；reason_code=`waiver_registry_missing:<path>`） |
| AM-7 | malformed explicit file fails closed（exit_code=2；reason_code=`waiver_registry_malformed_json`） |
| AM-8 | activation 必鏡像 TASK-1035 `--evidence-ref-policy` pattern：default in-module path 與 explicit registry path 互斥；無 flag 即走 default in-module path（即 quality-gate-policy.v3.5.json#waiver_policy.discovery.mode=explicit_policy_waivers_array） |

### 5.2 Activation surface

未來 runtime 抽出之 activation surface 限定為：

```text
artifacts/scripts/run_quality_gates.py            # quality gate runner
template/artifacts/scripts/run_quality_gates.py   # template mirror
```

PCACC runner（`run_precommit_check.py`）**不**直接 load waiver
registry；waiver 只影響 quality gate 之 QC-SYNC-001 reason_code
表面（與 `quality-gate-policy.v3.5.json#waiver_policy` 對齊），
不影響 PCACC 四 active checks。

---

## 6. Runtime loading model

未來 runtime 之 registry load 行為：

| load_step | description |
|---|---|
| LM-1 | read registry from explicit path（CLI argument；無預設路徑） |
| LM-2 | validate `schema_version` 必為 `waiver-policy-registry/v1`（注意：runtime registry 之 schema_version 與 prototype 之 `waiver-policy-registry-prototype/v1` 不同；prototype 不得直接被 runner load） |
| LM-3 | validate plan / version compatibility（`plan_version` 必為 runner 支援之版本） |
| LM-4 | reject unknown top-level fields |
| LM-5 | validate top-level `non_authorization` 不與 runtime task authorization 矛盾（即若 runtime registry 自宣 `runtime_consumption_authorized=false`，runner 必拒絕 load） |
| LM-6 | validate 每筆 waiver entry（required field 完整性 / lifecycle state 合法性 / expires_at 格式 / scope 形狀 / evidence_ref 合規） |
| LM-7 | fail closed on load errors（exit_code=2） |
| LM-8 | do not partially apply invalid registry（若任一 waiver entry 失敗，整個 registry load 失敗） |
| LM-9 | runner 在 registry load 成功後方執行 quality gate；load 失敗時不執行 gate |
| LM-10 | runner 必輸出 machine-readable load failure envelope（`{"error":"waiver_registry_load_failed","reason_code":"<code>"}`），鏡像 TASK-1037 GCLI-PRECOMMIT-FAILCLOSED-001..004 之 envelope shape |

---

## 7. Fail-closed matrix

每一 runtime condition 對應之未來預期行為與 reason_code 表面如下。
所有 row 之 `implementation_authorized` 均為 `false`（本 plan 不
授權實作）。詳見 plan JSON `fail_closed_matrix`。

| condition_id | condition | future expected behavior | future exit_code | suppression_allowed | reason_code | golden_cli_required |
|---|---|---|---|---|---|---|
| FC-01 | missing explicit registry path | registry load failure；fail closed | 2 | false | `waiver_registry_missing:<path>` | true |
| FC-02 | malformed JSON | registry load failure；fail closed | 2 | false | `waiver_registry_malformed_json` | true |
| FC-03 | schema_version mismatch | registry load failure；fail closed | 2 | false | `waiver_registry_schema_version_mismatch:<actual>` | true |
| FC-04 | unknown top-level field | registry load failure；fail closed | 2 | false | `waiver_registry_unknown_top_level_field:<field>` | true |
| FC-05 | unknown waiver entry field | registry load failure；fail closed | 2 | false | `waiver_registry_unknown_enum_value:<field>=<value>` | true |
| FC-06 | missing required waiver field | registry load failure；fail closed | 2 | false | `waiver_registry_missing_required_field:<field>` | true |
| FC-07 | missing expires_at | runtime treats waiver as invalid；blocking | 1 | false | `waiver_invalid:missing_fields:expires_at` | true |
| FC-08 | malformed expires_at | runtime treats waiver as invalid；blocking | 1 | false | `waiver_invalid:malformed_expires_at:<value>` | true |
| FC-09 | expired waiver | runtime treats waiver as expired；blocking（mirrors GCLI-QUALITY-SYNC-006） | 1 | false | `waiver_invalid:expired:<date>` | true |
| FC-10 | revoked waiver | runtime treats waiver as revoked；blocking | 1 | false | `waiver_invalid:revoked:<waiver_id>` | true |
| FC-11 | superseded waiver | runtime treats waiver as superseded；blocking | 1 | false | `waiver_invalid:superseded:<waiver_id>` | true |
| FC-12 | invalid status | registry load failure；fail closed | 2 | false | `waiver_registry_unknown_enum_value:status=<value>` | true |
| FC-13 | missing owner | registry load failure；fail closed | 2 | false | `waiver_registry_missing_required_field:owner` | true |
| FC-14 | missing reason_code | registry load failure；fail closed | 2 | false | `waiver_registry_missing_required_field:reason_code` | true |
| FC-15 | missing evidence_ref | registry load failure；fail closed | 2 | false | `waiver_registry_missing_required_field:evidence_ref` | true |
| FC-16 | Evidence Ref violation（waiver evidence_ref 不合 evidence-ref-policy.v3.5.3.json） | registry load failure；fail closed | 2 | false | `waiver_registry_forbidden_pattern:<pattern>` | true |
| FC-17 | scope mismatch（waiver scope 與 finding target 不符） | runtime 不抑制；finding 維持 blocking | 1 | false | `waiver_invalid:scope_mismatch:<waiver_id>` | true |
| FC-18 | wildcard-only scope | registry load failure；fail closed | 2 | false | `waiver_registry_forbidden_pattern:wildcard_only_scope` | true |
| FC-19 | broad repo-wide waiver（無 decision artifact 顯式 override） | registry load failure；fail closed | 2 | false | `waiver_registry_forbidden_pattern:broad_repo_wide_waiver` | true |
| FC-20 | duplicate waiver_id | registry load failure；fail closed | 2 | false | `waiver_registry_pair_uniqueness_violation:<waiver_id>` | true |
| FC-21 | conflicting waiver entries（同 rule_id + scope 多筆 active） | registry load failure；fail closed（deterministic rejection） | 2 | false | `waiver_registry_qc_sync_001_conflict:<fixture>` | true |
| FC-22 | valid active unexpired waiver（schema OK；expires_at 未過；scope 命中 finding target） | runtime 抑制 **僅該 finding**；其他 finding 維持原狀（mirrors GCLI-QUALITY-SYNC-005） | 0 | future_targeted_only | `waivered_until:<date>` | true |
| FC-23 | post_baseline_new_pair valid active unexpired waiver | runtime 抑制 **僅該 pair finding** | 0 | future_targeted_only | `post_baseline_new_pair_waivered_until:<date>` | true |
| FC-24 | post_baseline_new_pair invalid waiver | runtime 不抑制；blocking | 1 | false | `post_baseline_new_pair_waiver_invalid:<reasons>` | true |

`suppression_allowed=false` 為硬約束；`future_targeted_only` 表示
僅目標 finding 可被抑制，其他 finding 不受影響。

---

## 8. Waiver selection and matching model

未來 runtime 之 waiver selection 與 matching 行為：

| select_step | description |
|---|---|
| SM-1 | 僅選 valid active unexpired waivers（status=`active` 且 `expires_at` 未過） |
| SM-2 | 不選 expired / revoked / superseded / invalid / advisory_only waivers |
| SM-3 | exact `rule_id` + target match preferred |
| SM-4 | path-scoped waivers 必為 exact path 或 constrained match（非萬用字元） |
| SM-5 | task-scoped waivers 必為 exact TASK-XXXX 命中 |
| SM-6 | artifact-scoped waivers 必為 exact path 或 path#anchor 命中 |
| SM-7 | pair-scoped waivers 必為 exact baseline_id 或 sourcepath+templatepath 命中 |
| SM-8 | wildcard-only scope rejected（FC-18） |
| SM-9 | broad repo-wide waiver rejected by default（FC-19） |
| SM-10 | multi-scope waiver requires explicit justification（decision artifact `## Guard Exception` 顯式 override） |
| SM-11 | conflicting waivers fail closed（FC-21；deterministic rejection；不依靠 first-match） |
| SM-12 | expired/revoked/superseded/invalid waivers cannot suppress（即便 selection 命中 target） |
| SM-13 | matching evaluation 為 deterministic（同 input 同 output） |
| SM-14 | runtime 不允許 silent skip（unmatched waiver 必走 FC-17 scope_mismatch） |

---

## 9. Evidence Ref integration requirements

未來 runtime 必委派 waiver `evidence_ref` 解析至
`evidence-ref-policy.v3.5.3.json`（或其後繼版本），並滿足下列
constraint：

| constraint_id | constraint |
|---|---|
| ER-1 | local artifact refs only（除非 later policy 顯式允許 remote） |
| ER-2 | absolute paths rejected |
| ER-3 | parent traversal（`../`）rejected |
| ER-4 | remote URLs（`http://` / `https://` / `ftp://` / `file://` / `ssh://` / `git://` / `git+ssh://`）rejected |
| ER-5 | shell tokens rejected |
| ER-6 | `.obsidian` / `.omc` / `.tmp` / `.pytest-basetemp` / `__pycache__` / `.pytest_cache` / `node_modules` / `.venv` / `.git` 任一作為 root directory rejected |
| ER-7 | missing required `evidence_ref` blocking（FC-15） |
| ER-8 | RRC-5 alignment：當 waiver 目標為 scope-drift finding 時，verify artifact 必回聲 decision artifact `## Guard Exception` 之 Scope Files；缺此回聲以 `missing_paths:<token>` reason_code 失敗（per evidence-ref-policy.v3.5.3.json#required_ref_contexts.RRC-5） |
| ER-9 | runtime 不允許 fallback to in-module evidence_ref check；必委派 evidence-ref-policy registry |
| ER-10 | Evidence Ref violation 對應 FC-16 fail-closed row（exit_code=2） |

---

## 10. Backward compatibility requirements

| compat_id | requirement |
|---|---|
| BC-1 | default behavior preserved without `--waiver-policy` flag；無 flag 之 quality gate run 必與 TASK-1029 QC-SYNC-001 fixture set byte-identically pass |
| BC-2 | `quality-gate-policy.v3.5.json#waiver_policy.discovery.mode=explicit_policy_waivers_array` 仍為 default discovery mode |
| BC-3 | `quality-gate-policy.v3.5.json#waiver_policy.discovery.registry_forbidden=true` 在 default mode 仍生效；只有 `--waiver-policy` flag 啟用後才允許讀取 registry |
| BC-4 | `quality-gate-policy.v3.5.json#waivers=[]` 之空陣列在 default mode 之行為不變 |
| BC-5 | TASK-1029 QC-SYNC-001 negative-test fixture set 之 reason_code 字面值不得改寫（preserve `in_sync` / `baseline_existing` / `post_baseline_new_pair_drift` 等） |
| BC-6 | TASK-1037 已實作之 24 golden CLI cases 在 future waiver runtime 抽出後仍 pass（GCLI-PRECOMMIT-* 16 cases + GCLI-QUALITY-* 8 cases）；其 expected_status / actual_status / expected_cli_status / observed_cli_status 不得 regress |
| BC-7 | TASK-1037 repair schema（split actual_status / observed_cli_status）不得回退至 pre-repair 之 conflated schema |
| BC-8 | PCACC active surface 維持 4 件（PCACC-001..PCACC-004）；不引入 PCACC-005；不擴張 PCACC active count |
| BC-9 | AC-to-verify coverage 維持 excluded |
| BC-10 | `artifact-obligation-matrix.v3.5.json#waiver_policy.mechanism=decision_artifact_only` 在 AOM 表面不變；runtime registry 僅作 quality-gate 之 QC-SYNC-001 表面，不取代 AOM 之 decision artifact `## Guard Exception` 機制 |
| BC-11 | Evidence Ref policy 之 RRC-5 不變；runtime registry 之 evidence_ref 仍走 evidence-ref-policy.v3.5.3.json |

---

## 11. Golden CLI coverage requirements

未來 runtime 抽出時，golden CLI 必新增以下 case，覆蓋 §7 fail-closed
matrix 之每一條 condition。所有 case 之 `authorized_now=false`
（本 plan 不授權實作）。

每 case 須繼承 TASK-1037 repair schema：split `actual_status` /
`observed_cli_status`、stable reason_code 字面值、stderr 必為空。

| case_id | title | surface | required_future_task | authorized_now | expected_status | reason_code |
|---|---|---|---|---|---|---|
| GCLI-WAIVER-001 | default behavior unchanged without `--waiver-policy` | CLI-QUALITY-GATES | TASK-1041 | false | pass | `default_no_waiver_registry_path` |
| GCLI-WAIVER-002 | valid explicit registry accepted；exit 0；no finding suppressed when no match | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_loaded_no_match` |
| GCLI-WAIVER-003 | valid active unexpired waiver suppresses only targeted finding（mirrors GCLI-QUALITY-SYNC-005） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waivered_until:<date>` |
| GCLI-WAIVER-004 | expired waiver blocking（mirrors GCLI-QUALITY-SYNC-006） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_invalid:expired:<date>` |
| GCLI-WAIVER-005 | missing expires_at blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_invalid:missing_fields:expires_at` |
| GCLI-WAIVER-006 | malformed expires_at blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_invalid:malformed_expires_at:<value>` |
| GCLI-WAIVER-007 | missing required field blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_missing_required_field:<field>` |
| GCLI-WAIVER-008 | unknown field blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_unknown_top_level_field:<field>` |
| GCLI-WAIVER-009 | malformed registry blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_malformed_json` |
| GCLI-WAIVER-010 | schema mismatch blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_schema_version_mismatch:<actual>` |
| GCLI-WAIVER-011 | Evidence Ref violation blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_forbidden_pattern:<pattern>` |
| GCLI-WAIVER-012 | scope mismatch blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_invalid:scope_mismatch:<waiver_id>` |
| GCLI-WAIVER-013 | wildcard-only scope blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_forbidden_pattern:wildcard_only_scope` |
| GCLI-WAIVER-014 | broad repo-wide waiver blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_forbidden_pattern:broad_repo_wide_waiver` |
| GCLI-WAIVER-015 | duplicate waiver_id blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_pair_uniqueness_violation:<waiver_id>` |
| GCLI-WAIVER-016 | conflicting waivers blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_qc_sync_001_conflict:<fixture>` |
| GCLI-WAIVER-017 | revoked waiver blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_invalid:revoked:<waiver_id>` |
| GCLI-WAIVER-018 | superseded waiver blocking | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_invalid:superseded:<waiver_id>` |
| GCLI-WAIVER-019 | invalid status blocking（exit 2） | CLI-QUALITY-GATES | TASK-1041 | false | pass | `waiver_registry_unknown_enum_value:status=<value>` |

---

## 12. Production runner and template mirror preservation

未來 implementation 須證明：

| preservation_id | requirement |
|---|---|
| PR-1 | root runner（`artifacts/scripts/run_quality_gates.py`）與 template mirror（`template/artifacts/scripts/run_quality_gates.py`）在 authorized changes 之後 byte-identical（sha256 prefix 比對） |
| PR-2 | diff 限制於 authorized runner files 與 TASK-1041 evidence path |
| PR-3 | default behavior preserved without explicit CLI argument |
| PR-4 | golden CLI coverage 在 closure 之前更新（GCLI-WAIVER-001..019 全 lock） |
| PR-5 | 5 件 production validator/test 檔（`guard_status_validator.py` /
  `guard_contract_validator.py` / `workflow_constants.py` /
  `run_red_team_suite.py` / `test_guard_units.py`）之 sha256
  prefix 不變 |
| PR-6 | template mirror（`template/artifacts/scripts/...`）之 sha256
  prefix 與 root mirror 一致 |
| PR-7 | TASK-1041 verify artifact 必含 sha256 prefix 比對表，鏡像
  TASK-1037 result JSON `production_preservation.targets` 表 |
| PR-8 | EXACT_SYNC_FILES 不得擴張（除非另有獨立 decision artifact 授權） |

---

## 13. Rollback strategy

若 future TASK-1041 之 implementation 發生問題，rollback 步驟：

| rollback_step | description |
|---|---|
| RB-1 | remove explicit CLI activation（移除 runner 之 `--waiver-policy` argument 與 loader code path） |
| RB-2 | restore runner / template pair from previous commit（`git checkout <pre-TASK-1041 sha> -- artifacts/scripts/run_quality_gates.py template/artifacts/scripts/run_quality_gates.py`） |
| RB-3 | preserve prototype / design artifacts as historical design records（不刪除 prototype JSON、design note、TASK-1039 evidence） |
| RB-4 | preserve TASK-1040 plan artifacts as historical planning records（不刪除 plan markdown、plan JSON、TASK-1040 inspection evidence） |
| RB-5 | do not delete prior evidence（TASK-1023..TASK-1040 任一 evidence 不刪除；不修改 prior task 之 status/verify） |
| RB-6 | create repair / rollback lifecycle task（如 `TASK-104X repair waiver runtime extraction`），以 lifecycle artifact 紀錄 rollback decision、scope、evidence |
| RB-7 | Codex 對 rollback 後之 working tree 執行 read-only verification（鏡像 TASK-1037 repair 模式） |
| RB-8 | rollback 完成後 quality gate run 必再次與 TASK-1029 QC-SYNC-001 fixture set byte-identically pass |
| RB-9 | rollback 不得 lift 任一 non_authorization 邊界；rollback 是 surface 復原，不是授權擴張 |

---

## 14. Migration and staged rollout plan

未來 TASK-1041 之 staged rollout（不在本 plan 執行）：

| stage | description | gate |
|---|---|---|
| ST-1 | TASK-1041 plan artifact + runtime registry skeleton（`waiver-policy-registry.v3.6.0.json` under `artifacts/governance/`，schema_version=`waiver-policy-registry/v1`，`runtime_consumption_authorized=true`，`waivers=[]`） | 顯式人類授權 |
| ST-2 | TASK-1041 runner attachment（`run_quality_gates.py` 加 `--waiver-policy` argument 與 `load_waiver_registry()` loader） | TASK-1041 plan ready |
| ST-3 | TASK-1041 controlled negative-case fixtures（GCLI-WAIVER-001..019 其中 fail-closed cases 對應之 fixture） | runner attachment 落地 |
| ST-4 | TASK-1041 golden CLI lock（GCLI-WAIVER-001..019 全 lock） | controlled fixtures 落地 |
| ST-5 | TASK-1041 production preservation 證據（sha256 prefix 比對表；diff 限制於 authorized files） | golden CLI lock |
| ST-6 | TASK-1041 verify + status；Codex post-commit PASS | preservation 證據 |
| ST-7 | （optional）TASK-1042 negative-regression 擴張（TASK-1029 fixture 之 waiver 變體） | TASK-1041 closure |

ST-1..ST-7 為 future work；本 plan 不授權執行任一 stage。

---

## 15. Future TASK-1041 acceptance criteria

未來 TASK-1041 啟動之 acceptance criteria（**前提門檻**，**非授權**）：

| ftc_id | criterion |
|---|---|
| FTC-1 | 顯式人類授權（`arcobaleno`）；無顯式授權即不啟動 |
| FTC-2 | implementation scope allowlist：staging set 僅含 TASK-1041 lifecycle artifacts、runtime registry JSON、runner mirror pair、TASK-1041 evidence；不得包含其他路徑 |
| FTC-3 | runner mirror preservation：root runner 與 template mirror sha256 prefix 一致；其餘 4 件 production validator/test 檔 sha256 prefix 不變 |
| FTC-4 | default behavior unchanged：無 `--waiver-policy` flag 時 quality gate run 與 TASK-1029 fixture byte-identically pass |
| FTC-5 | fail-closed tests：FC-01..FC-24 全部對應之 controlled fixture 與 negative-case test 落地 |
| FTC-6 | golden CLI cases：GCLI-WAIVER-001..019 全 lock；繼承 TASK-1037 repair schema |
| FTC-7 | Evidence Ref enforcement：FC-16 對應之 controlled negative case 通過；waiver evidence_ref 必走 evidence-ref-policy.v3.5.3.json（或其後繼） |
| FTC-8 | no validator split：5 件 production validator/test 檔 sha256 prefix 不變 |
| FTC-9 | no PCACC active check expansion：PCACC active surface 維持 4 件；不引入 PCACC-005 |
| FTC-10 | no AC-to-verify activation：AC-to-verify coverage 維持 excluded |
| FTC-11 | Codex post-commit PASS：Codex 對 TASK-1041 evidence 執行 PASS/FAIL verification 為 PASS |
| FTC-12 | no prior task artifact retroactive modification：TASK-1023..TASK-1040 任一 lifecycle artifact 不被 TASK-1041 修改 |
| FTC-13 | non_authorization preserved：TASK-1041 自身之 non_authorization 不得 lift TASK-1040 plan JSON 之 boundary（除已被 FTC-1 顯式授權之 runtime consumption surface 外） |
| FTC-14 | runtime registry lives at `artifacts/governance/waiver-policy-registry.v<version>.json`（active runtime path），與 prototype（`artifacts/governance/prototypes/...`）路徑分離；prototype 不得被 promote 為 runtime registry |
| FTC-15 | runtime registry schema_version 必為 `waiver-policy-registry/v1`（與 prototype 之 `waiver-policy-registry-prototype/v1` schema 區隔） |

FTC-1..FTC-15 為 TASK-1041 啟動之必要條件；任一條件未滿足即足以
使 TASK-1041 不被啟動。

---

## 16. Risks and unresolved decisions

DR-1：plan 被誤讀為 implementation 授權。

- mitigation: `plan_status="planning_only"`、
  `implementation_authorized=false`、
  `runtime_consumption_authorized=false`、12 條 false
  `non_authorization`、markdown §1 / §4 / §17 顯式宣告；每一
  fail-closed matrix row 之 `implementation_authorized=false`；每
  一 golden CLI requirement 之 `authorized_now=false`。

DR-2：plan 與 prototype contract 分歧。

- mitigation: §2 列 IN-1..IN-8 source；§7 fail-closed reason_code
  與 prototype `validation_semantics.registry_load_failure_reason_codes`
  + `reason_code_policy.qc_sync_001_runtime_reason_code_alignment`
  對齊；inspection check 對 fail-closed row 之 reason_code 取
  intersection 確認。

DR-3：TASK-1041+ 被誤啟動。

- mitigation: §15 FTC-1..FTC-15 為硬前提；FTC-1 要求顯式人類授權；
  本 plan 不滿足 FTC-12（顯式授權），故 TASK-1041 不得啟動；
  pre-commit `git diff --cached --name-only` 檢查無 TASK-104{1..9}*
  路徑。

DR-4：未來 TASK-1041 忽略 GCLI-QUALITY-SYNC-005/006 之 reason_code
字面值（如改為 `WAIVER_OK` 大寫）導致 backward compat 破裂。

- mitigation: §10 BC-5、§7 FC-09、FC-22；FTC-4 + FTC-6 共同守住；
  TASK-1029 既有 negative fixture 必跑於 TASK-1041 verify；plan
  JSON `fail_closed_matrix[?condition_id=FC-09].reason_code` 之
  字面值不得偏離 `waiver_invalid:expired:<date>`。

DR-5：未來 TASK-1041 將 prototype 直接 promote 為 runtime
registry，繞過 schema_version 區隔（FTC-14 / FTC-15）。

- mitigation: FTC-14 要求 runtime registry 必落於
  `artifacts/governance/waiver-policy-registry.v<version>.json`，
  與 prototype 之 `artifacts/governance/prototypes/...` 分離；
  FTC-15 要求 schema_version 必為 `waiver-policy-registry/v1`，
  與 prototype 之 `waiver-policy-registry-prototype/v1` 區隔；
  LM-2 要求 runner 拒絕 load 任一 schema_version 不符之 registry。

DR-6：未來 TASK-1041 將 PCACC runner 也接入 waiver registry。

- mitigation: §5.2 限定 activation surface 僅
  `run_quality_gates.py`；PCACC runner 不直接 load waiver registry；
  BC-8 + FTC-9 共同守住 PCACC active surface 不擴張。

DR-7：未來 TASK-1041 將 EXACT_SYNC_FILES 擴張至 waiver registry path。

- mitigation: PR-8 顯式禁止；EXACT_SYNC_FILES 擴張須由獨立
  decision artifact 授權（v3.5.x closure index 已記錄
  `exact_sync_files_extension_authorized=false`）。

DR-8：rollback 被誤用為 lift non_authorization 之機會。

- mitigation: RB-9 顯式宣告 rollback 不得 lift 任一
  non_authorization 邊界；rollback 是 surface 復原，不是授權擴張。

未解決決議：

- UD-1：runtime registry 之 schema_version pinning 策略（單一
  `v1` 或多版本共存）由 TASK-1041 plan 決定；本 plan 預設單一
  `v1`，由 TASK-1041 plan 視 runtime 需求調整。
- UD-2：runtime registry 之 file location 是 `artifacts/governance/`
  flat 或 `artifacts/governance/registries/` 子目錄由 TASK-1041
  plan 決定；本 plan 預設 flat（與 evidence-ref-policy.v3.5.3.json
  並列），由 TASK-1041 plan 視 runtime 需求調整。
- UD-3：runtime registry 是否支援 multi-source merge（quality-gate
  policy 之 explicit_policy_waivers_array + runtime registry
  union）由 TASK-1041 plan 決定；本 plan 預設**不支援 merge**，
  default mode 與 registry mode 互斥（鏡像 TASK-1035 模式），由
  TASK-1041 plan 視 runtime 需求調整。

---

## 17. Closure conclusion

TASK-1040 為 **planning-only** runtime extraction plan。

- runtime consumption 不被本 plan 授權。
- production runner 修改不被本 plan 授權。
- production validator / test 修改不被本 plan 授權。
- production governance policy 修改不被本 plan 授權。
- waiver prototype registry 修改不被本 plan 授權。
- 新測試實作不被本 plan 授權。
- validator module split 不被本 plan 授權。
- TASK-1041+ 執行不被本 plan 授權。
- 任何未來 waiver runtime 抽出 implementation 須獨立授權，且須
  滿足 §15 FTC-1..FTC-15 全部條件。

Claude Code 在 self-verification 通過後僅 commit 已授權之
TASK-1040 檔案。Codex 將執行 post-commit PASS/FAIL verification
per `agent_roles.negative_tester`。

完整 false-key 清單見 plan JSON 之 `non_authorization` 欄位。
完整 fail-closed matrix 見 plan JSON 之 `fail_closed_matrix`。
完整 golden CLI requirements 見 plan JSON 之
`golden_cli_coverage_requirements`。完整 future TASK-1041
acceptance criteria 見 plan JSON 之
`future_task_acceptance_criteria`。
