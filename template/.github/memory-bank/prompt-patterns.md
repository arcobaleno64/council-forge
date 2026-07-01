# Prompt Patterns — 本 Repo 的寫作範式

**Reference**: AGENTS.md, BOOTSTRAP_PROMPT.md  
**Last Updated**: 2026-07-01 +08:00

## Agent Dispatch Pattern

派發子代理時使用的 prompt 結構。每個 dispatch 都要嵌入對應 agent 的規則摘要。

### To Gemini (Research Agent / Memory Curator)

```
你是 research agent。任務：【describe】
範圍：【問題範圍】
模式：【research | Tavily-assisted research | Memory Bank Curator draft】
要求：
1. 找至少 2 個權威來源
2. 每個源都要 URL + 120 字摘述
3. 最後給 comparative analysis（how they differ）
4. 若啟用 Tavily-assisted research，先確認本機 Tavily CLI 可用；記錄 command、query、retrieved date、URLs；不可用時回報 blocked / UNVERIFIED
5. 若是 Memory Bank Curator，只能產出 Remember Capture draft，不得寫入 `.github/memory-bank/`
GEMINI.md 的規則：【embed key rules】
完成後輸出 Research artifact（see docs/schemas/artifact-spec-research.md §5.2）
```

Tavily 結果只能放在 research artifact draft 的 `## Tavily Cache` / `## Source Cache`；是否沉澱到 memory-bank 必須由 Claude/Codex 透過 Remember Capture 篩選。memory-bank 只收長期、可追蹤、非顯而易見、非短期排障且未過時的知識。

### To Codex (Implementation Agent)

```
你是 implementation agent。任務：【describe】
Routing inputs:
- Task Type: 【docs/code/test/workflow/security】
- Risk Score: 【0-10】
- Context Cost: 【S/M/L】
Task Scale: 【tiny | docs-only | standard | high-risk | cross-module | critical | security | architecture】
Model / Effort: 【model】 / 【reasoning effort】
先決條件：
- 已有 Plan artifact（位於 artifacts/plans/TASK-XXX.plan.md）
- Premortem 已完成，風險 R1-R4 都在
- 環境變數已設定（列舉必要的）
要求：
1. 實作【功能描述】
2. 通過【測試條件】
3. 輸出 Code artifact（see docs/schemas/artifact-spec-code.md §5.4），必須含 Execution Profile 與 Subagent Plan
4. 輸出 Verify artifact with Build Guarantee
5. 若使用 Codex subagent，scope check、test planning、implementation、regression verification 必須分工清楚；未使用時寫 `Subagent Plan: None` 與理由
範圍：【明確不做什麼】
CODEX.md 的規則：【embed key rules】
```

## Artifact Output Pattern

Artifact 範本。Status 值必須符合 docs/artifact_schema.md §4.2 的合法清單。

### Research Artifact Header

```markdown
# Research -- TASK-XXX
## Objective
【一句話：要回答什麼問題】
## Sources
- Source 1: Title | URL | 【120-word summary】
- Source 2: ...
## Analysis
【Comparative synthesis】
## Metadata
- Task ID: TASK-XXX
- Status: ready
- Last Updated: 2026-04-16T14:30:00+08:00
```

Plan artifact 範本以 `docs/artifact_schema.md` §5.3 為準；風險必須有 Risk / Trigger / Detection / Mitigation / Severity。

## 常見模式

Guard validator 或流程中常見的結構化輸出範本。

### 缺少前置 Artifact

當 research / plan / code 缺失時，停下並報告：

```
BLOCKED: TASK-XXX cannot proceed.
Missing artifact: artifacts/plans/TASK-XXX.plan.md
Required for: coding phase gate check
Action: Complete planning phase first (see docs/schemas/artifact-spec-plan.md §5.3)
```

### Scope 漂移

當 code.Files Changed 不是 plan.Files Likely Affected 的子集時：

