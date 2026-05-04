# consilium-fabri governance repair plan v3.5.0: quality control surface

## Document Metadata

- plan_version: v3.5.0
- schema_version: governance-repair-plan/v3.5
- created_at: 2026-05-04T10:20:00+08:00
- created_by: TASK-1023
- builds_on: consilium-fabri-governance-repair-plan-v3.4.md
- supersedes: null
- builds_on_decision_ref: artifacts/decisions/TASK-1023.decision.md
- manifest_ref: governance-repair-manifest.v3.5.json
- task_lifecycle_refs:
  - artifacts/tasks/TASK-1023.task.md
  - artifacts/plans/TASK-1023.plan.md
  - artifacts/decisions/TASK-1023.decision.md
  - artifacts/verify/TASK-1023.verify.md
  - artifacts/status/TASK-1023.status.json

## 0. Statement of Authority

This document is the single authoritative governance plan introducing the v3.5.0 **quality control surface** for the consilium-fabri repository. Its plan_version is **v3.5.0**.

This document **builds on** [consilium-fabri-governance-repair-plan-v3.4.md](consilium-fabri-governance-repair-plan-v3.4.md). It does **NOT** supersede v3.4. Any tool, validator, or agent that reads this file MUST treat `plan_version: v3.5.0` as the sole authoritative declaration for v3.5.0-introduced controls, while continuing to honor v3.4 controls (verify floor baseline, threat model rebuild, red team execution / regression, RACI auditor v2, Assurance strict/legacy, context hygiene, baseline repair) as still active. Self-validation gates that check `plan_version` MUST assert exactly `v3.5.0` for v3.5-scoped checks.

References to prior plan versions (`v3.4`, `v3.3`, `v3.2`, `v3.1`, `v3`) anywhere in this document are **builds_on context** or **historical framing** only. They are **not** plan_version assertions, and they are **not** supersession declarations. Any agent that interprets `v3.5.0` as superseding v3.4 has misread this document; consult [TASK-1023.decision.md](artifacts/decisions/TASK-1023.decision.md) §Reasoning §「v3.4 與 v3.5.0 之 control surface 區分」.

### 0.1 Why v3.5.0 is needed despite v3.4 being chain-sealed

v3.4 governance repair was completed and chain-sealed by TASK-1016 (end-to-end smoke test, commit `2403c98`) and TASK-1012 (final threat model rebuild). v3.4 is operationally stable. However, five new governance needs surfaced after chain seal that v3.4's control surface does not address:

1. **FIND-29** — source/template sync fragility (see §1).
2. **FIND-30** — validator and test monolith maintainability risk (see §1).
3. **FIND-31** — multi-model style and behavior drift (see §1).
4. **FIND-32** — cross-artifact consistency blind spot (see §1).
5. **FIND-33** — artifact obligation ambiguity (see §1).

These are not v3.4 defects. They are extensions of the control surface needed to keep v3.4 controls trustworthy under multi-model collaboration and longer maintenance horizons. v3.5.0 introduces the minimum verifiable consistency control surface to address them. v3.5.0 does **not** rewrite v3.4.

### 0.2 Artifact-First Lifecycle Self-Compliance

This v3.5.0 document was created **after** the TASK-1023 lifecycle artifacts existed (task → plan → decision → status). The reservation preflight evidence used in TASK-1023 verify was collected **only after** TASK-1023 lifecycle existed. This continues the artifact-first discipline established by TASK-1020 (v3.4 lifecycle) and prevents recurrence of the failure mode v3.3 attempted to repair: "governance plan first, artifacts later."

### 0.3 Scope Lock

v3.5.0 introduces:

- baseline-aware quality gates (P0: source/template sync, JSON schema, import-time side-effect, golden CLI output)
- waiver expiration enforcement
- Pre-Commit Cross-Artifact Consistency Check (PCACC) — exactly four structural checks
- Artifact Obligation Matrix (presence-only)

v3.5.0 does **not** introduce:

- validator real split (deferred to v3.5.1 / v3.6)
- policy registry extraction (deferred to v3.5.1 / v3.6)
- document content generation (forbidden in v3.5.0)
- Bootstrap Prompt Skill into core repo (forbidden; lives in independent skill project)
- waiver registry / style debt registry (deferred to v3.5.2 if data warrants)
- ruff strict enforcement (P1 advisory only in v3.5.0)
- full repo strict enforcement (deferred; activation is data-driven after v3.5.0)
- global model-brand-to-role binding (forbidden; per-task metadata only)
- FIND-18 Mitigated declaration (transition still requires four prerequisites; see §8)

[注意] Numeric task ID order is **not** execution order. Execution order is defined by [governance-repair-manifest.v3.5.json](governance-repair-manifest.v3.5.json) `execution_order`.

---

## 1. v3.5.0 Findings

