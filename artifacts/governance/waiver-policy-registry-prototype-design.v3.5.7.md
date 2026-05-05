# Waiver Policy Registry Prototype Design (v3.5.7)

## Document Metadata
- Document Type: governance prototype design note
- Plan Version: v3.5.7
- Created By Task: TASK-1039
- Created At: 2026-05-05T22:20:00+08:00
- Status: design-only (no runtime consumption authorized)
- Builds On:
  - artifacts/governance/quality-gate-policy.v3.5.json (TASK-1025)
  - artifacts/governance/precommit-check-policy.v3.5.json (TASK-1026)
  - artifacts/governance/artifact-obligation-matrix.v3.5.json (TASK-1027)
  - artifacts/governance/evidence-ref-policy.v3.5.3.json (TASK-1035)
  - artifacts/governance/golden-cli-coverage-matrix.v3.5.4.json (TASK-1036)
  - artifacts/governance/v3.5.x-governance-closure-index.json (TASK-1038)
  - artifacts/governance/v3.5.x-governance-closure-snapshot.md (TASK-1038)
- Companion Prototype JSON: artifacts/governance/prototypes/waiver-policy-registry.prototype.v3.5.7.json
- Inspection Evidence: artifacts/verify/TASK-1039/waiver-policy-prototype-inspection.json

---

## 1. Purpose

本文件為 **waiver policy registry prototype** 之共用 contract source
草案。其作用為將既有但散落於四個 governance 表面之 waiver 語義
集中至單一可讀來源；本文件**僅描述** prototype 之 schema、lifecycle、
expiration、reason_code、owner、evidence_ref、scope、validation
與 future runtime 抽出條件，**不**修改 production runner、validator、
PCACC policy、quality-gate policy、AOM、Evidence Ref policy、template
mirror、quality baseline、TASK-1023..TASK-1038 任一 lifecycle artifact，
**亦不**將 prototype 接入 runtime 任一執行路徑。

本 prototype 之 scope 限縮在 **waiver 單一 policy 域**：

- `quality-gate-policy.v3.5.json#waiver_policy`（QC-SYNC-001 等
  quality gate 之 waiver schema 與 expiration enforcement）；
- `artifact-obligation-matrix.v3.5.json#waiver_policy`（AOM 之
  decision_artifact_only 機制與六欄必填）；
- `evidence-ref-policy.v3.5.3.json#required_ref_contexts.RRC-5`
  （waiver_evidence_ref context；fail with missing_paths）；
- `golden-cli-coverage-matrix.v3.5.4.json#golden_case_groups[?group_id=GCLI-QUALITY-SYNC]`
  （runtime reason_code shapes：`waivered_until:<date>` 與
  `waiver_invalid:expired:<date>`）。

`split_design_into_smaller_followups` 之核心動機（TASK-1032
decision §「Chosen Option」）為：narrower design tasks 須有共用
contract source。本 prototype 即為 **waiver 子域之共用 contract
source**，但只實例化 waiver schema 與 future-runtime 抽出條件，
不一次性涵蓋 PCACC active surface 擴張、validator split、AC-to-verify
等高風險 slice。

`runtime_consumption_authorized=false` 為 prototype JSON 之第二級
保護；任何 runner 嘗試 load 時讀到此 false 必須立即 fail-closed。
prototype 落於 `artifacts/governance/prototypes/`（與 TASK-1033
Evidence Ref prototype 並列），刻意與 `artifacts/governance/`（active
runtime 候選 load 路徑）隔離。

---

## 2. Source of truth and limitations

本設計 note 之每一條主張均可追溯至下列 committed 來源：

| input_id | source | role |
|---|---|---|
| IN-1 | artifacts/governance/quality-gate-policy.v3.5.json | waiver schema 六欄 + expiration enforcement + registry_forbidden=true |
| IN-2 | artifacts/governance/artifact-obligation-matrix.v3.5.json | decision_artifact_only mechanism + narrative_only_waiver_invalid=true |
| IN-3 | artifacts/governance/evidence-ref-policy.v3.5.3.json | RRC-5 waiver_evidence_ref；missing → fail with reason_code=missing_paths |
| IN-4 | artifacts/governance/golden-cli-coverage-matrix.v3.5.4.json | GCLI-QUALITY-SYNC-005/006 reason_code shapes |
| IN-5 | artifacts/governance/precommit-check-policy.v3.5.json | PCACC active surface bounded to PCACC-001..004；canonical reviewer set |
| IN-6 | artifacts/governance/v3.5.x-governance-closure-index.json | TASK-1038 closure 之 non-authorization 邊界，含 task_1039_plus_authorized=false（候選描述）與 new_runtime_registry_extraction_authorized=false |
| IN-7 | artifacts/governance/v3.5.x-governance-closure-snapshot.md | 人類可讀之收束敘述 |
| IN-8 | artifacts/verify/TASK-1029/qc-sync-negative-test-result.json | QC-SYNC-001 negative cases；waiver-related fixture 之 reason_code 不變約束 |
| IN-9 | artifacts/verify/TASK-1037/golden-cli-coverage-result.json | GCLI-QUALITY-SYNC 已實作但 SYNC-005/006 尚為 implementation_authorized=false |

