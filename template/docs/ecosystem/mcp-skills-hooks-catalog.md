# Ecosystem Catalog — MCP / Skills / Hooks relevant to council-forge

Aggregated catalog of the GitHub/ecosystem building blocks relevant to an artifact-first,
multi-agent, security-gated workflow orchestrator. Each bucket ends with the **authoritative
source** to consult so coverage can be re-verified (the "no omission" anchor). Star counts and
niche community repos drift fast — treat anything marked _(verify)_ as "confirm current status
and version on the authoritative source before relying on it".

> Scope note: council-forge is **CLI-first**. MCP servers are governed (see
> `.github/mcp/approved-servers.json`) but optional; the PowerShell agent wrappers remain the
> primary integration path. Adopting anything below is a security decision: pin versions, pass
> secrets via `${ENV}`, and record rationale.

---

## 1. MCP servers — official reference

From `modelcontextprotocol/servers` (the canonical reference implementations):

| Server | Fit for council-forge | Notes |
|---|---|---|
| **filesystem** | High | Scoped file access; restrict to repo roots only. |
| **git** | High | Read/search history — supports artifact-first evidence (commit-range replay). |
| **fetch** | Medium | HTTP→markdown for research; SSRF surface — treat output as untrusted (Rule-3/4). |
| **memory** | Medium | Knowledge-graph memory; convenience cache only — artifacts stay authoritative. |
| **sequential-thinking** | Medium | Step-by-step reasoning aid for governance/red-team decisions. |
| **time** | Low | Timezone/scheduling for cadence work. |
| **everything** | Low | Reference/test server for validating new MCP patterns. |

> Authoritative source: <https://github.com/modelcontextprotocol/servers> + the official
> registry <https://registry.modelcontextprotocol.io>. (GitHub/Postgres/Slack/etc. reference
> servers were archived and are now vendor-maintained — see §2.)

## 2. MCP servers — vendor/community (security & governance relevant)

| Server | Maintainer | Fit | Notes |
|---|---|---|---|
| **tavily-mcp** (`tavily-ai/tavily-mcp`) | Tavily | High | Web search/extract for research; council-forge already uses Tavily. |
| **github-mcp-server** (`github/github-mcp-server`) | GitHub (official) | High | PR/issue/CI visibility, github-pr evidence; HIGH risk — least-privilege tokens. |
| **Semgrep MCP** | Semgrep | High | SAST across many languages; complements `bandit`/`semgrep` jobs + `sast_gate.py`. |
| **Snyk `agent-scan`** _(verify)_ | Snyk | High | Scans agents/MCP/skills for prompt injection & sensitive data — aligns with our gates. |
| **git-mcp-server** (`cyanheads/...`) _(verify)_ | community | Medium | GPG/SSH-signed git ops; audit-trail support. |
| **knowledge-graph memory** _(verify)_ | community | Medium | Local JSON graph; if richer memory than the official server is needed. |
| **Firecrawl MCP** _(verify)_ | Firecrawl | Low | Research scraping; Tavily already covers this need. |

> Authoritative source for breadth: the official registry. Curated quality:
> `mcpservers.org` and `punkpeye/awesome-mcp-servers`. Largest (least curated): `mcp.so`.

## 3. MCP directories / registries

- **Official**: <https://registry.modelcontextprotocol.io> — the canonical single source of truth.
- **Curated**: `mcpservers.org`, `punkpeye/awesome-mcp-servers` (GitHub awesome-list).
- **Breadth (experimental/unvetted)**: `mcp.so`, `glama.ai/mcp`.

> Use the official registry as the completeness baseline; cross-reference the curated lists for
> quality and `mcp.so` for breadth.

## 4. Claude Code skills

| Source | Fit | Notes |
|---|---|---|
| **`anthropics/skills`** (official) | High | Reference skill structure + official skills incl. **MCP Builder** (use when building servers). |
| **`cloudflare/security-audit-skill`** (MIT) | High | Six-phase generative vuln discovery — **already adopted** as `.github/skills/security-audit/` (PR #40). |
| community skill marketplaces _(verify)_ | Low–Med | Large aggregates exist; vet individually before importing (supply-chain + prompt-injection risk). |

> Authoritative source: `anthropics/skills`. council-forge already ships 11 skills under
> `.github/skills/` (incl. `security-audit`, `security-review`, `mcp-security-audit`,
> `agent-governance`).

## 5. Claude Code hooks

- **Official schema & events**: <https://code.claude.com/docs/en/hooks> (SessionStart, PreToolUse,
  PostToolUse, Stop, Notification, …).
- council-forge ships governance-aligned hooks opt-in: see `docs/hooks.md` and
  `.claude/settings.json.example` (PR adding SessionStart context, scope guard, post-artifact
  guard, closure reminder).
- Community hook collections exist _(verify before importing — hooks execute shell)_.

> Authoritative source: the official hooks docs. Treat third-party hook snippets as code to review.

## 6. Adjacent governance / quality frameworks

| Framework | Fit | Use |
|---|---|---|
| **OWASP Agentic AI — Threats & Mitigations / Top 10** | High | Risk taxonomy to map gates against — see `docs/governance/agentic-coverage-map.md`. |
| **NIST AI RMF (+ GenAI Profile)** | High | Govern/Map/Measure/Manage framing for the coverage map. |
| **MITRE ATLAS** | Medium | AI-specific adversary tactics for red-team case design. |
| **`github/spec-kit`** | Medium | Spec-driven dev (specify→plan→tasks→implement) — conceptual cousin of artifact-first; cross-pollinate, don't adopt wholesale. |
| **`microsoft/agent-governance-toolkit`** _(verify)_ | Medium | Runtime policy enforcement / MCP trust proxy; heavier than our CLI-first model. |

> Authoritative sources: OWASP (`owasp.org` agentic project), NIST AI RMF, MITRE ATLAS,
> `github/spec-kit`.

---

## Adopted vs deferred (this initiative)

**Adopted now:**
- `security-audit` skill (Cloudflare, MIT) wired into the quarterly exercise — **PR #40**.
- MCP governance keystone: approved-server allowlist + vetted `.mcp.json.example` + the
  skill's Check 5 + headless `mcp_config_audit.py` — **PR #41**.
- Governance-aligned hooks (opt-in `.example`) — **PR #42**.
- OWASP/NIST/ATLAS coverage map — `docs/governance/agentic-coverage-map.md` (this PR).

**Deferred (recorded, not yet done):**
- Wiring `mcp_config_audit.py` into CI as a fail-closed `mcp-config-audit` job.
- Actually adopting MCP servers at runtime (currently governance-only; wrappers remain primary).
- Extending injection detection / a structural guard to the `.github/memory-bank/` intake
  boundary (FIND-24 residual).
- A read-time intake trust-tagging guard (FIND-23 defense-in-depth residual).
- Snyk `agent-scan` / Semgrep MCP runtime integration (evaluate after the CI gate above).

## Maintenance

Re-verify this catalog at the quarterly threat-model exercise (`docs/red_team_runbook.md`,
Phase 5) against the authoritative sources above; record any new adopt/defer decisions in the
threat-findings staging layer.
