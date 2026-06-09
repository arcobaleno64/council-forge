# council-forge ↔ NIST SSDF SP 800-218 v1.1 Mapping

> **本檔校 mapping 完整性，非 SSDLC 認證。** `ssdf_mapping_validator.py` 只能機器校
> 每列之 ref 是否 **resolve 至真實 repo 位置**（path / path#heading-slug / path:line），
> 與每一 gap 之 waiver 是否具結構化 `SSDF-Gap-Waiver: <practice_id>` marker。機器**不能**
> 判斷機制之**質性效力**——該由雙對抗審查（codex+gemini）+ human-review ack 把關。
> 故本檔之綠（validator exit 0/3）僅表「mapping 結構完整且誠實」，**絕非**「已達 SSDLC 認證」。

## Status 詞彙

- `covered`：有實機制，且 Mechanism 與 Evidence ref 皆 resolve。
- `partial`：機制存在但繫於實作者或不全（覆蓋未完）。
- `gap`：無機制；Gap/Waiver 須具結構化 waiver marker（見 `docs/ssdf-roadmap.md` §8）。

## Canonical 出處

NIST SSDF **SP 800-218 v1.1**（PO/PS/PW/RV，**19 practices**）。**核實日 2026-06-07**（codex
對抗審查對官方 publication 證實 19-set；**PW.3 於 v1.1 已移除**，故不列）。出處：
https://doi.org/10.6028/NIST.SP.800-218

## Exit 語意（誠實，杜虛假認證）

`0`=結構有效且全 19 covered｜`3`=結構有效但有 open items（partial/gap）｜`2`=完整性違規｜`1`=usage/IO。

## Mapping

| Practice | Title | Status | Mechanism | Evidence | Gap/Waiver |
|---|---|---|---|---|---|
| PO.1 | Define Security Requirements | partial | docs/premortem_rules.md | CLAUDE.md | — |
| PO.2 | Roles and Responsibilities | covered | CLAUDE.md | GEMINI.md | — |
| PO.3 | Supporting Toolchains | covered | artifacts/scripts/guard_contract_validator.py | docs/artifact_schema.md | — |
| PO.4 | Criteria for Software Security Checks | partial | docs/artifact_schema.md | .github/workflows/workflow-guards.yml | — |
| PO.5 | Secure Software Development Environments | partial | CODEX.md | GEMINI.md | — |
| PS.1 | Protect All Forms of Code | covered | artifacts/scripts/drift_dashboard.py | artifacts/scripts/propagate_downstream.py | — |
| PS.2 | Provide a Mechanism for Verifying Software Release Integrity | partial | artifacts/scripts/release_gate.py | .github/workflows/security-scan.yml | — |
| PS.3 | Archive and Protect Each Software Release | partial | artifacts/scripts/sbom_gate.py | .github/workflows/security-scan.yml | — |
| PW.1 | Design Software to Meet Security Requirements | partial | docs/premortem_rules.md | CODEX.md | — |
| PW.2 | Review the Software Design | covered | docs/orchestration.md | CLAUDE.md | — |
| PW.4 | Reuse Existing, Well-Secured Software (SCA) | partial | .github/workflows/security-scan.yml | requirements.txt | — |
| PW.5 | Create Source Code Adhering to Secure Coding Practices | partial | AGENTS.md | CODEX.md | — |
| PW.6 | Configure the Compilation, Build, and Packaging Process | partial | artifacts/scripts/scaffold_downstream.py | .github/workflows/workflow-guards.yml | — |
| PW.7 | Review and/or Analyze Human-Readable Code (SAST) | partial | artifacts/scripts/sast_gate.py | .github/workflows/security-scan.yml | — |
| PW.8 | Test Executable Code | partial | artifacts/scripts/run_red_team_suite.py | docs/red_team_runbook.md | — |
| PW.9 | Configure Software to Have Secure Settings by Default | partial | docs/orchestration.md | GEMINI.md | — |
| RV.1 | Identify and Confirm Vulnerabilities (secret-scan/SCA/disclosure) | partial | artifacts/scripts/repo_security_scan.py | .github/workflows/security-scan.yml | — |
| RV.2 | Assess, Prioritize, and Remediate Vulnerabilities | partial | artifacts/scripts/guard_status_validator.py | docs/artifact_schema.md | — |
| RV.3 | Analyze Vulnerabilities to Identify Root Causes | covered | docs/premortem_rules.md | artifacts/improvement/PROCESS_LEDGER.md | — |

