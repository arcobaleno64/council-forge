# Waiver Runtime Authorization Readiness Decision (v3.5.9)

## Document Metadata
- Document Type: governance authorization readiness decision
- Plan Version: v3.5.9
- Created By Task: TASK-1041
- Created At: 2026-05-06T00:05:00+08:00
- Decision Status: decision_only (no implementation authorized; no runtime consumption authorized)
- Builds On:
  - artifacts/governance/waiver-policy-runtime-extraction-plan.v3.5.8.md (TASK-1040)
  - artifacts/governance/waiver-policy-runtime-extraction-plan.v3.5.8.json (TASK-1040)
  - artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json (TASK-1039)
  - artifacts/governance/waiver-policy-registry-prototype-design.v3.5.7.md (TASK-1039)
  - artifacts/governance/evidence-ref-policy.v3.5.3.json (TASK-1035)
  - artifacts/governance/v3.5.x-governance-closure-index.json (TASK-1038)
  - artifacts/verify/TASK-1037/golden-cli-coverage-result.json (TASK-1037)
  - artifacts/verify/TASK-1037/golden-cli-case-manifest.json (TASK-1037)
  - artifacts/verify/TASK-1040/waiver-runtime-extraction-plan-inspection.json (TASK-1040)
- Companion Matrix JSON: artifacts/governance/waiver-runtime-authorization-readiness-matrix.v3.5.9.json
- Inspection Evidence: artifacts/verify/TASK-1041/waiver-runtime-readiness-inspection.json

---

## 1. Purpose

本文件為 **waiver runtime authorization readiness decision** 之
共用 contract source。其作用為以 TASK-1040 runtime extraction
plan（v3.5.8）為基礎，記錄一次「未來 waiver runtime 實作
（candidate TASK-1042）是否已具備被個別人類授權之就緒度」之
決策，**僅描述**就緒度判定、未來任務之 implementation allowlist、
hard non-goals 與七道 gate（golden CLI、Evidence Ref、runner
mirror、fail-closed、rollback、human authorization、Codex
verification），**不**修改 prototype registry、production
runner、validator、PCACC policy、quality-gate policy、AOM、
Evidence Ref policy、template mirror、quality baseline、TASK-1023..
TASK-1040 任一 lifecycle artifact，**亦不**將 prototype 接入
runtime 任一執行路徑。

`decision_status=decision_only`、
`implementation_authorized=false` 與
`runtime_consumption_authorized=false` 為 matrix JSON 之三級保護。
即便本決策選擇
`ready_for_separate_human_authorization`，本決策**亦不**等同對
未來 implementation 之授權；任何未來 waiver runtime implementation
（如 candidate TASK-1042）必須由人類維護者（`arcobaleno`）獨立
顯式授權。

---

## 2. Source of truth and limitations

本就緒度決策之每一條主張均可追溯至下列 committed 來源：

| input_id | source | role |
|---|---|---|
| IN-1 | artifacts/governance/waiver-policy-runtime-extraction-plan.v3.5.8.md | TASK-1040 runtime extraction plan markdown（17 sections） |
| IN-2 | artifacts/governance/waiver-policy-runtime-extraction-plan.v3.5.8.json | TASK-1040 plan JSON：24 fail-closed rows、19 golden CLI requirements、15 future-task acceptance criteria（FTC-1..FTC-15）、48 non_authorization keys |
| IN-3 | artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json | TASK-1039 prototype JSON：waiver schema（10 required + 7 optional fields）、6 lifecycle states、9 registry_load_failure_reason_codes、QC-SYNC-001 reason_code alignment、41 條 non_authorization |
| IN-4 | artifacts/governance/waiver-policy-registry-prototype-design.v3.5.7.md | TASK-1039 prototype design note（16 sections） |
| IN-5 | artifacts/governance/evidence-ref-policy.v3.5.3.json | runtime-active Evidence Ref registry；waiver runtime 之 evidence_ref 必委派此 registry |
| IN-6 | artifacts/verify/TASK-1037/golden-cli-coverage-result.json | TASK-1037 24 已實作 golden CLI cases；TASK-1037 repair schema（split actual_status / observed_cli_status）為 future waiver golden CLI 模板 |
| IN-7 | artifacts/verify/TASK-1037/golden-cli-case-manifest.json | TASK-1037 case manifest（含 GCLI-QUALITY-SYNC-005/006 implementation_authorized=false） |
| IN-8 | artifacts/governance/v3.5.x-governance-closure-index.json | TASK-1038 closure 之 non-authorization 邊界，含 new_runtime_registry_extraction_authorized=false |
| IN-9 | artifacts/verify/TASK-1040/waiver-runtime-extraction-plan-inspection.json | TASK-1040 plan inspection JSON：25 checks all pass、overall_status=pass |