| Finding ID | Title | Priority | Addressed by |
|---|---|---|---|
| FIND-29 | Source/template sync fragility | high | Prompt 0 (TASK-1024 audit) + Prompt 1 (TASK-1025 QC-SYNC-001 gate) |
| FIND-30 | Validator and test monolith maintainability risk | high | Prompt 0 (TASK-1024 baseline metrics — measurement only; refactor deferred to v3.5.1 / v3.6) |
| FIND-31 | Multi-model style and behavior drift | high | Prompt 1 (TASK-1025 QC-SCHEMA-001, QC-IMPORT-001, QC-GOLDEN-001 gates) |
| FIND-32 | Cross-artifact consistency blind spot | medium-high | Prompt 2 (TASK-1026 minimal PCACC, four checks) |
| FIND-33 | Artifact obligation ambiguity | medium | Prompt 3 (TASK-1027 Artifact Obligation Matrix, presence-only) |

The five-finding list above is the **exact** v3.5.0 finding scope. v3.5.0 must not add new findings unless an unavoidable plan-level inconsistency is discovered during TASK-1023 itself, and must not repurpose FIND-29..FIND-33 for unrelated issues. Any later prompt (TASK-1024..TASK-1027) that needs to record a new defect must do so in v3.4's `threat-finding-backlog` or via a fresh decision artifact, not by reusing FIND-29..FIND-33.

### 1.1 Boundary against v3.4 findings

v3.5.0 findings (FIND-29..FIND-33) are **disjoint** from v3.4 findings (FIND-01..FIND-34, including the historical FIND-18 source/template drift entry). FIND-29 is the multi-model maintenance evolution of the same architectural concern that FIND-18 originally surfaced; the two are linked but separately tracked. FIND-18 status is governed by §8 below; FIND-29 is governed by Prompt 0 / Prompt 1.

---

## 2. Execution Order (Authoritative: Manifest)

The single authoritative source for execution order is [governance-repair-manifest.v3.5.json](governance-repair-manifest.v3.5.json) `execution_order`. The text table below is informational and must be regenerated from manifest if any drift is detected.

| Prompt | Task ID | Title | Depends On |
|---|---|---|---|
| -1 | TASK-1023 | v3.5 Scope Freeze & Quality Surface Decision | (none) |
| 0 | TASK-1024 | Baseline Metrics & Source/Template Sync Audit | TASK-1023 |
| 1 | TASK-1025 | P0 Quality Gates Bootstrap and Baseline Enforcement | TASK-1024 |
| 2 | TASK-1026 | Minimal PCACC | TASK-1025 |
| 3 | TASK-1027 | Artifact Obligation Matrix | TASK-1025 |

**DAG shape**: linear trunk TASK-1023 → TASK-1024 → TASK-1025; after TASK-1025 the graph forks into two parallel branches: TASK-1026 (PCACC) and TASK-1027 (Artifact Obligation Matrix). TASK-1027 does **not** depend on TASK-1026; the two are independent consumers of TASK-1025's gate semantics.

**Numeric task ID order is NOT execution order.** Hard-coded task ID checks in any validator must be replaced by reading the manifest.

If any of TASK-1023..TASK-1027 are unavailable at execution time, the manifest's `task_id_remapping` field captures the actual allocated IDs; the dependency graph shape is preserved.

---

## 3. Read-Only Pre-Mutation Preflight Policy

Every v3.5.0 task that allocates new task IDs MUST perform a strictly read-only preflight before the first repository mutation. This continues the policy established by v3.4 plan §3 and applies identically to v3.5.0 work.

### 3.1 Allowed during preflight

- inspect repository files
- run commands that only print to the interactive terminal
- display findings in stdout/stderr for the operator to read

### 3.2 Forbidden during preflight

- writing any repository file
- writing any non-repository file (including `/tmp`, logs, reports, cache, temporary JSON)
- shell redirection: `>`, `>>`, `2>`, `2>>`, `tee`
- storing stdout/stderr output for later evidence
- creating screenshots or exported artifacts
- writing to `.github/memory-bank/` or `artifacts/verify/`
- running tools that may create caches: `pytest`, `ruff`, `mypy`, `pyright`, validators that emit reports, formatters, package managers, or any script with unknown side effects (which would create `__pycache__/`, `.pytest_cache/`, etc.)

stdout/stderr is allowed only as ephemeral terminal output. It must not be redirected.

### 3.3 Evidence Rule

The preflight observed **before** the lifecycle task exists is **NOT evidence**. After the lifecycle artifacts exist, the reservation preflight MUST be re-run inside the task and recorded as verification evidence.

---

## 4. Prompt Definitions

Each prompt below defines the work authorized by its associated task ID. Any prompt referenced from this v3.5.0 plan must obey the artifact-first lifecycle: each task must produce its own task / plan / decision (when needed) / verify / status, and may produce code if runtime changes are involved.

### 4.-1 Prompt -1 — v3.5 Scope Freeze & Quality Surface Decision (TASK-1023)

