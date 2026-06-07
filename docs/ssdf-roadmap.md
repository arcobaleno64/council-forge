# P8 Roadmap — council-forge SSDLC Formalization（使能 → 強制）

> 狀態：**規劃中（未實作、未 commit 之草案，俟主公定案）**。本檔將 prose 缺口分析化為
> 可分階執行之 governed roadmap。**映射而非再造**；**最輕適足**；各營分治啟用；以
> conformance guard 使「缺口不得無聲復長」。
> 對標：**NIST SSDF SP 800-218 v1.1**（PO/PS/PW/RV）。

## 0. 目標與原則

- **目標**：由「security-flavored governance（使能 SSDLC）」進為「named, auditable, **enforced** conformance（強制 SSDLC）」。
- **不為**：不造平行 SSDLC 機器；不對每營強加統一 CI；不以重工具淹沒 gate。
- **原則**：
  1. **映射而非再造**——先名標準、映既有機制，缺口方補。
  2. **最輕適足**——每 practice 以最低 false-positive、最高訊號之工具補。
  3. **分治啟用**——母本只置 template/gate；啟用依各營狀態（凍結/remote/stack）裁之。
  4. **evidence-over-assumption**——conformance 由 guard 守（有機制 or logged gap/waiver），非自陳。

## 1. SSDF Practice Coverage Matrix（核心——P8-A 將其機器化）

狀態圖例：✅ 已有機制｜🟡 部分／繫於實作者｜❌ gap（待補）

| SSDF practice | council-forge 既有機制 | 狀態 | 缺口/補強 → 階 |
|---|---|---|---|
| **PO.1** 定義安全需求 | premortem 必備、AC 可含安全條目 | 🟡 | 模板強制「安全 AC」欄 → P8-A |
| **PO.2** 角色與責任 | single-writer、Gemini read-only、CLAUDE/CODEX/GEMINI 分權、RACI | ✅ | — |
| **PO.3** 支援工具鏈與完整性 | artifact-first、guards、wrappers、EXACT_SYNC | ✅ | 工具鏈完整性宣告 → P8-A |
| **PO.4** 軟體安全檢核準則與歸檔 | coverage gate、verify Build Guarantee、status state machine | 🟡 | 明文「security check criteria」+ release 歸檔 → P8-A/D |
| **PO.5** 安全開發環境 | secret hygiene（placeholder+env、拒空 secret、禁 prompt 載密） | 🟡 | 環境分離宣告（dev/prod env injection 已實踐） → P8-A |
| **PS.1** 防碼竄改/未授權存取 | EXACT_SYNC、**drift_dashboard / propagate**（P7/P7-B）、git | ✅ | — |
| **PS.2** 提供 provenance（SBOM） | — | ❌ | **SBOM 生成**（syft/cyclonedx；Rust+npm+.NET） → **P8-C** |
| **PS.3** 歸檔保護各 release | git tag、verify 之 commit anchor | 🟡 | release 歸檔 + checksum + 簽章 schema → **P8-D** |
| **PW.1** 設計合安全需求（威脅建模） | premortem 紅線、下游 threat-model（LINE-BOT STRIDE） | 🟡 | 母本「威脅建模」模板（非僅 premortem） → P8-A/D |
| **PW.2** 審查設計 | critic/architect agent、decision log | ✅ | — |
| **PW.4** 復用安全元件（**SCA**） | 無依賴漏洞掃描 | ❌ | **SCA**（pip-audit / `dotnet list package --vulnerable` / `cargo audit` / `pnpm audit`） → **P8-B** |
| **PW.5** 安全編碼 | AGENTS.md 專案紅線、scope-drift guard | 🟡 | 安全編碼 checklist 模板 → P8-A |
| **PW.6** 安全建置組態 | wrapper、build guarantee | 🟡 | 建置 hardening 宣告（reproducible/pinned） → P8-C |
| **PW.7** 審查/分析碼（**SAST**） | code-review/red_team、guards（治理 conformance，非碼安全屬性） | 🟡 | **SAST**（CodeQL/semgrep；.NET analyzers；clippy 已有） → **P8-C** |
| **PW.8** 測執行檔（DAST/fuzz） | red_team suite + scorecard | 🟡 | DAST/fuzz 模板（webhook/API 面，如 LINE-BOT） → P8-D（選擇性） |
| **PW.9** 安全預設組態 | placeholder + env 注入、CSP（下游 Tauri/.NET 已實踐） | 🟡 | 「secure-by-default」宣告模板 → P8-A |
| **RV.1** 識別/確認漏洞 | repo_security_scan（偏 secret/紅隊）、無 SCA/disclosure intake | ❌ | **secret-scan**（gitleaks/trufflehog）+ **SCA** + **vuln-disclosure** schema → **P8-B/D** |
| **RV.2** 評估/排序/修補 | decision log、status、waiver | 🟡 | patch-SLA + 漏洞分級模板 → **P8-D** |
| **RV.3** 根因分析 | premortem、improvement/PROCESS_LEDGER | ✅ | IR 根因模板 → P8-D |