限制：

- 本決策為 **decision_only**；不執行 runtime 實作；不創 fixture；
  不執行 production runner；不修改 EXACT_SYNC_FILES。
- 本決策不創建任何 production waiver registry；future runtime
  抽出時是否將 registry 推為 production 由 future TASK-1042 之
  plan 決定。
- 本決策不修改 prototype JSON 之
  `runtime_consumption_authorized=false` flag；prototype 仍為
  design-only。
- 本決策不修改 TASK-1040 plan JSON 之
  `implementation_authorized=false` 與
  `runtime_consumption_authorized=false` flags；plan 仍為
  planning-only。
- 本決策對 verify artifact 之 `## Decision Refs` /
  `## Build Guarantee` / `## Acceptance Criteria Checklist` 任一
  其他 section 不做 schema 約束；其他 section 由
  `docs/artifact_schema.md §5.6` 維護。
- inspection evidence JSON 為**靜態 inspection** 結果；不含
  QC-SYNC-001 fixture rerun（fixture rerun 屬未來 TASK-1042 之
  obligation）。
- 本決策之 readiness criteria（FTC-1..FTC-15）為**前提門檻**，
  非授權；本任務之 PASS 並不等於對 future TASK-1042 之執行授權。

---

## 3. Preconditions from TASK-1040

下列前提為本就緒度決策之輸入；皆引自 TASK-1040 plan JSON
`preconditions` block（PC-1..PC-12）：

| precondition_id | description | current_state |
|---|---|---|
| PC-1 | TASK-1039 waiver policy registry prototype JSON 存在且 prototype_status=design_only | satisfied |
| PC-2 | TASK-1039 prototype design note 存在且涵蓋 16 sections | satisfied |
| PC-3 | TASK-1039 inspection JSON 存在且 overall_status=pass | satisfied |
| PC-4 | TASK-1038 v3.5.x closure snapshot 與 closure index 已記錄 | satisfied |
| PC-5 | TASK-1037 golden CLI repair schema（actual_status / observed_cli_status 分離）已驗證 | satisfied |
| PC-6 | TASK-1035 Evidence Ref runtime extraction 已落地（PCACC-002 registry-driven mode） | satisfied |
| PC-7 | TASK-1029 QC-SYNC-001 negative-test fixture set 存在 | satisfied |
| PC-8 | quality-gate-policy.v3.5.json#waiver_policy.discovery.mode=explicit_policy_waivers_array 仍為 default discovery mode | satisfied |
| PC-9 | 5 件 production validator/test 檔之 sha256 prefix 與 TASK-1038 closure index 紀錄一致 | satisfied |
| PC-10 | TASK-1040 lifecycle artifacts 存在；plan markdown 與 plan JSON 存在；inspection JSON overall_status=pass | satisfied |
| PC-11 | TASK-1041 lifecycle artifacts 在本任務 commit 後存在 | satisfied at TASK-1041 commit |
| PC-12 | 顯式人類授權（`arcobaleno`）方可啟動 future implementation（candidate TASK-1042） | not satisfied（且本決策不滿足 PC-12） |

PC-1..PC-10 在 TASK-1040 commit 時已滿足；PC-11 在本 TASK-1041
commit 時即可滿足；PC-12 為任何 future implementation 啟動之
硬性前提，本就緒度決策不滿足。

---

## 4. Readiness decision

### 4.1 Final decision

```text
ready_for_separate_human_authorization
```

### 4.2 Rationale

下列要件均已備齊：

