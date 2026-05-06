## 使用示例 — MVP Context System 實戰

### 場景 1: 發現 Artifact 規則不清楚

#### 舊方式的痛點
打開 CLAUDE.md（2600 行）  
Ctrl+F 搜尋「metadata」  
翻來翻去找到相關段落  
花費 3-5 分鐘

#### 改進的新方式
問 Copilot：  
```
"Artifact metadata 的必需欄位是什麼？"
```

Copilot 自動查詢 .github/memory-bank/artifact-rules.md  
立即得到答案：Task ID、Status、Owner、Last Updated  
30 秒完成

---

### 場景 2: 開始複雜任務

TASK-950（Guard Contract Validator 改進）

#### 步驟 1：用 pack-context 收斂

```
Prompt:
我需要完成 TASK-950。在實作前，請幫我整理一下上下文。
（已存在）
- artifacts/plans/TASK-950.plan.md（已存在）
- artifacts/research/TASK-950.research.md（已存在）

主要問題：如何驗證 prompt regression？
```

#### Copilot 回應

```
## Context Pack — TASK-950

### 1. 任務核心
- 目標：改進 guard_contract_validator.py 的 prompt 變更檢測
- 輸入：
  * 現有 validator 代碼
  * CLAUDE.md、GEMINI.md、CODEX.md（baseline）
  * 新的 dotenv 規則
- 輸出：
  * Enhanced validator with additional checks
  * Code artifact + Verify artifact with Build Guarantee

### 2. 依賴與先決條件
- Artifact 依賴：plan TASK-950 已含 premortem (R1-R4)
- 文件引用：docs/schemas/artifact-spec-code.md §5.4, §5.6
- 外部依賴：pytest, GitHub API (GITHUB_TOKEN)

### 3. 關鍵規則
Rule 1（from artifact-rules.md）：Code artifact 的 Files Changed 必須是 plan 的 Files Likely Affected 的子集  
Rule 2（from prompt-patterns.md）：Dispatch 給 Codex 時要帶 CODEX.md 規則  
Rule 3（from workflow-gates.md）：Verify artifact 必須含 Build Guarantee（commit hash + CI log）

### 4. 快速檢查清單
plan 的 Risks 區段有 R1-R4（已完成）  
所有外部依賴已安裝（已完成）  
環境變數 PYTHONPATH 和 GITHUB_TOKEN 已設（待驗證）  
沒有 active PRs 造成衝突（已完成）

### 5. 進入點
先驗證 PYTHONPATH，然後執行 Codex dispatch
```

#### 步驟 2：實作

基於上述 Context Pack，執行以下項目：
1. 確認所有前置條件滿足
2. 確認要改哪些檔案（Files Likely Affected）
3. 確認 verify 要做什麼
4. 開始實作，無須中途查詢

### 場景 3：任務完成時

你剛完成了 TASK-950 的代碼編寫。

Task TASK-950 已完成。

摘要：
- Enhanced guard_contract_validator.py with prompt regression detection
- 新增 dotenv parsing 規則以支援新的 artifact patterns
- 所有測試通過（pytest -v artifacts/scripts/test_guard_contract_validator.py）

接下來要做什麼？

1. 執行完整 regression test suite
2. 同步變更到 template/ 目錄
3. Update README with new validator usage
4. Other (please specify)
```

你選 3

---

### 場景 4：發現新規則時

執行 guard_status_validator.py 時發現一個新的觸發條件：

Plan artifact 的 Objectives section 必須列舉至少 2 個明確的目標。
1. 打開 .github/memory-bank/artifact-rules.md。
2. 在 Plan Artifact 區段新增：
  Plan artifact 的 Objectives section 必須列舉至少 2 個明確目標。  
  每個目標都應該是可驗收的陳述，不可是模糊敘述。
3. git add、commit、push。

### 場景 5：向新隊友說明如何管理 artifact

#### 舊方式的痛點
需要自己翻長文件、搜尋段落、拼湊規則內容。

#### 新方式
你不需要自己在長文件裡翻找。

```
1. 讀 CLAUDE.md（168 行，5 分鐘）
2. 需要具體規則時，查 .github/memory-bank/
3. 當你卡住時，用 Copilot 問
```

隊友可以快速上手，無需翻大量文檔。

---

### 使用統計（預期）

| 指標 | 舊系統 | 新系統 | 改進 |
|---|---|---|---|
| 首次讀 instruction 時間 | 20 分鐘 | 5 分鐘 | 減少 75% |
| 查詢工作流規則時間 | 5 分鐘 | 30 秒 | 減少 90% |
| 更新規則所需改動 | 整個 CLAUDE.md | 單一 memory-bank 檔 | 減少 99% |
| 新隊友上手時間 | 1 天 | 2-3 小時 | 減少 67% |

---

## 建議的使用習慣

### 要做

每天 session 開始讀一下 .github/copilot-instructions.md 提醒（VS Code 會自動載入）。  
在 Chat 中主動問「show me the XXX rule」而不是自己翻檔案。  
發現新規則時立即記錄到 .github/memory-bank/。  
用 pack-context 開始大任務。

### 不要做

不要回到 CLAUDE.md 尋找詳細規則（改用 memory-bank）。  
不要把新規則只寫進 CLAUDE.md（改用 memory-bank 對應檔）。  
不要忽視 validate_mvp_context.py（定期驗證架構完整）。

---

## 常見 Q&A

**Q: 如果 memory-bank 的內容衝突怎辦？**

A: 依此優先級：
1. Tests 通過 (build guarantee)
2. 最新的 .github/memory-bank/ 檔
3. docs/ 檔
4. CLAUDE.md

**Q: 可以在 CLAUDE.md 中放具體例子嗎？**

A: 不建議。改用 `.github/memory-bank/prompt-patterns.md` 放例子。
好處是：
- CLAUDE.md 保持極簡
- 新隊友可以單獨讀 prompt-patterns 學習
- 方便版本更新

**Q: 如果沒有 GitHub Copilot Chat，能用嗎？**

A: 可以。不用自動提示，手動查：
```bash
cat .github/memory-bank/artifact-rules.md
cat .github/memory-bank/workflow-gates.md
```

但失去了「智能查詢」的便利。

---

總結：新系統是「**指導書（CLAUDE.md） + 參考手冊（memory-bank） + 智能助手（Copilot）**」的組合。
