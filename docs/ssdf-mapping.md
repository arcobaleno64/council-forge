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
| PS.2 | Provide a Mechanism to Verify Software Release Integrity (SBOM) | gap | — | — | docs/ssdf-roadmap.md#8-ssdf-gap-waiver-registry |
| PS.3 | Archive and Protect Each Software Release | partial | artifacts/scripts/guard_status_validator.py | docs/artifact_schema.md | — |
| PW.1 | Design Software to Meet Security Requirements | partial | docs/premortem_rules.md | CODEX.md | — |
| PW.2 | Review the Software Design | covered | docs/orchestration.md | CLAUDE.md | — |
| PW.4 | Reuse Existing, Well-Secured Software (SCA) | partial | .github/workflows/security-scan.yml | requirements.txt | — |
| PW.5 | Create Source Code Adhering to Secure Coding Practices | partial | AGENTS.md | CODEX.md | — |
| PW.6 | Configure the Compilation, Build, and Packaging Process | partial | artifacts/scripts/scaffold_downstream.py | .github/workflows/workflow-guards.yml | — |
| PW.7 | Review and/or Analyze Human-Readable Code (SAST) | gap | — | — | docs/ssdf-roadmap.md#8-ssdf-gap-waiver-registry |
| PW.8 | Test Executable Code | partial | artifacts/scripts/run_red_team_suite.py | docs/red_team_runbook.md | — |
| PW.9 | Configure Software to Have Secure Settings by Default | partial | docs/orchestration.md | GEMINI.md | — |
| RV.1 | Identify and Confirm Vulnerabilities (secret-scan/SCA/disclosure) | partial | artifacts/scripts/repo_security_scan.py | .github/workflows/security-scan.yml | — |
| RV.2 | Assess, Prioritize, and Remediate Vulnerabilities | partial | artifacts/scripts/guard_status_validator.py | docs/artifact_schema.md | — |
| RV.3 | Analyze Vulnerabilities to Identify Root Causes | covered | docs/premortem_rules.md | artifacts/improvement/PROCESS_LEDGER.md | — |
