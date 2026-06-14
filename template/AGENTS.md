# AGENTS -- 文件索引

本檔案是 artifact-first multi-agent workflow 的文件索引。每個 agent 只需載入自己的入口檔 + 當前階段所需的參考文件。

## Agent 入口檔

| Agent | 入口檔 | 角色 | 自動載入 |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | 協調者 | Yes (project instruction) |
| Gemini CLI | `GEMINI.md` | 研究與 read-only memory curator | Yes (passed via prompt) |
| Codex CLI | `CODEX.md` | 實作主責 | Yes (passed via prompt) |

## 文件模組

| File | 用途 | ~Tokens | 載入時機 |
|---|---|---|---|
| `docs/orchestration.md` | 系統提示骨幹：目標、原則（§1-§2.8） | 1100 | Claude：session 開始
| `docs/orchestration-workflow.md` | workflow/gate/PDCA 細節與 sync contract（§3+） | 1400 | Claude：流程與 gate 判定前 |
| `docs/artifact_schema.md` | schema 入口與通用規則（§1-§4 + §5索引） | 900 | 寫任何 artifact 前
| `docs/schemas/artifact-spec-task.md` | Task schema（原 §5.1） | 450 | 撰寫 task artifact 前
| `docs/schemas/artifact-spec-research.md` | Research schema（原 §5.2） | 650 | 撰寫 research artifact 前
| `docs/schemas/artifact-spec-plan.md` | Plan schema（原 §5.3） | 550 | 撰寫 plan artifact 前
| `docs/schemas/artifact-spec-code.md` | Code schema（原 §5.4） | 900 | 撰寫 code artifact 前
| `docs/schemas/artifact-spec-test.md` | Test schema（原 §5.5） | 350 | 撰寫 test artifact 前
| `docs/schemas/artifact-spec-verify.md` | Verify schema（原 §5.6） | 800 | 撰寫 verify artifact 前
| `docs/schemas/artifact-spec-decision.md` | Decision schema（原 §5.7） | 700 | 撰寫 decision artifact 前
| `docs/schemas/artifact-spec-status.md` | Status schema（原 §5.8） | 500 | 更新 status artifact 前
| `docs/schemas/artifact-gallery.md` | 跨類型範例集（源自 §5） | 250 | 需要快速對照範例時 |
| `docs/subagent_roles.md` | 角色責任敘述（§1, §3-§9） | 2200 | 派發 subagent 前
| `docs/raci-matrix.md` | RACI 與 capability 矩陣（原 §2） | 900 | 派發 subagent 前 |
| `docs/workflow_state_machine.md` | 8 個狀態 + 合法轉移 | 600 | 狀態轉移前 |
| `docs/premortem_rules.md` | 風險分析格式 + 品質護欄 | 1900 | 進入 coding gate 前 |
| `docs/red_team_runbook.md` | 紅隊演練 runbook：靜態攻擊、live drill、復盤流程 | 1500 | 紅隊演練前 |
| `docs/red_team_scorecard.md` | 紅隊演練評分矩陣與總結判定 | 900 | 演練記錄與復盤時 |
| `docs/red_team_backlog.md` | 紅隊演練後續補強清單 | 700 | 復盤 / 補強規劃時 |
| `docs/subagent_task_templates.md` | Template 索引（指向 `docs/templates/`） | 200 | 派發 subagent 時 |
| `docs/templates/<role>/TEMPLATE.md` | 各角色 prompt 範本（含 YAML frontmatter） | 每個 ~150 | 派發對應 subagent 時 |
| `artifacts/scripts/discover_templates.py` | Template auto-discovery CLI | 200 | 派發 subagent 前 |
| `docs/lightweight_mode_rules.md` | 小任務精簡流程規則 | 350 | lightweight mode 任務時 |

## Markdown 書寫語言規範

