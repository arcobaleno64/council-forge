# Golden CLI Coverage Expansion Plan (v3.5.4)

> Plan version: v3.5.4
> Created by task: TASK-1036
> Plan status: planning_only
> Implementation authorized: false
> Generated at: 2026-05-05T00:45:00+08:00

## 1. Purpose

本計畫定義 v3.5.4 之 **golden CLI coverage expansion plan**：將 governance runners（PCACC runner `artifacts/scripts/run_precommit_check.py`、quality gate runner `artifacts/scripts/run_quality_gates.py`）之 CLI 介面行為**鎖入 future golden CLI tests 之驗收契約**，使 future runtime extraction、validator split、policy registry 擴張之任一動作不會在 CLI 邊界上靜默漂移。

本計畫**不**實作 golden tests、**不**修改 production runners、**不**修改 production validator/test 檔、**不**抽 registry、**不**拆 validator、**不**創建 TASK-1037 及更後 lifecycle artifacts。

實作授權須由獨立後續 task（候選 ID `TASK-1037`）顯式給出。

## 2. Inputs

本計畫之 read-only 輸入清單：

- [artifacts/scripts/run_precommit_check.py](../scripts/run_precommit_check.py)（PCACC runner，post-edit sha prefix=`4dbb8a219093cc12`）
- [template/artifacts/scripts/run_precommit_check.py](../../template/artifacts/scripts/run_precommit_check.py)（mirror，byte-identical）
- [artifacts/scripts/run_quality_gates.py](../scripts/run_quality_gates.py)（quality gate runner，sha prefix=`456b8328482b18a5`）
- [template/artifacts/scripts/run_quality_gates.py](../../template/artifacts/scripts/run_quality_gates.py)（mirror，byte-identical）
- [artifacts/governance/precommit-check-policy.v3.5.json](precommit-check-policy.v3.5.json)（PCACC policy，sha prefix=`66ea7c53837ff034`）
- [artifacts/governance/quality-gate-policy.v3.5.json](quality-gate-policy.v3.5.json)（quality gate policy，sha prefix=`479154c353e0178b`）
- [artifacts/governance/quality-baseline.v3.5.json](quality-baseline.v3.5.json)（quality baseline，sha prefix=`0d8a05f39d31e6f7`）
- [artifacts/governance/evidence-ref-policy.v3.5.3.json](evidence-ref-policy.v3.5.3.json)（Evidence Ref policy registry，sha prefix=`0ca80e7eae09a25a`，schema_version=`evidence-ref-policy/v1`）
- [artifacts/verify/TASK-1035/evidence-ref-runtime-extraction-result.json](../verify/TASK-1035/evidence-ref-runtime-extraction-result.json)（runtime extraction 16/16 pass）
- [artifacts/verify/TASK-1035/registry-regression-result.json](../verify/TASK-1035/registry-regression-result.json)（registry regression 11/11 pass）
- [artifacts/verify/TASK-1030/pcacc-negative-test-result.json](../verify/TASK-1030/pcacc-negative-test-result.json)（PCACC NEG-002 / NEG-003 backward compat 錨點）

machine-readable 對偶：[artifacts/governance/golden-cli-coverage-matrix.v3.5.4.json](golden-cli-coverage-matrix.v3.5.4.json)。

## 3. Current CLI surfaces

採 read-only 靜態檢視，僅羅列**已觀察**之 CLI surface；不進行 broad runner execution。

### 3.1 CLI-PRECOMMIT — `artifacts/scripts/run_precommit_check.py`