> **PW.7（SAST）侷限聲明（P8-C，2026-06-07）**：`partial` 而非 `covered`。機制＝
> `sast_gate.py`（fail-closed SARIF gate）；evidence＝`.github/workflows/security-scan.yml`
> 之**運行中** `python-sast` job——`repo_security_scan.py sast` 跑 Python regex SAST，
> findings 經 `sast_gate.py` durably 暴露於 `$GITHUB_STEP_SUMMARY` 供審。此為 **advisory
> detection（visibility）**：SAST 運行且 findings 可審，**非 enforced remediation**——advisory
> exit 0、不 fail CI、未全語言 enforcing（下游 .NET analyzers / Rust clippy 為各營 native
> 機制，opt-in 模板見 `docs/templates/security/downstream-sast.yml`）。**正因 advisory-first
> 故 `partial`**。轉 enforcing（baseline + waiver + per-language 序）與 PW.7→`covered` 之升等
> 為後階 governed task（見 `docs/ssdf-roadmap.md` §8 與該 task plan §Enforcement Transition），
> 須過雙對抗審查 gate。

> **PS.2/PS.3（SBOM）正名與侷限聲明（P8-C2，2026-06-07）**：4-agent recon 逐字核 NIST SP
> 800-218 v1.1 揭——**PS.2 verbatim 標題＝「Provide a Mechanism for Verifying Software
> Release Integrity」，論雜湊與 code-signing（PS.2.1 例皆 hash/CA-signing），非 SBOM**；
> **SBOM 實屬 PS.3.2**（「...share provenance data... e.g., in a software bill of materials
> [SBOM]」，居 PS.3「Archive and Protect Each Software Release」）。故 council-forge 前
> 「PS.2…(SBOM)」為 **P8-A 誤植，已正**：① **PS.2** 復 verbatim 標題（release-integrity，非 SBOM）；
> 其 status 後於 **P8-D2** 由 `gap` 升 `partial`（under-claim 校正，見下 P8-D2 footnote）；
> ② **PS.3** 以 `sbom_gate.py` + `.github/workflows/security-scan.yml` 之運行中 `sbom` job
> 強化（PS.3.2 provenance facet：cyclonedx-py 由 **resolved 環境**生成 SBOM、捕 transitive、
> sbom_gate 驗之）。**PS.3 仍 `partial` 非 `covered`**：archive facet（PS.3.1）僅 via status/
> commit anchor，**deferred** 簽章/sharing-to-acquirer→P8-D。**completeness 邊界（誠實）**：
> sbom_gate **fail-closed** 驗 well-formedness + presence（`--min-components`）+ **直接依賴
> identity**（`--require-components`）；**窮盡 transitive completeness vs 真實 dep graph 為
> explicitly ACCEPTED RISK**——無 gate 能獨立斷（否則須自為生成器或另信一完整性同不可證之
> enumerator，無限回歸），由 resolved-env 配方 + identity + 恆印 advisory 共治，殘留以
> §Transitive-Completeness Follow-up 之非阻斷週期審計觀測。

> **RV.1/RV.2/RV.3（vuln-disclosure & response）強化（P8-D，2026-06-08）**：recon 逐字核 NIST——
> **RV.1.3**＝「Have a policy that addresses vulnerability **disclosure** and remediation...」。
> council-forge 立**運行中之 disclosure intake**：`SECURITY.md`（CVD policy：private intake /
> best-effort ack / 90-day coordinated window / safe-harbor）+ `.well-known/security.txt`
> （RFC 9116），由 `artifacts/scripts/security_txt_gate.py` 於 `.github/workflows/security-scan.yml`
> 之 `security-txt` job **per-PR + 每週 schedule** fail-closed 驗（well-formed + 必備 field +
> Expires 未過期）。**RV.1 仍 `partial`**（RV.1.2 之 code-analysis=SAST 為 advisory；強化 evidence
> 非升 covered）。**RV.2**：`SECURITY.md` 載**自訂 patch-prioritization**（CVSS-tiered + CISA KEV
> override，**明標非 NIST SP 800-218 數值**——NIST RV.2 為 risk-based 無定數）；仍 `partial`（policy
> 非 enforced）。**RV.3**（covered）：`docs/incident-response-runbook.md`（NIST SP 800-61 detect→
> triage→contain→eradicate→recover→**post-incident/root-cause**→PROCESS_LEDGER）為其操作骨架。
> **誠實界**：security_txt_gate 驗檔之語法/結構/未過期，**不能**驗 Contact 真達責任人/URL 可達/
> 非惡意（無網路 fetch）——**語義可信屬 human-review**（security.txt 變更之 PR review + policy
> owner）。**release-integrity（PS.2）析出 P8-D2**（後於 P8-D2 由 `gap` 升 `partial`，見下 P8-D2 footnote）。
> 映 `docs/security_cadence.md`（cross-ref）。

