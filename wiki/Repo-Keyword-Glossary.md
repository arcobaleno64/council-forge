# Council Forge Repo 關鍵字與技術術語速讀

這份文件是給第一次接觸這個 repo 的人看的「白話版索引」。  
如果你只想先知道這個 repo 在做什麼、常見名詞代表什麼、該從哪裡開始讀，先看這一份就夠。

## 先用一句話理解這個 Repo

Council Forge 不是一般以產品功能為主的 app repo；它比較像一套放在 repo 內部的 **multi-agent AI workflow framework**，用明確的文件、artifact、validator 與 GitHub Actions，把研究、規劃、實作、驗證流程固定下來。  
證據：`README.zh-TW.md`、`docs/orchestration.md`、`docs/artifact_schema.md`

## 一眼看懂整體結構

| 區塊 | 白話說明 | 主要證據 |
|---|---|---|
| `START_HERE.md`、`README*`、`AGENTS.md` | 新人入口；先告訴你專案是什麼、文件怎麼讀。 | `START_HERE.md`、`README.zh-TW.md`、`AGENTS.md` |
| `docs/` | 工作流規則本體；定義流程、schema、狀態機、風險規則。 | `README.zh-TW.md`、`docs/orchestration.md` |
| `artifacts/` | 任務執行痕跡；每個 task 的 task / research / plan / code / verify 等 markdown artifacts，以及獨立的 `status.json` 都放這裡。 | `docs/artifact_schema.md`、`README.zh-TW.md` |
| `artifacts/scripts/` | 自動檢查與治理腳本；負責驗證規則沒有被跳過。 | `README.zh-TW.md`、`.github/workflows/workflow-guards.yml` |
| `.github/` | GitHub 整合層；含 workflows、skills、prompts、memory-bank、agents。 | `README.zh-TW.md` |
| `template/` | source template repo 給新專案複製用的骨架。 | `README.zh-TW.md`、`CLAUDE.md` |
| `wiki/` | 對外說明文件；偏 onboarding 與概念導覽。 | `wiki/Home.md`、`README.zh-TW.md` |
| `external/` | 外部整合；目前透過 git submodule 追蹤 `external/hermes-agent`。 | `.gitmodules` |

## 核心工作流術語

| 術語 | 淺白說明 | 主要證據 |
|---|---|---|
| artifact-first | 重要資訊不能只留在聊天裡，必須先落成檔案，下一步才算有依據。 | `docs/orchestration.md`、`docs/artifact_schema.md` |
| gate-guarded workflow | 任務不能想跳哪一步就跳哪一步；要照 Intake → Research → Planning → Coding → Verification → Done 前進。 | `README.zh-TW.md`、`docs/workflow_state_machine.md` |
| state machine | 任務狀態機；規定哪些狀態可以合法轉移。 | `docs/workflow_state_machine.md` |
| task artifact | 任務定義檔，說明目標、限制、驗收條件。 | `docs/artifact_schema.md` §5.1 |
| research artifact | 研究檔；把外部知識、規格與限制整理成可交接內容。 | `docs/artifact_schema.md` §5.2 |
| plan artifact | 規劃檔；定義要改哪裡、風險在哪裡、哪些不做。 | `docs/artifact_schema.md` §5.3 |
| code artifact | 實作摘要檔；說明這次改了哪些檔案、怎麼對應 plan。 | `docs/artifact_schema.md` §5.4 |
| verify artifact | 驗收檔；逐條核對 acceptance criteria 有沒有真的完成。 | `docs/artifact_schema.md` §5.6 |
| status artifact | 機器可讀的狀態檔，讓 guard 能自動判斷 task 目前在哪個階段。 | `docs/artifact_schema.md`、`docs/workflow_state_machine.md` |
| decision artifact | 當需求衝突、要做取捨或記錄例外時，寫成 decision。 | `docs/artifact_schema.md` §5.7 |
| improvement artifact | 人類閱讀的復盤文件，用 PDCA 記錄根因、矯正與預防；從 `blocked` 恢復時必填，平時則屬建議補充。 | `docs/artifact_schema.md` §5.8、`docs/workflow_state_machine.md` |

