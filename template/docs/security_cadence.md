# Security Cadence

> 本檔為 council-forge repo 之 security / governance cadence 單一真實來源。彙整 weekly Claude routine review、quarterly threat model、continuous SAST 三層 cadence 之 trigger / cadence / artifact destination / owner，並列 user-side setup steps 與 cadence drift recovery 流程。

任何修改 `.github/workflows/security-scan.yml`、`.github/workflows/quarterly-threat-model.yml`、`.github/prompts/weekly-claude-audit.prompt.md` 之 PR 應同步更新本檔對應段；反之亦然。doc-yml drift 屬 governance risk（per `artifacts/plans/TASK-1058.plan.md` §Risks R4），於 weekly Claude routine review 之 doc-sync 維度被監測。

## Weekly Claude Routine Review

| 欄位 | 內容 |
|---|---|
| Trigger | user-side `/schedule` 建之 Claude Code Cloud Routine |
| Cadence | 每週 1 次（建議 Sunday 02:00 local；Cloud Routines 最短 1 hour interval，weekly 遠寬） |
| Artifact Destination | `artifacts/reviews/weekly-<YYYY-MM-DD>/<commit-range>.md`，於 `claude/weekly-audit-<YYYY-MM-DD>` branch 經 PR 合入 master |
| Owner | routine creator（user 個人 Claude 帳號）+ PR reviewer |
| Source Prompt | `.github/prompts/weekly-claude-audit.prompt.md` |
| Routine Type | Cloud Routine（跑於 Anthropic-managed cloud，fresh clone，無 access local files） |
| Plan Tier | Pro / Max / Team / Enterprise（須啟用 Claude Code on the web） |

review 涵蓋 master 過去 7 天 merged commits 之 五維度 risk tagging（security / dependency / scope-drift / doc-sync / test-coverage）。詳見 prompt 檔之 §「Review Scope」與 §「Output Format」。

## Quarterly Threat Model

| 欄位 | 內容 |
|---|---|
| Trigger | `.github/workflows/quarterly-threat-model.yml`（`on.schedule.cron: '30 5 1 1,4,7,10 *'` + `on.workflow_dispatch`） |
| Cadence | 每年 1/4/7/10 月 1 日 UTC 05:30（台灣時間 13:30）；備援 manual `workflow_dispatch` |
| Artifact Destination | reminder issue（labels `security, cadence, quarterly`）；exercise artifact 由 user 依 runbook 產出於 `artifacts/red_team/` 對應路徑 |
| Owner | user（執行 exercise）；issue close 後附 artifact link |
| Runbook | `docs/red_team_runbook.md` |
| Scorecard | `docs/red_team_scorecard.md` |
| Follow-up Backlog | `docs/red_team_backlog.md` |

issue 自動建立後 30 天為建議 deadline；workflow 不執行實際 threat model exercise，僅作 reminder。GitHub Actions schedule 於高負載時段可能延遲（per GitHub 官方文檔），故 cadence drift recovery 必須由 user 季首日 +1 日檢查 issue tracker。

## Continuous: pip-audit / repo-secrets-scan / repo-static-scan

| 欄位 | 內容 |
|---|---|
| Trigger | `.github/workflows/security-scan.yml`（`on: pull_request, push to master, workflow_dispatch`） |
| Cadence | per PR / per push to master / 手動 |
| Artifact Destination | GitHub Actions log；pip-audit 之 `pip-audit-report.json` 落於 run 之 group output |
| Owner | CI 自動 + PR reviewer |
| Components | (a) `pip-audit` 掃 `requirements.txt` CVE；(b) `repo_security_scan.py secrets` 掃 hardcoded credentials；(c) `repo_security_scan.py static` 掃 focused static rules |

continuous 層由既有 workflow 落地（前置 task TASK-* 已建立），本 task 不變動。任何 hardening（fail-on-severity threshold / SBOM 整合 / license audit）屬 future task 範圍。

## Setup Steps

### Weekly Claude Routine

前置條件：
1. Claude Code CLI v2.1.72 或更新（`claude --version` 確認）。
2. 個人 claude.ai 帳號為 Pro / Max / Team / Enterprise plan，且 Claude Code on the web 已啟用。
3. council-forge repo 之 GitHub clone 權限已授予 Claude Code（GitHub OAuth 或 PAT）。

