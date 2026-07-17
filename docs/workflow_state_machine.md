# WORKFLOW_STATE_MACHINE

本文件定義 artifact-first workflow 的狀態機。目的不是好看，而是讓流程「不能亂跳」。

沒有 state machine 的系統，本質上就是聊天。

狀態機只定義**合法轉移**；每個狀態真正需要哪些 artifacts，必須再由 `Assurance Level` 與 `Project Adapter` 決定，不能只靠某個 artifact 是否剛好存在來推導。

## 1. 狀態總覽

| 狀態 | 說明 |
|---|---|
| drafted | 任務已建立但尚未研究 |
| researched | 已完成 research artifact |
| planned | 已完成 plan artifact |
| coding | 正在或已完成程式修改 |
| testing | 測試進行中或完成 |
| verifying | 驗收進行中 |
| done | 任務完成 |
| blocked | 任務卡住 |

## 2. 狀態轉移圖（文字版）

```text
drafted
  -> researched
  -> planned（若任務不需要 research，lightweight mode）
  -> blocked

researched
  -> planned
  -> blocked

planned
  -> coding
  -> blocked

coding
  -> testing
  -> verifying
  -> blocked

testing
  -> verifying
  -> coding (若需修復)
  -> blocked

verifying
  -> done
  -> coding (驗收失敗)
  -> blocked

blocked
  -> 任意前一合法狀態（需先建立 `Status: applied` 的 improvement artifact — Gate E）
```

## 3. 每個狀態的進入條件

### drafted
- 已建立 task artifact

### researched
- 存在合法 research artifact

### planned
- 存在合法 plan artifact
- 若需要 research，則 research 必須已完成
- 若任務不需要外部知識，可從 drafted 直接轉移至 planned（略過 researched）

> **Guard 限制**：`guard_status_validator.py` 無法區分任務是否真正需要 research，
> `drafted → planned` 在 validator 層級是全局允許的。
> 跳過 research 的合理性仍由流程與 review 過程確保（見 `docs/orchestration.md`）。

### coding
- plan artifact 存在且 Ready For Coding = yes

### testing
- code artifact 存在

### verifying
- code artifact 存在
- 若有測試需求，test artifact 存在

### done
- verify artifact 存在
- verify result = pass

### blocked
- 任一必要 artifact 缺失
- 或發現衝突/風險/無法繼續

## 4. 非法轉移（必須阻止）

以下行為一律視為錯誤：

- drafted -> coding
- researched -> coding（跳過 plan）
- planned -> done
- coding -> done（未驗證）
- testing -> done（未驗證）
- verifying -> done（未 pass）

## 5. Blocked 規則

進入 blocked 時必須：

- 記錄 blocked_reason
- 指出缺失 artifact
- 指定下一個負責 agent

解除 blocked 條件：

- 缺失 artifact 補齊
- 或 decision log 解決衝突
- **且**必須建立 improvement artifact（Gate E, PDCA）
  - 記錄根因分析、矯正措施、與系統層級預防措施
  - improvement artifact 必須為 `Status: applied`
  - `guard_status_validator.py` 在 `blocked → *` 轉移時自動檢查

### 5.1 Blocked 之二處置別（disposition）

`blocked` sink 涵兩種 disposition，語意與出 sink 之條件迥異：

**(a) stuck-awaiting-resolution（預設、blocked 原義）**：任務因必要 artifact 缺失、衝突、風險或無法繼續而暫停，**待解後 resume**；出 blocked 須依上列解除條件（含 Gate-E `Status: applied` improvement artifact）。即 §1 之「任務卡住」。

**(b) superseded-via-reconciliation terminal（認可終態）**：任務之**實質 obligation 已全由 successor(s) 承載並 reconcile**，本身無工作可 resume，為一**認可之終態**（非待解）。識別條件（**三者全須**滿足）：

1. status.json 具 `superseded_by`（含 `reconciliation_ref` 指向 successor 之 verify）；
2. 該 successor(s) 已 `done`；
3. 對應 decision artifact 之 `## Verified AC Summary` 顯**全 AC 皆有 evidence**（verified／superseded-by-successor／covered，**無 deferred、無待解**）。

此別**不發生任何 exit/resume 轉移**——state **維 `blocked` 作為其 terminal disposition**。Gate-E 係治理「resume 工作」之 `blocked → 前一合法狀態` 轉移；superseded-terminal 無工作可 resume，故 **Gate-E 對其 N/A（非「繞過」）**。

**誠實界（documentary，非 guard-enforced）**：`guard_status_validator.py` **不讀** `superseded_by`／`reconciliation_ref`，仍以 `blocked` 驗此類任務（guard-clean）；本別之 terminal 性由「本節 + status／decision／verify 記載 + review 認定」共同確立，**非 guard enforced**。一般 stuck 任務（不滿足上三條件）**不得**藉此別繞 Gate-E——無 successor-reconciliation evidence 即不適用，§5 之 Gate-E 紀律照舊。

> 例：TASK-1001（v3.4 多階段任務）之 canonical AC 經 TASK-1011 reconcile、AC-5b 經 TASK-1095 resolved，全 AC 有 evidence 而自身無 plan/code → 處置為 superseded-via-reconciliation terminal（見 `artifacts/decisions/TASK-1001.decision.md` §Closing Amendment）。

**(c) abandoned-via-ruling terminal（棄置終態）**：任務標的已消失或經 commander／human ruling 裁定**不再 resume**，本身無工作可續且**無 successor 承載其 obligation**（與 (b) 之關鍵區隔），為一經裁定之**永久棄置終態**（非待解、非 superseded）。識別條件（**三者全須**滿足）：

1. 對應 decision artifact（Decision Class = `risk-acceptance` 或同級）明載 ruling 與**不 resume 理由**；
2. status.json `blocked_reason` 以 `ABANDONED` 起首並含 ruling 日期；
3. **無** `superseded_by`／successor 承載義務（與 (b) 之關鍵區隔）。

此別語義同 (b)：**不發生任何 exit/resume 轉移**，state **維 `blocked` 作為 terminal disposition**，**Gate-E 對其 N/A（非「繞過」）**。**限縮**：僅 commander／human ruling ＋ decision artifact 方可適用；一般 stuck 任務（無 ruling）**不得**藉此別繞 Gate-E。

> 例：TASK-901（標的 `external/Wino-Mail/` 自 workspace 移除）經主公 2026-06-13 裁 abandon → status `blocked_reason` 標 `ABANDONED (commander ruling 2026-06-13)`、無 successor（見 `artifacts/decisions/TASK-901.decision.md` §Amendment (2026-06-13)）。

## 6. 強制規則

1. 每次狀態變更必須更新 status.json
2. 狀態必須與實際 artifacts 一致
3. 不允許「口頭完成」狀態
4. 不允許跳過中間狀態
5. Every plan must be testable and mappable to code and verification artifacts
6. Implementation must not introduce changes not explicitly mapped to plan
7. verify 必須逐條對應 acceptance criteria
8. After any failure or blocked state, a Process Improvement artifact with `Status: applied` must exist before resuming workflow (Gate E)

## 7. 設計原則

- 狀態數量刻意少，避免複雜化
- 每個狀態對應明確 artifact
- 任何人都能從 artifacts 重建狀態

如果一個狀態不能用檔案證明存在，那它就不該存在