This is the prompt that produced this v3.5.0 plan and its manifest. See [TASK-1023.task.md](artifacts/tasks/TASK-1023.task.md), [TASK-1023.plan.md](artifacts/plans/TASK-1023.plan.md), [TASK-1023.decision.md](artifacts/decisions/TASK-1023.decision.md), [TASK-1023.verify.md](artifacts/verify/TASK-1023.verify.md), [TASK-1023.status.json](artifacts/status/TASK-1023.status.json).

**Scope class**: `DOCS_ONLY_PLAN_LIFECYCLE`.

**Authorized scope**: creation of the v3.5.0 plan, manifest, and TASK-1023 lifecycle artifacts only. No execution of Prompt 0 or later.

**Forbidden scope** (Prompt -1 must NOT modify):

- any file in `artifacts/scripts/` (runtime validators)
- any source/template paired file (any pair of root + `template/` corresponding files)
- any file in `docs/`
- any file in `.github/memory-bank/`
- any file in `template/`
- any v3.4 governance artifact (v3.4 plan, v3.4 manifest, TASK-1005..TASK-1022 lifecycle artifacts)
- any TASK-1024 / TASK-1025 / TASK-1026 / TASK-1027 lifecycle artifact
- any Bootstrap Prompt Skill artifact
- any waiver registry file (forbidden for v3.5.0)
- any style debt registry file (forbidden for v3.5.0)

**Non-authorization**:

- TASK-1023 does NOT authorize executing TASK-1024 or later.
- TASK-1023 does NOT authorize source/template remediation.
- TASK-1023 does NOT authorize validator modularization.
- TASK-1023 does NOT authorize code change.
- TASK-1023 does NOT authorize document content generation.
- TASK-1023 does NOT authorize Bootstrap Prompt Skill work.
- TASK-1023 does NOT authorize ruff format / lint enforcement.
- TASK-1023 does NOT declare FIND-18 Mitigated.
- TASK-1023 does NOT create a waiver registry or style debt registry.

**Acceptance**: TASK-1023 verify confirms the 22 acceptance criteria of [TASK-1023.task.md](artifacts/tasks/TASK-1023.task.md), and the post-creation reservation preflight confirms that no TASK-1024..TASK-1027 artifact was created and no runtime / validator / source-template / skill artifact was modified.

### 4.0 Prompt 0 — Baseline Metrics & Source/Template Sync Audit (TASK-1024)

**Goal**: produce a baseline snapshot of the v3.5.0 quality control surface inputs without remediating any drift.

**Required deliverable**: `artifacts/governance/quality-baseline.v3.5.json` (see §5.1 schema).

**Required baseline inventory**:

```text
LOC                                  per file under audit (validators, tests, hot-path scripts)
function_count                       per file
responsibility_tags                  per file (e.g. parser, schema, cli, ledger, audit)
source_template_pair_status          per (source, template) pair: in_sync | drift | missing_source | missing_template
existing_drift_entries               with stable baseline_id values
json_schema_surface                  list of declared schema_version values across artifacts and registries
import_side_effect_surface           modules whose import emits stdout/stderr or mutates global state
cli_output_surface                   CLI commands and their stable output shapes
golden_candidate_commands            CLI commands flagged as candidates for golden output capture
```

**Validator and test monolith analysis** (FIND-30):

- `artifacts/scripts/guard_status_validator.py` and any colocated test monolith (e.g. `test_guard_units.py` if present) must be inventoried with LOC, function_count, and responsibility_tags.
- This analysis is **measurement only**. It must NOT propose, justify, or attempt validator split. Split candidates are recorded as backlog hints for v3.5.1 / v3.6, not authorized work for v3.5.0.

**Existing drift baseline** (FIND-29 input):

- Existing source/template drift entries are assigned stable `baseline_id` values (e.g. `QB-SYNC-0001`).
- Existing drift is **not** treated as evidence of failure under TASK-1024. Failure semantics are defined by TASK-1025's baseline-aware enforcement.

**Forbidden scope** (TASK-1024 must NOT):

- modify any source/template paired file
- modify any validator code
- modify any drift entry (only inventory)
- run pytest, ruff, mypy, pyright, or other tools that may emit reports as side effects unless their output is captured into the baseline JSON deterministically
- emit any acceptance evidence based on grep/keyword scans of narrative prose (per v3.4 plan §7 anti-grep rule, which v3.5.0 inherits)

**Acceptance**: TASK-1024 verify confirms `quality-baseline.v3.5.json` exists, validates as JSON, contains all required inventory sections, and that no source/template paired file was modified.

**Non-authorization**: TASK-1024 does NOT authorize executing TASK-1025 or later.

### 4.1 Prompt 1 — P0 Quality Gates Bootstrap and Baseline Enforcement (TASK-1025)

**Goal**: implement baseline-aware P0 quality gates that:

- forbid any new or modified drift after the TASK-1024 baseline,
- require existing drift to be either remediated or explicitly waived with a waiver that has an `expires_at` field, and
- keep ruff format/lint as P1 advisory for the first cycle.