步驟：

1. **授權 GitHub clone**：於本 repo working dir 執行 `claude /web-setup` CLI 命令，依互動 flow 授予 council-forge repo 之 clone access。此步驟不裝 Claude GitHub App（webhook 觸發 routine 用，weekly schedule 不需）。
2. **建立 routine（CLI 路徑）**：於任一 Claude Code session 執行：

   ```text
   /schedule weekly review of last 7 commits on Sunday at 02:00
   ```

   Claude 對話式問 (a) routine name（建議 `weekly-claude-audit`）、(b) repository（選 council-forge）、(c) prompt（貼下方 thin pointer）、(d) environment（採 Default）、(e) connectors（皆移除，本 routine 不需 MCP connector）。
3. **routine saved prompt（thin pointer，貼上即可）**：

   ```text
   Read and execute the workflow described in `.github/prompts/weekly-claude-audit.prompt.md` of this repository. Follow its Mission, Review Scope, Output Format, and Attribution sections precisely. Do not deviate from the destinations and naming conventions specified in that file.
   ```

4. **branch permission**：採 default（Claude 僅可 push 至 `claude/`-prefixed branches；review PR 由 `claude/weekly-audit-<YYYY-MM-DD>` 開向 master）。如需放寬，於 routine edit 之 Permissions tab 開 `Allow unrestricted branch pushes`，但本 cadence 不建議。
5. **首次驗證**：建立後立即於 routine detail page 點 `Run now`，確認 (a) review artifact 正確 commit 至 `artifacts/reviews/weekly-<date>/`；(b) PR title 含 `[claude-routine]` prefix；(c) PR body 含 routine attribution 段。失敗則回到 saved prompt 確認 thin pointer 字面與本檔一致。

### Quarterly Threat Model Workflow

1. **GitHub Actions runtime 確認**：repo `Settings → Actions → General → Workflow permissions` 須為 `Read and write permissions`（既有 `security-scan.yml` 已要求）；`Allow GitHub Actions to create and approve pull requests` 不必開（本 workflow 僅建 issue）。
2. **首次手動驗證**：merge 後於 `Actions → Quarterly Threat Model Reminder` 點 `Run workflow` 手動觸發，確認 issue 正確建立、labels 套用、body 引用正確；錯誤則檢查 `actions/github-script` step 之 log。
3. **季首日確認**：每年 1/4/7/10 月 2 日（首日 +1 日）user 至 Issues tab 確認 `[Quarterly Threat Model]` issue 已建；未建則執 `workflow_dispatch:` 手動觸發。

## Cadence Drift Recovery

### 偵測

| Cadence | 偵測信號 | 偵測週期 |
|---|---|---|
| Weekly Claude routine | 週一檢查 master 是否有 `[claude-routine] Weekly Audit` 之 PR | 週一 |
| Quarterly threat model | 季首日 +1 日檢查 Issues tab 有無 `[Quarterly Threat Model]` issue | 季首日 +1 日 |
| Continuous SAST | PR check status / push to master 之 Actions tab 是否全綠 | 每 PR / push |

### 重啟

- **Weekly routine 漏跑**：(a) `claude.ai/code/routines` 確認 routine 未被 paused / quota 是否耗盡；(b) routine detail page 點 `Run now` 補跑；(c) 若連續 2 週漏跑，建 decision artifact 記 outage + root cause（如 plan downgrade、token rotate、GitHub auth lapse）。
- **Quarterly issue 漏建**：(a) `Actions → Quarterly Threat Model Reminder` 點 `Run workflow` 手動觸發；(b) 若 cron 連續 2 季漏觸發（≥6 個月），建 decision artifact 並檢 GitHub Actions schedule disable 風險（公開 repo 60 天無活動規則於本 repo 不適用，但 schedule 高負載延遲為已知風險）。
- **Continuous SAST 紅**：依 PR check log 修；不得 force-merge bypass。

### Escalation

任何 cadence outage 之 root cause 不明、或對應 mitigation 失效時，建 `artifacts/decisions/TASK-<id>.decision.md` 記錄：(a) outage 起訖；(b) detection 路徑；(c) suspected root cause；(d) mitigation 嘗試；(e) follow-up task ID（若需）。決定 artifact 由 user 簽核後關閉。
