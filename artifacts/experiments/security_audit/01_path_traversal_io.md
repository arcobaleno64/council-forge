# Security Audit 01 — Path Traversal, Unsafe Filesystem I/O, Archive/Diff Handling

- Scope: path traversal, unsafe FS ops, archive/diff replay, snapshot replay, symlink-follow on copy/cleanup, TOCTOU, zip-slip, unbounded reads.
- Mode: READ-ONLY review. No source modified.
- Repo root: `/home/user/council-forge`
- Reviewer note: every finding is grounded in `file:line`. Threat model distinguishes (a) **untrusted artifact content** (markdown/JSON ingested by guards, the highest-value attack surface since CI runs guards on PR-supplied artifacts) from (b) **trusted operator CLI args** (`--task-id`, `--artifacts-root`, `--root`).

---

## Findings

### F-01 — Archive replay byte cap is enforced *after* the full file is read into memory (read-amplification / cap bypass)
- Severity: Low
- Location: `artifacts/scripts/guard_status_validator.py:380-388` (`load_archive_snapshot`)
- Description: The Archive Path (an artifact-derived relative path) is read with `archive_path.read_bytes()` (line 380), which reads the **entire** file into memory unconditionally. Only afterward (line 385) is the `MAX_DIFF_EVIDENCE_REPLAY_BYTES` (128 KiB) cap checked. Contrast with the disciplined `read_bounded_file` used for artifacts (`guard_helpers/io.py:68-80`), which reads `cap + 1` bytes via a bounded `handle.read(...)`. An attacker who can place a large file inside the repo and reference it as `Archive Path` forces the guard to buffer the whole file in memory before rejecting it.
- Proof-of-concept sketch: Craft a `*.code.md` with `## Diff Evidence` of `Evidence Type: commit-range`, a valid `Archive SHA256` for a multi-GB in-repo file, and `Archive Path: <that file>`. The guard `read_bytes()` the whole file (memory pressure / potential OOM on CI) before the line-385 size check fires.
- Existing mitigation: Path is constrained to the repo via `resolve_workspace_relative_path` (line 376), and a cap exists (line 385) — but it is post-read. Practical impact is bounded because the referenced file must live inside `REPO_ROOT` (so it is attacker-influenced only to the extent they control repo contents), and SHA256 must match. Severity is therefore Low (DoS-class, not traversal).
- Recommended fix: Use the existing `read_bounded_file(archive_path, ..., too_large_label=...)` helper (cap+1 bounded read) instead of `read_bytes()`, or open and `handle.read(MAX_DIFF_EVIDENCE_REPLAY_BYTES + 1)` and reject if longer — mirroring `guard_helpers/io.py:71`.

### F-02 — Windows drive-letter and UNC path normalization is partial; `normalize_path_token` strips only single-letter `X:/` drives
- Severity: Low
- Location: `artifacts/scripts/guard_helpers/parsers.py:75-82` (`normalize_path_token`); consumed by `resolve_workspace_relative_path` at `guard_status_validator.py:295-311`.
- Description: `normalize_path_token` converts `\` to `/` and strips a leading `X:/` drive prefix, but does **not** strip a bare `X:` (no slash) prefix, nor does it handle UNC `//server/share`. The downstream guard `resolve_workspace_relative_path` rejects POSIX-absolute (`/...`), `..`, `../`, and `/../`, and then enforces `resolved_candidate.relative_to(resolved_root)` (lines 299-310). On Linux (the CI platform) the `relative_to` check after `.resolve()` is the real containment guarantee, so escape is not achievable. On Windows, a token like `C:..\evil` could normalize inconsistently; the `relative_to` check still backstops it. This is defense-in-depth hygiene, not a confirmed escape.
- Proof-of-concept sketch: Supply `Archive Path: C:windows\system32\x` in `## Diff Evidence`. `normalize_path_token` leaves `C:windows/system32/x`; on Windows `repo_root / "C:windows/..."` is anchored, the `relative_to` check rejects it. No bypass demonstrated on Linux.
- Existing mitigation: `relative_to(resolved_root)` containment check (lines 308-310) is the authoritative gate and holds on the CI platform.
- Recommended fix: In `normalize_path_token`, additionally reject/strip bare-drive (`^[A-Za-z]:`) and UNC (`^//`) forms, and treat any residual `:` as suspicious for path tokens. Keep the `relative_to` check as the primary defense.