- TASK-1040 runtime extraction plan markdown（17 sections）與 plan
  JSON（21 top-level fields；24 fail-closed rows；19 golden CLI
  requirements；15 future-task acceptance criteria；48 non_authorization
  keys all false）均存在且 schema 完整（IN-1, IN-2）。
- TASK-1040 inspection JSON `overall_status=pass`，25 checks 皆 pass，
  Codex post-commit verification 結果為 PASS（IN-9）。
- TASK-1039 prototype 與 design note 仍為 design-only，未被任何
  後續 task 修改（IN-3, IN-4）。
- TASK-1038 v3.5.x closure index 維持 `new_runtime_registry_extraction_authorized=false`，
  protected_surfaces 邊界未被任何後續 task 移除（IN-8）。
- TASK-1037 24 golden CLI cases 之 result JSON 與 case manifest
  皆已凍結；repair schema（split actual_status / observed_cli_status）
  為未來 GCLI-WAIVER-001..019 之模板（IN-6, IN-7）。
- TASK-1035 Evidence Ref runtime extraction 已驗證之 explicit-CLI
  pattern（`--evidence-ref-policy`）為未來 `--waiver-policy` 之
  模板。
- TASK-1029 QC-SYNC-001 negative-test fixture set 之 reason_code
  字面值已記錄於 TASK-1040 plan JSON 之 fail_closed_matrix
  reason_code 欄位（FC-09 / FC-22 等）。
- TASK-1040 plan JSON 已記錄 15 條 future-task acceptance criteria
  （FTC-1..FTC-15），覆蓋 explicit human authorization、implementation
  scope allowlist、runner mirror preservation、default behavior
  unchanged、fail-closed tests、golden CLI cases、Evidence Ref
  enforcement、no validator split、no PCACC active check expansion、
  no AC-to-verify activation、Codex post-commit PASS、no prior task
  artifact retroactive modification、non_authorization preserved、
  runtime registry path 與 prototype path 分離、runtime registry
  schema_version 與 prototype schema_version 區隔。

### 4.3 Authorization scope of this decision

**重要**：選擇 `ready_for_separate_human_authorization` 並**非**
implementation 授權。本就緒度決策只表示：

- TASK-1040 plan 已備齊 future implementation 所需之 contract
  source；
- FTC-1..FTC-15 均可被未來 implementation lifecycle 個別檢核；
- 七道 gate（golden CLI、Evidence Ref、runner mirror、fail-closed、
  rollback、human authorization、Codex verification）已被本決策
  surface 並各記載 acceptance criteria；
- 任何 future waiver runtime implementation 仍須由人類維護者
  （`arcobaleno`）獨立顯式授權，且該 future task 須通過 FTC-1
  至 FTC-15 全部前提才可啟動。

---

## 5. Implementation allowlist for future task

下列為 future implementation lifecycle（candidate TASK-1042）之
**建議 staging allowlist**。本 TASK-1041 **不**創建或修改下列
任一檔案。

| path_pattern | purpose | authorized_now | future_task_required | risk |
|---|---|---|---|---|
| artifacts/scripts/run_quality_gates.py | quality gate runner activation surface（new `--waiver-policy <path>` argument 與 `load_waiver_registry()` loader） | false | TASK-1042 | high（runner attachment） |
| template/artifacts/scripts/run_quality_gates.py | template mirror，必與 root 同步 byte-identical | false | TASK-1042 | high（runner mirror） |
| artifacts/governance/waiver-policy-registry.v\<version\>.json | runtime registry skeleton（schema_version=`waiver-policy-registry/v1`；初始 `waivers=[]`；位於 `artifacts/governance/` flat path 與 prototype 之 `prototypes/` parent 分離） | false | TASK-1042 | high（new runtime surface） |
| artifacts/verify/TASK-1042/... | TASK-1042 evidence path（fixtures、result JSONs） | false | TASK-1042 | medium（evidence only） |
| artifacts/tasks/TASK-1042.task.md | TASK-1042 task artifact | false | TASK-1042 | medium（lifecycle） |
| artifacts/plans/TASK-1042.plan.md | TASK-1042 plan artifact | false | TASK-1042 | medium（lifecycle） |
| artifacts/decisions/TASK-1042.decision.md | TASK-1042 decision artifact | false | TASK-1042 | medium（lifecycle） |
| artifacts/verify/TASK-1042.verify.md | TASK-1042 verify artifact | false | TASK-1042 | medium（lifecycle） |
| artifacts/status/TASK-1042.status.json | TASK-1042 status artifact | false | TASK-1042 | medium（lifecycle） |

