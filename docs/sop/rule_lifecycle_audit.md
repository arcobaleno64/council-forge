# Rule Lifecycle Audit

本 SOP 定義 workflow 規則的最小盤點循環：先看資料，再查 provenance，最後只記錄可回放的裁決。

## Purpose

- 適用對象：guard 規則、validator pattern、templates、wrapper flags、workflow 條款，以及本 SOP 自身。
- 目標：把「該不該拆、該不該放寬、為什麼還留著」收斂成固定三步，避免 ad-hoc 增生。
- 本 SOP 只定義盤點方法；不得要求新增腳本、guard、artifact type 或自動化強制。

## Trigger

- 當 [PROCESS_LEDGER](../../artifacts/improvement/PROCESS_LEDGER.md) 條目達 N=10 倍數時，同批執行本盤點；N=10 定義與節奏權威仍以 [architecture-synthesizer](../templates/architecture-synthesizer/TEMPLATE.md) 的 Trigger 為準。
- 使用者可隨時手動發起，不必等待 N=10。

## Step 1: Occam Pass

- 先讀：`artifacts/improvement/RELAXATION_LOG.md`、`artifacts/improvement/PROCESS_LEDGER.md`、`docs/templates/archive/README.md`、`docs/red_team_backlog.md`，以及最近的 Guard Exception / warning 證據。
- 把候選規則列入待查，只接受可見訊號：長期零使用、重複放寬、長期未動工、前提已消失、或同一例外反覆出現。
- 此步只找候選，不做裁決；沒有資料就不猜。
- 使用數據只產生候選，不產生裁決——零使用不等於零價值（保險機制平時即零觸發）；裁決一律過 Step 2 之 provenance 檢查。
- 候選訊號亦包含（TASK-1108）：高 blast-radius 變更缺 rollback/migration notes、僅以單一指標作為移除唯一理由、guard 被刪除卻無替代機制或 decision 記錄、欄位查無消費者（unknown consumer——unknown consumer ≠ no consumer，不得逕以此視為安全）。
- 評估候選訊號時（TASK-1109，Campbell's Law）：不得以原始指標值（如 firing_count、pass_rate、coverage）直接作為安全/價值/品質之證明；不得獎勵人為製造之 guard 觸發、警告壓制、淺層測試覆蓋，或僅改善指標而未降低實際風險之變更。

## Step 2: Chesterton Gate

| Verdict | 何時使用 | 最小要求 | 動作 |
|---|---|---|---|
| `keep` | 規則仍在攔真實事故，或成本低但保護面仍有效 | 找得到現行風險或歷史事故來源 | 原規則不動，補一句可驗證理由 |
| `relax` | 規則目的仍成立，但當前字面過嚴、誤傷穩定高於收益 | 找得到放寬前後差異與觸發案例 | 只縮到足以消除誤傷，不順手擴 scope |
| `retire` | 前提已消失、替代機制已接手，且撤回成本低 | 找得到前提消失或替代證據 | 移除或歸檔，並留下可復活路徑 |
| `open` | 查無 provenance，或現有證據不足以判定 keep / relax / retire | 缺口本身要可指認 | 不拆也不加碼，只記錄缺口待下輪 |

- `open` 是 fail-closed 的盤點裁決：先停在記錄，不用推測補洞；scope-drift guard Layer-1（2026-07-02）為先例。
- `retire` 若對象是 template，復活路徑預設記 `git mv docs/templates/archive/<name> docs/templates/<name>`；不適用時寫 `N/A`。
- 同型 detect-only 違規（如 dispatch write-scope / RACI 警告）連續被人工接受達 3 次：當輪必須裁 `relax`（承認規則過嚴、修規則字面）或轉強制（如 dispatch 顯式傳 `-AutoRestore`），不得停留於 detect-and-accept（Normalization of Deviance 防範）。

## Step 3: Record

- 每次盤點只追加，不覆寫既有紀錄。
- 最低記錄格式如下，放在當次 decision / improvement / verify 附錄或同批盤點筆記中：

| Rule / Path | Verdict | Provenance | Why | Revival Path |
|---|---|---|---|---|
| `docs/X.md` | `keep` | `docs/Y.md:12` | 一句話理由 | `N/A` |

- `Provenance` 要寫可 grep 回放的 citation；查無者明寫 `provenance: unrecorded`。
- 若 `RELAXATION_LOG` 累積達 3 筆以上，當次 closure 需升級 architect review。

## Guardrails

- 本 SOP 自身列入每輪盤點對象。
- 若 N=10 軌長期未觸發，下一輪盤點必須檢討是否改綁 unified audit。
- 任何較複雜方案若不能比簡單方案多守住安全性、正確性或可觀測性，維持較小方案。