### F-03 — `task_id` is used to build/glob filesystem paths before format validation
- Severity: Low
- Location: path build/glob: `guard_helpers/io.py:55-65` (`artifact_path`, `find_artifact_paths` glob `f"{task_id}*.improvement.md"`); call sites `guard_status_validator.py:2545` (`resolve_validation_mode`), `:2563`, `:2582` (`load_json(artifact_path(...))`). Format validation `validate_task_id` (`:786-787`) only runs deeper inside `validate_all`.
- Description: `--task-id` is interpolated into `Path` construction and a glob pattern before `TASK_ID_PATTERN` is enforced. `artifact_path` joins `artifacts_root / dir / f"{task_id}{ext}"`, so a `task_id` containing `../` or `/` would compose a traversal path; `find_artifact_paths` passes `task_id` into `Path.glob`, where glob metacharacters (`*`, `?`, `[`) would be interpreted. However, `--task-id` is a **trusted operator CLI argument**, not untrusted artifact content, so this is an input-hardening gap rather than a remote-exploitable traversal. The red-team harness itself only ever passes well-formed IDs.
- Proof-of-concept sketch: `guard_status_validator.py --task-id '../../etc/passwd' --artifacts-root ./artifacts` would attempt to read `artifacts/status/../../etc/passwd.status.json` via `load_json`. Requires local CLI access; not reachable through artifact ingestion.
- Existing mitigation: `read_bounded_file` will simply fail to find the file in most cases; `validate_task_id` eventually flags bad IDs but only after some path operations. The trust boundary (operator-supplied arg) limits severity.
- Recommended fix: Validate `args.task_id` against `TASK_ID_PATTERN` in `main()` immediately after parse (before any `artifact_path`/glob use), returning exit 2 on mismatch. Cheap, removes the ordering gap.

### F-04 — `copy_task_fixture` / `copy_contract_fixture` copy from the live repo without symlink hardening (symlink-follow on read)
- Severity: Low
- Location: `artifacts/scripts/red_team/helpers.py:332-354` (`copy_task_fixture`, uses `rglob` + `read_text`/`write_text`), `:377-383` (`copy_contract_fixture`, uses `shutil.copy2`).
- Description: Fixture copying walks `REPO_ROOT/artifacts` with `rglob` and reads each match, then writes into the temp root; `copy_contract_fixture` uses `shutil.copy2`. Both **follow symlinks** when reading the source. If a malicious artifact file in the source tree were a symlink to an out-of-tree file, its contents would be copied into the temp fixture. The destination path is always derived from `relative_to(REPO_ROOT/artifacts)` + a sanitized `dest_name` (line 343 `.replace(...)`), so the *write* side stays inside the temp root — there is no write-side traversal. Source-side symlink-follow only leaks readable content the operator already controls (their own repo). Low severity, contained to a self-owned tree.
- Proof-of-concept sketch: Plant `artifacts/status/TASK-900.status.json` as a symlink to `~/.ssh/id_rsa`; running the red-team suite would copy that content into `.codex-red-team/...`. Requires pre-existing local write access to the repo (already game-over), so not a privilege boundary crossing.
- Existing mitigation: Destination paths are normalized and confined; `dest_name` is a basename-level replace, not attacker-controlled join.
- Recommended fix: When copying fixtures, skip entries where `source_path.is_symlink()`, or resolve and assert each source stays within `REPO_ROOT/artifacts` before reading.