**P0 gates** (blocking after Phase 1):

| Gate ID | Title | Concern |
|---|---|---|
| QC-SYNC-001 | Source/template exact-sync gate | FIND-29 / FIND-18 prerequisite |
| QC-SCHEMA-001 | JSON schema validation gate | FIND-31 |
| QC-IMPORT-001 | Import-time side-effect gate | FIND-31 |
| QC-GOLDEN-001 | Golden CLI output harness | FIND-31 |

**P1 advisory** (not blocking in v3.5.0):

| Gate ID | Title | Status |
|---|---|---|
| QC-RUFF-001 | ruff format + lint | advisory only in v3.5.0 |

**Required rollout model** (baseline-aware):

```text
Phase 1 (v3.5.0):
  baseline inventory from TASK-1024 frozen
  existing drift classified by baseline_id
  no NEW or MODIFIED drift allowed beyond baseline
  expired waivers are blocking

Phase 2 (v3.5.0):
  existing drift must be remediated OR waived with explicit expires_at
  new or modified violations are blocking
  expired waivers remain blocking

Phase 3 (NOT in v3.5.0 scope):
  full repo strict enforcement
  activation is data-driven after v3.5.0
  requires evidence from Phase 1 + Phase 2 stability before activation
```

**Required waiver schema** (front matter on the waived artifact or in a waiver block referenced by the artifact):

```yaml
waiver:
  rule_id: QC-SYNC-001
  scope:
    - artifacts/scripts/example.py
  reason_code: baseline_existing_drift
  owner: arcobaleno
  evidence_ref: artifacts/verify/TASK-XXXX.verify.md
  expires_at: "YYYY-MM-DD"
```

**Waiver rules**:

- Every waiver MUST include all six fields: `rule_id`, `scope`, `reason_code`, `owner`, `evidence_ref`, `expires_at`.
- `expires_at` MUST NOT appear alone; missing peer fields cause the waiver to be invalid (i.e. blocking) regardless of `expires_at`.
- `owner` MUST reference a valid human reviewer or accountable maintainer (not an AI agent label).
- `evidence_ref` MUST reference a verify artifact path (`artifacts/verify/TASK-XXXX.verify.md`).
- `expires_at` MUST be enforceable: TASK-1025 gates MUST reject expired waivers as blocking.
- v3.5.0 does NOT create a global waiver registry. Waivers live alongside the artifact they cover.
- v3.5.0 does NOT create a style debt registry.

**Forbidden scope** (TASK-1025 must NOT):

- modify the v3.4 verify floor baseline (`artifacts/governance/verify-floor-baseline.v3.4.json`)
- declare FIND-18 Mitigated (FIND-18 transition rules live in §8)
- enforce ruff strict (P1 advisory only)
- create a waiver registry or style debt registry
- expand to full repo strict enforcement (deferred to post-v3.5.0)

**Acceptance**: TASK-1025 verify confirms the four P0 gates are implemented, the rollout model is documented, the waiver schema is enforced (a deliberately invalid waiver test case is rejected), and ruff remains advisory.

**Non-authorization**: TASK-1025 does NOT authorize executing TASK-1026 or TASK-1027.

### 4.2 Prompt 2 — Minimal PCACC (TASK-1026)

**Goal**: create a Pre-Commit Cross-Artifact Consistency Check (PCACC) that verifies **structural** cross-artifact invariants. PCACC v3.5.0 is **not** a reasoning-faithfulness audit and **not** a narrative self-audit.

**Required output**:

- per-task: `artifacts/verify/TASK-xxxx.precommit-check.json`
- policy: `artifacts/governance/precommit-check-policy.v3.5.json` (see §5.4 schema)

**PCACC v3.5.0 strict checks** (exactly four; no more, no fewer):

| Check ID | Title | Severity |
|---|---|---|
| PCACC-001 | Lifecycle artifact set exists (task / plan / decision / verify / status) | blocking |
| PCACC-002 | Evidence Refs exist and match required format | blocking |
| PCACC-003 | Status owner / reviewer references are canonical | blocking |
| PCACC-004 | Decision review_timestamp is later than evidence_generated_at | blocking |

**Explicitly excluded from v3.5.0 PCACC**:

- AC-to-verify coverage check (deferred to v3.5.1)
- reasoning faithfulness score
- belief-state audit
- model self-confidence audit
- free-text rationale field
- markdown SAVeR report

**Output rules**:

- JSON only.
- Each check entry MUST include: `check_id`, `target`, `expected`, `actual`, `evidence_ref`, `status`.
- `status` MUST be one of: `pass`, `fail`, `skipped_with_reason_code`.
- No free-text rationale field.
- Failures are detected by PCACC but resolved through the existing decision artifact workflow (not through PCACC self-resolution).

**Forbidden scope** (TASK-1026 must NOT):

