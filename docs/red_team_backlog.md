# Red Team Backlog

本文件記錄紅隊演練後應追蹤的缺口。每一項都必須能對應到具體規則、guard、文件或樣本。

## BKL-001 歷史 diff 重建仍未完全自動化

- 目前狀態：`guard_status_validator.py` 現在除了 dirty worktree 的 git-backed changed-files 比對外，也支援以 pinned `Base Commit` / `Head Commit`、`Changed Files Snapshot` 與 `Snapshot SHA256` 重放 clean task 的 `commit-range` historical diff；若 local git replay 失敗且附有合法 `Archive Path` / `Archive SHA256`，也可改走 archive fallback；若 task 記錄 `Evidence Type: github-pr`，則可透過 GitHub PR files API 重建 changed files。
- 分流定案（2026-07-02）：Branch A 是 dirty-worktree guard；標準 clean CI 不觸發 Branch A 屬設計分流，不是 dead-path bug。證據鏈：`TASK-954` 明文將 commit-range / historical diff reconstruction 列為 Out of Scope；`TASK-955` Background 接續定義 clean worktree task 需依 code artifact 的 historical diff evidence；RT-013 / RT-014 分別覆蓋 dirty worktree 與 pinned historical diff；`guard_status_validator.py` 與 README / schema 文件皆以 dirty worktree versus clean-task replay 描述同一分流。
- 殘餘風險：若 task 沒有記錄 diff evidence、沒有準備 archive file、需要 GitHub 以外的 provider、遭遇 provider auth / rate-limit 問題、或 PR files 超過 GitHub endpoint 上限，guard 仍可能無法自動重建歷史 changed files；目前 ref drift 也只會告警，不會直接阻斷。
- 已裁決（HC-1 A2，2026-07-03）：`## Diff Evidence` 選填 policy 經 human 裁決為**範圍限定的 A2**——僅對觸及 guard／EXACT_SYNC 敏感集（`guard_contract_validator.EXACT_SYNC_FILES` ∪ `artifacts/scripts/guard_*.py`、`run_quality_gates.py`、`workflow_constants.py`）之 clean-task closure（transition into `done`）強制提供 `## Diff Evidence`，其餘 clean task 維持選填。實作見 CHG-012（`guard_status_validator.is_sensitive_guard_path` + `validate_artifact_presence` 之 `enforce_clean_diff_evidence` gate，僅前向適用於新 transition，不回溯既有 done 存量；RT-032 覆蓋）。spot-check#1 確認 `github-pr` / archive replay arms KEEP 為此裁決之前提。原 `TASK-955.decision.md` / `TASK-956.plan.md` 之選填契約於敏感集外仍成立。
- 建議補強：下一輪可加入其他 provider（GitLab / Azure / Bitbucket）、provider response 的長期封存策略、把特定 ref drift / provider precondition 提升為 policy-driven hard fail（`## Diff Evidence` 選填 policy 已由 HC-1 A2 裁決，見上）。

## BKL-002 Contract guard 的 exact-sync 清單需人工維護

- 目前狀態：`guard_contract_validator.py` 以明確檔案清單驗證 root / template 同步。
- 風險：新增 workflow 文件或腳本時，若忘記把檔案加進 exact-sync 清單，就可能產生未受監控的漂移。
- 建議補強：增加 workflow docs registry，或將 `docs/` 內特定命名慣例自動納入 sync 驗證。

## BKL-003 Red-team runner 目前聚焦 repo 內建案例

- 目前狀態：`run_red_team_suite.py` 主要驗證 research contract、premortem、Gate E 與 contract drift。
- 風險：外部工具憑證失效、上游 repo 變動、或第三方 CLI 行為異常等情境仍需額外 drill。
- 建議補強：第二輪加入 environment-precondition drills 與 external dependency drills。

## BKL-004 Scorecard 的最終分數仍需人工判讀

- 目前狀態：runner 可驗證案例是否符合預期，但五個維度的成熟度分數仍需主持人與記錄者填寫。
- 風險：不同演練輪次之間，評分標準可能漂移。
- 建議補強：建立固定評語範本與「0 / 1 / 2」範例，降低主觀差異。

## BKL-005 跨文件引用層級核對檢查項

- 目前狀態：引用兩份文件互證時，尚無結構化步驟要求先核對兩者所述問題之層級與範圍是否同一。
- 風險：字面相似（如同用「必填」「所有 code artifact」）被誤當成同一問題之證據，導致把不同層級／範圍的問題錯接（friction 出處：2026-07-02 scope-drift 調查 session 同型錯誤三次穩定重現，並有 auto-memory 佐證）。
- 建議補強：新增檢查項——引用兩份文件互證前，先核對兩者所述問題之層級與範圍是否同一；字面相似不構成同一問題之證據。

## BKL-006 governance/ superseded 檔歸檔（flag-only 記錄）

- 目前狀態：`governance/` 中約 13 個 superseded 檔零 runtime caller，僅供歷史 evidence-ref 參照（HC-12 降級為 flag-only 記錄，本輪不執行歸檔）。
- 風險：直接歸檔會使既有 evidence-ref 斷鏈，其風險高於目錄可讀性之收益。
- 建議補強：留待未來 evidence-ref 遷移方案一併處理，屆時再評估歸檔；此前維持原位。
