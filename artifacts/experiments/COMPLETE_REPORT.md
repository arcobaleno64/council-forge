# Council-Forge 大型實驗與安全強化 — 完整報告

> 本報告彙整本次無人值守工作期間(指揮官出國)完成的全部交付:兩個大型自走實驗、
> 一次授權的自我安全評估、guard 校準與變異測試,以及隨之建立的 CI 永久防線。
> 所有結論皆有 committed artifact 與 commit hash 佐證(Build Guarantee)。

## Metadata

- Generated At: 2026-06-28 (Asia/Taipei, +08:00)
- 作者:Orchestrator(Claude),read-only 審計由 5 個 subagent 平行執行
- 來源 artifacts:`artifacts/experiments/**`
- 對應 PR:#18(實驗)、#19(安全評估 + SAST)、#20(校準 + 變異 + gate)
- 追蹤 issue:#21(guard 待修清單)
- master 合併證據:`e80735a`(#18)、`223cd5a`(#19)、`0115228`(#20)

---

## 0. 摘要(Executive Summary)

| 面向 | 結論 | 證據 |
|---|---|---|
| **Red-team 穩定度** | 30/30 case，10 輪全一致,**無 flaky** | `red_team_marathon/marathon_trend.md` |
| **Premortem 校準** | 111 plan,僅 2 個任務有事後負面信號(TASK-1012/1016) | `premortem_backtest/backtest_report.md` |
| **安全評估** | 1 Critical + 2 High + 4 Medium;**CI-01 已修**,其餘待親手 review | `security_audit/00_SUMMARY.md` |
| **Guard 過嚴/過鬆** | status & contract guard 皆 **0 FP / 0 FN**(不過嚴也不過鬆) | `guard_calibration/matrix_report.md` |
| **測試盲點** | mutation score 85.4%(137 mutants,**20 survived**),含 2 個邊界缺口 | `guard_mutation/mutation_report.md` |
| **新增防線** | Bandit/Semgrep SAST + calibration gate(fail-closed)+ mutation floor 0.80 | `.github/workflows/{security-deep-scan,guard-calibration}.yml` |

**一句話**:核心 workflow 健康(穩定、校準乾淨),但既有 guard 程式藏有 1 個 Critical ReDoS 等
邏輯漏洞,**不會被任何自動 gate 擋下**——需指揮官回國親手修補(已釘 issue #21)。

---

## 1. 大型自走實驗(PR #18)

兩個離線、可重跑、純 CPU 的實驗,並排程每日 03:00(Asia/Taipei)自動跑、快照進
`artifacts/experiments/history/<date>/`。

### 1.1 Red-Team Marathon — 穩定度趨勢

對 red-team 套件(static phase)連跑 10 輪,檢測 flaky。

- **結果:Stable ✅** — 每輪皆 30 case / 30 pass / 0 fail,distinct pass-counts = [30]。
- 耗時:min 10.87s / avg 13.43s / max 14.81s。
- Flaky case:**無**(所有 case 跨輪 outcome 一致)。

> 意義:防禦套件本身可信賴,日後若某輪突然翻轉即為迴歸信號。

### 1.2 Premortem Calibration Backtest — 事前風險 vs 事後結果

把 111 份 plan 的 premortem(R1..Rn)與對應 verify 的負面信號做 2×2 校準。

- Corpus:111 plan,**全部**有 premortem 且有對應 verify;平均每 premortem 5.26 條風險。
- 有事後負面信號的任務:**2**(TASK-1012、TASK-1016)。

| | Actual: 負面信號 | Actual: 乾淨 |
|---|---:|---:|
| **Pred: 有 blocking 風險** | 2 (TP) | 101 (FP) |
| **Pred: 無 blocking 風險** | 0 (FN) | 8 (TN) |

> 重點:**FN = 0**(沒有「事前沒標、事後爆雷」的案例)。premortem 偏保守(101 FP),
> 但這在風險管理上是可接受的方向。建議回來人工檢視 TASK-1012 / TASK-1016。
> 注意:plan 與 verify 非嚴格 1:1 因果,本表為可判讀的校準資料集,非精確命中率。

---

## 2. 授權安全自我評估(PR #19)

由 5 個 read-only subagent 平行執行(path-traversal/IO、ReDoS、subprocess/injection、
CI/供應鏈、secrets/SSRF),agent 僅讀碼產出 findings,改碼由協調者統一處理(single-writer)。

### 2.1 攻擊面前提

本 repo 無部署中的網路服務(Python 腳本 + 治理文件型)。真實攻擊面 = **會吃不可信輸入的
工作流腳本**:artifact 內容、git diff replay、GitHub PR 資料、archive 路徑,以及對這些輸入跑的 regex。

### 2.2 發現總表

| ID | 嚴重度 | 標題 | 位置 | 狀態 |
|---|---|---|---|---|
| REDOS-01 | **Critical** | `RESEARCH_SOURCES_ENTRY_PATTERN` 的 `.+\..+` 災難性回溯;~2KB 輸入 hang 15s | `guard_status_validator.py:174-176` | 實測確認 |
| REDOS-02 | **High** | `CITATION_PATTERN` 雙重無界填充;~40KB 輸入 hang 23.8s | `guard_helpers/markers.py:7-16`(+ gsv 重複) | 實測確認 |
| F-01 | **High** | SSRF + token 外洩:`urlopen` 跟隨 redirect 會把 `Authorization: Bearer` 轉送到 redirect 目標 | `guard_status_validator.py:448-450` | 機制確認(bandit B310) |
| SEC-LEAK | Medium | 秘密掃描器把命中整行 `excerpt` 印進 stdout/JSON/SARIF(等於複製秘密進 CI log) | `repo_security_scan.py:388-503` | 確認 |
| SEC-FN | Medium | 秘密規則漏抓:Slack/Google/Stripe(寫成 `sk-`)/AWS secret 後半/JWT 等 | `repo_security_scan.py` | 確認 |
| ARG-INJ | Medium | `Base/Head Ref` 未驗即進 `git rev-parse`,可注入 `--git-dir=` 類參數(影響有限) | `guard_status_validator.py:595-700` | 確認 |
| CI-01 | Medium | `workflow_dispatch` inputs 經 `${{ }}` 拼進 `run:`(template-injection) | `large-scale-experiments.yml` | **✅ 已修(本次)** |
| CI-02 | Medium | 同 job 持 `contents: write` + 保留 token → 注入碼可 push 未保護分支 | `large-scale-experiments.yml` | 緩解 |
| CI-03 | Low | weekly-council-audit 跑浮動 `@latest` 且同時持 write + secret | `weekly-council-audit.yml` | 待評估 |

### 2.3 已澄清(查核後無虞)

- **無** zip-slip(archive 是純文字路徑 manifest,非壓縮檔)、**無** 目錄穿越突破 `relative_to` 容器檢查。
- **無** `shell=True` / `os.system` / `eval` / `exec` / `pickle` / `yaml.load`(全用 argv-form subprocess)。
- 內嵌 HTTP server 僅 `127.0.0.1` ephemeral port、daemon、context-managed 測試 fixture。
- host allowlist 對 userinfo@/大小寫/port/trailing-dot 繞過具抵抗力(`urlparse().hostname`)。
- 所有 workflow `uses:` 皆 pin 40 字元 SHA;無 `pull_request_target` + 不可信 ref + secret 組合。
- 自製 SAST 規則經查為線性,無 ReDoS。

### 2.4 業界 SAST 進 CI(A)

`security-deep-scan.yml`:Bandit(HIGH/HIGH fail-closed,基線 0)+ Semgrep(`p/python`+`p/bandit`,advisory),
補自製 regex SAST 的盲點。每 PR/push/每週一自動跑。

---

## 3. Guard 校準量測 — 過嚴/過鬆(PR #20)

**問題**:現有 1877 測試 + 100% line coverage 只證明 guard「照程式碼跑」(conformance),
不證明「accept/reject 邊界畫對」(calibration)。本實驗首次系統性量測。

- 方法:SHOULD_PASS(真 artifact → 期望 PASS,失敗即 **FP=過嚴**);SHOULD_FAIL(5 類標註腐化 →
  期望被擋,放行即 **FN=過鬆**)。全在 temp copy 操作,真實樹不動。

| Guard | TP | TN | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| `guard_contract_validator` | 1 | 1 | **0** | **0** | 1.000 | 1.000 |
| `guard_status_validator` | 20 | 18 | **0** | **0** | 1.000 | 1.000 |

腐化類別(各 4 例,全數攔截):刪必填 metadata、非法狀態、壞 timestamp、缺 lifecycle artifact、>512KB 超大;
外加 1 例 root/template 分歧(contract guard 攔截)。

> **結論:受測類別內既不過嚴也不過鬆。**
> 誠實限制:SHOULD_PASS 語料是「以通過 guard」挑出的,無法回溯「曾被誤擋而從未提交」的 artifact。

---

## 4. 變異測試 — 測試盲點(PR #20)

**問題**:line coverage 100% ≠ 測試能抓到「guard 被改鬆/改嚴」。用自包含 AST mutation runner
(零外部依賴)把 guard 改鬆/改嚴,看既有測試抓不抓得到。survived = 盲點。

| Module | Mutants | Killed | Survived | Score |
|---|---:|---:|---:|---:|
| `sast_gate.py` | 35 | 31 | 4 | 88.6% |
| `security_txt_gate.py` | 48 | 40 | 8 | 83.3% |
| `release_gate.py` | 54 | 46 | 8 | 85.2% |
| **TOTAL** | **137** | **117** | **20** | **85.4%** |

### 4.1 最值得補的兩個邊界盲點

- `security_txt_gate.py:149` `expires <= now` → `<` **無測試覆蓋**(剛好「現在」過期不被標記 stale)。
- `security_txt_gate.py:152` `days_out > max_validity_days` → `>=` **無測試覆蓋**(RFC-9116 一年效期 off-by-one)。

其餘 18 個 survived 多為 exit-code 常數(如 `EXIT_FAIL=1`→`2`)、`required=True`→`False` 的 argparse
flag、與長度/頁數常數,無測試 pin。

> **結論:85.4% < ~100% line coverage,實證「覆蓋率 ≠ 變異充分性」。** 補上述 boundary 測試可直接消除。

---

## 5. 新增的 CI 永久防線

| Workflow | Job | 行為 |
|---|---|---|
| `security-deep-scan.yml` | bandit | HIGH/HIGH **fail-closed**(新出現的高危即擋) |
| | semgrep | advisory,寫入 job summary |
| `guard-calibration.yml` | calibration | **fail-closed** — 任何 guard 出現 FP/FN 即擋 PR |
| | mutation | 分數寫入 summary,低於 floor **0.80** 即失敗 |

> 觸發:PR / push master / 每週一 / 手動。三個排程已在 master(default branch),會自動跑。

---

## 6. 待辦與建議(issue #21)

### 6.1 安全修補(依優先序)

1. **REDOS-01(Critical)** — 以欄位切割解析取代 `.+\..+`,或加每行長度上限 + wall-clock 預算。
2. **REDOS-02(High)** — 收斂雙重填充(或加 `')' in item` precheck);**root + template 兩份同步修**。
3. **F-01(High)** — 自訂 redirect handler,跨 host 不轉送 `Authorization`;每次 redirect 重驗 allowlist。
4. **SEC-LEAK / SEC-FN(Medium)** — excerpt 改遮罩;補秘密規則格式。

### 6.2 測試盲點

5. 補 `security_txt_gate.py:149/152` 兩個 boundary 測試(BND-01/02)。
6. 視需要 pin 其餘 18 個 survived mutants。

### 6.3 為何「現在不修」是對的

- **F-01 無人值守時 unreachable**:5 個排程(experiments/deep-scan/calibration/weekly-audit/threat-model)
  皆**不呼叫** `guard_status_validator`;網路抓取僅在顯式傳 `--pr-number` 時觸發。
- **REDOS** 只在 `workflow-guards`(push/PR)被惡意 artifact 觸發,且被 CI job timeout 擋住——
  可用性問題,非外洩/RCE,且本 repo 為 single-owner、無敵意 PR 流量。
- guard 屬 **security-critical + template-synced + single-writer**:**無人複核就急改、再自動合併的風險,
  高於這些休眠 bug 本身**。故維持「回國親手 review 再修」。

### 6.4 修補注意事項

- 每筆 guard 修補需同步 `template/` 對應檔 + 跑 `guard_contract_validator.py --root .`。
- 每筆須附 regression / boundary 測試(ReDoS 用 timeout-based 測試證明不再 hang)。

---

## 7. Build Guarantee(完成證據)

| 交付 | 證據 |
|---|---|
| 兩個大型實驗 + 每日排程 | PR #18 → master `e80735a` |
| 安全評估 6 報 + SAST + CI-01 修補 | PR #19 → master `223cd5a` |
| 校準 + 變異 + CI gate | PR #20 → master `0115228` |
| guard 待修追蹤 | issue #21 |
| 兩 harness 實跑 | calibration ~14.2s / mutation ~51.8s,輸出皆 committed |

所有 PR 之 CI 皆全綠後 squash 合併;harness 皆於 temp copy 操作、不動真實樹。

---

## 8. 誠實限制(總表)

1. calibration SHOULD_PASS 以「通過 guard」挑出,無法回溯歷史誤擋。
2. mutation gate 僅涵蓋 3 模組;**新增 guard 不會自動納入**(`DEFAULT_TARGETS`)。
3. mutation 未涵蓋 `guard_helpers/{markers,parsers,io}.py`(test shim 在 temp 隔離下 repo-root 偵測失敗)。
4. premortem backtest 之 plan↔verify 非嚴格因果,為校準資料集而非精確命中率。
5. 安全評估範圍限 `artifacts/scripts/**` 與 `.github/workflows/**`;CI-03 標為「待評估」。
6. F-01 標「機制確認」而非端到端 PoC(避免實際外送 token)。

---

_本報告為自走交付之彙總入口;逐項細節見 `artifacts/experiments/` 各子目錄與對應分報。_
