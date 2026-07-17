# 派發 Implementation SOP

本 SOP 由 `CLAUDE.md` 外移（TASK-1055）；authoritative 版本以本檔為準。CLAUDE.md 保留 quick-ref pointer 指向此檔。

### 派發 Implementation

```
1. 驗證 plan artifact 已完成 premortem（R1-R4 都有）
2. 準備 dispatch prompt，包含：
   - CODEX.md 的規則條文
   - plan artifact 的摘述
   - Scope 限制（什麼不做）
   - Routing inputs: task type、risk score、context cost
   - Codex model/effort policy
3. 執行 `artifacts/scripts/Invoke-CodexAgent.ps1`，依 task scale 指定 model policy
4. 接收 code artifact 與 verify artifact
5. 檢查 `## Files Changed` ⊆ plan 的 `## Files Likely Affected`
```

> Prompt token-cost 慣例（inline vs path-reference vs temp file vs fabrication-prone）：詳見 `docs/dispatch_prompt_discipline.md`。

### Fallback tier 產出之驗收紀律（TASK-1106）

wrapper 之 fallback tier（後位模型，如 `gpt-5.4-mini`）產出**預設不可信**：驗收必須逐 tier 讀 dispatch log 分辨各 attempt 實際行為，關鍵宣稱（驗證結果、sources、Files Changed）以命令直驗，不採信口頭回報；credits 中斷後接手之 tier 尤然。出處：TASK-1105 Bug-B3——mini 於 shell 封鎖下未驗證覆寫 code artifact 並引用 fabricated sources（見 `artifacts/code/TASK-1105.code.md` §Post-Dispatch Amendment）。

### Dispatch 逾時重派紀律（TASK-1112）

前次 `Invoke-CodexAgent.ps1` / `Invoke-GeminiAgent.ps1` dispatch 若因**工具呼叫逾時**（harness timeout，而非 wrapper 自身回報結束）而中斷，caller 重新派發前必須先確認底層 process 是否仍存活（例如 `Get-Process -Name codex,node`，或觀察目標檔案 mtime 於數分鐘內是否穩定），確認確實無殘留 process 後才可重派；不得將「工具呼叫逾時」直接等同「dispatch 已終止」。出處：TASK-1107——前景 dispatch 逾時後未確認即發起併發背景 dispatch，兩個底層 process 同時 `git stash`/`stash pop`，導致 conflict markers 與測試方法重複定義（見 `artifacts/improvement/TASK-1107.improvement.md`）。
