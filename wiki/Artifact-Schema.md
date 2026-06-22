# Artifact Schema

所有工作流產物遵循 [docs/artifact_schema.md](https://github.com/arcobaleno64/council-forge/blob/master/docs/artifact_schema.md) 定義的 9 種 schema。

## 9 種 Artifact 類型

| 類型 | 檔案格式 | 用途 |
|---|---|---|
| Task (§5.1) | `TASK-XXX.task.md` | 任務定義與驗收條件 |
| Research (§5.2) | `TASK-XXX.research.md` | 研究結果（fact-only，不含 recommendation） |
| Plan (§5.3) | `TASK-XXX.plan.md` | 實作計畫、風險分析、影響範圍 |
| Code (§5.4) | `TASK-XXX.code.md` | 程式碼變更記錄 |
| Test (§5.5) | `TASK-XXX.test.md` | 測試結果 |
| Verify (§5.6) | `TASK-XXX.verify.md` | 驗證結果與 Build Guarantee |
| Decision (§5.7) | `TASK-XXX.decision.md` | 決策記錄（guard exception、scope waiver 等） |
| Status (§5.8) | `TASK-XXX.status.json` | 機器可讀狀態 |
| Improvement (§5.9) | `TASK-XXX.improvement.md` | PDCA 改進記錄：失敗分析、矯正與預防、verify／done 後輕量復盤 |

## 共用 Metadata 欄位

所有 artifact 必須包含：

```markdown
## Metadata

- Task ID: TASK-XXX
- Artifact Type: [type]
- Owner: [agent name]
- Status: [status value]
- Last Updated: 2026-04-16T12:00:00+08:00
```

## 核心原則

- **No artifact = not done** — 沒有 artifact 就不算完成
- **No verification = not done** — 沒有驗證就不算完成
- **No evidence = not valid** — 沒有證據就不算有效

## 存放位置

```
artifacts/
├── tasks/       # Task artifacts
├── research/    # Research artifacts
├── plans/       # Plan artifacts
├── code/        # Code artifacts
├── test/        # Test artifacts
├── verify/      # Verify artifacts
├── decisions/   # Decision artifacts
├── improvement/ # Improvement artifacts + PROCESS_LEDGER
├── status/      # Status JSON
├── registry/    # decision_registry.json
├── metrics/     # Aggregate metrics
└── red_team/    # Red-team exercise reports
```

詳見 [docs/artifact_schema.md](https://github.com/arcobaleno64/council-forge/blob/master/docs/artifact_schema.md)。
