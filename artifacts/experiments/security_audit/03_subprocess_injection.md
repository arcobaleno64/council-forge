# Security Audit 03 — Command/Argument Injection, Subprocess, Env Trust, Dynamic Code

Authorized defensive self-assessment of council-forge. Scope: command/argument
injection, unsafe subprocess use, environment-variable trust, and dynamic code
execution. Code was reviewed READ-ONLY; no source files were modified.

All subprocess use in the reviewed scripts is `subprocess.run` / `subprocess.Popen`
with an **argument list and `shell=False` (default)** — there is no `os.system`,
no `shell=True`, no `eval`/`exec`, no `pickle`, and no `yaml.load`. The remaining
risk surface is (a) argument injection via untrusted git refs, (b) env-var trust
for SSRF host-allowlisting and token forwarding, and (c) `importlib` of fixed
local paths.

---

## Summary Table

| ID | Severity | Location | Issue |
|---|---|---|---|
| F-01 | Medium | guard_status_validator.py:699-700,595-604 | Git `rev-parse` argument injection via untrusted `Base Ref`/`Head Ref` artifact fields (no ref-format validation, leading-dash option injection) |
| F-02 | Low | guard_status_validator.py:323-356,434-455 | SSRF allowlist + `GITHUB_TOKEN` forwarding governed by env var `CONSILIUM_ALLOWED_GITHUB_API_HOSTS`; token can leak to any allowlisted host taken from an untrusted artifact |
| F-03 | Low | guard_status_validator.py:554-575,578-592,595-604 | Git scope subprocesses inherit ambient environment and have no `timeout`; a hostile repo/hook config or a hanging git can stall the validator |
| F-04 | Low | migrate_artifact_schema.py:198-211 | `git show HEAD:<relative_path>` built from artifact-derived path tokens; constrained but unvalidated against leading-dash / refspec abuse |
| F-05 | Info | run_red_team_suite.py:29-32,75-81; red_team/helpers.py:75-81 | `importlib.util.spec_from_file_location` + `from … import *` of fixed in-repo modules — safe today, but a code-execution sink if those paths ever become attacker-influenced |

### Cleared (reviewed, no actionable finding)

- **release_gate.py**, **sast_gate.py**, **sbom_gate.py**, **sca_gate.py**,
  **security_txt_gate.py** — pure JSON/SARIF parsers. No subprocess, no network,
  no dynamic code; strict type-before-membership, fail-closed on malformed input.
- **run_precommit_check.py** — no subprocess/network/dynamic code. Task id is
  regex-pinned (`^TASK-\d+$`, line 865). Evidence-ref registry loader fails closed
  (lines 255-373) and forbids URL schemes, parent traversal, absolute/Windows
  paths. Evidence-ref forbidden-pattern sieve at 550-585 is read-only path
  classification (no execution).
- **run_red_team_suite.py / red_team/helpers.py / case_builders.py** —
  `run_command` (helpers.py:148-193) is argv-only, enforces an **env override
  allowlist** (`ALLOWED_ENV_OVERRIDES = {CONSILIUM_ALLOWED_GITHUB_API_HOSTS}`,
  raises on any other key, requires str values), copies `os.environ` then updates,
  applies a `timeout` (default 60s / git 30s) and an output byte cap (1 MiB).
  Temp roots are uuid-suffixed under the repo; cleanup handles read-only files.
  This is the model the other scripts should follow.
- **run_quality_gates.py** QC-IMPORT-001 (lines 760-848) — see F under "Notable
  good controls"; reviewed as acceptable.
- **experiments/red_team_marathon.py:44-64** — fixed argv (`sys.executable SUITE
  --phase <choice>`), `timeout=600`, phase value is a constrained CLI choice.

---

## Findings

### F-01 — Argument injection into `git rev-parse` via untrusted Base/Head Ref
**Severity:** Medium
**Location:** `artifacts/scripts/guard_status_validator.py:699-700` (extraction),
`:716-731` (use), `:595-604` (`resolve_git_revision_commit`).

**Description.**
`base_ref` and `head_ref` are read directly from a code artifact's
`## Diff Evidence` block (`evidence.get("base ref")`, `evidence.get("head ref")`)
with only `.strip()` applied. They are then passed to:

```python
command = ["git", "-C", str(repo_root), "rev-parse", f"{revision}^{{commit}}"]
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
```