限制：

- prototype 不對 verify artifact 之 `## Decision Refs` /
  `## Build Guarantee` / `## Acceptance Criteria Checklist` 任一
  其他 section 做 schema 約束；其他 section 由
  `docs/artifact_schema.md §5.6` 維護。
- prototype 不對 helper script invocation pattern 做約束；任何
  未來 runtime task 須自行設計 invocation 介面。
- inspection evidence JSON 為**靜態 inspection** 結果；不含
  QC-SYNC-001 fixture rerun（fixture rerun 屬未來 runtime task）。
- 本 prototype 對 GCLI-QUALITY-SYNC-005 / 006 之 reason_code
  shape 為**informative**而非**authoritative**；GCLI-QUALITY-SYNC-005 / 006
  在 TASK-1037 closure 時 implementation_authorized=false，
  prototype 不能將其降為已鎖定。
- 本 prototype 不對 QB-DRIFT-0001 出 waiver；
  QB-DRIFT-0001 之 baseline_existing 狀態自 v3.5.0 起延續，
  remediation deferred to a separate decision-artifact lifecycle
  per TASK-1038 closure index。

---

## 3. Existing waiver semantics inventory

下表盤點四個既有來源之 waiver 語義；prototype JSON
`existing_waiver_semantics_inventory` 欄位提供 byte-level
reference。

### 3.1 quality-gate-policy.v3.5.json (TASK-1025)

```text
$.waiver_policy.schema.required_fields
  = [rule_id, scope, reason_code, owner, evidence_ref, expires_at]

$.waiver_policy.schema.rules
  - All six required fields must be present
  - expires_at MUST NOT appear alone
  - owner MUST reference a human reviewer or accountable maintainer (not an AI agent label)
  - evidence_ref MUST point to a verify artifact path under artifacts/verify/
  - expires_at MUST be enforceable: TASK-1025 gates MUST reject expired waivers as blocking
  - scope MUST be a non-empty list of repo-relative paths
  - Date format: YYYY-MM-DD; expiration check uses lexicographic comparison against Asia/Taipei date

$.waiver_policy.discovery.mode = "explicit_policy_waivers_array"
$.waiver_policy.discovery.registry_forbidden = true
$.waiver_policy.discovery.style_debt_registry_forbidden = true

$.waiver_policy.expiration_enforcement
  - expired_is_blocking = true
  - missing_expires_at_is_blocking = true
  - missing_required_field_is_blocking = true

$.waivers = []   (length 0 at v3.5.x closure)
```

### 3.2 artifact-obligation-matrix.v3.5.json (TASK-1027)

```text
$.waiver_policy.mechanism = "decision_artifact_only"
$.waiver_policy.no_standalone_registry_in_v3_5_0 = true
$.waiver_policy.no_style_debt_registry_in_v3_5_0 = true
$.waiver_policy.narrative_only_waiver_invalid = true
$.waiver_policy.required_waiver_fields
  = [rule_id, scope, reason_code, owner, evidence_ref, expires_at]
$.waiver_policy.expired_waivers_are_invalid = true

$.waiver_policy.notes
  - Waivers MUST be declared inside a decision artifact under '## Guard Exception'
    or an equivalent structured block
  - All six required_waiver_fields MUST be present
  - owner MUST reference a human reviewer or accountable maintainer (not an AI agent label)
  - evidence_ref MUST point to a verify artifact path under artifacts/verify/
  - expires_at MUST be present and enforceable
  - v3.5.0 explicitly forbids creating a standalone waiver registry or style debt registry
```

### 3.3 evidence-ref-policy.v3.5.3.json (TASK-1035)

```text
$.required_ref_contexts[?context_id=RRC-5]
  context_name = "waiver_evidence_ref"
  description  = "decision artifact ## Guard Exception with Exception Type=allow-scope-drift cites Scope Files; verify artifact must echo references to those waivered files"
  evidence_ref_required = true
  missing_behavior      = "fail"
  missing_reason_code   = "missing_paths"
```