**重要**：

- 本 allowlist **僅供未來任務參考**；TASK-1041 不得創建或修改其
  任一檔案。
- `run_precommit_check.py` **不**列入 allowlist：TASK-1040 plan §5.2
  顯式宣告 PCACC runner 不直接 load waiver registry；waiver 只
  影響 quality gate 之 QC-SYNC-001 reason_code 表面；將 PCACC
  runner 接入 waiver registry 屬 PCACC active surface 擴張，違反
  BC-8 / FTC-9。
- 五件 production validator/test 檔（`guard_status_validator.py`、
  `guard_contract_validator.py`、`workflow_constants.py`、
  `run_red_team_suite.py`、`test_guard_units.py`）**不**列入
  allowlist：TASK-1040 plan §12 PR-5 要求其 sha256 prefix 不變；
  validator split 屬 v3.6 範疇（FTC-8）。
- 五件 production governance policy 檔
  （`precommit-check-policy.v3.5.json`、`quality-gate-policy.v3.5.json`、
  `quality-baseline.v3.5.json`、`artifact-obligation-matrix.v3.5.json`、
  `evidence-ref-policy.v3.5.3.json`）**不**列入 allowlist：waiver
  runtime 屬於新 runtime surface，不應改寫 default discovery mode
  或 mechanism（BC-2 / BC-10）。

---

## 6. Hard non-goals for future task

下列為 future implementation lifecycle 之 **hard non-goals**，
任何 future task 違反任一 non-goal 即足以使其被 reject：

| non_goal_id | description |
|---|---|
| NG-1 | no validator split（5 件 production validator/test 檔 sha256 prefix 必不變，FTC-8） |
| NG-2 | no PCACC active check expansion（PCACC active surface 必維持 4 件，BC-8 / FTC-9） |
| NG-3 | no PCACC-005 introduction |
| NG-4 | no AC-to-verify activation（FTC-10） |
| NG-5 | no production validator/test modification unless separately authorized（FTC-3） |
| NG-6 | no Evidence Ref policy mutation unless separately authorized（BC-11 / FTC-7） |
| NG-7 | no waiver prototype mutation（runtime_registry_promotion_from_prototype_authorized=false；FTC-14） |
| NG-8 | no default behavior change without explicit `--waiver-policy` CLI flag（BC-1 / FTC-4） |
| NG-9 | no automatic discovery（AM-2） |
| NG-10 | no environment-variable-only activation（AM-3） |
| NG-11 | no document generation pipeline（SRS / RTM / threat model / migration / user guide / runbook 內容皆非 future task 範疇） |
| NG-12 | no PCACC runner waiver registry attachment（pcacc_runner_waiver_registry_attachment_authorized=false） |
| NG-13 | no EXACT_SYNC_FILES extension（PR-8） |
| NG-14 | no broad runner execution outside controlled fixtures during verification |
| NG-15 | no prior task artifact retroactive modification（FTC-12） |

---

## 7. Golden CLI gate

未來 implementation lifecycle 必新增 19 項 golden CLI cases
（GCLI-WAIVER-001..019），覆蓋 TASK-1040 plan §11 之全表。每
case 必繼承 TASK-1037 repair schema（split `actual_status` /
`observed_cli_status`、stable reason_code 字面值、stderr 必為空）。

Required future cases:

