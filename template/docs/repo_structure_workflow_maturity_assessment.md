# Repo 結構與工作流成熟度評估

> **版本**: v2.3 | **評估日期**: 2026-04-17 | **評估基準**: commit (pending)

## 評估範圍

本報告根據目前 repo 內可見結構、自動化驗證工具實際執行結果、以及 `repo_health_dashboard.py` 的即時資料進行評估。主要依據如下：

**結構與規範文件**：
- `README.md`、`README.zh-TW.md`、`AGENTS.md`、`BOOTSTRAP_PROMPT.md`、`OBSIDIAN.md`
- `docs/orchestration.md`、`docs/artifact_schema.md`、`docs/workflow_state_machine.md`
- `docs/subagent_roles.md`、`docs/lightweight_mode_rules.md`、`docs/subagent_task_templates.md`
- `docs/red_team_runbook.md`、`docs/red_team_scorecard.md`、`docs/red_team_backlog.md`

**自動化驗證（即時執行）**：
- `artifacts/scripts/guard_status_validator.py` — 狀態守衛
- `artifacts/scripts/guard_contract_validator.py` — 合約守衛 ✅ PASS
- `artifacts/scripts/validate_context_stack.py` — 上下文堆疊守衛 ✅ PASS（v2.0 時曾有 24 errors，已全數修復）
- `artifacts/scripts/repo_health_dashboard.py` — Repo Health Dashboard（即時 JSON）
- `.github/workflows/workflow-guards.yml` — CI pipeline（10 步驟）
- `.github/workflows/security-scan.yml` — pip-audit 依賴掃描（v2.1 新增）

**執行痕跡**：
- 18 個 task（含 TASK-001 至 TASK-999）、58 commits、2 release tags（v0.3.0、v0.3.1）
- 9 個 GitHub Skills、2 個 custom agents、9 頁 wiki

## 一、Repo 結構概覽

此 repo 不是以應用程式原始碼為中心，而是以 **workflow framework 與 governance artifacts** 為中心。