### 3.4 golden-cli-coverage-matrix.v3.5.4.json (TASK-1036)

```text
$.golden_case_groups[?group_id=GCLI-QUALITY-SYNC]
  - GCLI-QUALITY-SYNC-005 "Drift covered by valid waiver -> reason_code=waivered_until:<date>; exit 0"
  - GCLI-QUALITY-SYNC-006 "Drift covered by expired waiver -> reason_code=waiver_invalid:expired:<date>; exit 1"
  - implementation_authorized=false (TASK-1036 planning-only)

$.cli_surfaces[?surface_id=CLI-QUALITY-GATES].observed_json_surfaces
  reason_code surface for QC-SYNC-001 includes:
    waivered_until:<date>
    waiver_invalid:<reasons>
    post_baseline_new_pair_waivered_until:<date>
    post_baseline_new_pair_waiver_invalid:<reasons>
```

### 3.5 Reconciliation

四源之 required field 集合一致（六欄）；AOM 之
`narrative_only_waiver_invalid=true` 與 quality-gate-policy 之
`expiration_enforcement.missing_required_field_is_blocking=true`
彼此一致。Evidence Ref policy 之 RRC-5 強化了 evidence_ref 必為
verify artifact 對 Scope Files 之回聲；當 verify 缺此回聲時，
PCACC-002 reason_code=missing_paths。

prototype 不放鬆任一既有約束；相反地，prototype 在六欄基礎上
增補四欄 lifecycle metadata（waiver_id / created_by_task /
created_at / status），以利未來 runtime 抽出時做 registry-level
索引、revocation 與 supersession。

---

## 4. Proposed waiver registry shape

prototype JSON top-level 共 16 個欄位：

```text
schema_version                                     -> "waiver-policy-registry-prototype/v1"
plan_version                                       -> "v3.5.7"
created_by_task                                    -> "TASK-1039"
generated_at                                       -> "2026-05-05T22:15:00+08:00"
prototype_status                                   -> "design_only"
runtime_consumption_authorized                     -> false
source_policy_refs                                 -> 14 條來源引用
waiver_surface                                     -> domain / consumed_by_checks_today / anchors / items_governed / items_explicitly_out_of_scope
existing_waiver_semantics_inventory                -> 四源 inventory
waiver_schema                                      -> required_fields(10) / optional_fields(7) / field_descriptions / schema_semantics(11)
waiver_lifecycle_states                            -> active / expired / revoked / superseded / invalid / advisory_only
expiration_policy                                  -> 11 條布林 + 比對策略
reason_code_policy                                 -> allowed_categories(6) / rejected_patterns(6) / qc_sync_001_runtime_reason_code_alignment
owner_policy                                       -> 7 條約束 + 拒絕 AI agent labels
evidence_ref_policy                                -> 與 evidence-ref-policy.v3.5.3.json 對齊 + RRC-5 alignment
scope_policy                                       -> 5 種 shape + matching semantics
validation_semantics                               -> 17 條 fail-closed + exit_code mapping + 9 條 registry_load_failure_reason_codes
interaction_notes                                  -> QC-SYNC / quality-gate / PCACC / Evidence Ref / golden CLI / future closure snapshots
future_runtime_extraction_acceptance_criteria      -> FE-1..FE-13
non_authorization                                  -> 41 條 false key
limitations                                        -> 12 條
```

設計選擇：

- **`prototype_status: "design_only"`** 為第一級可機讀標記；
  其值僅 `design_only` 一種。未來 runtime 抽出時須以另一個
  schema_version 之 registry file 取代，**不得**就地將此值改為
  `runtime_consumed`。
- **`runtime_consumption_authorized: false`** 為配套之第二級
  保護，亦為 prototype 之強約束；若有任一 runner 嘗試 load 時
  讀到 `false`，必須立即 fail-closed exit≠0。
- **prototype 落於 `artifacts/governance/prototypes/`** 而非
  `artifacts/governance/`，刻意將其與 quality-gate runner /
  PCACC runner 之候選 load 路徑隔離；EXACT_SYNC_FILES 不擴張、
  template mirror 不創建、quality baseline 不變更。
- **欄位列表採既有 policy 之忠實寫照 + 必要 lifecycle metadata**；
  不擴張為更鬆（如允許 reason_code=`unknown`），亦不縮限為更嚴
  （如取消 `path_scoped`）。任何擴張須由獨立 decision artifact
  授權。