| 屬性 | 觀察值 |
|---|---|
| path | `artifacts/scripts/run_precommit_check.py` |
| exists | true |
| observed_cli_options | `--task <TASK-ID>` / `--policy <path>` / `--evidence-ref-policy <path>` / `--format json` / `--self-check` / `--output <path>` |
| observed_output_modes | (a) stdout JSON `precommit-check-result/v1`（`--self-check` 或無 `--output`）；(b) stdout JSON `{output_written, overall_status}`（`--output` 設定時）；(c) stdout JSON `{error, ...}`（invocation 失敗） |
| observed_exit_code_semantics | `0`=overall_status=pass；`1`=至少一條 PCACC 檢查 fail；`2`=invocation error（`repo_root_detection_failed` / `policy_not_found` / `policy_invalid` / `invalid_task_id` / `evidence_ref_registry_load_failed`） |
| observed_json_surfaces | `result.schema_version=precommit-check-result/v1`；`result.task_id` / `generated_at`(Taipei ISO) / `self_check` / `policy_ref` / `overall_status` / `checks[]` / `limitations[]`；`checks[].check_id ∈ {PCACC-001..004}`；`checks[].status ∈ {pass, fail, skipped_with_reason_code}`；`checks[].reason_code` 含 `lifecycle_complete` / `lifecycle_missing:<kinds>` / `evidence_refs_resolved` / `evidence_refs_section_empty` / `evidence_refs_section_absent` / `missing_paths:<refs>` / `malformed_refs:<tokens>` / `evidence_refs_optional_per_orc_<id>` / `owner_and_reviewer_canonical` / `non_canonical:<fields>` / `review_after_evidence` / `review_equal_to_evidence_not_strictly_after` / `review_before_evidence` / `no_review_or_evidence_timestamp` / `no_review_timestamp` / `no_evidence_generated_at` / `verify_artifact_missing` / `status_or_task_missing` / `canonical_registry_missing_in_policy` / `status_parse_error`；registry-load 失敗 envelope `{error: evidence_ref_registry_load_failed, reason_code, detail, path}` |
| coverage_priority | high |
| known_limitations | runner 直讀磁碟 policy / registry，CLI 啟動須穩定 working directory；PCACC-004 timestamp 比較依 Taipei ISO 字串，fixture 須注入 deterministic timestamps；ORC marker 為子字串比對（`evidence_refs_optional_per_orc_<id>`），契約包含字面 |

### 3.2 CLI-QUALITY-GATES — `artifacts/scripts/run_quality_gates.py`

| 屬性 | 觀察值 |
|---|---|
| path | `artifacts/scripts/run_quality_gates.py` |
| exists | true |
| observed_cli_options | `--baseline <path>` / `--policy <path>` / `--format json` / `--self-check` / `--output <path>` |
| observed_output_modes | (a) stdout JSON `quality-gate-result/v1`；(b) stdout JSON `{output_written, overall_status}`；(c) stdout JSON `{error, ...}`（`baseline_not_found` / `policy_not_found` / `repo_root_detection_failed`） |
| observed_exit_code_semantics | `0`=overall_status=pass；`1`=至少一條 gate fail；`2`=invocation error |
| observed_json_surfaces | `result.schema_version=quality-gate-result/v1`；`result.task_id`（TASK-1025 lineage） / `generated_at` / `self_check` / `baseline_ref` / `policy_ref` / `overall_status` / `checks[]` / `limitations[]`；`checks[].gate_id ∈ {QC-SYNC-001, QC-SCHEMA-001, QC-IMPORT-001, QC-GOLDEN-001, QC-RUFF-001}`；`checks[].status ∈ {pass, fail, skipped_with_reason_code, advisory}`；reason_code 詳見 matrix JSON `cli_surfaces[CLI-QUALITY-GATES].observed_json_surfaces` |
| coverage_priority | high |
| known_limitations | QC-IMPORT-001 用 subprocess 執行 `python -S -B -c`，fixture 須以 `PYTHONDONTWRITEBYTECODE=1` 防止 `__pycache__` 污染；QC-SYNC-001 結果取決於 fixture 之 source/template 對偶 sha256，須採 synthetic 樹避免耦合 live runner sha；QC-RUFF-001 永遠 status=advisory，從不 driving exit |

### 3.3 額外 advisory candidate