**揭示之硬 gap（❌）**：PS.2（SBOM）、PW.4（SCA）、PW.7（SAST）、RV.1（secret-scan/SCA/disclosure）。**最輕高效先補者＝RV.1 之 secret-scan + PW.4 之 SCA**（語言工具成熟、低 FP、高訊號）。

## 2. 分階任務（每階為 council-forge SSOT governed task，含 premortem + cov gate + guards）

- **P8-A（基石，TASK-1077）— SSDF mapping + conformance guard**
  - `docs/ssdf-mapping.md`：本 matrix 之正式化（每 practice：mechanism ref / status / evidence / gap-waiver）。
  - `ssdf_conformance_validator.py`（source-only）：解析 mapping，校每 practice 為 ✅(有 mechanism+evidence ref) 或具 `logged gap/waiver`（decision 引用），否則紅。納 cov gate。
  - 強制 task/plan 模板含「Security Requirements / Threat」欄（PO.1/PW.1）。
  - **產出 = (b)(c) 之 backlog**（matrix 之 ❌/🟡 即工單）。

- **P8-B（最輕實控，TASK-1078）— secret-scan + SCA gate**（RV.1 / PW.4）
  - secret-scan：gitleaks（或 trufflehog），全 repo。
  - SCA：`pip-audit`（council-forge 自身）、`dotnet list package --vulnerable`（Sentinel/LINE-BOT）、`cargo audit` + `pnpm audit`（Verso/Vero）。
  - 形式：council-forge `template/.github/workflows/security-scan.yml` 強化 + 一 source-only orchestrator；**opt-in**（下游 CI template，非強啟）。

- **P8-C（較重，TASK-1079）— SAST + SBOM**（PW.7 / PS.2 / PW.6）
  - SAST：CodeQL 或 semgrep（多語）；.NET analyzers；clippy（Rust，已有）。
  - SBOM：syft 或 cyclonedx（Rust+npm+.NET），附 release。
  - 語言相關、FP 較高 → 後於 B。

- **P8-D（release/operations，TASK-1080）— release/IR governed 模板**（PS.3 / RV.1-3 / PW.8）
  - schemas：code-signing（EV cert）、patch-SLA、vuln-disclosure（intake + 90-day）、IR-runbook、release-archive（checksum/簽章）。
  - DAST/fuzz 模板（選擇性，webhook/API 面）。

- **P8-E（收束，TASK-1081）— 各營啟用 + conformance dashboard**
  - 將 ssdf conformance 納 drift/health dashboard（per-downstream SSDF 覆蓋率視圖）。
  - 各營啟用矩陣落地（見 §3）。

## 3. 各營啟用策略（分治）

| 營 | stack | CI/remote | 啟用策略 |
|---|---|---|---|
| **Sentinel** | .NET（政府、**凍結**） | Azure Pipelines | 凍結期**僅置 template**，不啟、不動 azure-pipelines；解凍後由其自有 CI 掛 gate。最強合規對象。 |
| **LINE-BOT** | .NET（活躍） | GitHub Actions（docker-publish） | 可 **opt-in** council-forge 安全 workflows 至 GitHub Actions；secret-scan/SCA 最切（AI keys、LINE secret）。 |
| **Verso** | Tauri（Rust+TS，本地無 remote） | 無 | 本地 / pre-commit 跑 gate；SBOM（cargo+pnpm）；無 CI 可掛。 |
| **Vero** | Tauri（Rust+TS，本地無 remote） | 無 | 同 Verso；evidence-zip 安全模型尤重 SCA。 |