## 這個 Repo 最常出現的治理名詞

| 術語 | 淺白說明 | 主要證據 |
|---|---|---|
| Assurance Level | 驗證強度等級；目前有 `POC`、`MVP`、`Production`。等級越高，必備 artifact 和驗證要求越高。 | `docs/artifact_schema.md`、`docs/orchestration.md` |
| Project Adapter | 任務類型；像 `generic`、`docs-spec`、`backend-service`。它會影響 validator 該套用哪套規則。 | `docs/artifact_schema.md` |
| resolved policy | 真正生效的規則組合；先看 `Assurance Level`，再套 `Project Adapter`。 | `docs/orchestration.md`、`docs/artifact_schema.md` |
| lightweight mode | 小任務的簡化流程；可以減少 research / test 密度，但不能放棄範圍與驗收紀律。 | `docs/lightweight_mode_rules.md` |
| Build Guarantee | verify artifact 裡的建置證據；不是口頭說有跑過，而是要明列 build 指令、exit code、輸出結果尾段。 | `CLAUDE.md`、`docs/artifact_schema.md`、`docs/orchestration.md` |
| scope drift | 實際改動超出 plan 原本允許的範圍。這個 repo 把它視為高風險問題，預設直接 fail。 | `README.zh-TW.md`、`docs/artifact_schema.md` |
| Gate E | 任務要從 `blocked` 狀態恢復到其他合法狀態前，必須先補一份 improvement artifact 並完成必要紀錄；這個恢復關卡就叫 Gate E。 | `docs/workflow_state_machine.md`、`docs/artifact_schema.md` |
| PDCA | 一種持續改善方法；在這個 repo 裡，常用來組織 improvement artifact 的根因、矯正與預防內容。 | `docs/artifact_schema.md`、`docs/workflow_state_machine.md` |
| PROCESS_LEDGER | 任務履歷索引；用一行摘要記錄最近任務與改善脈絡，方便快速理解近況。 | `README.zh-TW.md`、`artifacts/improvement/PROCESS_LEDGER.md` |

## Agent 與上下文相關術語

| 術語 | 淺白說明 | 主要證據 |
|---|---|---|
| Claude Code | 主控／協調者；負責拆解任務、建 plan、驗收結果、更新狀態。 | `CLAUDE.md`、`docs/subagent_roles.md` |
| Gemini CLI | 研究代理；負責查文件、驗證事實、整理 research artifact。 | `GEMINI.md`、`docs/subagent_roles.md` |
| Codex CLI | 實作代理；依 plan 修改程式或文件，產出 code artifact。 | `CODEX.md`、`docs/subagent_roles.md` |
| subagent | 主代理底下的子角色，例如 Implementer、Tester、Verifier、Reviewer。 | `docs/subagent_roles.md` |
| memory-bank | 穩定知識區；放不容易變動、能幫助未來任務的 repo facts。 | `.github/memory-bank/README.md`、`README.zh-TW.md` |
| prompts | 可重複使用的提示模板，例如 pack-context、remember-capture。 | `.github/prompts/`、`README.zh-TW.md` |
| skills | 專門能力模組，例如 code-tour、security-review、quality-playbook。 | `.github/skills/` |
| custom agents | 額外定義的代理人格；目前 repo 內有 `autonomous-executor` 與 `readonly-process-auditor`。 | `.github/agents/` |
| source template repo | 這個 repo 本身；它是其他專案複製 workflow 骨架的來源，而且因為根目錄有 `.council-forge-source-repo`，所以要維護 root、`template/`、Obsidian 文件的一致性。 | `.council-forge-source-repo`、`CLAUDE.md` |
| downstream terminal repo | 從 `template/` 複製出去的新專案；只維護 root 文件與 `OBSIDIAN.md`，不再保留新的 `template/`。 | `CLAUDE.md`、`README.zh-TW.md` |
| Obsidian | 這個 repo 的另一個文件入口；`OBSIDIAN.md` 供 Obsidian vault 使用。 | `OBSIDIAN.md`、`README.zh-TW.md` |

## 進階治理與架構術語