未涵蓋之 CLI surface（如 `artifacts/scripts/guard_status_validator.py` / `guard_contract_validator.py` / `run_red_team_suite.py`）為 governance validator/test 檔，本計畫**不**將其納入 v3.5.4 golden CLI coverage 範疇；若未來欲覆蓋，須由獨立 lifecycle 任務啟動。

## 4. Coverage gaps

依 matrix JSON `coverage_gaps` 列舉，每條對應一條 GAP-* ID：

| gap_id | surface | description | risk | blocks_future_refactor |
|---|---|---|---|---|
| GAP-PCACC-DEFAULT-OUTPUT | CLI-PRECOMMIT | default success path stdout JSON 未鎖入 | high | true |
| GAP-PCACC-FAIL-OUTPUT | CLI-PRECOMMIT | 失敗路徑 stdout 與 exit_code=1 未鎖入 | high | true |
| GAP-PCACC-EVREF-DEFAULT | CLI-PRECOMMIT | TASK-1030 NEG-002 / NEG-003 anchor 在 CLI 邊界未鎖入 | high | true |
| GAP-PCACC-EVREF-EXPLICIT | CLI-PRECOMMIT | `--evidence-ref-policy` registry-mode 行為（valid local / ORC skip / 禁止模式）未鎖入 | high | true |
| GAP-PCACC-EVREF-LOAD-FAIL | CLI-PRECOMMIT | registry-load 失敗 fail-closed envelope 未鎖入 | high | true |
| GAP-PCACC-INVOCATION | CLI-PRECOMMIT | invocation-error envelopes 未鎖入 | medium | false |
| GAP-QUALITY-SYNC | CLI-QUALITY-GATES | QC-SYNC-001 reason_code 全 surface 未鎖入 | high | true |
| GAP-QUALITY-SCHEMA | CLI-QUALITY-GATES | QC-SCHEMA-001 reason_code surface 未鎖入 | high | true |
| GAP-QUALITY-IMPORT | CLI-QUALITY-GATES | QC-IMPORT-001 import-clean / first-cycle-advisory / fail 未鎖入；subprocess pycache hygiene 亦未對外鎖定 | medium | true |
| GAP-QUALITY-GOLDEN | CLI-QUALITY-GATES | QC-GOLDEN-001 deferred capture_policy 契約未鎖入 | medium | false |
| GAP-QUALITY-RUFF-ADVISORY | CLI-QUALITY-GATES | QC-RUFF-001 advisory-only 契約未鎖入 | low | false |
| GAP-QUALITY-WAIVER-EXPIRY | CLI-QUALITY-GATES | waiver expiration / shape-invalid 行為未鎖入 | medium | false |

## 5. Proposed golden CLI case groups

本計畫提出 9 條 group ID（與 matrix JSON 嚴對齊）：

| group_id | surface | purpose（簡述）|
|---|---|---|
| GCLI-PRECOMMIT-DEFAULT | CLI-PRECOMMIT | 鎖死 default 成功路徑 |
| GCLI-PRECOMMIT-EVREF | CLI-PRECOMMIT | 鎖死 `--evidence-ref-policy` registry-mode 行為 |
| GCLI-PRECOMMIT-FAILCLOSED | CLI-PRECOMMIT | 鎖死 registry-load 失敗 envelope |
| GCLI-PRECOMMIT-LIFECYCLE | CLI-PRECOMMIT | 鎖死 PCACC-001 / 003 / 004 失敗路徑 |
| GCLI-QUALITY-SYNC | CLI-QUALITY-GATES | 鎖死 QC-SYNC-001 reason_code surface |
| GCLI-QUALITY-SCHEMA | CLI-QUALITY-GATES | 鎖死 QC-SCHEMA-001 reason_code surface |
| GCLI-QUALITY-IMPORT | CLI-QUALITY-GATES | 鎖死 QC-IMPORT-001 三種 outcome + pycache hygiene |
| GCLI-QUALITY-GOLDEN | CLI-QUALITY-GATES | 鎖死 QC-GOLDEN-001 deferred-capture 契約 |
| GCLI-QUALITY-RUFF-ADVISORY | CLI-QUALITY-GATES | 鎖死 QC-RUFF-001 advisory-only 契約 |