Unlike `base_commit`/`head_commit`, which are strictly validated by
`COMMIT_SHA_PATTERN = ^[0-9a-f]{40}$` (line 154, enforced at 709-711), the *refs*
receive **no character validation**. Because the value is interpolated as a
standalone argv element and `git rev-parse` parses leading `-` as options, an
attacker who controls a code artifact can supply a ref such as `--git-dir=...`,
`-` or other `rev-parse` flags. There is no `shell=True`, so this is **argument
injection, not full command injection** — the blast radius is limited to what
`git rev-parse` flags can do (e.g. `--git-dir`/`--show-toplevel` to point at
another repo, or option-confusion causing misleading resolution). The resolved
value only drives a *warning* (lines 719-731), and the authoritative diff at
line 732 uses the SHA-validated `base_commit`/`head_commit`, which bounds impact.

**PoC sketch.** In a code artifact under validation:
```
## Diff Evidence
- Evidence Type: commit-range
- Base Ref: --git-dir=/tmp/evil/.git
- Head Ref: HEAD
- Base Commit: <40 hex>
- Head Commit: <40 hex>
- Diff Command: git diff --name-only <base>..<head>
```
`resolve_git_revision_commit(repo_root, "--git-dir=/tmp/evil/.git")` runs
`git -C <root> rev-parse --git-dir=/tmp/evil/.git^{commit}`, feeding an
attacker-chosen flag to git.

**Existing mitigation.** No shell; refs only influence a non-blocking warning;
the binding diff uses SHA-validated commits. `git -C` fixes the working
directory.

**Recommended fix.** Validate refs before use, e.g. reject any ref starting with
`-` and constrain to a git-ref-safe charset, or pass `--end-of-options` /
`--` so git stops option parsing:
`["git","-C",root,"rev-parse","--end-of-options", f"{revision}^{{commit}}"]`,
and add `git -c protocol.ext.allow=never` discipline if refs could ever name
remotes.

---

### F-02 — Env-controlled SSRF allowlist and token forwarding to artifact-named host
**Severity:** Low
**Location:** `artifacts/scripts/guard_status_validator.py:323-356`
(`get_allowed_github_api_hosts`, `normalize_api_base_url`), `:434-455`
(token + `urlopen`).

**Description.**
The github-pr diff-evidence path fetches `…/pulls/<n>/files` from an
**`API Base URL` taken from the untrusted code artifact** (`collect_github_pr_files`).
The host is checked against an allowlist: `api.github.com` plus whatever is in
the env var `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` (lines 323-336). Two trust
concerns:

1. **Env var widens SSRF reach.** Any host added to
   `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` becomes reachable by an artifact-supplied
   URL. The red-team suite itself sets this to `127.0.0.1` (helpers/case_builders),
   demonstrating that loopback/internal hosts are intended to be allowlistable.
   In an environment where this env var is set broadly, an artifact could point
   the fetch at internal services. This is by design (GitHub Enterprise), but it
   is an env-trust-to-SSRF coupling worth documenting.
2. **Token leakage to allowlisted host.** `GITHUB_TOKEN`/`GH_TOKEN` (line 434) is
   attached as `Authorization: Bearer <token>` (line 441) to **whatever
   allowlisted host the artifact named**, not solely `api.github.com`. If an
   operator allowlists an attacker-influenced or compromised Enterprise host, the
   token is sent there.

**PoC sketch.** With `CONSILIUM_ALLOWED_GITHUB_API_HOSTS=internal.example` set in
CI, an artifact sets `API Base URL: https://internal.example` and the validator
issues an authenticated request (Bearer token) to that internal host.

**Existing mitigation.** Strong: scheme restricted to http/https, host must be in
the allowlist (default = only `api.github.com`), 30s `urlopen` timeout, response
size capped at `MAX_DIFF_EVIDENCE_REPLAY_BYTES + 1` (line 451), page cap, strict
JSON-shape validation. Default behavior reaches only `api.github.com`.

**Recommended fix.** Only forward the bearer token when the resolved host is
`api.github.com` (or an explicitly token-trusted Enterprise host list distinct
from the reachability allowlist). Optionally resolve+pin the host IP to reject
DNS-rebinding and block RFC1918 targets unless explicitly opted in.

---

### F-03 — Git scope subprocesses: inherited env, no timeout
**Severity:** Low
**Location:** `artifacts/scripts/guard_status_validator.py:554-575`
(`collect_git_changed_files`), `:578-592` (`collect_git_diff_range_files`),
`:595-604` (`resolve_git_revision_commit`).

**Description.** These `subprocess.run(["git", …])` calls pass **no `env=`** (so
they inherit the full ambient environment, including any `GIT_*` overrides such as
`GIT_DIR`, `GIT_CONFIG_*`, `GIT_SSH_COMMAND`, `GIT_PROXY_COMMAND`) and **no
`timeout=`**. A malicious or misconfigured environment, or a git invocation that
hangs (e.g. pager/credential prompt, hostile in-repo config), can stall the
validator indefinitely. Contrast `red_team/helpers.run_command`, which caps
timeout and output. `git -C` is used (good — fixes cwd), and outputs are parsed
via `normalize_path_token` with traversal/dir filtering (good).