- 長期維護的 Markdown 文件以繁體中文（臺灣）為主。
- 專有名詞、檔名、CLI 指令、環境變數、`artifact type`、狀態值、placeholder、schema literal 保留英文原字。
- 不得更動會被 agent、validator、腳本依賴的精確字串，例如 `## Metadata`、`Task ID`、`Artifact Type`、`Owner`、`Status`、`Last Updated` 與各種狀態值。
- 所有規範中的紀錄時間、`Last Updated` 與相關時間戳，一律使用 `Asia/Taipei`，採 ISO 8601 並帶 `+08:00`。
- source template repo（含 `.council-forge-source-repo`）中，`root`、`template/` 與 Obsidian 入口文件必須保持語義一致；由 `template/` 複製出的 downstream terminal repo 不再建立新的 `template/`，只維護 root 文件與 `OBSIDIAN.md`。
- GitHub 對外入口以 `README.md` / `README.zh-TW.md` 為準；Obsidian 入口以 `OBSIDIAN.md` 為準。
- 歷史 artifacts、實驗輸出、外部 repo 內 Markdown 不在追溯改寫範圍內。

## 階段載入矩陣

| 階段 | PDCA 階段 | Claude Code 載入 | Gemini 載入 | Codex 載入 |
|---|---|---|---|---|
| **Intake** | P (pre-Plan) | `docs/orchestration.md` | -- | -- |
| **Research** | P (Plan 前準備) | `docs/subagent_roles.md` §4, `docs/subagent_task_templates.md`, `docs/templates/` | (GEMINI.md has all needed rules) | -- |
| **Planning** | P (Plan，含 premortem) | `docs/schemas/artifact-spec-plan.md` §5.3, `docs/workflow_state_machine.md`, `docs/premortem_rules.md` | -- | -- |
| **Coding** | D (Do；微觀內含 TAO) | `docs/subagent_roles.md` §5, `docs/subagent_task_templates.md`, `docs/templates/` | -- | (CODEX.md has all needed rules) |
| **Verification** | C (Check) | `docs/schemas/artifact-spec-test.md` §5.5 + `docs/schemas/artifact-spec-verify.md` §5.6, `docs/workflow_state_machine.md` | -- | -- |
| **Closure** | A (Act；Gate E + 回灌) | `docs/workflow_state_machine.md`, `.github/prompts/remember-capture.prompt.md` | Memory Bank Curator 模式時讀 `docs/templates/memory-curator/TEMPLATE.md` | -- |
| **Red Team Exercise** | C (Check 衍生) | `docs/red_team_runbook.md`, `docs/red_team_scorecard.md`, `docs/red_team_backlog.md` | -- | -- |
| **Sync Contract** | meta | `docs/orchestration-workflow.md` §9 | -- | -- |

兩層架構詳見 [docs/orchestration.md §2.8](docs/orchestration.md)：管理層 PDCA 對應上表「PDCA 階段」欄；執行層 TAO/ReAct 內含於 Coding 階段內 subagent dispatch（詳見 [docs/agentic_execution_layer.md](docs/agentic_execution_layer.md)）。

## 交叉引用慣例

- 使用 `see docs/X.md §N` 引用特定章節，避免重複貼內容。
- 範例："Research artifact format: see `docs/artifact_schema.md` §5.2"
- Agent 入口檔（CLAUDE/GEMINI/CODEX.md）內嵌了 agent 無法自行額外載入時必須遵守的關鍵規則。
- `docs/` 內的參考文件由協調者（Claude Code）依階段按需載入。

## 章節速查

### docs/artifact_schema.md
- §1-§4 通用規則 / §5 索引

### docs/schemas/*
- artifact-spec-task.md(§5.1) / artifact-spec-research.md(§5.2) / artifact-spec-plan.md(§5.3)
- artifact-spec-code.md(§5.4) / artifact-spec-test.md(§5.5) / artifact-spec-verify.md(§5.6)
- artifact-spec-decision.md(§5.7) / artifact-spec-status.md(§5.8) / artifact-gallery.md

### docs/subagent_roles.md
- §3 Claude Code / §4 Gemini CLI（含 Memory Bank Curator 模式） / §5 Codex CLI / §6 Implementer / §7 Tester / §8 Verifier / §9 Reviewer

### docs/premortem_rules.md
- §1-2 When & where / §3 Required fields / §4 Quality rules (P1-P8) / §5 Violation levels / §6 Minimum counts