每 group 之 `planned_cases` / `expected_contracts` / `fixture_requirements` 詳見 matrix JSON 對應條目。所有 group 之 `implementation_authorized` 皆為 `false`；本計畫**不**實作。

## 6. run_precommit_check.py coverage plan

涵蓋 4 個 group（GCLI-PRECOMMIT-DEFAULT / EVREF / FAILCLOSED / LIFECYCLE），共 18 條 planned case。

關鍵錨點：

- **default 成功路徑**：synthetic compliant lifecycle bundle 跑出 `overall_status=pass`、4 條 `PCACC-*` reason_code 全 stable literal、exit 0、stderr empty。
- **`--evidence-ref-policy` 顯式啟動**：EVREF-001 valid local 解析、EVREF-002 ORC-1 skip、EVREF-003 forbidden URL 模式、EVREF-004 parent traversal、EVREF-005/006 default mode TASK-1030 NEG-002/003 anchor。
- **fail-closed envelope**：FAILCLOSED-001..004 對應 `evidence_ref_registry_missing` / `_malformed_json` / `_schema_version_mismatch` / `_pcacc_002_conflict`，全 exit 2 + stable JSON envelope `{error, reason_code, detail, path}`。
- **lifecycle 失敗路徑**：LIFECYCLE-001..005 涵蓋 `lifecycle_missing:verify` / `non_canonical:<fields>` / `review_equal_to_evidence_not_strictly_after` / `review_before_evidence` / `invalid_task_id`。

## 7. run_quality_gates.py coverage plan

涵蓋 5 個 group（GCLI-QUALITY-SYNC / SCHEMA / IMPORT / GOLDEN / RUFF-ADVISORY），共 18 條 planned case。

關鍵錨點：

- **QC-SYNC-001**：6 case 分別錨定 `in_sync` / `baseline_existing` / `post_baseline_new_pair_in_sync` / `post_baseline_new_pair_drift` / `waivered_until:<date>` / `waiver_invalid:expired:<date>`。
- **QC-SCHEMA-001**：4 case 錨定 `schema_and_keys_ok` / `schema_version_mismatch` / `missing_required_keys` / `json_parse_error`。
- **QC-IMPORT-001**：4 case 錨定 `import_clean` / `import_error_when_expected_clean` / `first_cycle_observation_dirty_import`(advisory) + post-run `__pycache__` 0 hits。
- **QC-GOLDEN-001**：2 case 錨定 `post_task_evidence_only_capture_deferred`(skipped_with_reason_code) 與 `unsafe_capture_policy:<value>`(fail)。
- **QC-RUFF-001**：2 case 錨定 advisory-only 契約（has config 與 no config 兩種 fixture 皆 status=advisory、reason_code=`advisory_only_in_v3.5.0`、never blocking）。

## 8. Evidence Ref policy coverage after TASK-1035

GCLI-PRECOMMIT-EVREF + GCLI-PRECOMMIT-FAILCLOSED 共 10 條 planned case，配合 default mode 之 EVREF-005/006，覆蓋 prompt §8.6 列舉之**全部 9 種未來 golden case 行為**：