- introduce reasoning faithfulness scoring
- introduce belief-state or model-confidence checks
- emit free-text rationale
- emit markdown reports as authoritative output
- modify v3.4 verify floor or threat model artifacts
- expand checks beyond the four listed (any additional check requires a separate decision artifact and a v3.5.1 follow-up task)

**Acceptance**: TASK-1026 verify confirms `precommit-check-policy.v3.5.json` exists with exactly four `checks` entries, that a sample TASK's `precommit-check.json` is produced and parses, and that PCACC correctly fails on a deliberately malformed lifecycle (e.g. missing decision artifact).

**Non-authorization**: TASK-1026 does NOT authorize executing TASK-1027.

### 4.3 Prompt 3 — Artifact Obligation Matrix (TASK-1027)

**Goal**: define which artifacts are required, optional, or forbidden for each task type, risk level, and assurance level — to prevent artifact bloat — without generating any artifact content.

**Required deliverable**: `artifacts/governance/artifact-obligation-matrix.v3.5.json` (see §5.5 schema).

**Required schema concepts**:

```text
matrix_version
effective_from
task_type
risk_level
assurance_level
required_artifacts
optional_artifacts
forbidden_artifacts
supersession_policy
legacy_task_policy
presence_only
```

**Required supersession semantics**:

- Completed tasks are **not** retroactively re-evaluated under a newer matrix.
- Superseded tasks freeze their original obligation state.
- Superseding tasks inherit still-open obligations unless explicitly waived by a decision artifact.
- Matrix changes apply **only** from `effective_from` forward.

**Forbidden generation** (TASK-1027 must NOT generate content for):

- SRS (Software Requirements Specification)
- RTM (Requirements Traceability Matrix)
- design spec
- threat model
- release note
- migration note
- user guide
- runbook

The matrix MAY require the **presence** of artifacts; it MUST NOT generate their content. The matrix is an anti-bloat **control**, not a document generation plane.

**Acceptance**: TASK-1027 verify confirms `artifact-obligation-matrix.v3.5.json` exists with `presence_only: true`, contains `effective_from`, `matrix_version`, and supersession policy, and that no SRS / RTM / design spec / threat model / release note / migration note / user guide / runbook content was generated as part of TASK-1027.

**Non-authorization**: TASK-1027 does NOT authorize subsequent v3.5.x or v3.6 work.

---

## 5. v3.5 Schemas

### 5.1 quality-baseline.v3.5.json

```json
{
  "schema_version": "quality-baseline/v1",
  "plan_version": "v3.5.0",
  "created_at": "<deterministic timestamp>",
  "created_by_task": "TASK-1024",
  "metrics": [
    {
      "path": "artifacts/scripts/example.py",
      "loc": 0,
      "function_count": 0,
      "responsibility_tags": ["parser", "schema", "cli"]
    }
  ],
  "source_template_pairs": [
    {
      "baseline_id": "QB-SYNC-0001",
      "source_path": "artifacts/scripts/example.py",
      "template_path": "templates/artifacts/scripts/example.py",
      "status": "in_sync|drift|missing_source|missing_template",
      "sha256_source": "...",
      "sha256_template": "...",
      "enforcement": "baseline_existing"
    }
  ],
  "json_schema_surface": [
    {"schema_version": "task/v1", "declared_in": "docs/artifact_schema.md §5.1"}
  ],
  "import_side_effect_surface": [
    {"module": "artifacts/scripts/example.py", "side_effect": "stdout|stderr|global_mutation|none"}
  ],
  "cli_output_surface": [
    {"command": "python artifacts/scripts/example_validator.py --help", "stable_output_shape": "..."}
  ],
  "golden_cli_candidates": [
    {
      "command_id": "QB-CLI-0001",
      "command": "python artifacts/scripts/example_validator.py --help",
      "expected_exit_code": 0,
      "capture_policy": "post_task_evidence_only"
    }
  ]
}
```

Rules:

- `created_at` MUST come from a deterministic source (e.g. `git:<sha>`); not wall-clock.
- `baseline_id` values MUST be stable across reruns; once assigned, never reassigned.
- `enforcement: baseline_existing` is the only allowed enforcement label for entries inventoried at TASK-1024 time. New / modified entries get their enforcement from TASK-1025.

### 5.2 Waiver Front Matter Extension

```yaml
waiver:
  rule_id: QC-SYNC-001
  scope:
    - artifacts/scripts/example.py
  reason_code: baseline_existing_drift
  owner: arcobaleno
  evidence_ref: artifacts/verify/TASK-XXXX.verify.md
  expires_at: "YYYY-MM-DD"
```

Rules (mandatory in v3.5.0):

- All six fields required: `rule_id`, `scope`, `reason_code`, `owner`, `evidence_ref`, `expires_at`.
- `owner` MUST be a human reviewer or accountable maintainer.
- `evidence_ref` MUST point to a verify artifact path under `artifacts/verify/`.
- `expires_at` MUST be present.
- `expires_at` enforcement is owned by TASK-1025 gates; expired waivers MUST be rejected as blocking.
- v3.5.0 forbids a global waiver registry. Waivers live with the artifact they cover.