```
SCOPE DRIFT DETECTED: TASK-XXX
Planned: [src/foo.py, tests/]
Changed: [src/foo.py, src/bar.py, src/config.py]
Decision:
Option A: Revert bar.py / config.py
Option B: Create decision artifact with Guard Exception
Option C: Abort and refile as sub-task
```
## Claude Fable 5 / Mythos 5 提示調校

**Source**: platform.claude.com/docs `build-with-claude/prompt-engineering/prompting-claude-fable-5`（zh-TW，retrieved 2026-07-01）。以下把 Fable 5 特有行為映射到本 repo 的 orchestration 流程；升級模型（Opus 4.8 → Fable 5 / Mythos 5）時據此重估既有 dispatch prompt 與 skill。

### Effort 分層（對應 dispatch 的 `Model / Effort` 欄）

- 預設 `high`；能力最敏感者（架構決策、跨模組 verify、premortem R1-R4）用 `xhigh`；docs-only / 例行 lint 用 `medium`/`low`。Fable 5 低 effort 常已超越舊模型 `xhigh`。
- 任務能完成但耗時過長，或想要更互動的風格 → 降 effort。
- 高 effort 下 Fable 5 易過度收集 context 與做未要求的重構；dispatch 的 `範圍：【明確不做什麼】` 欄必須實填（呼應 single-writer 與 scope-drift guard）。

### 強指令遵循 ⇄ Dispatch Prompt Discipline

Fable 5 用一條簡短指令即可引導行為，無需逐條列舉每種情況。這與 `docs/dispatch_prompt_discipline.md` 的 ≤500 char 路由互為印證：短 prompt 不再犧牲行為精度，故不得在 dispatch 內鋪陳冗長行為清單。

### 進度聲明須有據（同源於 Build Guarantee）

長時間 dispatch 加一句：「報告前逐條 claim 對照本 session 的 tool result；未驗證就明說 UNVERIFIED」。此與本 repo「No evidence = not valid」/ Build Guarantee 同源；Anthropic 測試顯示此指令幾乎消除虛構狀態報告。

### 不要指示 agent 複述其推理（reasoning_extraction 拒絕風險）

凡要求 agent「回顯 / 謄寫 / 在回應文字中解釋內部推理」的 dispatch 或 skill，在 Fable 5 可能觸發 `reasoning_extraction` 拒絕、升高 fallback 至 Opus 4.8 的比例。遷移時稽核既有 skill 與 system prompt；需推理可見性時改讀 adaptive thinking 的結構化 `thinking` 區塊。注意本 repo 的 anti-fabrication 規則要求的是「直驗回報」（gh api / grep）而非「複述推理」，兩者不同——保留直驗要求即可。

### 平行 subagent 與 send-to-user

- Fable 5 更積極派 parallel subagent 且偏好 async 溝通勝於阻塞等待（呼應 Code artifact 的 Subagent Plan 分工）。
- 長時間非同步 agent 若需把交付物 / 進度原樣傳給使用者，定義 `send_to_user` 類 client tool 並於 system prompt 明確引導；僅定義不引導時模型很少主動呼叫。

### 明確界限（呼應 single-writer / 「Claude 預設不自行實作」）

Fable 5 偶爾採取未被要求的行動（草擬 email、建防禦性 git 備份分支）。dispatch 須界定：使用者在描述問題 / 提問而非要求變更時，交付物是評估報告，report and stop，不自行 apply fix。

### 更長的預設回合

高 effort 下單一請求可能跑數分鐘、自主執行延續數小時。呼叫端須調整 client timeout / streaming / 進度指示；框架宜以排程工作非同步檢查狀態，勿阻塞等待每個 subagent 回傳。

## 禁止項

- Artifact 不按 schema 寫 — see docs/artifact_schema.md §5
- 使用非標準 status 值 — see docs/artifact_schema.md §4.2
- Metadata 缺時間戳（ISO 8601 +08:00）或 owner
- Risk 區段只寫結論，不寫 trigger / detection / mitigation
