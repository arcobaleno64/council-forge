# RACI Matrix

> 本檔之 §2 角色總表已回歸單一真源 [docs/subagent_roles.md](subagent_roles.md) §2；本檔僅保留下列 §2.1 TAO Trace 必要程度表（此檔獨有）。

## 2. 角色總表

RACI 與 agent capability 矩陣之單一真源為 [docs/subagent_roles.md](subagent_roles.md) §2「角色總表」（hybrid-sync guard 綁定該檔 ↔ `workflow_constants.RACI_MATRIX`）。本檔不再重複該表。

### 2.1 TAO Trace 必要程度（執行層）

每位 subagent 在 dispatch 時須依下表決定是否填寫 TAO Trace（Thought-Action-Observation 微循環紀錄）。完整 schema 與 mismatch 處理見 [docs/agentic_execution_layer.md](agentic_execution_layer.md)。

| 角色 | TAO Trace 必要程度 | 觸發門檻 | 落點 artifact |
|---|---|---|---|
| **Implementer** | 必填 | task risk ≥ 3（plan `## Risks` 任一條 `Severity: blocking`） | code artifact `## TAO Trace` |
| **Verifier** | 必填 | task risk ≥ 3 | verify artifact `## TAO Trace` |
| **Tester** | 建議 | 任意；risk ≥ 3 強烈建議 | test artifact 或 code artifact `## TAO Trace` |
| **Reviewer** | 建議 | 任意 | verify artifact 或 decision artifact `## TAO Trace` |
| **Memory Curator (Gemini)** | 免 | -- | -- (Curator 之內隱循環已由 [`.github/prompts/remember-capture.prompt.md`](../.github/prompts/remember-capture.prompt.md) 規範) |

**Lightweight 任務、risk ≤ 2 之微改動、純文件變更**：TAO Trace 全部可省，artifact 對應欄位寫 `None`。

**Mismatch 處理（Observation 與 Thought 預期不符）**：subagent 須產 `Observation: mismatch — <對比>`，並設 `Next-Step Decision: halt`。不得自行 retry 或繼續，回管理層由 Claude 決定是否 escalate 至 mini-PDCA 子循環。詳見 [docs/agentic_execution_layer.md §3](agentic_execution_layer.md)。
