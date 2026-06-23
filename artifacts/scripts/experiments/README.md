# Large-Scale Experiments — 自走實驗

兩個離線、確定性、帶護欄的批次實驗，設計給「無人值守數日」情境。
皆只用 Python 3 標準庫，零外部依賴，可安全反覆執行。

## ① Red-Team Marathon（穩定度 / soak）

反覆執行 `run_red_team_suite.py`，檢查紅隊套件在多輪下是否**穩定**
（每輪結果一致）、是否有 **flaky case**（outcome 在輪間翻轉）、執行時間是否漂移。

```bash
python3 artifacts/scripts/experiments/red_team_marathon.py \
    --iterations 30 --max-minutes 45 --phase static
```

- 護欄：`--iterations` 與 `--max-minutes` 任一達到即停。
- 產出：`artifacts/experiments/red_team_marathon/`
  - `marathon_trend.md`（趨勢表 + 穩定度判定 + flaky 清單）
  - `marathon_results.json`（每輪原始資料）

## ② Premortem Backtest（校準回測）

拿 `artifacts/plans/*.plan.md` 的 premortem（R1..Rn / Severity）當事前預測，
對照 `artifacts/verify/*.verify.md` 的實際結果，產生校準資料集。

```bash
python3 artifacts/scripts/experiments/premortem_backtest.py
```

- 產出：`artifacts/experiments/premortem_backtest/`
  - `backtest_report.md`（語料摘要 + 2×2 校準表 + 需檢視清單）
  - `backtest_results.json`（每個 task 的逐筆資料）
- 誠實邊界：plan 與 verify 非嚴格 1:1 因果，本工具提供**可判讀的校準資料集**，
  不宣稱精確命中率。`negative_signal` 採強訊號（red-team FAIL 或未通過的 result）。

## 自動排程

`.github/workflows/large-scale-experiments.yml` 每天 03:00 (Asia/Taipei) 跑兩個實驗，
快照進 `artifacts/experiments/history/<date>/`，推到 `claude/experiments-results` 分支。

> ⚠️ GitHub 的 `schedule` 觸發只從**預設分支**執行；workflow 合併進 master 前，
> 請用 Actions 的 `workflow_dispatch` 手動觸發。

## ③ Guard Calibration Matrix（過嚴/過鬆量測）

量測各 guard 的 **false positive（過嚴：誤擋合法 artifact）** 與
**false negative（過鬆：放行該擋的 artifact）**，輸出每個 guard 的混淆矩陣。

```bash
python3 artifacts/scripts/experiments/guard_calibration_matrix.py
```

- SHOULD_PASS：對真 artifact 跑 guard，期望 PASS；失敗即 FP。
- SHOULD_FAIL：對 artifact 施 5 類標註腐化（刪 Status、去 +08:00、非法狀態、>512KB、刪 plan），期望被擋；放行即 FN。
- 產出：`artifacts/experiments/guard_calibration/`（`matrix_report.md` + `matrix_results.json`）。
- 誠實限制：SHOULD_PASS 語料是「以通過 guard」挑出的，無法回溯「曾被誤擋而從未提交」的 artifact。

## ④ Guard Mutation Testing（測試盲點）

把 guard 程式碼**改鬆/改嚴**（AST 變異），看既有測試**抓不抓得到**。
mutation score 低 = 測試對該處的鬆緊變化無感（盲點）。純 stdlib `ast`，零外部依賴。

```bash
python3 artifacts/scripts/experiments/guard_mutation_runner.py \
    --max-mutants 200 --max-minutes 7
```

- 每個 mutant 寫到 temp copy，跑該模組 focused pytest;測試失敗=killed，通過=survived（盲點）。
- 護欄：`--max-mutants` / `--max-minutes` 任一達到即停;per-mutant 90s timeout（timeout 計為 survived，抓 ReDoS 型 hang）。
- 產出：`artifacts/experiments/guard_mutation/`（`mutation_report.md` + `mutation_results.json`,含 survived mutants 清單）。

## CI 校準 gate（永久防線）

`.github/workflows/guard-calibration.yml`（每週 + PR + push + dispatch）：
- **calibration job：fail-closed** — 一旦出現任何 FP 或 FN（guard 變過嚴或過鬆）即擋 PR。
- **mutation job：** 跑變異測試，分數寫入 job summary;低於 floor（0.80）即失敗，抓測試套件被弱化。