> **PS.2（release-integrity）under-claim 校正（P8-D2，2026-06-08）**：4-agent recon 逐字核 NIST SP
> 800-218 v1.1——**PS.2.1**＝「Make software integrity verification information available to software
> acquirers」（notional examples：張貼 release 之 cryptographic hashes、CA code-signing、定期審簽章流程），
> **artifact-type-agnostic**。前態（P8-C2/P8-D）稱 PS.2「council-forge 無二進位 release→covered 結構不可
> 達」**實為 under-claim**：「不產編譯 artifact」≠「不釋出 release artifact」——council-forge 經
> `propagate_downstream.py` 釋出之 `template/` SSOT snapshot **即真實 release artifact**（governance 檔
> 樹亦 software，竄改正威脅之）。故 **PS.2 由 `gap` 升 `partial`**：機制＝`artifacts/scripts/release_gate.py`
> （fail-closed checksums-manifest 結構 gate）+ `artifacts/scripts/snapshot_manifest.py`（content-addressed、
> **可獨立復現**之 manifest 生成，source-only）；evidence＝`.github/workflows/security-scan.yml` 之**運行中**
> `release-integrity` job（`snapshot_manifest.py verify` regenerate-diff + `release_gate.py` 結構驗
> `.well-known/release-manifest.json`，step-level guarded by `.council-forge-source-repo`；per-PR + 每週
> schedule），且 `propagate --apply` 寫入各下游 durable `.council-forge/release-snapshot.json`（acquirer
> 持其所收 snapshot 之 verifier，PS.2.1）。**誠實上限 `partial` 非 `covered`**：本階為 NIST PS.2.1
> **Example 1**（刊布**可復現**之 cryptographic hash manifest 供 acquirer，零 key 負擔）；**真簽章
> （signed tag / minisign / cosign）+ key rotation/revocation/review（Example 2/3）＝path-to-covered，
> defined follow-up**。**release_gate 驗結構非密碼學**：簽章真驗/憑證鏈/key 信任/digest-vs-bytes 屬
> native verify（cosign/`gh attestation verify`/`dotnet nuget verify`/`minisign -V`）+ human-review，
> **explicitly accepted residual**（in-toto/Sigstore/Tauri 結構+密碼學交 native tool，map-don't-recreate，
> 不於 release_gate 重造）。**PS.2 ≠ PS.3.2（SBOM），不 double-count**：release_gate 驗 integrity manifest
> （hashes），sbom_gate 驗 SBOM（provenance）——機制相異。**歷史可驗**賴 manifest `root` content-address +
> git per-commit 不可變；CI regenerate-diff **僅證 HEAD 一致**；**全量 release-manifest archive 屬 PS.3-鄰，
> 緩**。下游 .NET/Tauri 之 PS.2 以 `docs/templates/security/downstream-release-integrity.yml`（native verify
> 主驗）opt-in/local 行之。

> **PS.2（release-integrity）signing 機制備齊（P8-D3，2026-06-08，TASK-1084）**：承 P8-D2 之 path-to-covered
> （真簽章 + key rotation/revocation/review＝Example 2/3），P8-D3 **備齊且經測**此簽章驗證機制——**然 PS.2
> 仍 `partial` 不 flip**。機制：① `.github/workflows/security-scan.yml` 之 `release-integrity` job 增 native
> `gpg --verify` step（隔離 `GNUPGHOME` + **VALIDSIG 簽章者綁定**：pin 先 **40-hex 格式嚴驗**（`grep -Eq ^[0-9A-F]{40}$`，杜 `.*`/short 等弱/regex pin），再以 **awk 精確 field 全等**比 GnuPG status `VALIDSIG` 行之**簽章者/primary key fingerprint（`$3`/`$NF`）== pinned `EXPECTED_SIGNING_FINGERPRINT`**——**fixed-string 非 substring/regex**、非 pubkey 檔首 key，杜 attacker-key-in-bundle 替換 + 弱 pin fail-open；`set -eo pipefail` + capture-then-check 杜 pipefail-masking；`test -n` refuse-unpinned；**`if` 唯 sentinel `.council-forge-source-repo`**，artifact presence 入 bash 之 **armed-triad**（pin/`.asc`/pubkey **全缺方 no-op**；**任一在即 ARMED，三件全須在否則 fail-closed**——杜「signing provision 後刪 `.asc`/pubkey 無聲關閉密碼學驗」之 fail-open）；既有 snapshot_manifest/release_gate 結構 step 維 sentinel-only·**恆跑**·不條件於 `.asc`）；② `docs/security/release-signing.md`（key-lifecycle：
> 生成 / **儲存出 repo** / rotation / revocation / protection / **periodic signing-process review**＝Example 3；
> Mechanism＝`gpg --detach-sign --armor`→`.asc`、`gpg --verify`，簽章 detached、manifest schema 不動）；③ pubkey/
> fingerprint 刊布槽（`.well-known/release-signing.pub` + `EXPECTED_SIGNING_FINGERPRINT`，**現未填**）；④ **ephemeral-
> key 端到端測**（`artifacts/scripts/test_release_signing.py`：正向 pinned sign→VALIDSIG fp==pinned→pass；tamper→fail；
> **負向 multi-key**——attacker key 附 bundle + attacker 簽，以 pinned 為 expected→fail，證綁簽章者非檔首 key；
> gpg-gated skip-if-unavailable，**不 commit key**）。**誠實上限——故仍 `partial` 而非 `covered`**：covered 之
> load-bearing 三事（真 key 生成保管、真簽章、pubkey/fingerprint **out-of-band 刊布**＝須 push）**皆 operator 之舉、
> 非寫碼者所能**；本 repo 守 no-push 故**不 flip**——status 義為 **mechanism-implemented（operator-action-dependent）**。
> **殘餘（樞）**：**同-repo fingerprint pin 僅及 repo 自身完整性**（控 commit 之攻擊者可同改 pin+pubkey+sig），真
> publisher trust 須 fingerprint **out-of-band** 刊布於 acquirer 獨立信之渠道——operator covered-gating 之舉，見
> `docs/security/release-signing.md` §4。validator 仍 **exit 3**（covered 5/partial 14/gap 0，PS.2 不偽升）。**covered
> ＝operational follow-up**：operator 生 key + 真簽 + out-of-band 刊布 trust anchor + 首驗 + 解 no-push（另 governed task）。