## 4. 事前驗屍（Premortem）

| # | Risk | Trigger | Mitigation | Sev |
|---|---|---|---|---|
| R1 | 疊床架屋——造平行 SSDLC 機器 | 重寫既有為 SSDF 結構 | conformance guard **引用**既有機制；映射而非再造；最輕工具 | blocking |
| R2 | 偽 conformance——mapping 高估覆蓋 | practice 標 ✅ 而機制薄弱 | 每 practice 須 evidence ref；薄者標 🟡/gap+waiver；外部 review | blocking |
| R3 | 工具噪訊——SAST/secret-scan 高 FP 淹沒 gate | 啟高-FP 工具為強 gate | 先 B（低 FP：gitleaks/pip-audit）；waiver via decision；C 後置且可 advisory | blocking |
| R4 | 語言/CI 異質——4 營 2 stack 異 CI 面 | 強加統一 CI | per-downstream 啟用矩陣；template + opt-in；不強啟 | blocking |
| R5 | 凍結/無 remote 營無法跑 CI gate | 將 gate 設為 mandatory-on | template-only + 本地/pre-commit 模式；gate 為 opt-in | non-block |
| R6 | scope 蔓延——19 practice 一次全做 | 無優先序 | 分階；P8-A 揭優先 gap；先補最高風險（RV.1/PW.4） | blocking |
| R7 | 掃描洩密——secret-scan/SBOM surface 機密 | 對含真機密之 repo 跑且 log | 各營已驗無真機密（placeholder+env）；SBOM 排除 secret；掃描輸出不入庫 | blocking |
| R8 | 工具供應鏈——引入 gitleaks/syft 等本身為依賴 | 未釘版/未驗來源 | 釘版 + checksum；母本 model-allowlist 之延伸（tool-allowlist） | non-block |

## 5. 序列、依賴、優先

```
P8-A (mapping+conformance guard, keystone)
   │  ← 揭 gap、定 backlog、強制安全 AC 欄
   ├─► P8-B (secret-scan + SCA)   ← 最輕高效，先
   ├─► P8-C (SAST + SBOM)         ← 較重，後
   └─► P8-D (release/IR 模板)
                 └─► P8-E (各營啟用 + conformance dashboard)
```

- **建議首工＝P8-A**（基石，無 mutation、低風險、最高槓桿；產出後續 backlog）。
- 依賴：P8-B/C/D 皆繫於 P8-A 之 mapping 揭示之 gap 與 evidence 規格；P8-E 繫於 B/C/D 落地。
- 每階：governed lifecycle（task/plan/code/test/verify/status）+ premortem + cov gate（source-only 工具 100%）+ 母本 guards 不退 + 本地 commit、未 push。

## 6. 估量

| 階 | 規模 | 風險 | 主要產出 |
|---|---|---|---|
| P8-A | 中 | 低（無 mutation） | mapping doc + conformance validator + 模板安全欄 |
| P8-B | 中 | 中（FP、CI 異質） | secret-scan/SCA gate template + orchestrator |
| P8-C | 大 | 中-高（語言相關、FP） | SAST/SBOM template（多語） |
| P8-D | 中 | 低-中 | release/IR schemas |
| P8-E | 中 | 低 | 啟用矩陣 + conformance dashboard |

## 7. 定案待裁項（主公）

1. 是否採此 roadmap 為 P8 基準（或調整對標框架/範圍）。
2. 首工確認（建議 P8-A）。
3. 工具選型偏好（secret-scan：gitleaks vs trufflehog；SAST：CodeQL vs semgrep；SBOM：syft vs cyclonedx）。
4. 各營啟用紅線（尤 Sentinel 凍結、Verso/Vero 無 remote 之 gate 形式）。
5. 本 roadmap 是否即 commit 為 council-forge 規劃 artifact。