---

## 5. Required waiver fields

prototype JSON `waiver_schema.required_fields` 共十欄：

| field | 來源 | 說明 |
|---|---|---|
| waiver_id | TASK-1039 新增 | 穩定 id；註冊表唯一；推薦樣式 `WAIVER-<plan-version>-<NNNN>` |
| rule_id | quality-gate / AOM | 目標規則 id；如 `QC-SYNC-001`、`AOM-009` |
| scope | quality-gate / AOM | 非空 list；shape 見 §11 |
| reason_code | quality-gate / AOM | 顯式分類；見 §8 |
| owner | quality-gate / AOM | 人類 reviewer / 可問責 maintainer，非 AI agent label |
| evidence_ref | quality-gate / AOM / Evidence Ref RRC-5 | 必落於 `artifacts/verify/`（或 Evidence Ref policy 允許之 prefix） |
| expires_at | quality-gate / AOM | YYYY-MM-DD；timezone 顯式或 normalized |
| created_by_task | TASK-1039 新增 | 撰寫 waiver 之 lifecycle TASK-XXXX |
| created_at | TASK-1039 新增 | ISO-8601 timestamp；Asia/Taipei +08:00 |
| status | TASK-1039 新增 | lifecycle state；見 §6 |

optional 七欄：`reviewer`、`notes`、`supersedes`、
`related_artifacts`、`revoked_at`、`revoked_by_task`、
`superseded_by_waiver_id`。

`schema_semantics` 共十一條布林，主要包含：

- `reject_unknown_fields=true`
- `missing_required_field_is_blocking=true`
- `missing_expires_at_is_blocking=true`
- `expired_is_blocking=true`
- `missing_reason_code_is_blocking=true`
- `missing_owner_is_blocking=true`
- `missing_evidence_ref_is_blocking=true`
- `scope_must_be_non_empty_list=true`
- `owner_must_be_non_empty_string=true`
- `evidence_ref_must_resolve_under_evidence_ref_policy=true`
- `narrative_only_waiver_invalid=true`

---

## 6. Waiver lifecycle states

六個 state：

| state_id | 描述 | may_suppress_blocking_finding | transitions_to |
|---|---|---|---|
| active | 在效；expires_at 未過；schema 通過 | true | expired / revoked / superseded |
| expired | expires_at 已過或等於今日（Asia/Taipei） | false | — |
| revoked | 後續 decision artifact 顯式撤銷；應記 revoked_at + revoked_by_task | false | — |
| superseded | 被另一 waiver 取代；應記 superseded_by_waiver_id | false | — |
| invalid | schema validation 失敗 | false | — |
| advisory_only | 套用於 advisory-only finding（如 QC-RUFF-001） | false | — |

transition 由後續 decision artifact 觸發；prototype 不允許
runtime 自動將 status 由 active 改為其他值（除了 expires_at
已過時自然推導為 expired）。

---

## 7. Expiration and invalidation policy

quality-gate-policy.v3.5.json 之 expiration_enforcement
為 prototype 之底線，prototype 不放鬆：

- `valid_future_expires_at_may_suppress_targeted_blocking_finding=true`
- `past_expires_at_is_blocking=true`
- `missing_expires_at_is_blocking=true`
- `malformed_expires_at_is_blocking=true`
- `expires_at_format = "YYYY-MM-DD with explicit timezone token or normalized to Asia/Taipei"`
- `comparison_strategy = lexicographic comparison against Asia/Taipei date`
- `timezone_must_be_explicit_or_normalized=true`
- `far_future_placeholder_dates_require_owner_and_evidence_justification=true`
- `far_future_threshold = "expires_at more than 365 days beyond created_at"`（advisory only；非 fail-closed）
- `extension_requires_new_decision_artifact=true`
- `expiration_check_runs_at_each_consumer_invocation=true`

**遠期 placeholder（如 9999-12-31）**：runtime 應拒絕或要求
強佐證（owner 顯式承諾 + evidence_ref 證實長期合理性）；
prototype 採保守策略，將其視為**advisory warning**，不直接
fail-closed，以利 transition_period 類別之合法使用。

---

## 8. Reason code policy

`reason_code_policy.allowed_categories` 共六：