**PoC sketch.** A repo with `core.pager`/hook config or env `GIT_SSH_COMMAND`
pointing at a slow/interactive command causes `git diff` to block; the validator
has no timeout to recover.

**Existing mitigation.** `git -C <repo_root>` pins the directory; non-zero exit
is handled and downgraded to a warning; output is normalized and traversal-checked.

**Recommended fix.** Add a bounded `timeout=` to each git call and pass a
sanitized `env` (strip/normalize `GIT_*`, set `GIT_TERMINAL_PROMPT=0`,
`GIT_OPTIONAL_LOCKS=0`, no pager) as the red-team `run_command` does.

---

### F-04 — `git show HEAD:<path>` from artifact-derived path tokens
**Severity:** Low
**Location:** `artifacts/scripts/migrate_artifact_schema.py:198-211`
(`load_git_head_text`); token source `:162-195`.

**Description.** `load_git_head_text` runs
`["git", "show", f"HEAD:{relative_path}"]` with `check=True`, `cwd=root`, argv,
no shell. `relative_path` originates from artifact text via
`extract_path_like_tokens` / `is_path_like_reference`, which require the token to
start with an allowlisted prefix (`artifacts/`, `docs/`, `template/`, `README…`,
etc.) or contain `/` and not start with `python`. This blocks a bare leading-dash
token and the `HEAD:` prefix constrains git to a tree path, so practical injection
is low. However, the token is not explicitly validated against `..`/refspec
tricks here (it relies on the prefix filter), and a value like
`docs/../-something` is conceivable.

**PoC sketch.** Limited: the `HEAD:` revspec prefix and the prefix allowlist make
option/refspec injection impractical, but no positive ref/path validation is
applied at the call site.

**Existing mitigation.** argv (no shell); fixed `HEAD:` prefix; prefix allowlist;
failures swallowed to empty string.

**Recommended fix.** Normalize and reject `..` in `relative_path` before use
(reuse `resolve_workspace_relative_path` semantics), and add `--` /
`--end-of-options` after `git show` defensively.

---

### F-05 — Dynamic import of in-repo module paths
**Severity:** Informational
**Location:** `artifacts/scripts/run_red_team_suite.py:29-32`
(`from red_team.helpers import *`, `from red_team.case_builders import *`);
`artifacts/scripts/red_team/helpers.py:75-81` (`load_module` via
`importlib.util.spec_from_file_location` + `exec_module`), used at
`case_builders`/helpers to load `guard_contract_validator` from
`CONTRACT_GUARD` (a fixed repo path).

**Description.** `load_module` executes module code from a path. Today every path
is a **fixed, repo-controlled constant** (`CONTRACT_GUARD`, `STATUS_GUARD`), not
attacker-influenced, so there is no current code-execution exposure. It is
flagged so the invariant is explicit: these paths must never be derived from
artifact/PR/env input, or `exec_module` becomes an arbitrary-code sink.

**Existing mitigation.** Import targets are hard-coded module paths derived from
`detect_repo_root()`; no untrusted input reaches `spec_from_file_location`.

**Recommended fix.** Keep import targets constant; add a comment/assert that the
path is repo-root-relative and never artifact-sourced.

---

## Notable good controls (defense-in-depth observed)

- `red_team/helpers.run_command` (helpers.py:148-193): env-override **allowlist**
  with type checks, `os.environ.copy()` + update, timeout, 1 MiB output cap,
  graceful exception capture. Strong reference implementation.
- `resolve_workspace_relative_path` (guard_status_validator.py:295-311): rejects
  absolute paths, `..`, `/../`, and post-`resolve()` escapes from repo root.
- Strict SHA validation for pinned commits (`COMMIT_SHA_PATTERN`), archive byte
  caps, response byte caps, and JSON-shape validation throughout the diff-evidence
  replay path.
- `run_quality_gates.py` QC-IMPORT-001 (760-848): import probe runs in a child
  `python -S -B -c` with `PYTHONDONTWRITEBYTECODE/PYTHONUTF8/PYTHONNOUSERSITE`
  and a 30s timeout; module name is `path.stem` of a baseline-listed file (not
  arbitrary). `run_precommit_check.py` / `run_quality_gates.py` registry loaders
  fail closed and forbid URL schemes, shell tokens, traversal, and absolute paths
  in evidence refs.
- The pure-parser gates (release/sast/sbom/sca/security_txt) deliberately do
  **no** subprocess/network — "map, don't recreate" boundary is honored.
