# 驗證指令

## 核心驗證

| 指令 | 用途 |
|---|---|
| `python artifacts/scripts/guard_status_validator.py --task-id TASK-XXX` | 驗證任務狀態、產物與 scope drift |
| `python artifacts/scripts/guard_status_validator.py --task-id TASK-XXX --auto-classify` | 自動判定任務為 lightweight 或 full-gate |
| `python artifacts/scripts/guard_contract_validator.py --audit-raci <file> <agent>` | RACI auditor v2 稽核（針對單檔對某 agent） |
| `python artifacts/scripts/guard_contract_validator.py` | 驗證 root ↔ template ↔ Obsidian 同步 |
| `python artifacts/scripts/guard_contract_validator.py --check-readme` | 驗證 README 結構與雙語合規性 |
| `python artifacts/scripts/prompt_regression_validator.py --root .` | 執行 prompt regression 測例 |
| `python artifacts/scripts/validate_context_stack.py` | 驗證分層式上下文堆疊 |
| `python artifacts/scripts/run_quality_gates.py` | 執行 baseline-aware P0 quality gate（QC-SYNC/SCHEMA/IMPORT/GOLDEN/RUFF） |
| `python artifacts/scripts/migrate_artifact_schema.py --input-mode external-legacy --root .` | 匯入外部 legacy artifacts（預設 root-tracked 嚴格模式；非結構化 verify 降級為 manual-review／deferred） |

## 下游 generator 與散播

| 指令 | 用途 |
|---|---|
| `python artifacts/scripts/scaffold_downstream.py --target <dir> --project-name <name> --repo-name <repo> --project-summary "<summary>" --owner <org>` | 從 template 產生新下游專案（greenfield） |
| `python artifacts/scripts/scaffold_downstream.py --retrofit --target <dir> --project-name <name> --repo-name <repo> --project-summary "<summary>" --owner <org>` | 於既有 repo 疊加治理（additive、僅補缺檔） |
| `python artifacts/scripts/drift_dashboard.py --downstream <name>=<path>` | 回報 template 與下游之 drift（唯讀） |
| `python artifacts/scripts/propagate_downstream.py --downstream <name>=<path> --apply` | 將下游自有檔刷新對齊 template（預設 dry-run） |

## 安全與供應鏈 gate

| 指令 | 用途 |
|---|---|
| `python artifacts/scripts/repo_security_scan.py --root . secrets` | repo-local 高信心 secrets 掃描 |
| `python artifacts/scripts/repo_security_scan.py --root . static` | 聚焦式靜態 control-plane 規則 |
| `python artifacts/scripts/ssdf_mapping_validator.py --mapping docs/ssdf-mapping.md` | 檢查 NIST SSDF（SP 800-218 v1.1）對應完整性（非 conformance 認證） |
| `python artifacts/scripts/sca_gate.py dotnet --json <scan.json>` | fail-closed 軟體成分分析（SCA）gate |
| `python artifacts/scripts/sast_gate.py --sarif <results.sarif>` | 諮詢式靜態應用安全測試（SAST）gate |
| `python artifacts/scripts/sbom_gate.py --sbom <bom.json>` | 驗證 CycloneDX 軟體物料清單（SBOM） |
| `python artifacts/scripts/security_txt_gate.py --file <security.txt>` | RFC 9116 security.txt gate |
| `python artifacts/scripts/release_gate.py --format checksums --file <manifest.json>` | 發布完整性 gate（搭配 `snapshot_manifest.py`） |

## 紅隊、儀表板與發布

| 指令 | 用途 |
|---|---|
| `python artifacts/scripts/run_red_team_suite.py --phase all` | 執行完整紅隊演練 |
| `python artifacts/scripts/run_red_team_suite.py --phase prompt` | 透過報表流程執行 prompt regression |
| `python artifacts/scripts/repo_health_dashboard.py` | 產生儲存庫健康儀表板 |
| `python artifacts/scripts/ssdf_conformance_dashboard.py` | SSDF conformance 儀表板 |
| `python artifacts/scripts/standards_backaudit_dashboard.py` | 標準回溯稽核儀表板 |
| `python artifacts/scripts/build_decision_registry.py --root .` | 重建決策登錄冊 |
| `python artifacts/scripts/update_repository_profile.py` | 更新 GitHub 儲存庫 profile |
| `pwsh artifacts/scripts/push-wiki.ps1` | 推送 wiki/ 到 GitHub Wiki（含 preflight） |
| `pwsh artifacts/scripts/publish-release.ps1 -Tag v0.4.0` | 建立 GitHub Release（含 preflight） |

## Guard Status Validator

`guard_status_validator.py` 負責驗證：

- 任務狀態轉換是否合法
- 必要 artifacts 是否存在且 metadata 完整
- Scope drift 檢測（Files Changed ⊆ Files Likely Affected）
- Build Guarantee 是否到位

### Scope Drift 處理

- **預設行為**: scope drift 視為 hard fail
- **Dirty worktree**: 直接比對實際 git changed files
- **Clean task**: 可用 `commit-range` evidence 重放 historical diff
- **Git objects 遺失**: 改用 `archive fallback`（Archive Path / Archive SHA256）
- **GitHub PR**: 透過 GitHub PR files API 重建 changed files
- **`--allow-scope-drift`**: 僅在附顯式 decision waiver 時可用，且只能降級真正的 drift

## Guard Contract Validator

`guard_contract_validator.py` 負責驗證：

- root ↔ template 檔案同步（5 層 Tier 分級）
- Obsidian 入口同步
- README 結構合規性（`--check-readme` 模式）
- Prompt regression cases 與 agent 入口檔一致性
- Bootstrap 規則

### 同步 Tier 分級

| Tier | 策略 | 內容 |
|---|---|---|
| Tier 1 | Exact Sync | AGENTS.md、BOOTSTRAP_PROMPT.md、docs/*.md、guard scripts |
| Tier 2 | Placeholder-Generalized | CLAUDE.md |
| Tier 3 | Phrase-Checked | OBSIDIAN.md、README 系列 |
| Tier 4 | Manual Sync | .gitignore、requirements.txt、workflows |
| Tier 5 | Project-Specific | artifacts/tasks、decisions、.env |

## 紅隊演練

- **Runbook**: `docs/red_team_runbook.md`
- **評分矩陣**: `docs/red_team_scorecard.md`
- **補強清單**: `docs/red_team_backlog.md`
- **重跑指令**: `python artifacts/scripts/run_red_team_suite.py --phase all`

## Prompt Regression

固定測例位於 `artifacts/scripts/drills/prompt_regression_cases.json`，涵蓋：

- artifact-only truth/completion
- workflow sync completeness
- Gemini blocked preconditions
- Codex summary discipline
- conflict-to-decision routing
- decision schema integrity
- external failure STOP
- decision-gated scope waiver
- historical diff evidence contract
- pinned diff evidence integrity
- GitHub provider-backed diff evidence
- archive retention fallback contract
