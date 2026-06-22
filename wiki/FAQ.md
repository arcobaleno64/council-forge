# 常見問題

## 一般問題

### Q: 這個專案跟一般的 prompt 範本集有什麼不同？

Council Forge 不只是一組 prompt，而是一套完整的工作流治理框架。它包含：
- 明確的狀態機與 gate 驗證
- 9 種 artifact schema
- 自動化驗證腳本
- 三個 agent 的角色分工
- 分層式上下文管理

### Q: 一定要用三個 agent 嗎？

不一定。最小版只需 Claude Code 即可運作。Gemini CLI（研究）和 Codex CLI（實作）是選配，可依需求啟用。

### Q: 可以用在既有專案上嗎？

可以。將 `template/` 目錄內容複製到專案根目錄，替換 placeholder 後即可使用。

### Q: 支援什麼程式語言？

Council Forge 是語言無關的工作流框架。它管理的是開發流程，不限制你用什麼語言實作。驗證腳本本身以 Python 撰寫。

---

## 工作流問題

### Q: Lightweight 模式跟完整模式差在哪裡？

| 項目 | 完整模式 | Lightweight 模式 |
|---|---|---|
| Premortem | 必須有 R1–R4 | 可跳過（需 basic plan） |
| Verify | 需要 Build Guarantee | 可用 Environment constraint |
| Code artifact | 必須 | 必須 |
| Research | 視需求 | 視需求 |

### Q: 什麼情況必須 STOP？

- Task / research / plan / code artifact 缺失
- Metadata 不完整（無 Task ID、status、timestamp+08:00）
- Status transition 違反 workflow state machine
- Premortem 缺失或 R1–R4 不完整
- Verify artifact 無 Build Guarantee
- Scope drift 無 decision waiver

### Q: 什麼算「Build Guarantee」？

合法的 Build Guarantee 證據：
- Commit hash（`git rev-parse HEAD`）
- CI log URL
- Binary checkpoint / 測試結果

不接受口頭「我測過了」。

---

## 技術問題

### Q: memory-bank 的內容衝突怎麼辦？

依此優先順序：
1. Tests 通過（build guarantee）
2. 最新的 `.github/memory-bank/` 檔
3. `docs/` 檔
4. `CLAUDE.md`

### Q: 如果沒有 VS Code Copilot Chat，能用嗎？

可以。手動查詢 memory-bank 檔案即可：
```bash
cat .github/memory-bank/artifact-rules.md
cat .github/memory-bank/workflow-gates.md
```

### Q: 修改 workflow 文件後需要同步哪些？

修改以下檔案後必須同步：
1. `template/` 對應檔案
2. `OBSIDIAN.md` 與 `template/OBSIDIAN.md`
3. `README.md` 與 `README.zh-TW.md`（若涉及結構變更）
4. 執行 `guard_contract_validator.py` 確認無漂移

### Q: Prompt regression cases 何時需更新？

當 `CLAUDE.md`、`GEMINI.md`、`CODEX.md` 有變更時，必須同步更新 `artifacts/scripts/drills/prompt_regression_cases.json`。