| reason_code | 描述 |
|---|---|
| baseline_existing | TASK-1024 baseline 既存 drift；非 baseline 後新增；對齊 QC-SYNC-001 行為 (b) |
| approved_deferred_remediation | 緩解已核可但延遲；expires_at 須指向延遲到期 |
| external_dependency | 上游依賴限制；evidence_ref 或 related_artifacts 須含外部依賴引用 |
| tooling_limitation | 工具無法檢測或修復；expires_at 須指向工具修復到期 |
| transition_period | 計畫版本切換、runner sha drift 等已知過渡期；expires_at 指向過渡結束 |
| false_positive_with_evidence | 已驗證之 false positive；evidence_ref 須指向 false-positive 分析 |

`reason_code_policy.rejected_patterns` 共六：

| pattern | 描述 |
|---|---|
| empty | reason_code 為空字串或 null |
| generic | 泛用值（`misc` / `other`） |
| unknown | 字面值 `unknown` |
| todo | TODO 標記（`todo` / `FIXME` / `tbd`） |
| temporary_without_expiry | 宣稱暫時但未附 expires_at |
| because_model_said_so | 將理由歸於 AI agent 偏好；AI agent label 無權問責 |

`reason_code_policy.qc_sync_001_runtime_reason_code_alignment`
對齊 GCLI-QUALITY-SYNC-005/006：

```text
valid_active_unexpired                      -> waivered_until:<date>
expired                                     -> waiver_invalid:expired:<date>
missing_required_field                      -> waiver_invalid:missing_fields:<fields>
post_baseline_new_pair_valid_active         -> post_baseline_new_pair_waivered_until:<date>
post_baseline_new_pair_invalid              -> post_baseline_new_pair_waiver_invalid:<reasons>
```

此對齊**informative**（記錄 runtime 應產生之 reason_code 字面值），
**非 authoritative**（不授權任何 runner 改寫其 reason_code 表面）。

---

## 9. Owner and accountability policy

`owner_policy` 七條：

- `owner_must_be_non_empty_string=true`
- `owner_must_identify_accountable_role_or_task_authority=true`
- `owner_ai_agent_labels_rejected` 列舉 Claude / Codex / Gemini /
  claude-code / claude-opus-4-7 / claude-sonnet-4-6 /
  claude-haiku-4-5-20251001 / gpt 等
- `owner_canonical_human_set_reference =
  "owner SHOULD reference a canonical human reviewer; current
  canonical reviewer set is recorded at
  precommit-check-policy.v3.5.json#checks[?check_id=PCACC-003].canonical_reviewers"`
  （即 `arcobaleno`）
- `reviewer_optional_when_distinct_from_owner=true`
- `owner_must_match_a_real_human_or_role_at_task_creation=true`
- `owner_change_requires_new_waiver=true`

PCACC-003 之 canonical_reviewers 與 canonical_owners 集合
（`arcobaleno` / `Claude` / `Codex` / `Gemini`）同時也是
PCACC-003 之 owner-canonical 比對表面；**waiver owner**
與 **status owner** 為兩個不同欄位：

- status artifact 之 `current_owner` 可為 AI agent label
  （Claude / Codex / Gemini）以記錄當前執行 agent；
- waiver owner 必為人類問責對象，**不**得為 AI agent label。

此區分避免「AI agent 自簽 waiver」之 governance 風險。

---

## 10. Evidence Ref alignment

`evidence_ref_policy` 之每一條約束直接繼承自
`evidence-ref-policy.v3.5.3.json`：

- `evidence_ref_must_resolve_under_evidence_ref_policy_v3_5_3=true`
- `allowed_prefixes_inherited_from_evidence_ref_policy=true`
- `primary_allowed_prefix_for_waiver_evidence = "artifacts/verify/"`
- `remote_url_evidence_rejected_unless_future_policy_explicitly_authorizes=true`
- `absolute_path_rejected=true`、`windows_drive_letter_rejected=true`
- `parent_traversal_rejected=true`、`shell_token_rejected=true`
- `forbidden_root_directories` 含 `.obsidian` / `.omc` / `.tmp` /
  `.pytest-basetemp` / `__pycache__` / `.pytest_cache` /
  `node_modules` / `.venv` / `.git`
- `forbidden_url_schemes` 含 `http://` / `https://` / `ftp://` /
  `file://` / `ssh://` / `git://` / `git+ssh://`
- `evidence_ref_must_be_committed_or_task_authorized=true`

特別對齊 RRC-5：

> 當 waiver 目標為 scope-drift finding 時，verify artifact 必
> 回聲 decision artifact `## Guard Exception` 所引之 Scope
> Files；缺此回聲將以 reason_code=missing_paths 失敗（per
> evidence-ref-policy.v3.5.3.json#required_ref_contexts.RRC-5）。