| 區塊 | 主要內容 | 角色 |
|---|---|---|
| 根目錄 | `README*`、`AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`CODEX.md`、`BOOTSTRAP_PROMPT.md`、`OBSIDIAN.md` | 專案入口、agent 入口、bootstrap 指引 |
| `docs/` | orchestration、schema、state machine、premortem、red team、lightweight mode（13 檔） | 流程規範與制度文件 |
| `docs/templates/` | `implementer/`、`tester/`、`verifier/`、`reviewer/`、`parallel/`、`blocking/` | subagent 任務模板 |
| `artifacts/` | `tasks/`(19)、`research/`(10)、`plans/`(15)、`code/`(13)、`verify/`(13)、`status/`(21)、`decisions/`(11)、`improvement/`(3)、`scripts/`(18)、`red_team/`(1) | 流程執行痕跡與自動化腳本 |
| `.github/` | `workflows/`(2)、`agents/`(2)、`skills/`(9)、`prompts/`(5)、`memory-bank/`(5)、`copilot-instructions.md`、`dependabot.yml` | CI、agent 定義、上下文系統、依賴更新 |
| `template/` | root 的 scaffold 鏡像（文件 + 骨架 artifacts） | 新專案 bootstrap 範本 |
| `wiki/` | 9 頁 GitHub Wiki 內容 | 對外文件 |
| `external/` | `hermes-agent/`（git submodule，大型 Python/CLI 專案） | 外部依賴 |
| `.obsidian/` | vault 設定 | Obsidian 文件工作區整合 |

從結構上看，repo 已明確區分出 **四個層次**：

1. **規則層**：`docs/`、`AGENTS.md`、各 agent 入口檔。
2. **執行層**：`artifacts/` 與 validator / red-team scripts。
3. **上下文層**：`.github/memory-bank/`、`.github/prompts/`、`.github/skills/`、`.github/agents/`。
4. **發佈層**：`README*`、`.github/`、`template/`、`wiki/`、`OBSIDIAN.md`。

相較 v1.x 評估，新增的「上下文層」是 v0.3.0 引入的重要結構升級。

## 二、工作流機制盤點

目前 repo 內的工作流能力已從「文件宣告」全面升級為「可驗證的執行系統」。

| 能力 | 證據 | 狀態 | 評語 |
|---|---|---|---|
| Artifact-first | `docs/orchestration.md`、`docs/artifact_schema.md`、`artifacts/*` | ✅ | 18 個 task、100+ artifacts 的實際留痕 |
| 狀態機管理 | `docs/workflow_state_machine.md` | ✅ | 8 狀態 + 合法轉移規則，guard 強制執行 |
| 角色分工 | `docs/subagent_roles.md`、`CLAUDE.md`、`GEMINI.md`、`CODEX.md` | ✅ | 主控、研究、實作三角分工 |
| Gate 驗證 | `guard_status_validator.py`（動態掃描全部 task） | ✅ | CI 自動檢查每一個 TASK-*.status.json |
| Contract drift 防護 | `guard_contract_validator.py` | ✅ | root / template 核心文件同步守衛 |
| Prompt regression | `prompt_regression_validator.py` + `drills/prompt_regression_cases.json` | ✅ | Prompt 視為可回歸測試的資產 |
| 上下文堆疊 | `validate_context_stack.py`（7 項檢查） | ✅ | v2.0 曾有 24 errors（template/skills 同步缺口），v2.1 已全數修復 |
| Red-team | `run_red_team_suite.py`（23 static + 2 live + 20 prompt） | ✅ | 完整演練機制含 scorecard |
| Repo Health Dashboard | `repo_health_dashboard.py`（`--json` / `--stale-days`） | ✅ | 即時全域 task coverage、stale、blocked aging |
| Lightweight mode | `docs/lightweight_mode_rules.md` | ✅ | 效率與治理平衡 |
| Template discovery | `discover_templates.py`、`docs/templates/` | ✅ | 模板可發現化 |
| Custom agents | `.github/agents/`（Autonomous Executor、Readonly Process Auditor） | ✅ NEW | 可重用的 agent 人格定義 |
| GitHub Skills | `.github/skills/`（9 個 skill） | ✅ NEW | 可組合的專業能力模組 |
| Wiki | `wiki/`（9 頁）+ `push-wiki.ps1` | ✅ NEW | 對外文件化，含自動推送機制（v2.1 改用 preflight + dynamic URL） |
| Supply-chain hardening | `dependabot.yml`、`security-scan.yml`、SHA-pinned actions | ✅ NEW | Dependabot 自動 PR、pip-audit CI 掃描、Actions SHA pin（v6.0.2/v6.2.0）|
| Release automation | `publish-release.ps1`、`github_publish_common.ps1` | ✅ NEW | gh CLI 發佈腳本含 preflight 檢查，與 push-wiki.ps1 共用認證模組 |
| Lightweight mode | `docs/lightweight_mode_rules.md` | ✅ | v2.1 新增 drafted→planned 轉移、釐清 verify artifact 不可省略 |
| KPI 追蹤 | `artifacts/metrics/kpi_sprint2.json`、`artifacts/metrics/kpi_sprint6.json` | ✅ NEW | 跨 sprint 效能與品質指標 |
| Decision Registry | `build_decision_registry.py` → `artifacts/registry/decision_registry.json` | ✅ | 決策可追溯 |

### 即時 Dashboard 摘要（2026-04-17T12:01:16+08:00）

| 指標 | 數值 |
|---|---|
| 總 Task 數 | 18 |
| 完成率 | 77.8%（14 done） |
| Blocked | 1（TASK-901，已歸檔） |
| Stale（>14 天） | 0 |
| 缺 Verify（有 code 但無 verify） | 0 |
| 進行中（researched / planned / research_ready） | 3（TASK-959, 962, 999） |

### Artifact Coverage（即時）

| 類型 | 覆蓋 | 缺口 |
|---|---:|---|
| task | 100% | — |
| status | 100% | — |
| plan | 83.3% | TASK-959, 962 未進入 planning |
| code | 77.8% | 正常——未到 coding 階段的 task 不需要 |
| verify | 77.8% | 與 code 1:1 對應，符合預期 |
| research | 55.6% | 部分 lightweight task 可跳過 research |
| decision | 55.6% | 非必要 artifact，僅在有重大決策時產生 |
| improvement | 16.7% | 僅在 Gate E 失敗或主動改善時產生 |

## 三、成熟度評估

本報告以 5 級制評估（CMM-inspired）：

- Level 1: Initial — 無固定流程
- Level 2: Repeatable — 有流程但依賴個人經驗
- Level 3: Defined — 流程已文件化且標準化
- Level 4: Managed — 流程有量化監控與自動執行
- Level 5: Optimizing — 持續改善循環已制度化

### 3.1 Repo 結構成熟度

| 維度 | v1.2 | v2.0 | 判斷 |
|---|---:|---:|---|
| 目錄分層 | 4 | 4.5 | 三層→四層（新增上下文層：agents、skills、prompts、memory-bank） |
| 文件入口清晰度 | 4 | 4.5 | 新增 wiki 9 頁 + 階段載入矩陣已成熟 |
| 範本化程度 | 5 | 5 | `template/` 完整鏡像 + contract guard 護欄 |
| 可發現性 | 4 | 4 | 文件量持續增長（13 docs + 9 skills + 5 prompts），仍需載入矩陣導航 |
| 工作樹衛生 | 4 | 4 | `.gitignore` 完善，無殘留暫存目錄 |
| 上下文系統 | — | 4 | NEW：memory-bank（5 檔）、prompts（5 檔）、skills（9 個）、agents（2 個），含自動化驗證 |
| 對外文件 | — | 4 | NEW：wiki 9 頁 + push-wiki.ps1 自動推送 |

**Repo 結構整體評級：Level 4+ / Managed**

結構已高度模組化，支援 bootstrap、同步驗證、上下文分層載入、與對外文件化。主要短板是文件量大，新手需要學習導航路徑。

### 3.2 工作流成熟度

| 維度 | v1.2 | v2.0 | 判斷 |
|---|---:|---:|---|
| 流程定義完整度 | 5 | 5 | Intake 到 Closure、blocked 與 Gate E 都有制度 |
| Artifact schema 完整度 | 5 | 5 | 8 類 artifact、欄位、狀態與品質要求完整 |
| 自動化驗證 | 4.5 | 5 | 新增 context stack validator（7 項檢查）、CI 10+1 步驟全涵蓋（v2.1 新增 security-scan workflow） |
| 實際採用程度 | 4 | 4.5 | 18 tasks × 多 artifact type = 100+ artifacts，橫跨 58 commits |
| CI 整合廣度 | 4.5 | 5 | 2 個 workflow：workflow-guards（10 步驟）+ security-scan（pip-audit）。Actions SHA-pinned + Dependabot 自動 bump |
| 治理閉環能力 | 4 | 4.5 | blocked → improvement → resume 的 PDCA + decision registry + KPI sprint tracking |
| 持續最佳化能力 | 4.5 | 5 | red-team/backlog/prompt regression + repo health dashboard + KPI sprint 追蹤（S2→S6 效能改善 -47.8ms） |
| 上下文管理 | — | 4 | NEW：分層式上下文（memory-bank / prompts / skills / agents），validator 自動檢查完整性與 cross-ref |
| 外部協作支援 | — | 3.5 | NEW：wiki、custom agents、skills，但尚無 contributor guide 或 onboarding automation |

**工作流整體評級：Level 4.5 / Managed（接近 Level 5 Optimizing）**

相比 v1.2，CI pipeline 從 7 步驟擴展到 10 步驟，新增 context stack validation、KPI sprint tracking，工作流已具備量化改善的閉環。

## 四、主要優勢

1. **制度完整且分層合理**
   - `orchestration`、`artifact schema`、`state machine`、`subagent roles` 各自負責不同層次，沒有全部塞進單一大文件。
   - v2.0 新增上下文層（memory-bank / prompts / skills / agents），進一步將「知識」從「流程」中分離。

2. **規範已被程式化**
   - 6 支 validator（status guard、contract guard、prompt regression、context stack、red team suite、repo health dashboard）代表核心規則已從文件走向執行。
   - CI pipeline 10 步驟全自動，無人工 gate。

3. **Template 與 root 同步有護欄**
   - `template/` 作為 bootstrap scaffold 很完整，contract guard 檢查 drift。
   - `docs/orchestration.md` §9.6 已定義 Tier 1-5 同步責任邊界。

4. **重視失敗演練，而不只正向流程**
   - 內建 red-team runbook（23 static + 2 live + 20 prompt drill），scorecard、backlog 完整。
   - KPI sprint tracking（S2→S6）提供跨時間的量化改善證據。

5. **已有真實運作痕跡**
   - 18 個 task、100+ artifacts、54 commits、2 release tags。
   - 完成率 72.2%，0 stale、0 missing verify，表示流程不是紙上制度。

6. **上下文系統已制度化** *(v2.0 新增)*
   - memory-bank 5 檔（artifact-rules、workflow-gates、prompt-patterns、project-facts、README）。
   - 9 個可組合 skills（security-review、quality-playbook、code-tour、agent-governance 等）。
   - 2 個 custom agents（Autonomous Executor、Readonly Process Auditor）。
   - `validate_context_stack.py` 自動驗證 cross-ref 完整性、frontmatter 合法性、名稱唯一性。

7. **對外文件已建立** *(v2.0 新增)*
   - Wiki 9 頁，含 Getting Started、Workflow Overview、Artifact Schema、Agent Roles、Validator Commands、Context System、FAQ。
   - `push-wiki.ps1` 支援自動推送。

## 五、主要風險與缺口

### 現存風險（v2.0 新發現）

| # | 風險 | 嚴重度 | 說明 |
|---|---|---|---|
| ~~R1~~ | ~~template/skills 同步大幅落後~~ | ~~High~~ | ✅ **v2.1 已修復**：37 個 reference files 已同步至 `template/.github/skills/`，`validate_context_stack.py` 全數通過 |
| ~~R2~~ | ~~wiki Context-System 頁面空殼~~ | ~~Medium~~ | ✅ **v2.1 已修復**：新增 7 項檢查清單、Skills & Agents 層、正式驗證腳本路徑 |
| R3 | **單一 owner 風險** | Medium | 全部 18 task 的 owner 都是 Claude，無人類 reviewer 或第二 agent 參與。對真實多人團隊的可轉移性尚未被驗證。 |
| ~~R4~~ | ~~TASK-001 孤兒~~ | ~~Low~~ | ✅ **v2.1 已解決**：PR #1 關閉未合併，TASK-001 artifacts 不存在於 master，dashboard 未回報 |
| ~~R5~~ | ~~Coverage threshold 偏低~~ | ~~Low~~ | ✅ **已修復**：目前 validate coverage gate 為 100%，13 個 Python 模組 / 3118 stmts / 959 tests 全數 100%。 |
| ~~R6~~ | ~~外部依賴管理~~ | ~~Low~~ | ✅ **v2.1 已修復**：TASK-963 已完成 supply-chain hardening — Actions SHA pin（checkout v6.0.2、setup-python v6.2.0）、`dependabot.yml` 自動 PR、`security-scan.yml` pip-audit CI 掃描 |

### 已解決風險（v1.x → v2.0 期間）

| # | 原始風險 | 解決方式 |
|---|---|---|
| ~~R1~~ | CI 驗證覆蓋偏樣板化 | ✅ CI 已改為動態掃描 `TASK-*.status.json` |
| ~~R2~~ | 工作樹衛生不足 | ✅ `.gitignore` 已補齊所有暫存目錄 |
| ~~R3~~ | 文件存在局部一致性風險 | ✅ BOOTSTRAP_PROMPT.md 已對齊 subagent_roles.md |
| ~~R4~~ | Template 完整鏡像維護成本高 | ✅ orchestration.md §9.6 Tier 1-5 同步責任邊界 |
| ~~R5~~ | 治理指標以文件與單次驗證為主 | ✅ repo_health_dashboard.py + KPI sprint tracking |

## 六、整體判斷

### 總結評級

| 維度 | v1.0 | v1.2 | v2.0 | v2.1 | 趨勢 |
|---|---:|---:|---:|---:|---|
| Repo 結構成熟度 | 4.0 | 4.0 | **4.3** | **4.5** | ↑ supply-chain + template/skills 全同步 |
| 工作流成熟度 | 4.0 | 4.5 | **4.7** | **4.8** | ↑ 2 workflow CI + dependabot + drafted→planned |
| Code Review 綜合 | 4.0 | 4.5 | 4.5 | 4.5 | → 維持（見§八） |
| **綜合** | **4.0** | **4.3** | **4.5** | **4.6** | **Level 4.5+ / Managed → Optimizing** |

### 判斷摘要

這個 repo 是一套**成熟度高於多數內部工具、接近 Level 5 Optimizing** 的 workflow framework。

**已具備的關鍵特徵**：
- ✅ 結構四層分離（規則、執行、上下文、發佈）
- ✅ 100% 的 task / status artifact 覆蓋
- ✅ 10 步驟全自動 CI pipeline（零人工 gate）
- ✅ 量化改善循環（KPI S2→S6：驗證速度改善 47.8ms、FP rate 0%）
- ✅ 紅隊演練機制（45 項 drill）
- ✅ 上下文分層管理（memory-bank / prompts / skills / agents）
- ✅ 對外文件（wiki 9 頁 + 雙語 README）
- ✅ 真實採用痕跡（18 tasks、54 commits、2 releases）

**尚缺的 Level 5 要素**：
- ✅ ~~template/skills 同步自動化~~ — v2.1 已完成（37 檔同步 + validator 全 PASS）
- ✅ ~~Supply-chain hardening~~ — TASK-963 done（SHA pin + dependabot + pip-audit + release scripts）
- ⬜ 多 owner / 多人協作驗證
- ✅ ~~Coverage target 從 45% → 100%~~ — 已達成 100%（13 個模組 / 3118 stmts / 959 tests）
- ⬜ Contributor onboarding automation

## 七、建議優先事項

### 立即行動（High Priority）

| # | 行動 | 對應風險 | 預期效果 |
|---|---|---|---|
| ~~1~~ | ~~同步 `template/.github/skills/` 與 root~~ | ~~R1~~ | ✅ 已完成（37 檔同步，validator 全 PASS） |
| ~~2~~ | ~~補建 `TASK-001.status.json` 或將 TASK-001 歸檔移除~~ | ~~R4~~ | ✅ 已解決（PR #1 關閉，artifacts 不存在於 master） |

### 短期改善（Medium Priority）

| # | 行動 | 對應風險 | 預期效果 |
|---|---|---|---|
| ~~3~~ | ~~實作 TASK-963（supply-chain hardening：pin actions、pip-audit、release automation）~~ | ~~R6~~ | ✅ 已完成（TASK-963 done，CI security-scan 全綠） |
| 4 | ~~提升 unit test coverage threshold 至 80%~~ | ~~R5~~ | ✅ 已完成（51%→83%，410 tests，threshold 80%） |
| 5 | ~~審查 wiki `Context-System.md` 內容是否對齊 `validate_context_stack.py` 的 7 項檢查~~ | ~~R2~~ | ✅ 已完成（新增 7 項檢查清單 + Skills & Agents 層） |

### 中期規劃（Low Priority）

| # | 行動 | 對應風險 | 預期效果 |
|---|---|---|---|
| 6 | 建立 contributor onboarding script 或 tour（可用 code-tour skill） | R3 | 降低多人協作門檻 |
| 7 | 增加第二 owner 或 human reviewer 的 artifact 案例 | R3 | 驗證多人場景可行性 |
| 8 | PowerShell wrapper 加入 `-ErrorAction Stop` | — | 捕獲非 terminating error |

---

## 八、Code Review：代碼品質、安全性與可維護性

### 8.0 總覽

本次 code review 涵蓋 `artifacts/scripts/` 下的所有 Python 與 PowerShell 腳本。

| 腳本 | 行數（約） | 角色 |
|---|---:|---|
| `guard_status_validator.py` | ~1850 | 核心：artifact / state / scope drift / premortem / Gate E 驗證 |
| `guard_contract_validator.py` | ~300 | root ↔ template 同步守護 |
| `run_red_team_suite.py` | ~800+ | 23 static + 2 live + 20 prompt 紅隊演練 |
| `validate_context_stack.py` | ~350 | 上下文系統完整性驗證（7 項檢查） |
| `repo_health_dashboard.py` | ~200 | 全域 task / artifact 健康指標 |
| `prompt_regression_validator.py` | ~180 | prompt 回歸測試引擎 |
| `build_decision_registry.py` | ~250 | decision artifact → JSON registry |
| `aggregate_red_team_scorecard.py` | ~110 | red-team report → 計分卡 |
| `discover_templates.py` | ~100 | subagent 範本發現 |
| `update_repository_profile.py` | ~90 | `.github/repository-profile.json` 管理 |
| `validate_scorecard_deltas.py` | ~90 | reviewer delta 驗證 |
| `workflow_constants.py` | ~50 | 共用常數 |
| `test_guard_units.py` | ~8400 | validator / runner 單元與回歸測試主體 |
| `test_security_scans.py` | ~160 | `repo_security_scan.py` 的 secrets / static 回歸測試 |
| `Invoke-CodexAgent.ps1` | ~120 | Codex CLI resilient wrapper |
| `Invoke-GeminiAgent.ps1` | ~120 | Gemini CLI resilient wrapper |
| `load_env.ps1` | ~12 | `.env` 載入 |
| `push-wiki.ps1` | ~80 | wiki 推送（v2.1 改用 preflight + dynamic URL） |
| `github_publish_common.ps1` | ~100 | 共用認證 / preflight helper（v2.1 新增） |
| `publish-release.ps1` | ~100 | GitHub Release 發佈腳本（v2.1 新增） |

### 8.1 代碼品質

#### 優點

1. **結構清晰，職責分離**
   - 每支腳本都有明確的單一職責，沒有 god script。
   - `guard_status_validator.py` 雖然最長（~1850 行），但內部以 `validate_*`、`detect_*`、`parse_*` 系列函式組織，可讀性仍在合理範圍。

2. **型別標註完整**
   - 所有 Python 腳本均使用 `from __future__ import annotations` 與 `typing` 模組。
   - 資料結構以 `@dataclass` 定義，語義清楚。

3. **常數集中管理**
   - 狀態機規則（`LEGAL_TRANSITIONS`）、artifact marker（`MARKERS`）、premortem 規則等全部以常數表定義在檔案頂部，便於審查與維護。

4. **錯誤處理一致**
   - 統一使用 `GuardError` exception 與 `ValidationResult(errors, warnings)` 模式。
   - CLI exit code 嚴格區分：0 = pass、1 = fail、2 = usage error。

5. **PowerShell wrapper 設計合理**
   - `Invoke-CodexAgent.ps1` 與 `Invoke-GeminiAgent.ps1` 實作了 exponential backoff + model fallback 的多層韌性機制。

#### 可改進項目

| # | 類別 | 位置 | 說明 | 嚴重度 |
|---|---|---|---|---|
| Q1 | 複雜度 | `guard_status_validator.py` | 單檔約 1850 行。函式拆分尚可，但 `validate_artifact_presence()` 與 `detect_historical_diff_scope_drift()` 已偏長（各 ~80 行），可考慮拆成更小的子函式。 | Low |
| Q2 | ~~重複定義~~ | `guard_contract_validator.py` + `update_repository_profile.py` | ~~`REQUIRED_TOPICS` 與 `TOPIC_PATTERN` 在兩個檔案中重複定義。~~ **已解決** — 已提取共用常數至 `_shared_constants.py`。 | ~~Medium~~ ✅ |
| Q3 | 重複函式 | `guard_status_validator.py` + `run_red_team_suite.py` | `compute_snapshot_sha256()` 在兩個檔案中都有定義，簽章略有不同（一個接受 `Set[str]`，一個接受 `Sequence[str]`）。 | Low |
| Q4 | 硬編碼 | `run_red_team_suite.py` | `blocked_sample_source()` 硬編碼檢查 `TASK-902` / `TASK-901`，未來新增或移除 sample task 時容易遺漏。 | Low |
| Q5 | ~~缺少單元測試~~ | 全局 | ~~目前只有 red-team suite 作為 integration test。~~ **已解決** — `test_guard_units.py` 與 `test_security_scans.py` 合計 959 項 tests，覆蓋 validator、runner 與 repo security scan 的核心邊界；目前 coverage 100%，CI 以 `--cov-fail-under=100` 強制執行。 | ~~Medium~~ ✅ |

### 8.2 安全性

#### 優點

1. **GitHub API 呼叫安全**
   - `collect_github_pr_files()` 使用 `urllib.parse.quote()` 做 URL 編碼，避免 injection。
   - token 從環境變數讀取（`GITHUB_TOKEN` / `GH_TOKEN`），不硬編碼。
   - API 版本 header 明確指定，降低不可預期行為。

2. **路徑穿越防護**
   - `resolve_workspace_relative_path()` 明確檢查路徑不得以 `/`、`..` 開頭，且 resolve 後的路徑必須在 repo root 內（`relative_to()` 驗證）。

3. **JSON 解析安全**
   - 所有 `json.loads()` 呼叫都有 `try/except json.JSONDecodeError` 處理。

4. **沒有 shell injection 風險**
   - `subprocess.run()` 均使用 list 形式傳參，不走 `shell=True`。

#### 風險項目

| # | 類別 | 位置 | 說明 | 嚴重度 |
|---|---|---|---|---|
| S1 | 敏感資訊洩漏 | `load_env.ps1` | `.env` 載入後使用 `Write-Host "Loaded: $varName"` 輸出變數名稱。雖然只輸出 key 不輸出 value，但在 CI log 中仍可能洩漏內部環境變數的名稱清單。 | Low |
| S2 | HTTP server 綁定 | `run_red_team_suite.py` | `github_pr_files_server()` 綁定 `127.0.0.1:0`（動態 port），僅用於短暫測試 fixture。安全設計合理，但無 request body size 限制、無超時設定。因為只用於本地測試且生命週期極短，實際風險很低。 | Low |
| S3 | archive 讀取 | `guard_status_validator.py` | `load_archive_snapshot()` 讀取使用者指定路徑的檔案內容。雖有路徑穿越防護（`resolve_workspace_relative_path`），但若 archive 檔案極大，可能造成記憶體壓力。缺少 file size 上限檢查。 | Low |
| S4 | temp 目錄殘留 | `run_red_team_suite.py` | `prepare_temp_root()` 使用 `.codex-red-team/` 且 `finally` 中呼叫 `shutil.rmtree()`，但 Windows 上若檔案被鎖定可能殘留（git status 已可見 permission denied 的 `.codex-red-team/` 和 `.tmp-red-team/`）。 | Low |

### 8.3 可維護性

#### 優點

1. **CLI interface 統一**
   - 所有 main 腳本都使用 `argparse`，參數一致（`--root`、`--task-id`），學習成本低。

2. **Markdown 報告輸出標準化**
   - `run_red_team_suite.py`、`aggregate_red_team_scorecard.py`、`prompt_regression_validator.py` 的輸出都是可機器解析的 markdown 表格。

3. **`discover_templates.py` 支援 JSON 輸出**
   - 方便自動化工具消費，不限於人工閱讀。

4. **版本標記**
   - `guard_status_validator.py` 有 `__version__`，有利於追蹤。

#### 可改進項目

| # | 類別 | 位置 | 說明 | 嚴重度 |
|---|---|---|---|---|
| M1 | ~~.gitignore 缺漏~~ | `.gitignore` | ~~缺少 `.codex-red-team/`、`.tmp-red-team/`、`*.override_log.json` 等工作流產出。~~ **已解決** — `.gitignore` 已補齊所有工作流暫存目錄與 coverage 產出。 | ~~Medium~~ ✅ |
| M2 | PyYAML 依賴 | `discover_templates.py` | 唯一有外部依賴（`yaml`）的腳本，且在 import 失敗時直接 `sys.exit(1)`。其他腳本全部 stdlib only，這個依賴可能在 CI 或新環境上造成意外失敗。 | Low |
| M3 | ~~CI 覆蓋不足~~ | `.github/workflows/workflow-guards.yml` | ~~Status guard 只跑 TASK-900、TASK-950、TASK-951。~~ **已解決** — 已改為動態掃描 `artifacts/status/TASK-*.status.json`，覆蓋全部 task，並移除 `--allow-scope-drift` 啟用嚴格模式。 | ~~Medium~~ ✅ |
| M4 | ~~無 requirements.txt~~ | 全局 | ~~Python 腳本沒有 `requirements.txt`。~~ **已解決** — 已建立 `requirements.txt`（含 PyYAML pin），CI 可自動安裝。 | ~~Low~~ ✅ |
| M5 | PowerShell 無 -ErrorAction | `Invoke-*.ps1` | try/catch 可捕獲 terminating error，但非 terminating error（如 cmdlet warning）不會被攔截。 | Low |

### 8.4 綜合評分

| 維度 | v1.0 | v1.2 | v2.0 | 摘要 |
|---|---:|---:|---:|---|
| 代碼品質 | 4 | 4.5 | 4.5 | 維持。新增 `validate_context_stack.py`（350 行）、`repo_health_dashboard.py`（200 行），代碼品質一致。 |
| 安全性 | 4.5 | 4.5 | 4.5 | 維持。路徑穿越、shell injection、API token 處理均到位。 |
| 可維護性 | 3.5 | 4.5 | 4.5 | 維持。CI 10 步驟、requirements.txt、共用常數均穩定。 |
| **綜合** | **4** | **4.5** | **4.5** | **生產等級的 workflow toolchain。新增腳本品質一致，無退步。** |

### 8.5 建議行動優先順序

| 優先 | 行動 | 狀態 | 效果 |
|---:|---|---|---|
| 1 | ~~補 `.gitignore` 條目~~ | ✅ 已完成 | git status 噪音消除 |
| 2 | ~~CI status guard 改為動態掃描~~ | ✅ 已完成 | CI 治理覆蓋 3 → 18 task |
| 3 | ~~提取共用常數~~ | ✅ 已完成 | `workflow_constants.py` 消除重複定義 |
| 4 | ~~加入 `requirements.txt`~~ | ✅ 已完成 | CI 可自動安裝依賴 |
| 5 | ~~為核心函式加 unit test~~ | ✅ 已完成 | 959 項 tests，coverage 100% |

### 8.6 剩餘改進項目

| 優先 | 行動 | 效果 |
|---:|---|---|
| 1 | ~~對齊 `BOOTSTRAP_PROMPT.md` 與 `docs/subagent_roles.md` 的 Gemini/Codex 認證指引~~ ✅ 已完成 | 降低新使用者 onboarding 摩擦 |
| 2 | 維持 unit test coverage 100%（新增模組時同步補測試） | 強化回歸保護並避免 validate 退化 |
| 3 | PowerShell wrapper 加入 `-ErrorAction Stop` | 捕獲非 terminating error |
| 4 | ~~制定 `template/` 同步責任邊界說明~~ ✅ 已完成 | `docs/orchestration.md` §9.6 Tier 1–5 定義 |
| 5 | ~~將 `validate_context_stack.py` 的 template/skills 檢查結果降為 warning 或修正同步~~ ✅ 已完成 | 37 檔同步，errors 24→0 |

---

## 九、v2.0 → v2.1 變更摘要（本次 session）

### v2.1 新增/修復能力

| 能力 | 來源 | 影響 |
|---|---|---|
| Supply-chain hardening | TASK-963: `dependabot.yml`、`security-scan.yml`、SHA pin | 自動化依賴更新 + pip-audit CI 掃描 |
| Release automation | `publish-release.ps1`、`github_publish_common.ps1` | gh CLI 發佈腳本含 preflight 與 -WhatIf |
| Wiki preflight 改造 | `push-wiki.ps1` 重寫 + `github_publish_common.ps1` 共用 | Dynamic URL、5 階段 preflight、不再硬編碼 repo URL |
| Dependabot auto-bump | `actions/checkout` v4.3.1→v6.0.2、`setup-python` v5.6.0→v6.2.0 | Dependabot PR #3/#4 自動建立並合併 |
| template/skills 同步修復 | 37 個 reference files 同步至 `template/.github/skills/` | context stack errors 24→0 |
| drafted→planned 轉移 | `guard_status_validator.py` + `workflow_state_machine.md` + `lightweight_mode_rules.md` | Lightweight mode 現可直接 drafted→planned |
| Verify artifact 釐清 | `lightweight_mode_rules.md` | 釐清 verify artifact 不可省略（內容可精簡，文件不可缺） |
| CI pip-audit 修正 | `security-scan.yml`：`pip-audit` → `pip_audit` 模組名 | Security Scan workflow 修復 |
| 孤兒 gitlink 清理 | `.claude/worktrees/` 移除 + `.gitignore` 防護 | CI checkout 修復 |

---

## 十、v1.x → v2.0 變更摘要

### 新增能力

| 能力 | 來源 | 影響 |
|---|---|---|
| 上下文堆疊驗證 | `validate_context_stack.py`（7 項檢查） | CI 新增 context stack validation 步驟 |
| Custom Agents | `.github/agents/`（2 個 agent 定義） | 可重用的 agent 人格與工具邊界 |
| GitHub Skills | `.github/skills/`（9 個 skill） | 可組合的專業能力模組 |
| Wiki | `wiki/`（9 頁） + `push-wiki.ps1` | 對外文件化 |
| KPI Sprint Tracking | `artifacts/metrics/kpi_sprint2.json`、`artifacts/metrics/kpi_sprint6.json` | 跨 sprint 量化改善證據 |
| Memory Bank Prompts | `.github/prompts/`（5 個 prompt） | context-review、remember-capture、pack-context 等 |
| Writing Style Unification | commit `aeada64` | 全部 MD 統一繁中（臺灣）、去 emoji |

### 量化變化

| 指標 | v1.2 (2025-07) | v2.0 (2026-04) | v2.1 (2026-04) | 變化（v2.0→v2.1） |
|---|---:|---:|---:|---|
| Total Tasks | ~5 | 18 | 18 | → |
| Done Tasks | ~3 | 13 | 14 | +1（TASK-963） |
| Total Commits | ~20 | 54 | 58 | +4 |
| CI Workflows | 1 | 1 | 2 | +1（security-scan.yml） |
| CI Steps（workflow-guards） | 7 | 10 | 10 | → |
| Python Scripts | ~10 | 14 | 14 | → |
| PowerShell Scripts | ~3 | ~5 | 7 | +2（github_publish_common、publish-release） |
| Skills | 0 | 9 | 9 | → |
| Wiki Pages | 0 | 9 | 9 | → |
| Custom Agents | 0 | 2 | 2 | → |
| Release Tags | 0 | 2 | 2 | → |
| Context Stack Errors | — | 24 | 0 | -24（template/skills 同步修復） |
| Actions checkout | — | v4.3.1 | v6.0.2 | Dependabot auto-bump |
| Actions setup-python | — | v5.6.0 | v6.2.0 | Dependabot auto-bump |

---

## 十一、修訂紀錄

| 日期 | 版本 | 變更摘要 |
|---|---|---|
| 2025-07-17 | v1.0 | 初版評估：Repo 結構 4/5、工作流 4/5、Code Review 4/5（綜合 Level 4 Managed） |
| 2025-07-17 | v1.1 | 反映 session 改進成果：.gitignore 補齊、CI 動態掃描、共用常數提取、requirements.txt、255 項 unit test、repo health dashboard。工作流 4→4.5、可維護性 3.5→4.5、綜合 4→4.5（Level 4+ 接近 Level 5） |
| 2025-07-17 | v1.2 | 對齊 BOOTSTRAP_PROMPT.md 與 subagent_roles.md 的 Gemini 認證方式（GEMINI_API_KEY → OAuth）；新增 orchestration.md §9.6 同步責任邊界（Tier 1–5）。§5 風險 5/5 已解決或緩解，§7 建議 5/5 已完成 |
| 2026-04-17 | v2.0 | 全面重新評估。新增上下文系統（memory-bank / prompts / skills / agents）、wiki 9 頁、KPI sprint tracking、custom agents、validate_context_stack.py。Task 數 5→18、commits 20→54、CI steps 7→10。發現 template/skills 同步落後（24 errors）。綜合 4.3→4.5（Level 4.5 Managed → Optimizing） |
| 2026-04-17 | v2.1 | 反映 session 內所有修復成果。template/skills 同步修復（37 檔，R1 ✅）；TASK-963 supply-chain hardening 完成（SHA pin v6.0.2/v6.2.0 + dependabot + pip-audit CI + release scripts，R6 ✅）；CI pip-audit 模組名修正；Dependabot PR #3/#4 合併；PR #1 關閉（不完整）並手動實作 drafted→planned 轉移 + lightweight mode 文件釐清。Done 13→14、commits 54→58、CI workflows 1→2、context stack errors 24→0。綜合 4.5→4.6 |
| 2026-04-18 | v2.2 | 反映 validate coverage 收尾：`test_guard_units.py` 與 `test_security_scans.py` 合計 959 項 tests，13 個 Python 模組 / 3118 stmts 全數 100%，CI coverage gate 維持 `--cov-fail-under=100`。 |
