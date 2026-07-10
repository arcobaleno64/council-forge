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