prototype 不擴張 Evidence Ref 之 prefix 集合；任何擴張須由
獨立 decision artifact 授權，並同步更新 evidence-ref-policy
與本 prototype。

---

## 11. Scope matching policy

`scope_policy.allowed_scope_shapes` 五種：

| shape_id | 描述 |
|---|---|
| rule_id_scoped | scope 為單一 rule_id token（例：`QC-SYNC-001`） |
| path_scoped | scope 為非空 list 之 repo-relative paths |
| task_scoped | scope 為單一 TASK-XXXX id |
| artifact_scoped | scope 為單一 artifact ref（path 或 path#anchor） |
| pair_scoped | scope 為 source/template pair ref（baseline_id 或 sourcepath+templatepath） |

`scope_policy.matching_semantics`：

- `exact_match_preferred=true`
- `wildcard_only_scope_rejected=true`（禁止單一 `*` 或全萬用字元）
- `broad_repo_wide_waiver_rejected_by_default=true`
- `broad_repo_wide_waiver_requires_explicit_decision_artifact_override=true`
- `multi_scope_waiver_requires_explicit_justification=true`
- `scope_must_be_non_empty_list=true`
- `scope_path_normalization_rules` 對齊
  `evidence-ref-policy.v3.5.3.json#local_artifact_constraints`

廣域 waiver（rule_id 為 `*` 或 path 為 `repo-root`）為**反模式**；
prototype 預設拒絕，僅在 decision artifact 顯式指定 broad scope
override 時方可放行。

---

## 12. Validation semantics

`validation_semantics` 共十七條 fail-closed 約束 +
exit_code mapping + 九條 registry_load_failure_reason_codes。

關鍵：

- `fail_closed_on_malformed_registry=true`
- `fail_closed_on_schema_mismatch=true`
- `fail_closed_on_unknown_fields=true`
- `fail_closed_on_missing_required_field=true`
- `select_only_valid_active_unexpired_waivers=true`
- `expired_waiver_cannot_suppress_blocking_finding=true`
- `revoked_waiver_cannot_suppress_blocking_finding=true`
- `superseded_waiver_cannot_suppress_blocking_finding=true`
- `invalid_waiver_cannot_suppress_blocking_finding=true`
- `advisory_only_waiver_does_not_change_advisory_outcome=true`
- `waiver_scope_must_match_finding_target=true`
- `waiver_reason_code_must_be_explicit=true`
- `waiver_evidence_ref_must_resolve_under_evidence_ref_policy=true`
- `waiver_evaluation_is_deterministic=true`
- `silent_skip_forbidden=true`
- `fallback_to_in_module_default_forbidden=true`

`exit_code_mapping_if_runtime_consumed`：

```text
exit_code = 0  -> no blocking violation remains after applying valid active waivers
exit_code = 1  -> blocking violations remain after applying valid active waivers
exit_code = 2  -> registry load failure (missing / malformed / schema mismatch / forbidden pattern)
```

`registry_load_failure_reason_codes` 九條：

```text
waiver_registry_missing:<path>
waiver_registry_malformed_json
waiver_registry_schema_version_mismatch:<actual>
waiver_registry_missing_required_field:<field>
waiver_registry_unknown_enum_value:<field>=<value>
waiver_registry_forbidden_pattern:<pattern>
waiver_registry_invalid_local_artifact_constraint:<key>
waiver_registry_pair_uniqueness_violation:<waiver_id>
waiver_registry_qc_sync_001_conflict:<fixture>
```

最後一條（`waiver_registry_qc_sync_001_conflict:<fixture>`）對齊
TASK-1035 evidence-ref-policy 之
`evidence_ref_registry_pcacc_002_conflict` 模式：runtime 抽出
時若任一 fixture 之 reason_code 與 GCLI-QUALITY-SYNC-005/006
（或 TASK-1029 既有 fixture）不一致，立即 fail-closed。

---

## 13. Interaction with existing governance surfaces