| 術語 | 淺白說明 | 主要證據 |
|---|---|---|
| Double-Loop Learning | 雙環學習；當系統性防線（如 RACI Auditor）報錯時，強制協調者產出 decision 來調整 policy 的學習閉環機制，而不只是解決單一 Bug。 | `docs/orchestration.md`、`artifacts/decisions/` |
| TAO Trace | Task, Artifact, Orchestration 的縮寫；執行的微觀追蹤軌跡，用於標記程式碼變更究竟是由哪個 Task 觸發，確保修改具備可溯源性。 | `docs/agentic_execution_layer.md`、`artifacts/code/` |
| Waiver | 豁免／特批；用於合約驗證的特例紀錄。分為 `ex-ante`（事前特批）與 `pre-existing-dirty`（歷史包袱豁免）。 | `artifacts/scripts/guard_contract_validator.py` |
| Hybrid Sync | 混合式同步；以人類好讀的 Markdown 作為「唯一真相來源 (Truth Source)」，以 Python 腳本常數作為「執行快取 (Execution Cache)」，再透過 CI 強制確保兩者 100% 同步的治理設計。 | `artifacts/scripts/guard_contract_validator.py`、`artifacts/scripts/workflow_constants.py` |

## 紅隊演練 (Red Team) 專屬名詞

| 術語 | 淺白說明 | 主要證據 |
|---|---|---|
| Premortem | 事前驗屍；在 Plan 階段強制執行的防禦性分析，預判可能導致專案失敗或資安外洩的風險，並提早設立品質護欄。 | `docs/premortem_rules.md`、`artifacts/plans/` |
| Live Drill | 動態演練；與 Static Scan (靜態掃描) 相對，指透過 Red Team 腳本在執行期模擬惡意行為來測試工作流防線。 | `docs/red_team_runbook.md`、`artifacts/scripts/run_red_team_suite.py` |
| Red Team Scorecard | 紅隊評分卡；每次演練後的量化指標紀錄，用來判定防禦力是否有退步，以及防線的涵蓋率。 | `docs/red_team_scorecard.md`、`docs/red_team_backlog.md` |

## 自動化腳本與 CI 術語

| 術語 / 腳本 | 淺白說明 | 主要證據 |
|---|---|---|
| `guard_status_validator.py` | 最核心的流程守門員；檢查 task 狀態、artifact 完整度、scope drift、Gate E 等。 | `README.zh-TW.md`、`.github/workflows/workflow-guards.yml` |
| `guard_contract_validator.py` | 檢查 root / template / Obsidian / README 等同步契約有沒有漂移。 | `README.zh-TW.md`、`.github/workflows/workflow-guards.yml` |
| `prompt_regression_validator.py` | 把 prompt 當成可回歸測試的資產來驗證。 | `README.zh-TW.md`、`.github/workflows/workflow-guards.yml` |
| `run_red_team_suite.py` | 自動化紅隊演練腳本；測試 workflow 面對惡意輸入、規則漂移時是否仍能守住。 | `README.zh-TW.md`、`docs/red_team_runbook.md` |
| `repo_health_dashboard.py` | 產生整體健康儀表板，例如 task 覆蓋率、stale、blocked aging。 | `README.zh-TW.md`、`docs/repo_structure_workflow_maturity_assessment.md` |
| `repo_security_scan.py` | 本地安全掃描工具；支援 secrets 掃描與聚焦式 static scan。 | `README.zh-TW.md`、`.github/workflows/security-scan.yml` |
| `build_decision_registry.py` | 把 decision artifacts 彙整成決策登錄冊。 | `README.zh-TW.md` |
| `push-wiki.ps1` | 把 `wiki/` 內容推到 GitHub Wiki，且先做 preflight 檢查。 | `README.zh-TW.md` |
| GitHub Actions | CI 執行平台；repo 內有 `workflow-guards.yml` 與 `security-scan.yml` 兩條 workflow。 | `.github/workflows/workflow-guards.yml`、`.github/workflows/security-scan.yml` |
| SHA-pinned actions | GitHub Actions 不只寫版本 tag，而是固定到完整 commit SHA，降低供應鏈風險。 | `README.zh-TW.md`、`.github/workflows/workflow-guards.yml` |
| pip-audit | Python 依賴弱點掃描工具；在 `security-scan.yml` 中執行。 | `.github/workflows/security-scan.yml` |

