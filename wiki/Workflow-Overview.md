# 工作流總覽

## 流程階段

```
Intake → Research → Planning → Coding → Verification → Done
```

每個階段產出的 artifact 就是下一階段的依據。不允許跳步。

## 階段說明

### Intake
- 建立 task artifact（`artifacts/tasks/TASK-XXX.task.md`）
- 定義任務目標與驗收條件

### Research
- 由 Gemini CLI 執行研究任務
- 產出 research artifact（`artifacts/research/TASK-XXX.research.md`）
- 每個具體主張須有支撐來源（source）

### Planning
- 建立 plan artifact（`artifacts/plans/TASK-XXX.plan.md`）
- 包含 premortem 風險分析（R1–R4）
- 定義 Files Likely Affected

### Coding
- 由 Codex CLI 執行實作
- 產出 code artifact（`artifacts/code/TASK-XXX.code.md`）
- Files Changed 必須是 plan 中 Files Likely Affected 的子集

### Verification
- 產出 verify artifact（`artifacts/verify/TASK-XXX.verify.md`）
- 需要 Build Guarantee（commit hash、CI log、測試結果）
- 不接受口頭「我測過了」

### Done
- 所有 artifacts 符合 schema
- 狀態轉換合法
- 驗證通過

## Gate 驗證

每個階段轉換都有 gate 檢查：

| Gate | 檢查項目 |
|---|---|
| Gate A | Task artifact 存在且 metadata 完整 |
| Gate B | Research artifact 有 ≥2 條 source + URL |
| Gate C | Plan artifact 有 premortem（R1–R4） |
| Gate D | Code artifact 的 Files Changed ⊆ plan 的 Files Likely Affected |
| Gate E | Verify artifact 有 Build Guarantee |

## Lightweight 模式

若任務標記 `lightweight: true`：
- 可跳完整 premortem（但需 basic plan with objectives）
- 可簡化 verify（可用 Environment constraint 替代 Build Guarantee）
- 仍需 code artifact + Files Changed

詳見 [docs/lightweight_mode_rules.md](https://github.com/arcobaleno64/council-forge/blob/master/docs/lightweight_mode_rules.md)。

## 狀態機

8 個合法狀態與轉移規則，詳見 [docs/workflow_state_machine.md](https://github.com/arcobaleno64/council-forge/blob/master/docs/workflow_state_machine.md)。