| surface | interaction |
|---|---|
| QC-SYNC post-baseline drift | prototype 保留 GCLI-QUALITY-SYNC-005/006 之 reason_code 字面值；任何未來 runtime 抽出不得改寫 `waivered_until:<date>` 或 `waiver_invalid:expired:<date>` |
| quality gate policy | quality-gate-policy.v3.5.json 之 explicit_policy_waivers_array 為 default mode；任何 runtime 抽出須以 CLI flag 啟動（仿 TASK-1035 之 `--evidence-ref-policy` 模式），預設不變 |
| PCACC | PCACC active surface 維持 4 件（PCACC-001..004）；prototype 不引入 PCACC-005；PCACC-002 維持 Evidence Ref policy 為唯一外部 registry |
| Evidence Ref policy | waiver evidence_ref 必落於 evidence-ref-policy.v3.5.3.json 允許 prefix；RRC-5 強約束（waiver scope-drift verify 必 echo Scope Files） |
| golden CLI coverage | GCLI-QUALITY-SYNC-005/006 已於 TASK-1036 規劃但 implementation_authorized=false；任何 waiver runtime 抽出落地時必同期將其鎖定在新一輪 golden CLI coverage 擴張 lifecycle |
| future closure snapshots | 若有 v3.5.7+ closure snapshot，該 snapshot 應在 capabilities 中加入 `waiver_policy_registry_prototype` 並維持 `runtime_consumption_authorized=false` |

---

## 14. Future runtime extraction acceptance criteria

prototype JSON `future_runtime_extraction_acceptance_criteria`
列 FE-1..FE-13。摘要：

| id | 描述 | 對應證據要求 |
|---|---|---|
| FE-1 | runtime consumption gated 於 explicit CLI activation | 後續 task plan 加 CLI flag（如 `--waiver-registry <path>`），預設 unchanged |
| FE-2 | 預設行為不變（current explicit_policy_waivers_array 保留） | 後續 task verify 重跑 quality-gate baseline 無 flag，TASK-1029 fixture 仍 byte-identically pass |
| FE-3 | malformed registry exit_code=2；reason_code 對齊 9 條 registry_load_failure |
| FE-4 | 過期 waiver 為 blocking；reason_code=`waiver_invalid:expired:<date>` |
| FE-5 | 缺必填欄位為 blocking；reason_code=`waiver_invalid:missing_fields:<fields>` |
| FE-6 | 有效未過期 waiver 僅抑制目標 finding；其餘 finding 正常 |
| FE-7 | unknown 欄位 reject；reject_unknown_fields=true 落實 |
| FE-8 | Evidence Ref policy 套用於每一 evidence_ref；malformed 走 evidence-ref reason_code |
| FE-9 | Golden CLI cases 覆蓋 valid / expired / missing field / malformed / broad scope rejected；inherits TASK-1037 repair schema |
| FE-10 | production runner / template mirror sha256 prefix 重錨；保持 byte-identical 或經 baseline-refresh task |
| FE-11 | Codex post-commit PASS/FAIL verification 通過 |
| FE-12 | 不修改 TASK-1023..TASK-1039 任一 lifecycle artifact |
| FE-13 | PCACC active 仍 4 件；無 PCACC-005；AC-to-verify 仍 excluded |

FE-* 為**前提門檻**，非授權；本 task 不滿足任一 FE-* 即足以
使 runtime 抽出不被啟動，但本 task 之 PASS 並不等於授權執行
runtime 抽出。

---

## 15. Risks and limitations

DR-1：prototype 被誤讀為授權 runtime consumption。

- mitigation: `prototype_status="design_only"`、
  `runtime_consumption_authorized=false`、41 條 false
  `non_authorization`、設計文件多處顯式宣告。

DR-2：prototype JSON 被誤放至 `artifacts/governance/`（與
quality-gate-policy 並列），可能被誤掃為 runtime registry。

- mitigation: prototype 強制落於
  `artifacts/governance/prototypes/`；任何移動須由獨立
  decision artifact 授權；prototype 路徑名含 `prototype` 字面
  以利 grep 排除。

DR-3：prototype 之欄位集合與 quality-gate-policy / AOM
分歧。

- mitigation: §3 / §5 明列 four sources 之觀察值；
  `existing_waiver_semantics_inventory` 對 four sources 做
  byte-level reference；inspection helper 對 prototype 之
  `waiver_schema.required_fields` 與 quality-gate-policy
  `waiver_policy.schema.required_fields` 取交集確認；任何
  分歧由 inspection evidence 之 check 標 fail。

DR-4：未來 runtime 抽出時忽略 GCLI-QUALITY-SYNC-005/006 之
reason_code 字面值（如改為 `WAIVER_OK` 大寫）導致 backward
compat 破裂。

- mitigation: prototype 明列 reason_code 字面值（§8）；
  FE-2 + FE-9 共同守住；TASK-1029 既有 negative fixture 必跑於
  未來 runtime task verify。

DR-5：prototype 之 advisory_only state 被未來 runtime 不慎當成
silent skip 後門。

- mitigation: prototype 明文
  `advisory_only_waiver_does_not_change_advisory_outcome=true`；
  advisory_only state 之 `may_suppress_blocking_finding=false`；
  silent_skip_forbidden=true。