1. `no registry path → default behavior unchanged` — EVREF-005 / EVREF-006（default mode 對 NEG-002 / NEG-003 fixture 之字面 reason_code 嚴等）。
2. `valid registry path → registry accepted` — EVREF-001（valid local artifact ref resolves）。
3. `missing explicit registry → fail closed` — FAILCLOSED-001（reason_code=`evidence_ref_registry_missing`）。
4. `malformed registry JSON → fail closed` — FAILCLOSED-002（reason_code=`evidence_ref_registry_malformed_json`）。
5. `schema-invalid registry → fail closed` — FAILCLOSED-003（reason_code=`evidence_ref_registry_schema_version_mismatch`）。
6. `policy conflict → fail closed` — FAILCLOSED-004（reason_code=`evidence_ref_registry_pcacc_002_conflict`）。
7. `invalid Evidence Ref patterns rejected` — EVREF-003（forbidden URL scheme）+ EVREF-004（parent traversal）。
8. `optional missing Evidence Ref with reason code skipped` — EVREF-002（ORC-1 marker → skipped_with_reason_code）。
9. `optional missing Evidence Ref without reason code fails` — EVREF-006（default mode）+ 內含於 EVREF group registry-mode 對應 case（empty section without ORC marker → fail with `evidence_refs_section_empty`）。

backward compat 硬性錨：default mode 對 TASK-1030 NEG-002 / NEG-003 之 reason_code（`malformed_refs:garbage_token_not_a_known_prefix` 與 `evidence_refs_section_empty`）必須**字面嚴等**；任一漂移即破壞契約並 block future implementation。

## 9. Output contract expectations

### 9.1 preferred contracts

- 穩定 schema_version literal（`precommit-check-result/v1`、`quality-gate-result/v1`）。
- 穩定 check_id / gate_id set（PCACC-001..004；QC-SYNC-001 / QC-SCHEMA-001 / QC-IMPORT-001 / QC-GOLDEN-001 / QC-RUFF-001）。
- 穩定 status enum（`pass` / `fail` / `skipped_with_reason_code` + `advisory` for QC-IMPORT-001 / QC-RUFF-001）。
- 穩定 reason_code literal 或 prefix（templated 用 prefix，例：`malformed_refs:<token>`、`waivered_until:<date>`）。
- 穩定 exit_code（0 / 1 / 2）。
- stderr 預設 empty；非 empty 須 case-level 顯式 justification。
- post-run `__pycache__` 與 `*.pyc` 0 hits。

### 9.2 rejected contracts

- 全 stdout byte-equality（會被 Taipei timestamp、JSON key 排序、fixture-local path interpolation 打掉）。
- 對絕對路徑或 actual filesystem 位置 byte 比對。
- 對 `actual` free-form descriptor（含 counts / stderr tails）byte 比對。

### 9.3 exit_code、stdout、stderr、JSON、reason_code、cache 策略

詳見 matrix JSON `output_contract_strategy`：

- `exit_code_strategy`：兩 runner 之 0 / 1 / 2 語意嚴對齊。
- `stdout_strategy`：JSON-only stdout；future 改動不得引入 stray prints；測試以 `json.loads(stdout)` 解析後做 subset 對欄位比對。
- `stderr_strategy`：兩 runner 預設 empty。
- `json_strategy`：subset 比對；`generated_at` 永遠排除；`actual` 字串若含 counts / path 預設排除。
- `reason_code_strategy`：穩定 reason_code 採 exact literal；templated reason_code 採 prefix。
- `cache_strategy`：測試 runner 設 `PYTHONDONTWRITEBYTECODE=1`；post-run 比對 fixture root + project root 無 `__pycache__` / `*.pyc` 新增。

## 10. Fixture strategy

- **fixture root**：`artifacts/verify/TASK-1037/fixtures/`（依 future implementation lifecycle 命名；若實際 task ID 不為 TASK-1037 須由 implementation 任務 re-map）。
- **synthetic task ID pattern**：`TASK-9XXXX`（避開 `TASK-{1000..1099}` 與 `TASK-{900..999}` 既有區段）。
- **無 production artifact mutation**：fixtures 落於 fixture tree；`--policy` / `--baseline` / `--evidence-ref-policy` 必須指向 fixture tree 內之副本。
- **fixture repo root**：synthetic 包含 `consilium-fabri-governance-repair-plan-v3.5.md` sentinel + `artifacts/governance/` + `template/`，使 `detect_repo_root()` 成立；或直接 monkeypatch `detect_repo_root()`。
- **policy override**：fixture-local `precommit-check-policy.v3.5.json` / `quality-gate-policy.v3.5.json` / `quality-baseline.v3.5.json` 為 controlled 副本；production policy 在測試中**永不**被消費。
- **registry override**：`--evidence-ref-policy` 指向 fixture-local `evidence-ref-policy.v3.5.3.json` 副本；controlled malformed registries 落於 fixture 內，**不**落於 `artifacts/governance/`。
- **timestamp**：deterministic Taipei ISO 8601；runner 自產之 `generated_at` 永遠排除於 byte lock。
- **forbidden fixture locations**：`.obsidian` / `.omc` / `.tmp` / `.pytest-basetemp` / `__pycache__` / `.pytest_cache` 任一目錄皆**不**寫入。

