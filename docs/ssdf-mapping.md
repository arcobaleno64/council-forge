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
| PS.2 | Provide a Mechanism for Verifying Software Release Integrity | gap | — | — | docs/ssdf-roadmap.md#8-ssdf-gap-waiver-registry |
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
> 「PS.2…(SBOM)」為 **P8-A 誤植，已正**：① **PS.2** 復 verbatim 標題、status 仍 `gap`、改隸
> **P8-D**（release 簽章/雜湊/integrity-verification info 供 acquirer，council-forge 尚無）；
> ② **PS.3** 以 `sbom_gate.py` + `.github/workflows/security-scan.yml` 之運行中 `sbom` job
> 強化（PS.3.2 provenance facet：cyclonedx-py 由 **resolved 環境**生成 SBOM、捕 transitive、
> sbom_gate 驗之）。**PS.3 仍 `partial` 非 `covered`**：archive facet（PS.3.1）僅 via status/
> commit anchor，**deferred** 簽章/sharing-to-acquirer→P8-D。**completeness 邊界（誠實）**：
> sbom_gate **fail-closed** 驗 well-formedness + presence（`--min-components`）+ **直接依賴
> identity**（`--require-components`）；**窮盡 transitive completeness vs 真實 dep graph 為
> explicitly ACCEPTED RISK**——無 gate 能獨立斷（否則須自為生成器或另信一完整性同不可證之
> enumerator，無限回歸），由 resolved-env 配方 + identity + 恆印 advisory 共治，殘留以
> §Transitive-Completeness Follow-up 之非阻斷週期審計觀測。
