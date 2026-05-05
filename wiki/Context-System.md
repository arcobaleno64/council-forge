# 上下文管理系統

Council Forge 內建分層式上下文管理系統，搭配 VS Code Copilot 使用，取代傳統的「一次讀完整套文件」策略。

## 架構分層

```
Layer 1: .github/copilot-instructions.md  (全域穩定規則，VS Code 自動載入)
Layer 2: CLAUDE.md                          (精簡入口檔，~168 行)
Layer 3: .github/memory-bank/              (穩定參考知識庫)
Layer 4: .github/prompts/                  (任務導向 prompt)
Layer 5: docs/                             (詳細規範，按需載入)
```

## 各層說明

### Layer 1 — 全域規則

`.github/copilot-instructions.md` 由 VS Code 自動載入，包含：
- 核心原則（信任文件不信任記憶）
- 上下文分層指引
- 知識庫系統
- 任務完成標準
- 禁止項

### Layer 2 — Agent 入口檔

- `CLAUDE.md` — 協調者入口（~168 行，非原始 ~2600 行）
- `GEMINI.md` — 研究者入口（自包含）
- `CODEX.md` — 實作者入口（自包含）

### Layer 3 — 知識庫（Memory Bank）

`.github/memory-bank/` 包含 5 個穩定參考文件：

| 檔案 | 內容 |
|---|---|
| `artifact-rules.md` | Artifact 觸發點、必填欄位、常見錯誤 |
| `workflow-gates.md` | Gate 驗證規則與觸發條件 |
| `prompt-patterns.md` | Dispatch prompt 常用模式 |
| `project-facts.md` | 技術棧、部署、環境資訊 |
| `README.md` | 知識庫使用說明 |

### Layer 3.5 — 可組合能力（Skills & Agents）

`.github/skills/` 包含 8 個可組合的 GitHub Copilot 專業能力模組（如 security-review、quality-playbook、code-tour、agent-governance 等），可依任務需求使用；它們不是強制 lifecycle hook。

`.github/agents/` 包含 2 個自訂 agent 定義（Autonomous Executor、Readonly Process Auditor），提供可重用的 agent 人格與工具邊界。

### Layer 4 — 任務導向 Prompt

`.github/prompts/` 包含：

| 檔案 | 用途 |
|---|---|
| `pack-context.prompt.md` | 上下文收斂工具 — 在大任務前整理所需資訊 |
| `context-review.prompt.md` | 檔案級就緒度分析 |
| `remember-capture.prompt.md` | 結構化知識寫入 memory-bank |
| `memory-bank.instructions.md` | 記憶體管理規範 |

### Layer 5 — 詳細規範

`docs/` 內的規範文件由協調者按階段按需載入，不會一次全讀。

## 使用方式

### 查詢規則

```
「Artifact metadata 的必填欄位是什麼？」
→ Copilot 自動查詢 .github/memory-bank/artifact-rules.md
```

### 開始大任務

```
「我要做 TASK-XXX。先用 pack-context 幫我整理上下文。」
→ 產生 Context Pack（含目標、依賴、檢查清單）
```

### 記錄新發現

```
「把這條規則寫入 memory-bank。」
→ 使用 remember-capture.prompt.md 結構化寫入
```

## 驗證

正式驗證腳本（CI 中使用）：

```bash
python artifacts/scripts/validate_context_stack.py
```

此腳本執行 7 項檢查：

| # | 檢查項目 | 說明 |
|---|---|---|
| 1 | Memory Bank existence | `.github/memory-bank/` 必要檔案是否存在 |
| 2 | Cross-references | 各層文件間的交叉引用是否有效 |
| 3 | Copilot instructions size | `.github/copilot-instructions.md` 是否在合理大小範圍 |
| 4 | Template sync | `template/` 下的上下文檔案是否與 root 同步 |
| 5 | Frontmatter validity | Skills / Prompts 的 YAML frontmatter 格式是否正確 |
| 6 | Name uniqueness | Skills / Prompts 名稱是否唯一（無重複） |
| 7 | Memory Bank quality | 知識庫文件是否有實質內容（無空殼段落） |

Legacy wrapper（向後相容）：

```bash
python validate_mvp_context.py
```

此 wrapper 會自動轉呼叫 `validate_context_stack.py`。