### F-05 — `copy_task_fixture` uses `mkdir(exist_ok=True)` + dirless writes; `migrate_repository` globs/writes in place — no `dirs_exist_ok` overwrite-outside-root, but in-place writes are unbounded by symlink checks
- Severity: Info
- Location: `red_team/helpers.py:333-335` (per-dir `mkdir(parents=True, exist_ok=True)`), `:345` (`ensure_parent` + `write_text`); `migrate_artifact_schema.py:719-736` (`write_if_changed`/`write_json_if_changed` `path.write_text`).
- Description: I specifically checked for `shutil.copytree(..., dirs_exist_ok=True)` overwrite-outside-root and zip/tar extraction — **none exist** in scope (no `copytree`, no `tarfile`, no `zipfile`). Fixture creation uses per-directory `mkdir(exist_ok=True)` into the freshly created temp root, and migration writes back to the exact files it globbed (`artifacts/**/TASK-*.*`). If any of those tracked target files were a symlink, `write_text` would follow it and overwrite the link target. As with F-04, the target set is operator-owned repo files, so this is informational hardening.
- Proof-of-concept sketch: Make `artifacts/verify/TASK-XXX.verify.md` a symlink to an out-of-repo file, run `migrate_artifact_schema.py --apply`; the migrated content overwrites the link target. Requires local repo write access.
- Existing mitigation: Migration operates only on `glob("TASK-*.*.md")` matches within `artifacts/`; no path is built from file *contents*.
- Recommended fix: Before `write_text` in migration, assert `not path.is_symlink()` (or `O_NOFOLLOW`-style open) to avoid following a planted symlink.

### F-06 — `cleanup_temp_roots` deletes via `shutil.rmtree` with a readonly-chmod `onerror` handler; safe but worth noting for symlinked temp entries
- Severity: Info
- Location: `red_team/helpers.py:303-329` (`handle_remove_readonly`, `cleanup_temp_roots`).
- Description: I checked specifically for "cleanup deleting outside temp root." The cleanup only operates on paths in `CREATED_TEMP_ROOTS`, each produced by `prepare_temp_root` as `LOCAL_TMP_ROOT / f"{case_id}-{uuid4}"` (`:291-296`) — i.e., always a child of `.codex-red-team` with a random suffix, created via `mkdir(exist_ok=False)`. The final `root.rmdir()` (line 324) only runs when `next(root.iterdir())` raises `StopIteration` (empty dir), so a non-empty `LOCAL_TMP_ROOT` is never blown away. `handle_remove_readonly` (line 303-305) chmods then retries on `rmtree` errors. `shutil.rmtree` does not recurse into symlinked directories (it unlinks the symlink), so a planted symlink inside a temp root does not cause deletion of the link target's contents. No traversal/over-deletion path found. Recorded as cleared-with-note.
- Existing mitigation: Random per-case subdir, `exist_ok=False` creation, empty-only `rmdir` of the root.
- Recommended fix: None required. Optionally validate each path `is_relative_to(LOCAL_TMP_ROOT)` before `rmtree` as belt-and-suspenders.

### F-07 — `load_archive_snapshot` / snapshot replay path normalization correctly blocks `../` in archive lines
- Severity: Info (positive finding)
- Location: `guard_status_validator.py:404-416`.
- Description: Each archive line is run through `normalize_path_token` and rejected if empty, `..`, `../`-prefixed, or containing `/../` (line 408), plus blank-line, duplicate, and sort-order checks. The archive contents are only ever compared as a **set of strings** against the Changed Files Snapshot — they are never used to open or write files. So even a malicious archive line cannot cause filesystem access outside the repo; worst case is a false scope-match, which is independently gated by the SHA256 match (line 390) and the snapshot equality check (line 417). Confirmed safe.

---

## Surfaces checked and cleared ("no issue found here")