> **secret-scan/SCA（RV.1.1/RV.1.2 + PW.4）evidence 補（P9-A·FB-4，2026-06-09，TASK-1091）**：承 TASK-1087
> CP-4 back-audit——`repo_security_scan.py` 之 secret/static 掃描（TASK-980 引入）與 `pip-audit` SCA（TASK-963
> 引入）於完成時尚無 SSDF mapping evidence；其 RV.1/PW.4 列已於 P8-A/B 補入，本註補其**具體運行證據**（前每
> 安全實踐皆有誠實界註，獨此二機制缺，故補之以對稱）。
> **RV.1（secret-scan：RV.1.1 識別 / RV.1.2 code-analysis）運行證據**：穩定契約＝`repo_security_scan.py … secrets`
> （憑證/金鑰 regex 啟發式）+ `… static`（危險模式）之 invocation；現行接線＝`.github/workflows/security-scan.yml`
> 之 `repo-secrets-scan` / `repo-static-scan` job（`on:` = per-PR + push[master] + `workflow_dispatch` + weekly schedule Mon 06:00 UTC）。
> **enforcement 界（誠實）**：job 非零退出即 **fail CI**（workflow 層級事實）；**不宣稱阻 merge**——required-status-
> check / branch-protection 配置不在本 repo 可驗範圍，故不據以宣稱 enforcement。**fail-closed 硬化（TASK-1088/
> FB-1）**：**應讀而不可讀之 in-scope 檔**（read/stat/walk OS 錯）今 raise `ScanReadError`，杜「不可讀＝靜默
> clean」之 fail-open。
> **PW.4（SCA）運行證據**：穩定契約＝`python -m pip_audit -r requirements.txt`（job 全令＝`… --format=json
> --output=pip-audit-report.json`）；現行接線＝`pip-audit` job（pinned `pip-audit==2.7.3`，單一 enforcing step、
> 無 exit-masking），發現漏洞即 job 非零退出 fail CI（同上不宣稱阻 merge）。
> **誠實界——RV.1/PW.4 仍 `partial`（不可協商，不 flip covered）**：本註強化 evidence、**非升等**；綠 CI 不得讀為
> SSDLC 完備。界：① secret/static 為**啟發式 regex**（非窮盡、非語義，可漏新型 secret 樣式）；② SCA 為**以
> `requirements.txt` 為入口之 Python SCA**（pip-audit 對該入口可解析之 Python 套件查 PyPI advisory DB；**不掃
> vendored / 非-Python 生態**）；③
> **fail-closed 非「全無 fail-open」**——oversize（>1MB，`MAX_FILE_BYTES`）/ binary（**首 4096 bytes 含 NUL 之
> 啟發式**，`b"\x00" in raw[:4096]`）檔為**刻意之非文字 skip**，經 `_report_skipped` 具名揭示（`[INFO] … skipped
> (oversize/binary)`，揭示非靜默；regex 文字掃描本不能掃二進位/逾巨檔）。**升 covered 之所需**（皆另 governed task）：窮盡（非啟發式）掃描器 + baseline/waiver
> enforcement + transitive/跨生態 SCA + 簽核流程。job 名為**現行接線**（security-scan.yml 變更經雙審 + human
> review，footnote 隨之維護）。validator 仍 **exit 3**（covered 5/partial 14/gap 0，本註不動 table 列、不偽升）。