## 11. No-cache and no-pycache execution requirements

- driver 採標準庫 only（`unittest` 或簡易腳本）；driver 第二行設 `sys.dont_write_bytecode = True`。
- subprocess 啟動兩 runner 時環境必含 `PYTHONDONTWRITEBYTECODE=1` 與 `-B`。
- 不得使用 `pytest`、`ruff`、formatter、package manager。
- post-run 須對 fixture repo root + project root + `artifacts/verify/TASK-1037/` 全域 sweep `find -name __pycache__ -o -name '*.pyc'`，必為 0 hits；任一條 hit 即測試 fail。
- 不得依賴 `.pytest-basetemp` / `.tmp` / `.omc` / `.obsidian` 任一暫存目錄。

## 12. Future TASK-1037 acceptance criteria

每條 criterion 對應 matrix JSON `future_task_acceptance_criteria` 中之 FTA-1..FTA-11，且 `current_status` 為 `not_satisfied`（FTA-1 / FTA-2 / FTA-3 / FTA-4 / FTA-5 / FTA-8 / FTA-10 / FTA-11）或 `satisfied`（FTA-6 / FTA-7 / FTA-9）：

| ID | 描述（簡）| 當前狀態 |
|---|---|---|
| FTA-1 | golden CLI test artifacts 僅落於 TASK-1037 lifecycle | not_satisfied |
| FTA-2 | future implementation 不修改兩 runner 與其 mirror（sha256 不變）| not_satisfied |
| FTA-3 | 採標準庫 only；無 pytest / 第三方斷言庫 / package install | not_satisfied |
| FTA-4 | 無 `__pycache__` / `*.pyc` 產生 | not_satisfied |
| FTA-5 | 兩 runner 之 CLI 啟動採 subprocess + 顯式 fixture-local `--policy` / `--baseline` / `--evidence-ref-policy` 路徑 | not_satisfied |
| FTA-6 | 保留 PCACC default mode 對 TASK-1030 NEG-002 / NEG-003 reason_code 字面嚴等 | satisfied |
| FTA-7 | 保留 Evidence Ref registry-mode 行為（forbidden patterns、ORC skip、fail-closed exit 2 envelope） | satisfied |
| FTA-8 | 涵蓋 QC-SYNC-001 / SCHEMA-001 / IMPORT-001 / GOLDEN-001 之 pass / fail / advisory / skipped_with_reason_code surface；QC-RUFF-001 advisory 契約獨立鎖 | not_satisfied |
| FTA-9 | 不引入 PCACC-005、不啟用 AC-to-verify coverage、不拆 validator、不抽新 registry | satisfied |
| FTA-10 | future implementation 之 result evidence 落於 `artifacts/verify/TASK-1037/` 內 | not_satisfied |
| FTA-11 | Codex post-commit verification 通過 | not_satisfied |

## 13. Risks and limitations