- **Zip-slip / archive extraction**: No `tarfile`, `zipfile`, `shutil.unpack_archive`, or `copytree` anywhere in scope. "Archive" here means a plain UTF-8 text manifest of file paths (`guard_status_validator.py:367-422`), not a compressed archive. Not applicable.
- **Changed Files Snapshot replay → filesystem access**: Snapshot/archive paths are compared as string sets only; never opened or joined for I/O (`guard_status_validator.py:404-421`, `743-748`). No traversal.
- **`resolve_workspace_relative_path` containment**: Rejects absolute, `..`, `../`, `/../`, and enforces `resolved_candidate.relative_to(resolved_root)` after `.resolve()` (`:295-311`). On the Linux CI platform this is a sound containment check. Cleared (see F-02 for Windows-only hygiene note).
- **GitHub PR files fetch**: URL host is allow-listed (`normalize_api_base_url`, `:339-356`), owner/repo are `urllib.parse.quote(..., safe='')`-escaped (`:445`), pull_number is `isdigit()`-validated (`:429`), response is read with a `cap+1` bounded `response.read(MAX_DIFF_EVIDENCE_REPLAY_BYTES + 1)` and size-checked (`:451`, `:458`), page count is capped (`:466-467`). No SSRF beyond the allow-list, no unbounded read. Cleared.
- **Artifact file reads (`load_text`/`load_json`/`read_bounded_file`)**: Bounded `cap+1` read with explicit size ceiling (`guard_helpers/io.py:68-98`), UTF-8 decode errors raise `GuardError`. Cleared. (Note: the archive read at `:380` does NOT use this helper — see F-01.)
- **`override_log` / `load_override_log`**: Bounded read + JSON-array shape validation (`guard_helpers/io.py:123-136`). Cleared.
- **`migrate_artifact_schema.py` path building**: All artifact paths are built from `glob("TASK-*.*")` results and `task_id` derived from `path.stem` — never from file *contents*. `linked_artifacts_for_task` (`:274-288`) builds fixed `artifacts/<dir>/<task_id>.<ext>` strings and only `.exists()`-checks them. `load_git_head_text` (`:198-211`) passes `HEAD:<relative_path>` to `git show` with `cwd=root`; `relative_path` is a constant template, not attacker-controlled. Cleared.
- **`legacy_verify_corpus.py`**: Reads `manifest.json` and `row["fixture_name"]` from a repo-internal `test/legacy_verify_corpus` dir (`:24-51`). `fixture_name` is joined onto `base_root` without a containment check, but the manifest is a tracked, non-untrusted fixture catalog (test data, not PR-ingested artifact input). Noted but not a finding under the threat model (would only matter if the corpus manifest were attacker-controlled). Cleared.
- **`run_command` env handling** (`red_team/helpers.py:148-193`): Rejects env overrides outside `ALLOWED_ENV_OVERRIDES`, enforces string values, applies subprocess timeout + output cap. Cleared.
- **`subprocess` git invocations**: All use argument-vector form (`["git", "-C", str(repo_root), ...]`), never `shell=True`; refs (`base_commit`/`head_commit`) are validated as 40-char hex (`COMMIT_SHA_PATTERN`, `:709`) before being passed to `git diff` (`:578-592`). No shell injection. Cleared.
- **`prepare_temp_root` / TOCTOU**: Uses `mkdir(exist_ok=False)` with a random uuid suffix, so it cannot silently reuse a pre-existing attacker-planted dir (`:291-296`). Cleared.

---

## Summary Table

| ID | Severity | Title | Location |
|----|----------|-------|----------|
| F-01 | Low | Archive replay cap enforced after full `read_bytes()` (read-amplification) | guard_status_validator.py:380-388 |
| F-02 | Low | Partial Windows drive/UNC normalization (Linux backstopped by `relative_to`) | guard_helpers/parsers.py:75-82 |
| F-03 | Low | `task_id` (CLI arg) used in path/glob before format validation | guard_helpers/io.py:55-65; gsv.py:2545 |
| F-04 | Low | Fixture copy follows source symlinks (self-owned tree) | red_team/helpers.py:332-383 |
| F-05 | Info | In-place migration `write_text` follows planted symlinks (self-owned) | migrate_artifact_schema.py:719-736 |
| F-06 | Info | `cleanup_temp_roots` confined to random temp subdirs (cleared w/ note) | red_team/helpers.py:303-329 |
| F-07 | Info | Archive-line `../` rejection + set-only comparison (positive finding) | guard_status_validator.py:404-421 |

**Bottom line:** No Critical/High issues. No zip-slip, no archive extraction outside root, no demonstrated directory traversal through untrusted artifact ingestion on the Linux CI platform — the `relative_to(resolved_root)` containment check and bounded reads are the consistent strong controls. All findings are Low/Info hardening items: a post-read byte cap on the archive replay (F-01, the only one with real DoS potential), incomplete Windows path-prefix normalization (F-02, Linux-backstopped), early `task_id` validation ordering (F-03, trusted-arg), and source-side symlink-follow on copy/migrate over operator-owned trees (F-04/F-05).