| case_id | title | reason_code |
|---|---|---|
| GCLI-WAIVER-001 | default behavior unchanged without `--waiver-policy` | `default_no_waiver_registry_path` |
| GCLI-WAIVER-002 | valid registry no-match accepted | `waiver_registry_loaded_no_match` |
| GCLI-WAIVER-003 | valid active unexpired waiver suppresses only targeted finding | `waivered_until:<date>` |
| GCLI-WAIVER-004 | expired waiver blocking | `waiver_invalid:expired:<date>` |
| GCLI-WAIVER-005 | missing expires_at blocking | `waiver_invalid:missing_fields:expires_at` |
| GCLI-WAIVER-006 | malformed expires_at blocking | `waiver_invalid:malformed_expires_at:<value>` |
| GCLI-WAIVER-007 | missing required field blocking | `waiver_registry_missing_required_field:<field>` |
| GCLI-WAIVER-008 | unknown field blocking | `waiver_registry_unknown_top_level_field:<field>` |
| GCLI-WAIVER-009 | malformed registry blocking（exit 2） | `waiver_registry_malformed_json` |
| GCLI-WAIVER-010 | schema mismatch blocking（exit 2） | `waiver_registry_schema_version_mismatch:<actual>` |
| GCLI-WAIVER-011 | Evidence Ref violation blocking（exit 2） | `waiver_registry_forbidden_pattern:<pattern>` |
| GCLI-WAIVER-012 | scope mismatch blocking | `waiver_invalid:scope_mismatch:<waiver_id>` |
| GCLI-WAIVER-013 | wildcard-only scope blocking（exit 2） | `waiver_registry_forbidden_pattern:wildcard_only_scope` |
| GCLI-WAIVER-014 | broad repo-wide waiver blocking（exit 2） | `waiver_registry_forbidden_pattern:broad_repo_wide_waiver` |
| GCLI-WAIVER-015 | duplicate waiver_id blocking（exit 2） | `waiver_registry_pair_uniqueness_violation:<waiver_id>` |
| GCLI-WAIVER-016 | conflicting waivers blocking（exit 2） | `waiver_registry_qc_sync_001_conflict:<fixture>` |
| GCLI-WAIVER-017 | revoked waiver blocking | `waiver_invalid:revoked:<waiver_id>` |
| GCLI-WAIVER-018 | superseded waiver blocking | `waiver_invalid:superseded:<waiver_id>` |
| GCLI-WAIVER-019 | invalid status blocking（exit 2） | `waiver_registry_unknown_enum_value:status=<value>` |

Acceptance criteria:

- 19 cases 全 lock 於 future task 之 result JSON。
- default unchanged（GCLI-WAIVER-001 必為 pass，且無 finding 被
  抑制）。
- TASK-1037 既有 24 golden CLI cases（16 GCLI-PRECOMMIT-* + 8
  GCLI-QUALITY-*）必繼續 pass，無 regression（BC-6）。

`authorized_now=false`：本 TASK-1041 不實作任何 case，且
`golden_cli_harness_modification_authorized=false`。

---

## 8. Evidence Ref gate

waiver registry 之每筆 entry 之 `evidence_ref` 必委派
`artifacts/governance/evidence-ref-policy.v3.5.3.json` 解析。

Acceptance criteria（引自 TASK-1040 plan §9 ER-1..ER-10）：

- local artifact refs only（除非 later policy 顯式允許 remote）。
- absolute paths rejected。
- parent traversal（`../`）rejected。
- remote URLs（`http://`、`https://`、`ftp://`、`file://`、
  `ssh://`、`git://`、`git+ssh://`）rejected。
- shell tokens rejected。
- `.obsidian` / `.omc` / `.tmp` / `.pytest-basetemp` /
  `__pycache__` / `.pytest_cache` / `node_modules` / `.venv` /
  `.git` 任一作為 root directory rejected。
- missing required `evidence_ref` blocking（FC-15）。
- RRC-5 alignment：當 waiver 目標為 scope-drift finding 時，verify
  artifact 必回聲 decision artifact `## Guard Exception` 之 Scope
  Files。
- runtime 不允許 fallback to in-module evidence_ref check；必委派
  evidence-ref-policy registry。
- Evidence Ref violation 對應 fail-closed FC-16（exit_code=2）。

`authorized_now=false`：本 TASK-1041 不修改 evidence-ref-policy
registry。

---

## 9. Runner mirror preservation gate

future implementation lifecycle 必證明：

