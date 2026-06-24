# Premortem Calibration Backtest — 校準報告

## Metadata
- Generated At: 2026-06-25T03:41:24+08:00
- Timezone: Asia/Taipei (+08:00)
- Corpus: `artifacts/plans/*.plan.md` × `artifacts/verify/*.verify.md`

## Corpus Summary

- Plans total: 111
- Plans with premortem (R1..Rn): 111
- Plans with matching verify: 111
- Avg risks per premortem: 5.26 (min=2, max=16)
- Tasks with negative verify signal: 2

## Calibration 2×2 (預測 blocking 風險 × verify 負面信號)

| | Actual: 負面信號 | Actual: 乾淨 |
|---|---:|---:|
| **Pred: 有 blocking 風險** | 2 (TP) | 101 (FP) |
| **Pred: 無 blocking 風險** | 0 (FN) | 8 (TN) |

> 說明：plan 與 verify 非嚴格 1:1 因果，本表為可判讀的校準資料集，非精確命中率。
> FN（事前沒標 blocking、事後卻出現負面信號）最值得回來人工檢視。

## Tasks with negative verify signal (建議回來檢視)

| Task | Premortem risks | Blocking | RedTeam FAIL | Escalated | Blocked |
|---|---:|---:|---:|---:|:--:|
| `TASK-1012` | 4 | 3 | 2 | 2 | no |
| `TASK-1016` | 4 | 4 | 2 | 4 | yes |