- **靜態檢視限制**：本計畫之 reason_code surface 由 read-only 靜態檢視 runner source 取得（PCACC sha=`4dbb8a219093cc12`、quality sha=`456b8328482b18a5`）；future runner 編輯後須由獨立任務刷新。
- **runner sha 漂移**：兩 runner 任一檔在 future task 中被改動即觸發 baseline 漂移，此計畫之 expected_reason_codes 須重新比對。
- **ORC marker 子字串依賴**：GCLI-PRECOMMIT-EVREF-002 採 substring `evidence_refs_optional_per_orc_<id>`；若未來改 marker 為結構化 heading，runner 與本 group 同時須 re-anchor。
- **subprocess hygiene**：GCLI-QUALITY-IMPORT 依賴 Python interpreter 之 subprocess 行為；未來 Python release（如 default site-packages 行為改動）可能要求 fixture 更新。
- **QC-RUFF-001 advisory 鎖定**：本計畫僅鎖 advisory；若 v3.6 將 ruff 升 blocking，須由獨立 decision 啟動新 group。
- **fixture root 未來 ID**：`artifacts/verify/TASK-1037/fixtures/` 為 placeholder；若 future implementation lifecycle 之實際 task ID 不為 TASK-1037，須由 implementation 任務 re-map。
- **未列舉之 reason_code**：matrix `coverage_gaps` 與 `golden_case_groups` 為 best-effort 列舉；某些經過特殊 fixture 才能命中之 reason_code 可能未涵蓋；future 任務發現遺漏時須擴充 matrix。
- **不保證 future implementation 必通過**：本計畫僅列出**須鎖定**之內容與**如何鎖定**，不對 future implementation 之結果做承諾。
- **PCACC 主動 surface 變更耦合**：若 future task 新增 PCACC active check，須由同一 lifecycle 同步擴充本 matrix；本計畫**不**為此預留接口。

## 14. Explicit non-authorization

TASK-1036 does not authorize golden CLI test implementation.

TASK-1036 does not authorize production runner modification.

TASK-1036 does not authorize validator split.

TASK-1036 does not authorize production validator/test modification.

TASK-1036 does not authorize new policy registry extraction.

TASK-1036 does not authorize TASK-1037+ execution.

TASK-1036 does not authorize creation of TASK-1037 or any later lifecycle artifact.

TASK-1036 does not authorize modification of `artifacts/scripts/run_precommit_check.py` or its template mirror.

TASK-1036 does not authorize modification of `artifacts/scripts/run_quality_gates.py` or its template mirror.

TASK-1036 does not authorize modification of `artifacts/scripts/guard_status_validator.py`、`guard_contract_validator.py`、`workflow_constants.py`、`run_red_team_suite.py`、`test_guard_units.py` 任一檔或其 template mirror。

TASK-1036 does not authorize modification of `artifacts/governance/precommit-check-policy.v3.5.json`、`quality-gate-policy.v3.5.json`、`quality-baseline.v3.5.json`、`artifact-obligation-matrix.v3.5.json`、`evidence-ref-policy.v3.5.3.json` 任一 governance policy。

TASK-1036 does not authorize modification of v3.5 plan / v3.5 manifest / v3.5.1 plan / v3.5.1 manifest / TASK-1023..TASK-1035 任一 lifecycle artifact。

TASK-1036 does not authorize introduction of PCACC-005 or any new active PCACC check.

TASK-1036 does not authorize activation of AC-to-verify coverage.

TASK-1036 does not authorize ruff / mypy / pyright / coverage / pylint / bandit / safety / formatter / package manager 之執行。

TASK-1036 does not authorize pytest 執行。

TASK-1036 does not authorize broad runner execution（兩 runner 之 CLI 在 planning 階段不執行）。

TASK-1036 does not authorize SRS / RTM / design spec / threat model / release note / migration note / user guide / runbook 之內容生成。

TASK-1036 does not authorize Bootstrap Prompt Skill modification、`.obsidian/` / `.omc/` / `.tmp/` / `.pytest-basetemp/` 之修改。

TASK-1036 does not authorize quality baseline refresh、QB-DRIFT-0001 remediation 或 waiver 簽發。

TASK-1036 does not authorize EXACT_SYNC_FILES 擴張。

TASK-1036 does not authorize global model-brand-to-role binding 或 assurance_level taxonomy 加入 `high`。