| preservation_id | requirement |
|---|---|
| PR-1 | root runner（`run_quality_gates.py`）與 template mirror byte-identical（sha256 prefix 比對） |
| PR-2 | diff 限制於 authorized runner files 與 future TASK 之 evidence path |
| PR-3 | default behavior preserved without explicit `--waiver-policy` |
| PR-4 | golden CLI coverage 在 closure 之前更新（GCLI-WAIVER-001..019 全 lock） |
| PR-5 | 5 件 production validator/test 檔 sha256 prefix 不變 |
| PR-6 | template mirror sha256 prefix 與 root mirror 一致 |
| PR-7 | future task verify artifact 必含 sha256 prefix 比對表 |
| PR-8 | EXACT_SYNC_FILES 不得擴張 |

Anchor sha256 prefixes（自 TASK-1040 plan JSON
`runner_mirror_preservation.preservation_targets`，HEAD `bbdd7ad`）：

| path | sha256_prefix_baseline |
|---|---|
| artifacts/scripts/run_quality_gates.py | 456b8328482b18a5 |
| template/artifacts/scripts/run_quality_gates.py | 456b8328482b18a5 |
| artifacts/scripts/run_precommit_check.py | 4dbb8a219093cc12 |
| template/artifacts/scripts/run_precommit_check.py | 4dbb8a219093cc12 |
| artifacts/scripts/guard_status_validator.py | d58a41f6ca49ccfe |
| artifacts/scripts/guard_contract_validator.py | 7a38af7e2e0af5b7 |
| artifacts/scripts/workflow_constants.py | e1f09d2100b5685f |
| artifacts/scripts/run_red_team_suite.py | 77540c3b29f6ece6 |
| artifacts/scripts/test_guard_units.py | 5c7228c9997edffd |

`authorized_now=false`：本 TASK-1041 不修改任一上述檔案，
all sha256 prefixes 必繼續匹配 baseline。

---

## 10. Failure handling and fail-closed gate

future implementation lifecycle 之 runtime loader 必滿足
TASK-1040 plan §6 LM-1..LM-10 與 §7 fail-closed matrix（FC-01..
FC-24）：

- registry load failure（FC-01..FC-06、FC-12..FC-16、FC-18..FC-21）：
  exit_code=2；blocking；不允許 partial application。
- waiver-level failure（FC-07..FC-11、FC-17、FC-24）：exit_code=1；
  blocking；waiver 不得抑制 finding。
- valid active row（FC-22 / FC-23）：exit_code=0；
  `suppression_allowed=future_targeted_only`（僅目標 finding 可被
  抑制；其他 finding 不受影響）。
- 不允許 silent skip（unmatched waiver 走 FC-17 scope_mismatch）。
- machine-readable load failure envelope（`{"error":"waiver_registry_load_failed","reason_code":"<code>"}`）
  鏡像 TASK-1037 GCLI-PRECOMMIT-FAILCLOSED-001..004。

`authorized_now=false`：本 TASK-1041 不實作 loader。

---

## 11. Rollback gate

future implementation lifecycle 必準備 rollback 路徑（引自
TASK-1040 plan §13 RB-1..RB-9）：

| rollback_step | description |
|---|---|
| RB-1 | remove explicit CLI activation（移除 `--waiver-policy` argument 與 loader） |
| RB-2 | restore runner / template pair from previous commit（`git checkout <pre-future-task sha> -- artifacts/scripts/run_quality_gates.py template/artifacts/scripts/run_quality_gates.py`） |
| RB-3 | preserve prototype / design artifacts as historical records |
| RB-4 | preserve TASK-1040 plan artifacts as historical records |
| RB-5 | preserve TASK-1041 readiness decision artifacts as historical records；不刪除 prior evidence |
| RB-6 | create repair / rollback lifecycle task |
| RB-7 | Codex 對 rollback 後之 working tree 執行 read-only verification |
| RB-8 | post-rollback quality gate run 必再次與 TASK-1029 fixture set byte-identically pass |
| RB-9 | rollback 不得 lift 任一 non_authorization 邊界 |

`authorized_now=false`：本 TASK-1041 不執行 rollback；rollback 只
有在 future implementation 落地後出現問題時方執行，且需要獨立
lifecycle task。

---

## 12. Human authorization gate

future implementation lifecycle 之啟動必滿足：