## Python / Git / 發布相關術語

| 術語 | 淺白說明 | 主要證據 |
|---|---|---|
| Python 3.11 | README 與 CI 目前都以它作為建議／執行版本；新人照這個版本準備環境最不容易踩雷。 | `README.zh-TW.md`、`.github/workflows/workflow-guards.yml` |
| PyYAML | 目前 `requirements.txt` 中明確列出的基礎相依；供 workflow 腳本使用。 | `requirements.txt` |
| pytest / pytest-cov | 主要測試工具；CI 會跑單元測試與 coverage。 | `requirements-dev.txt`、`.github/workflows/workflow-guards.yml` |
| git submodule | `external/` 的外部整合方式；目前追蹤 `external/hermes-agent`。 | `.gitmodules`、`README.zh-TW.md` |
| Wiki publish | 文件發布路徑之一；`wiki/` 搭配 `push-wiki.ps1` 使用。 | `wiki/Home.md`、`README.zh-TW.md` |
| Release publish | repo 也內建 GitHub Release 發布腳本。 | `README.zh-TW.md` |

## 新人最實用的閱讀順序

1. `START_HERE.md`：先知道要從哪三份文件開始。  
2. `README.zh-TW.md`：看專案定位、結構、常用指令。  
3. `AGENTS.md`：知道每份文件是做什麼的、各階段該讀哪些。  
4. `docs/orchestration.md`：看完整工作流與 gate。  
5. `docs/artifact_schema.md`：理解 artifact 之間怎麼串起來。  
6. `docs/workflow_state_machine.md`：理解任務狀態不能亂跳。  
7. `artifacts/improvement/PROCESS_LEDGER.md`：快速了解最近任務真的怎麼跑。  

## 容易搞混，但其實差很多的名詞

| 名詞 A | 名詞 B | 差別 |
|---|---|---|
| `docs/` | `artifacts/` | `docs/` 是規則說明；`artifacts/` 是任務實際執行證據。 |
| `plan artifact` | `code artifact` | plan 是「準備怎麼做」；code artifact 是「實際做了什麼」。 |
| `verify artifact` | `test artifact` | test 偏技術測試結果（例如單元測試、整合測試）；verify 會回頭對照 task / plan 的 acceptance criteria 做最後判定。 |
| `guard_status_validator.py` | `guard_contract_validator.py` | 前者管任務流程與 artifact；後者管文件與同步契約。 |
| source template repo | downstream terminal repo | 前者要維護 `template/`；後者不需要也不應該建立新的 `template/` 目錄。 |
| lightweight mode | 省略紀律的流程 | 不是同義詞；它只是小任務簡化流程，仍然要有範圍、artifact 與驗證。 |
| `ex-ante` Waiver | `pre-existing-dirty` Waiver | 前者是用於未來例外的合法特批；後者是針對過去累積的技術債，絕對不能用在新的架構防禦（如 RACI）上。 |
| Truth Source | Execution Cache | 前者（如 `subagent_roles.md`）給人看，後者（如 `workflow_constants.py`）給機器跑；前者是源頭，後者是派生物。 |

## 證據來源

- `START_HERE.md`
- `README.zh-TW.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CODEX.md`
- `GEMINI.md`
- `OBSIDIAN.md`
- `docs/orchestration.md`
- `docs/artifact_schema.md`
- `docs/workflow_state_machine.md`
- `docs/subagent_roles.md`
- `docs/lightweight_mode_rules.md`
- `docs/red_team_runbook.md`
- `docs/repo_structure_workflow_maturity_assessment.md`
- `.github/workflows/workflow-guards.yml`
- `.github/workflows/security-scan.yml`
- `.github/memory-bank/README.md`
- `.gitmodules`
- `requirements.txt`
- `requirements-dev.txt`
- `wiki/Home.md`
- `artifacts/improvement/PROCESS_LEDGER.md`
