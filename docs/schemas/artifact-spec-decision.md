# Artifact Spec: decision

> 本檔由 `docs/artifact_schema.md` §5.7 拆分而來；schema literal、欄位定義、字串契約皆與原檔逐字對齊。

## 5.7 Decision Artifact Schema

> PDCA Stage: 跨層橫切（cross-cutting；可承接任一階段之衝突、取捨或 routing override）

檔名：`artifacts/decisions/TASK-001.decision.md`

用途：處理衝突、取捨、補查決策與流程分歧。

必填區段：

```md
# Decision Log: TASK-001

## Metadata
- Task ID:
- Artifact Type: decision
- Owner:
- Status: done
- Last Updated:

## Decision Class

## Affected Gate

## Scope

## Issue

## Options Considered

## Chosen Option

## Reasoning

## Implications

## Expiry

## Linked Artifacts

## Follow Up
```

若 decision 用於 guard waiver，需額外提供：

```md
## Guard Exception
- Exception Type:
- Scope Files:
- Justification:
- Override_Reason:
```

若 decision 涉及高風險或外部可見之變更（guard/schema/report/CI gate/預設值/可觀察輸出），建議額外提供（TASK-1108，Reversibility & Blast Radius / Separation of Duties / Least Privilege 三個治理視角之落點）：

```md
## Reversibility & Blast Radius
- Reversibility: reversible | partially_reversible | irreversible | unknown
- Blast Radius: local | module | repo | external_consumers | unknown
- Rollback Plan:
- Reviewer Independence:
- Least Privilege Notes:
```

`## Reversibility & Blast Radius` 規則：本區段為**可選**，無自動 validator 強制；`Reversibility` 與 `Blast Radius` 之 `unknown` 值視為「尚待查明」，不得等同安全、低風險或零風險，選填 `unknown` 時須於 `Reasoning` 補充查明計畫。本區段唯一既有消費者為後續審查者與週期性 architect review（見 `docs/sop/rule_lifecycle_audit.md`）；未來若有自動化強制需求，須依實際使用資料另立 task 評估（Occam's Razor + Gall's Law：無消費者不強制、無使用資料不預先重機制化）。

若 decision 部分依據治理指標（firing_count/block_count/warning_count/pass_rate/coverage/evaluation_count/intervention_count 等）作成，或決策本身構成治理規則之建制變動，建議額外提供（TASK-1109，Campbell's Law / Lucas Critique 兩個治理視角之落點）：

```md
## Metrics Policy
- Campbell Risk: low | medium | high | unknown
- High Stakes Metric: true | false
- Gaming Vectors:
  - <plausible gaming vector>
- Metric Interpretation:

## Policy Regime
- Regime ID:
- Changed At:
- Changed By:
- Comparable To Previous: true | false
- Baseline Reset Required: true | false
- Adaptation Expected:
  - <expected behavior adaptation>
- Notes:
```

`## Metrics Policy` 規則：本區段為**可選**，適用於決策部分依據治理指標作成之情境；`Campbell Risk` 之 `unknown` 值視為「尚待查明」，不得等同 `low` 或安全，選填 `unknown` 時須於 `Reasoning` 補充查明計畫（與 `## Reversibility & Blast Radius` 之 `unknown` 語意一致）；`Metric Interpretation` 必須寫明「指標為證據而非自動核准依據」之語意，不得留空；指標值本身不構成裁決之充分理由，不得單獨用以獎勵人為製造之 guard 觸發、警告壓制或淺層測試覆蓋。`## Policy Regime` 規則：本區段為**可選**，適用於決策本身構成治理規則之建制變動（CI gate、guard 定義、telemetry schema、model 角色、escalation 規則、pass/fail 門檻、report 格式或 prompt 政策之變更）；`Comparable To Previous: false` 為預設安全假設，用以防止「新政策降低可見失敗即視為指標改善」之誤判，不代表該案例不重要。兩區段皆無自動 validator 強制，唯一既有消費者為後續審查者與週期性 architect review；未來若有自動化強制需求，須依實際使用資料另立 task 評估（Occam's Razor + Gall's Law）。

何時必須建立 decision artifact：

- 研究結果互相衝突
- 計畫需做取捨
- Codex 提出超出原計畫的必要修改
- 驗收未通過，需決定回退或補改
- 對話內容與 artifact 衝突
- 使用 `--allow-scope-drift` 將 drift 降級為 warning

`Decision Class` 目前固定 taxonomy：

- `scope-drift-waiver`
- `risk-acceptance`
- `defer`
- `reject`
- `conflict-resolution`

`## Guard Exception` 規則：

- `Exception Type: allow-scope-drift` 代表此 decision 是 scope drift 的顯式豁免。
- `Scope Files`: 必須明列此次豁免涵蓋的 drift files，使用逗號分隔；不可只寫 `all` 或留白。
- `Justification`: 必須說明為何這次 drift 可以被受控接受。若 `guard_status_validator.py` 在 `--allow-scope-drift` 模式下找不到對應 waiver，仍會 fail。
- `Override_Reason`: 當使用 `guard_status_validator.py --override ... --override-approver ...` 時，decision artifact 應同步記錄人工核准的 override 理由；此欄位不得只寫 `test` 或空泛字眼，必須能對應 override log 中的 `reason`。

---