- explicit human authorization（`arcobaleno`）之顯式 confirmation
  必落地為 future task 之 prompt 或 decision artifact。
- 啟動時間早於任一檔案修改；不得「先做後問」。
- authorization 之 scope 必明確：限定為 candidate TASK-1042
  staging allowlist（§5）+ TASK-1042 evidence path；不得擴張至
  其他 path。
- authorization 不得隱式由本 TASK-1041 之
  `ready_for_separate_human_authorization` 推導；本決策只是「可被
  考慮授權」之就緒度指示，**非**授權本身。
- 任何欲將 PCACC runner / 五件 validator/test 檔 / 五件 governance
  policy 納入 future scope 之請求必另立 decision artifact 申請
  scope override。

`authorized_now=false`：本 TASK-1041 不滿足 PC-12（顯式人類
授權）。

---

## 13. Codex verification gate

future implementation lifecycle commit 後必通過 Codex
（`agent_roles.negative_tester`）之 post-commit PASS/FAIL
verification：

- read-only verification only（Codex 不得修改 working tree）。
- verify 必涵蓋 staging set 是否限於 future TASK staging allowlist。
- verify 必涵蓋 19 golden CLI cases 之 result JSON 與 case
  manifest。
- verify 必涵蓋 fail-closed matrix 之 controlled fixture 結果。
- verify 必涵蓋 Evidence Ref enforcement（FC-16 對應 controlled
  negative case 通過）。
- verify 必涵蓋 runner / template mirror sha256 prefix 比對表。
- verify 必涵蓋 5 件 production validator/test 檔 sha256 prefix
  不變。
- verify 必涵蓋 prior task artifact 不被 retroactively 修改。
- 任一 verify 結果為 FAIL 即 future task status=blocked，不得
  closure。

`authorized_now=false`：本 TASK-1041 不執行任何 Codex run；Codex
之 TASK-1041 post-commit verification 由 Codex agent 在 commit
後自行執行。

---

## 14. Risk assessment

| risk_id | description | severity | mitigation |
|---|---|---|---|
| RA-1 | 本就緒度決策被誤讀為 implementation 授權 | blocking | matrix JSON `decision_status=decision_only`、`implementation_authorized=false`、`runtime_consumption_authorized=false`；non_authorization block 含 13 條 false key；§4.3 / §16 / §17 顯式宣告；每一 allowlist 與 gate 之 `authorized_now=false` |
| RA-2 | 本決策與 TASK-1040 plan contract 分歧 | blocking | matrix JSON `source_refs` 列 IN-1..IN-9；`readiness_criteria` 一一對應 FTC-1..FTC-15；inspection check 對 FTC 條目取 intersection 確認 |
| RA-3 | TASK-1042+ artifact 在本 task 期間被誤建 | blocking | 本 task 寫入路徑限定為 8 件 allowed file；pre-commit `git diff --cached --name-only` 檢查無 `TASK-104{2..9}*` 路徑 |
| RA-4 | future implementation 將 PCACC runner 接入 waiver registry | blocking | §5 allowlist 排除 PCACC runner；§6 NG-12；§7 BC-8；TASK-1040 plan FTC-9 |
| RA-5 | future implementation 將 prototype 直接 promote 為 runtime registry | blocking | TASK-1040 plan FTC-14 / FTC-15 要求 runtime registry 必落於 `artifacts/governance/waiver-policy-registry.v<version>.json` 與 prototype path 分離；schema_version 必為 `waiver-policy-registry/v1`，與 prototype 之 `waiver-policy-registry-prototype/v1` 區隔 |
| RA-6 | future implementation 跳過 GCLI-WAIVER-001..019 lock | blocking | §7 golden CLI gate 列 19 cases；future task verify 必含全 19 case result；TASK-1040 plan §11 |
| RA-7 | future implementation 改寫 quality-gate-policy.v3.5.json 之 default discovery mode | blocking | TASK-1040 plan BC-2；§5 allowlist 排除 governance policy 修改；activation 必為 explicit CLI-only |
| RA-8 | future implementation 擴張 EXACT_SYNC_FILES | blocking | TASK-1040 plan PR-8；§6 NG-13；EXACT_SYNC_FILES 擴張須由獨立 decision artifact 授權 |
| RA-9 | rollback 被誤用為 lift non_authorization 之機會 | blocking | §11 RB-9；rollback 只是 surface 復原，不是授權擴張 |
| RA-10 | future implementation 改寫 TASK-1029 QC-SYNC-001 fixture 之 reason_code 字面值 | blocking | TASK-1040 plan BC-5；FC-09 / FC-22 reason_code 必字面保留 |