### 5.3 agent_roles Per-Task Metadata Extension

For task artifacts, v3.5.0 defines task-level agent role assignment metadata:

```yaml
agent_roles:
  implementer:
    agent_label: claude-code
    model_family: claude
    assignment_basis: code-editing-capability
  architecture_critic:
    agent_label: opus-chat
    model_family: claude
    assignment_basis: architecture-review
  negative_tester:
    agent_label: codex
    model_family: gpt
    assignment_basis: regression-and-scope-check
  final_approver:
    reviewer_id: arcobaleno
    type: human
```

Rules (mandatory in v3.5.0):

- Role definitions (`implementer`, `architecture_critic`, `negative_tester`, `final_approver`) are **global**.
- Model assignments are **per-task metadata** only.
- **Forbidden**: global model-brand-to-role binding (e.g. "Codex is always negative_tester" written into a global config).
- The same model MUST NOT be both `implementer` and `final_approver` for the same task.
- `final_approver` MUST be human (`type: human` with a `reviewer_id`).

### 5.4 precommit-check-policy.v3.5.json

```json
{
  "schema_version": "precommit-check-policy/v1",
  "plan_version": "v3.5.0",
  "checks": [
    {
      "check_id": "PCACC-001",
      "title": "Lifecycle artifact set exists",
      "severity": "blocking",
      "required_fields": ["task", "plan", "decision", "verify", "status"]
    },
    {
      "check_id": "PCACC-002",
      "title": "Evidence Refs exist and match required format",
      "severity": "blocking"
    },
    {
      "check_id": "PCACC-003",
      "title": "Canonical owner and reviewer references",
      "severity": "blocking"
    },
    {
      "check_id": "PCACC-004",
      "title": "Review timestamp follows evidence generation timestamp",
      "severity": "blocking"
    }
  ],
  "excluded_checks": [
    {
      "check_id": "PCACC-DEFERRED-AC-COVERAGE",
      "reason": "Deferred to v3.5.1 after the four structural checks stabilize."
    }
  ],
  "output_policy": {
    "format": "json",
    "free_text_rationale": false
  }
}
```

Rules:

- Exactly four `checks` entries in v3.5.0; no more, no fewer.
- `output_policy.format` MUST be `"json"`.
- `output_policy.free_text_rationale` MUST be `false`.
- Per-task PCACC output entries (`artifacts/verify/TASK-xxxx.precommit-check.json`) MUST use status values from `{"pass", "fail", "skipped_with_reason_code"}` only.

### 5.5 artifact-obligation-matrix.v3.5.json

```json
{
  "schema_version": "artifact-obligation-matrix/v1",
  "matrix_version": "v3.5.0",
  "effective_from": "TASK-1027",
  "presence_only": true,
  "rules": [
    {
      "rule_id": "AOM-001",
      "task_type": "docs_only_plan_lifecycle",
      "risk_level": "high",
      "assurance_level": "mvp",
      "required_artifacts": ["task", "plan", "decision", "verify", "status", "manifest"],
      "optional_artifacts": [],
      "forbidden_artifacts": ["runtime_code_change"]
    }
  ],
  "supersession_policy": {
    "completed_tasks_retroactive_evaluation": false,
    "superseded_task_obligation_state": "frozen",
    "superseding_task_inherits_open_obligations": true,
    "waiver_requires_decision_artifact": true
  },
  "legacy_task_policy": {
    "tasks_completed_before_effective_from": "not_re-evaluated",
    "tasks_open_at_effective_from": "subject_to_matrix_from_next_state_transition"
  }
}
```

Rules:

- `presence_only` MUST be `true`. Matrix MUST NOT generate artifact content.
- `effective_from` MUST be present and MUST denote a task ID or commit reference.
- `supersession_policy` MUST contain all four sub-fields shown above.
- `legacy_task_policy` MUST be defined to prevent retroactive enforcement against historically completed tasks.

### 5.6 v3.5 Version Split Rule

```text
v3.5.0:
  controls before refactor
  define control surface, baseline, minimum gates, four PCACC checks, and obligation matrix
  allow new controls
  forbid large refactors

v3.5.1:
  refactor only after controls are green
  allow small validator split candidates
  forbid new governance plane

v3.5.2:
  maintenance policies after evidence accumulates
  retention, archival, waiver registry only if data shows need
  no preemptive policy bloat

v3.6:
  structural evolution after behavior is characterized
  validator split
  policy registry extraction
  PCACC AC coverage
  validator output schema versioning
  requires v3.5.x characterization tests and gates to remain green for at least one release cycle
```

This split rule is duplicated in [governance-repair-manifest.v3.5.json](governance-repair-manifest.v3.5.json) `version_split_rule` for machine readability. Drift between the two MUST be treated as a v3.5 plan inconsistency and resolved via decision artifact.

