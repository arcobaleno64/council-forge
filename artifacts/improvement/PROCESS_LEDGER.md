# Process Ledger

本檔是冷啟動入口，用來快速回顧最近幾次流程實際做了什麼、哪裡浪費、哪裡容易出錯。

建議閱讀順序：

1. 先看這份 ledger。
2. 再看最近 3 份 `TASK-XXX.improvement.md`。
3. 需要細節時，再回跳對應的 `verify` / `decision` / `status` artifact。

維護規則：

- 每個 task 只寫一行。
- 不貼 raw log，只寫結論與短證據方向。
- `Applied?` 表示對應修正是否已落地為文件、prompt、guard 或 template 變更。
- **何時必記**：凡於 closure 產出 improvement artifact（Gate E 或 retrospective）之 task，必記一條；純 lightweight／docs 小任務（無 improvement artifact）可免。此與 improvement artifact 產生連動，確保 architecture-synthesizer 之 N=10 觸發能真實累積（否則 ledger 停更會使該觸發永不達標）。

| Date | Task | Outcome | Top Waste | Top Risk | Fix Candidate | Applied? |
|---|---|---|---|---|---|---|
| 2026-04-11 | [TASK-902](TASK-902.improvement.md) | Gate E resume 條件被明文化為 `Status: applied` | improvement 存在但沒有把 applied 視為 hard gate | blocked 任務可能在沒有系統修正時恢復 | 強化 Gate E 規則在 schema / README / Obsidian 的一致性 | yes |
| 2026-04-11 | [TASK-950](TASK-950.improvement.md) | role-boundary live drill 被固定進可重跑流程 | 研究越界與 code-over-plan 只能靠人工串起證據 | 超出 plan 的必要修改仍可能缺乏自動 guard | 將 live drill 與 diff-to-plan 補強列入 runbook / backlog | yes |
| 2026-04-11 | [TASK-951](TASK-951.improvement.md) | blocked resume drill 補齊 PDCA 證據鏈 | 只補 decision 容易被誤當成足夠的 resume 依據 | blocked_reason 與 decision 可能取代 applied improvement | 將 Gate E 演練保留為固定 live drill 樣本 | yes |
| 2026-05-05 | [TASK-1044](TASK-1044.improvement.md) | workflow MD 全面同步審核確認無漂移 | 將 read-only audit 也包成完整 lifecycle 略嫌厚重 | 漏報 Tier 5 generated 檔之合法漂移 | POC profile 已釋 test 但仍要 code，docs-only audit 可考慮再簡化 | yes |
| 2026-05-05 | [TASK-1045](TASK-1045.improvement.md) | schema/validator 演進至兼容 v2 governance（α/β/γ 三案後選 β） | 多次驗證迭代之間的脈絡來回 | MARKERS substring 比對未行端錨易誤觸 (## Decision vs ## Decision Class) | parser 寫成 alternates + 行錨 + 條件嚴格化；docs-spec 釋 code；§5.13 紀錄 | yes |
| 2026-05-06 | [TASK-1047](TASK-1047.improvement.md) | CI Workflow Guards 修復 36 unit test 失敗 + coverage gate 90% | 中央 fixture helper 漏更（TASK-1008 strict mode 後遺累 9 日 CI 紅） | --cov-fail-under=100 不可達；CI 紅長忍 | central helper 一次修；CLI runner 入 omit；threshold 降至 90 並紀錄整合測試 follow-up | yes |
| 2026-05-06 | [TASK-1046](TASK-1046.improvement.md) | 專案改名 Consilium Fabri → Council Forge（含 sentinel α 路徑與 root↔template 鏡同步） | 多次驗證迭代 + GitHub 端 rename 為手動後續 | 歷史 artifact 改寫之誘惑；rename 前忘 push 舊 commits 之 race | bulk rewrite script + 顯式 whitelist + git mv sentinel；歷史 artifact 嚴格不動 | yes |