---

## 15. Unresolved questions

下列為 TASK-1040 plan §16 已記錄之 unresolved decisions，由 future
TASK-1042 之 plan 決定：

- UD-1：runtime registry 之 schema_version pinning 策略（單一
  `v1` 或多版本共存）由 future TASK-1042 plan 決定。
- UD-2：runtime registry 之 file location 是
  `artifacts/governance/` flat 或
  `artifacts/governance/registries/` 子目錄由 future TASK-1042
  plan 決定。
- UD-3：runtime registry 是否支援 multi-source merge（quality-gate
  policy 之 explicit_policy_waivers_array + runtime registry
  union）由 future TASK-1042 plan 決定。

本 TASK-1041 不解決 UD-1..UD-3；它們不是 readiness 阻塞項，而是
future TASK-1042 plan 之 design choice。

---

## 16. Explicit non-authorization

下列為本決策之硬約束。即便 §4.1 readiness decision 為
`ready_for_separate_human_authorization`，下列依舊全部生效：

```text
TASK-1041 does not authorize implementation.
TASK-1041 does not authorize runtime consumption.
TASK-1041 does not authorize `--waiver-policy` CLI activation.
TASK-1041 does not authorize production runner modification.
TASK-1041 does not authorize production validator/test modification.
TASK-1041 does not authorize production governance policy modification.
TASK-1041 does not authorize waiver prototype modification.
TASK-1041 does not authorize TASK-1040 plan artifact modification.
TASK-1041 does not authorize new tests.
TASK-1041 does not authorize validator split.
TASK-1041 does not authorize PCACC active check expansion.
TASK-1041 does not authorize PCACC-005 introduction.
TASK-1041 does not authorize AC-to-verify activation.
TASK-1041 does not authorize TASK-1042+ execution.
TASK-1041 does not authorize Evidence Ref policy mutation.
TASK-1041 does not authorize prior task artifact modification.
TASK-1041 does not authorize EXACT_SYNC_FILES extension.
TASK-1041 does not authorize PCACC runner waiver registry attachment.
TASK-1041 does not authorize runtime registry promotion from prototype.
TASK-1041 does not authorize prototype schema_version runtime consumption.
```

任何違反上述之動作必須由 future lifecycle 透過獨立 decision
artifact 顯式 override；沒有獨立 decision artifact 即不可違反。

---

## 17. Closure conclusion

TASK-1041 為 **decision_only** 之 authorization readiness package。

- 本決策不授權 implementation。
- 本決策不授權 runtime consumption。
- 本決策不授權 production runner / validator / test / governance
  policy 修改。
- 本決策不授權 prototype / TASK-1040 plan artifact 修改。
- 本決策不授權 prior task artifact retroactive 修改。
- 本決策不授權 TASK-1042+ 執行。
- 本決策之 `ready_for_separate_human_authorization` 結果僅表示
  TASK-1040 plan contract 已備齊、FTC-1..FTC-15 可被個別檢核、
  七道 gate 已 surface 並各記載 acceptance criteria；它**不**等於
  對 future implementation 之授權。
- 任何未來 waiver runtime 抽出 implementation 須由人類維護者
  （`arcobaleno`）獨立顯式授權，且須滿足 TASK-1040 plan FTC-1..
  FTC-15 全部條件 + 本決策之七道 gate。

Claude Code 在 self-verification 通過後僅 commit 已授權之
TASK-1041 檔案。Codex 將執行 post-commit PASS/FAIL verification
per `agent_roles.negative_tester`。

完整 false-key 清單見 matrix JSON 之 `non_authorization` 欄位。
完整 readiness criteria 見 matrix JSON 之 `readiness_criteria`。
完整 future-task implementation allowlist 見 matrix JSON 之
`future_implementation_allowlist`。
