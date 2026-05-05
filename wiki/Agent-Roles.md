# Agent 角色分工

Council Forge 採用三個 AI agent 分工協作，各自有明確的職責邊界。

## 三個 Agent

### Claude Code — 協調者（Orchestrator）

- **入口檔**: `CLAUDE.md`
- **職責**: 流程控制、artifact 管理、任務派發、驗收
- **權限**: 唯一可修改程式碼的 agent（single agent can modify code）
- **載入**: 依階段按需載入 `docs/` 內文件

### Gemini CLI — 研究者（Researcher）

- **入口檔**: `GEMINI.md`（已內嵌所有規則，不依賴 CLAUDE.md）
- **職責**: 外部 API 調查、技術研究、版本差異分析
- **限制**: 僅負責事實收集，不做 recommendation 或 solution 設計
- **產出**: Research artifact，每個 claim 需有 ≥2 條 source + URL

### Codex CLI — 實作者（Implementer）

- **入口檔**: `CODEX.md`（已內嵌所有規則，不依賴 CLAUDE.md）
- **職責**: 程式碼實作、測試撰寫、Build Guarantee 產出
- **限制**: 僅在有 approved plan artifact 後才可實作
- **產出**: Code artifact + Verify artifact

## 角色邊界

```
Claude Code (協調)
  ├── 派發 Research → Gemini CLI
  ├── 派發 Implementation → Codex CLI
  ├── 驗收 artifacts
  └── 狀態管理與 gate 檢查

Gemini CLI (研究)
  └── 回傳 research artifact

Codex CLI (實作)
  └── 回傳 code artifact + verify artifact
```

## 7 種 Agent 角色定義

除了三個主要 agent，`docs/subagent_roles.md` 另外定義了 7 種角色：

| 角色 | 章節 | 說明 |
|---|---|---|
| Claude Code | §3 | 協調者 |
| Gemini CLI | §4 | 研究者 |
| Codex CLI | §5 | 實作者 |
| Implementer | §6 | 實作子代理 |
| Tester | §7 | 測試子代理 |
| Verifier | §8 | 驗證子代理 |
| Reviewer | §9 | 審查子代理 |

## 階段載入矩陣

| 階段 | Claude Code 載入 | Gemini 載入 | Codex 載入 |
|---|---|---|---|
| Intake | `docs/orchestration.md` | — | — |
| Research | `docs/subagent_roles.md` §4 | GEMINI.md | — |
| Planning | `docs/artifact_schema.md` §5.3 | — | — |
| Coding | `docs/subagent_roles.md` §5 | — | CODEX.md |
| Verification | `docs/artifact_schema.md` §5.5-6 | — | — |
| Closure | `docs/workflow_state_machine.md` | — | — |

詳見 [AGENTS.md](https://github.com/arcobaleno64/council-forge/blob/master/AGENTS.md)。