DR-6：未來 runtime 抽出落入 paired path
（artifacts/scripts/）但忘記擴 EXACT_SYNC_FILES 與 template
mirror。

- mitigation: FE-10 顯式要求；TASK-1029 NEG 模式之 negative
  test 為 FE-9 必要條件；EXACT_SYNC_FILES 擴張須由獨立
  decision artifact 授權。

DR-7：AI agent 自簽 waiver。

- mitigation: §9 owner_policy 拒絕所有 AI agent labels；
  `owner_must_match_a_real_human_or_role_at_task_creation=true`；
  `because_model_said_so` 為 reason_code rejected_patterns。

限制：

- 本 prototype 僅涵蓋 waiver 子域；其他 RC-A / RC-B / RC-C /
  RC-D / RC-F / RC-G / RC-H / RC-I 之 prototype 由 v3.6 後續
  lifecycle 處理。
- 本 prototype 對 verify artifact 之 `## Decision Refs` /
  `## Build Guarantee` / `## Acceptance Criteria Checklist`
  任一其他 section 不做 schema 約束。
- 本 prototype 不對 helper script invocation pattern 做約束。
- inspection evidence JSON 為**靜態 inspection** 結果；不含
  QC-SYNC-001 fixture rerun。
- GCLI-QUALITY-SYNC-005/006 之 implementation 仍為
  implementation_authorized=false；prototype 不能將其降為
  已鎖定。
- QB-DRIFT-0001 不被本 prototype 出 waiver；其
  baseline_existing 狀態自 v3.5.0 起延續，remediation deferred
  per TASK-1038 closure index。

---

## 16. Explicit non-authorization

This prototype is not consumed by production validators or runners.

This task does not authorize any production policy registry
extraction, runtime consumption, or runner attachment.

This task does not authorize validator split.

完整未授權清單見 prototype JSON 之 `non_authorization` 欄位
（41 條 false key）。摘要：

- TASK-1039 不授權 runtime consumption。
- TASK-1039 不授權修改 production runners
  (`run_precommit_check.py`, `run_quality_gates.py`) 或其
  template mirror。
- TASK-1039 不授權修改 5 件 production validator/test 檔
  (`guard_status_validator.py`, `guard_contract_validator.py`,
  `workflow_constants.py`, `run_red_team_suite.py`,
  `test_guard_units.py`) 任一檔或其 template mirror。
- TASK-1039 不授權修改 production governance policy
  (`precommit-check-policy.v3.5.json`,
  `quality-gate-policy.v3.5.json`,
  `quality-baseline.v3.5.json`,
  `artifact-obligation-matrix.v3.5.json`,
  `evidence-ref-policy.v3.5.3.json`)。
- TASK-1039 不授權修改 v3.5.x closure snapshot / closure index
  （TASK-1038 deliverables）。
- TASK-1039 不授權修改 golden CLI coverage matrix /
  expansion plan / harness / case manifest / result JSON。
- TASK-1039 不授權新增 PCACC-005 或任一 active PCACC check。
- TASK-1039 不授權啟用 AC-to-verify coverage。
- TASK-1039 不授權 quality baseline refresh。
- TASK-1039 不授權 QB-DRIFT-0001 remediation 或 waiver。
- TASK-1039 不授權 EXACT_SYNC_FILES 擴張。
- TASK-1039 不授權執行 validator module split。
- TASK-1039 不授權修改 v3.5 / v3.5.1 plan 與 manifest。
- TASK-1039 不授權修改 TASK-1023..TASK-1038 任一 lifecycle
  artifact（含 TASK-1037 repair evidence 與 TASK-1038 closure
  evidence）。
- TASK-1039 不授權創建 TASK-1040 及更後之 lifecycle artifact。
- TASK-1039 不授權執行 reasoning faithfulness audit /
  belief-state audit / model self-confidence audit /
  free-text rationale 添加 / SAVeR markdown report。
- TASK-1039 不授權生成 SRS / RTM / design spec / threat model /
  release note / migration note / user guide / runbook 任一
  **內容**。
- TASK-1039 不授權執行 ruff / mypy / pyright / coverage /
  pylint / bandit / safety / formatter / package manager
  任一執行。
- TASK-1039 不授權執行 pytest。
- TASK-1039 不授權執行 production runner 之 CLI 或 main()。

任何未來 runtime extraction implementation 須由獨立後續 task
顯式授權；本 prototype 之存在不構成授權。