---

## 6. Resume Policy

| Already Started State | Required v3.5 Gap Policy |
|---|---|
| No v3.5 work started | Start from Prompt -1 / TASK-1023. |
| TASK-1023 draft exists but incomplete | Treat as prior work. Do not overwrite blindly. Run TASK-1023 gap analysis and complete lifecycle artifacts. |
| TASK-1024 started before TASK-1023 completion | Stop TASK-1024. Complete TASK-1023 lifecycle first. Reclassify TASK-1024 outputs as non-evidence unless re-run under TASK-1024 after lifecycle exists. |
| TASK-1025 started before TASK-1024 baseline exists | Stop TASK-1025. Create TASK-1024 baseline first. Any gate output before baseline is advisory only. |
| TASK-1026 started before TASK-1025 gates exist | Stop TASK-1026. PCACC depends on baseline-aware gate policy. |
| TASK-1027 started before TASK-1025 exists | Stop TASK-1027 unless it is design-only. Final matrix must depend on TASK-1025 gate semantics. |
| Validator split already started | Stop refactor. Move split work to v3.5.1 or v3.6 candidate backlog. Do not mix with v3.5.0. |
| Document generation already drafted | Mark as out of scope for v3.5.0. Preserve only as non-authoritative research note if needed. |
| Bootstrap Skill work already drafted | Move to independent skill project. Do not assign consilium-fabri core task ID. |
| FIND-18 already marked Mitigated | Reopen or reclassify unless exact-sync guard, drift regression, decision path evidence, and clean guard_contract_validator result all exist (see §8). |
| Waiver registry already created | Remove or move to v3.5.2 candidate backlog. v3.5.0 forbids a waiver registry. |
| Style debt registry already created | Remove or move to v3.5.2 candidate backlog. v3.5.0 forbids a style debt registry. |
| Ruff strict enforcement already activated | Downgrade to advisory. v3.5.0 keeps ruff as P1 advisory only. |
| PCACC AC coverage check already implemented | Move to v3.5.1. v3.5.0 PCACC has exactly four structural checks and excludes AC coverage. |
| Global model-brand-to-role binding already configured | Remove. v3.5.0 forbids global binding; per-task metadata only. |

**Hard rule**: If work was completed before its required predecessor task, it is not automatically invalidated, but it must pass v3.5 gap analysis before being treated as complete under v3.5.0.

---

## 7. FIND-18 Transition Conditions

FIND-18 (source/template drift, originally surfaced in v3.4) status is currently `In-Progress`. v3.5.0 does **not** declare FIND-18 Mitigated.

FIND-18 transition from `In-Progress` to `Mitigated` requires **all four** of the following prerequisites to exist and be verifiable:

1. CI exact-sync guard for root↔template pairs (delivered by Prompt 1 / TASK-1025 QC-SYNC-001 — note: gate implementation alone is necessary, not sufficient).
2. Drift regression case present in the test corpus (covers known drift scenarios deterministically).
3. Decision path evidence (decision artifact recording how drift entries are resolved or waived).
4. Clean `guard_contract_validator` run result.

If any of the four is missing, FIND-18 MUST remain `In-Progress` with the missing items enumerated. v3.5.0 inherits and reaffirms v3.4's policy that grep / keyword scans are NOT acceptance evidence for FIND-18 transition.

---

## 8. TASK-1023 Verification Requirements

TASK-1023 verify artifact MUST verify the following (corresponding to [TASK-1023.task.md](artifacts/tasks/TASK-1023.task.md) AC-1 through AC-22):

