# Agentic-AI Governance Coverage Map

Maps council-forge's existing controls to the major agentic-AI risk frameworks, so coverage
is demonstrable and gaps are explicit. This is the "no omission" anchor for the security
posture: every framework category is either covered (with the control named) or recorded as a
gap (with a tracking reference).

> Taxonomy-version caveat: OWASP's agentic project and the exact item IDs evolve. Categories
> below use stable **names**; verify current IDs against the authoritative sources before
> citing them externally. Sources: OWASP Agentic AI (Threats & Mitigations / Top 10),
> NIST AI RMF (+ GenAI Profile), MITRE ATLAS.

## OWASP Agentic threat categories → council-forge controls

| Threat category | council-forge control(s) | Coverage | Residual / gap |
|---|---|---|---|
| **Prompt injection / instruction manipulation** (indirect, via research/artifacts) | `prompt_injection_scan.py` + adversarial corpus; TASK-1021 Rule-3/4 policy; `security-audit` skill | **Strong (detective)** | Detect-and-block at CI, not a preventive read-time trust boundary — FIND-23 residual |
| **Memory poisoning** (cumulative authority) | RACI matrix authority model; `agent-governance` skill; artifacts-as-SoT principle | **Partial** | Detector scopes `artifacts/` only, not `.github/memory-bank/` — FIND-24 (In-Progress) |
| **Tool misuse / insecure tool use** (MCP) | `.github/mcp/approved-servers.json` allowlist; `.mcp.json.example`; `mcp-security-audit` Check 5; `mcp_config_audit.py`; `scope_guard` hook | **Strong** | `mcp_config_audit` not yet a fail-closed CI job (deferred) |
| **Identity / privilege abuse** | Single-writer rule + `AllowedPaths` in agent wrappers; least-privilege CI tokens (CI-02); RACI auditor | **Strong** | Token-scope review remains partly manual |
| **Excessive agency / autonomy** | Artifact-first gates; premortem R1–R4; decision artifacts; phase state machine | **Strong** | — |
| **Supply chain** (deps, actions, skills, MCP) | `sca_gate`/`sbom_gate`/`pip-audit`; SHA-pinned actions + Dependabot; approved-MCP allowlist; `security-audit` on skills | **Strong** | Skill/MCP runtime scanning (Snyk/Semgrep MCP) deferred |
| **Sensitive information disclosure** | `repo_security_scan secrets` (+ redaction); `prompt_injection_scan` exfil rules; secret-pattern coverage | **Strong** | — |
| **Resource exhaustion / DoS** | `regex_safety_audit` (ReDoS, FIND-35); prompt-size bounds in wrappers; artifact size ceiling | **Strong** | Heuristic shape-detector (novel ReDoS could evade) |
| **Cascading / multi-agent failures** | Guard calibration (FP/FN); contract validator; red-team suite; single-writer | **Strong** | — |
| **Insufficient monitoring / traceability** | Artifacts-as-evidence (Build Guarantee); `PROCESS_LEDGER`; decision registry; dashboards; threat-model cadence; weekly audit | **Strong** | Several cadence checks remain manual (see `docs/security_cadence.md`) |

## NIST AI RMF function → council-forge mechanism

| Function | Mechanism |
|---|---|
| **Govern** | CLAUDE.md/AGENTS.md contracts; RACI; `docs/security_cadence.md`; decision artifacts; SSDF mapping (`docs/ssdf-mapping.md`) |
| **Map** | Threat-model inventory + `threat-findings-pending-update.*.json` staging; this coverage map; research artifacts |
| **Measure** | Guard calibration confusion matrix; mutation testing (≥0.80); prompt-injection corpus calibration (100% recall / 0 FP); dashboards |
| **Manage** | Fail-closed CI gates; red-team suite + quarterly exercise; `docs/incident-response-runbook.md`; threat-finding lifecycle |

## MITRE ATLAS

Used as an input to red-team case design (`docs/red_team_runbook.md`) — AI-specific adversary
tactics (e.g. evasion, model/prompt manipulation, exfiltration) inform new attack-class cases in
the `security-audit` skill's hunting phase and the static red-team matrix.

## Gap register (live)

| Gap | Tracking |
|---|---|
| Read-time preventive trust boundary for untrusted input | FIND-23 residual (threat-findings staging) |
| Memory-bank intake injection/authority guard | FIND-24 (In-Progress) |
| `mcp_config_audit` as a fail-closed CI job | deferred (catalog §Adopted/Deferred) |
| Runtime MCP/skill scanning (Snyk/Semgrep MCP) | deferred |
| Manual cadence checks (weekly audit, quarterly) | `docs/security_cadence.md` |

## Maintenance

Refresh at each quarterly threat-model exercise: re-confirm each category's control still holds,
re-verify framework IDs against the authoritative sources, and move any closed gaps out of the
register via the threat-findings staging layer.