1. TASK-1023 task, plan, decision, verify, and status artifacts exist and match schema.
2. `consilium-fabri-governance-repair-plan-v3.5.md` exists at repo root.
3. `governance-repair-manifest.v3.5.json` exists at repo root with `schema_version: "governance-repair-manifest/v1"` and `plan_version: "v3.5.0"`.
4. v3.5 plan declares `plan_version: v3.5.0` consistently; no `v3.4`/`v3.3`/`v3.2`/`v3.1` self-assertion remains.
5. v3.5 plan declares `builds_on: consilium-fabri-governance-repair-plan-v3.4.md` and `supersedes: null`.
6. v3.5 manifest `execution_order` contains exactly five entries (Prompt -1 to Prompt 3) with valid linear-trunk-plus-fork DAG (TASK-1023 → TASK-1024 → TASK-1025 → {TASK-1026, TASK-1027}).
7. v3.5 manifest `findings` lists FIND-29..FIND-33 with titles and priorities matching task §Background.
8. TASK-1023 is defined as `DOCS_ONLY_PLAN_LIFECYCLE` and explicitly does not authorize TASK-1024 or later execution.
9. Prompt 0 (TASK-1024) is defined as baseline metrics and source/template sync audit only; required inventory fields enumerated; baseline_id stability required.
10. Prompt 1 (TASK-1025) is named exactly `P0 Quality Gates Bootstrap and Baseline Enforcement`; defines four P0 gates and ruff as P1 advisory; defines three-phase rollout (Phase 3 not in v3.5.0); waiver schema contains all six required fields with enforceable expiration.
11. Prompt 2 (TASK-1026) defines exactly four strict PCACC checks; excludes AC-to-verify coverage, reasoning faithfulness, belief-state audit, free-text rationale, and SAVeR markdown report; output is JSON only with status in `{pass, fail, skipped_with_reason_code}`.
12. Prompt 3 (TASK-1027) defines Artifact Obligation Matrix as `presence_only: true`; includes `effective_from`, `matrix_version`, and supersession policy; forbids generation of SRS, RTM, design spec, threat model, release note, migration note, user guide, and runbook content.
13. v3.5 plan §1 lists FIND-29..FIND-33 with titles and priorities consistent with task §Background and manifest `findings`.
14. v3.5 plan §7 documents FIND-18 transition conditions (four prerequisites); v3.5.0 does not declare FIND-18 Mitigated.
15. v3.5 plan §5.6 documents version split rule for v3.5.0 / v3.5.1 / v3.5.2 / v3.6; v3.6 work requires v3.5.x characterization tests and gates green for at least one release cycle.
16. v3.5 plan §6 contains a resume policy with at least 10 rows.
17. v3.5 plan §3 documents read-only pre-mutation preflight constraints with explicit allowed / forbidden lists and the evidence rule.
18. v3.5 plan §5.3 documents agent_roles per-task metadata schema; role definitions are global; model assignments are per-task; global brand-to-role binding is forbidden; same model cannot be implementer and final_approver; final_approver must be human.
19. Prompt -1 explicitly states `DOCS_ONLY_PLAN_LIFECYCLE` and forbids modification of runtime code, validators, source/template paired files, and Bootstrap Prompt Skill artifacts; forbids creation of waiver registry / style debt registry.
20. Read-only pre-mutation preflight evidence (Phase 1, before lifecycle existed) is recorded in task §Current Status Summary and verify §Preflight Evidence as ephemeral terminal output, not as authoritative evidence.
21. Post-creation reservation preflight (Phase 4) was run after TASK-1023 lifecycle existed and is recorded in verify artifact §Preflight Evidence as authoritative evidence.
22. No TASK-1024 / TASK-1025 / TASK-1026 / TASK-1027 lifecycle artifact was created or modified by TASK-1023; no runtime / validator / source-template / Bootstrap Skill artifact was modified.

Additional plan-level checks (corresponding to additional invariants):

- Bootstrap Prompt Skill is explicitly out of consilium-fabri core lifecycle scope.
- Document content generation is explicitly out of v3.5.0 scope.
- Validator modularization is deferred to v3.5.1 / v3.6.
- Policy registry extraction is deferred to v3.5.1 / v3.6.

---

## 9. TASK-1023 Status Rules

TASK-1023 may be marked `done` only when all of the following are true:

1. TASK-1023 task, plan, decision, verify, and status artifacts exist.
2. `consilium-fabri-governance-repair-plan-v3.5.md` exists at repo root.
3. `governance-repair-manifest.v3.5.json` exists at repo root.
4. TASK-1023 verify artifact confirms all 22 acceptance criteria with `result: verified`.
5. No TASK-1024 or later v3.5.0 task has been executed as part of TASK-1023.
6. Any actual task ID remapping is recorded in the v3.5 manifest `task_id_remapping` field.
7. No runtime code, validator code, source/template pair, or Bootstrap Skill artifact was modified.
8. `Pass Fail Result` in verify artifact is `pass`.

Otherwise TASK-1023 remains `blocked` (with `blocked_reason`) or another valid non-`done` state with evidence.

---

## 10. Self-Consistency Discipline (Anti-Grep Rule, Inherited)

v3.5.0 inherits v3.4 plan §7 anti-grep rule:

- Acceptance evidence MUST come from structured artifact fields (verify checklist `result`, status structured fields, manifest entries).
- Acceptance evidence MUST NOT come from grep / keyword-based scans of narrative prose.
- The anti-grep rule applies to v3.5.0 acceptance and to FIND-18 transition.

Grep is allowed as a sanity check inside verify artifacts for line presence / absence (e.g. confirming no `plan_version: v3.4` self-assertion remains). The acceptance judgment itself is taken from the structured artifact field, not the grep line count.

---

## 11. Final Notes

- v3.5.0 builds on v3.4. v3.5.0 does not supersede v3.4. v3.4 controls remain active.
- v3.5.0 is the controls-before-refactor phase. v3.5.1 is refactor. v3.5.2 is maintenance. v3.6 is structural evolution.
- v3.5.0 does not authorize any work beyond TASK-1023's plan-introduction lifecycle until each subsequent task's own lifecycle authorizes it.
