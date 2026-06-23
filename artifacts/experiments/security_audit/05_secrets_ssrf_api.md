# Security Audit 05 — Secrets Handling, SSRF, URL/Host Validation, Embedded HTTP Server

Scope: `artifacts/scripts/run_red_team_suite.py` + `artifacts/scripts/red_team/helpers.py` (embedded HTTP server, allowlist), `artifacts/scripts/guard_status_validator.py` (GitHub PR files reconstruction), `artifacts/scripts/repo_security_scan.py` (secret scanner), `artifacts/scripts/security_txt_gate.py`.
Mode: READ-ONLY review. Owner-requested defensive self-assessment. All findings grounded in file:line.

## Summary Table

| ID | Severity | Component | Title |
|---|---|---|---|
| F-01 | High | guard_status_validator.py | Redirect-following SSRF + token leak (no custom redirect handler) |
| F-02 | Medium | guard_status_validator.py | Host allowlist enforced only on base URL, not per-request / not on redirect target |
| F-03 | Medium | repo_security_scan.py | Secret scanner echoes the matched secret into report/JSON/SARIF output |
| F-04 | Medium | repo_security_scan.py | Structured-secret false-negative gaps (missing common token formats) |
| F-05 | Low | repo_security_scan.py | `generic_secret_is_actionable` entropy/placeholder gate misses low-entropy & non-quoted secrets |
| F-06 | Low | guard_status_validator.py | Provider JSON response trusted for filenames; no scheme-downgrade guard on `API Base URL` redirect |
| F-07 | Info | repo_security_scan.py | `0.0.0.0` bind rule is `low`/advisory-only and not enforced |

## Cleared (reviewed, no action required)

- **Embedded HTTP server bind address** — `red_team/helpers.py:257` binds `ThreadingHTTPServer(("127.0.0.1", 0), Handler)`: loopback only, ephemeral port, `daemon=True` thread, lifetime scoped to a `@contextmanager` with `server.shutdown()`/`server_close()` in `finally` (helpers.py:257-265). It is a *test fixture* serving canned PR-files JSON (helpers.py:231-252), not a production listener, and never binds `0.0.0.0`. No exposure. `run_red_team_suite.py:19` imports the symbols but the live server is instantiated only in the helper. Cleared.
- **Userinfo / case / port host-bypass on the allowlist** — `get_allowed_github_api_hosts` (guard_status_validator.py:323-336) and `normalize_api_base_url` (339-356) both derive the host via `urllib.parse.urlparse(...).hostname`, which lowercases and strips `user@` userinfo and `:port` (verified: `API.GitHub.com`→`api.github.com`, `user@api.github.com`→`api.github.com`, `api.github.com:443`→`api.github.com`). So `user@evil.com@api.github.com` style and case tricks do not bypass. Cleared.
- **Trailing-dot bypass** — `api.github.com.` parses to hostname `api.github.com.` (with the dot), which is NOT in `DEFAULT_GITHUB_API_ALLOWED_HOSTS = {"api.github.com"}` (guard_status_validator.py:167), so it is *rejected* (fail-closed), not accepted. Cleared.
- **security_txt_gate.py network use** — pure parsing, no `urllib`/`socket`/`subprocess`; it explicitly does NOT fetch Policy/Canonical URLs (docstring line 27, code 66-155). `validate_uri` rejects `http://` web URIs and host-less `https` (72-76). No SSRF surface. Cleared.
- **Token presence in error strings** — `summarize_remote_error_detail` (guard_status_validator.py:359-364) returns response *body*, not request headers; `Authorization` is not echoed into error messages. URL is echoed (455) but the URL carries no token. Cleared (subject to F-01, where the token travels over the wire, not into logs).
- **Scanner fail-closed coverage** — `read_text`/`iter_repo_files`/`main` are fail-closed on traversal/stat/read OSError (repo_security_scan.py:283-329, 540-570), exit 2 on any in-scope read failure. Good. Cleared.

---

## F-01 — Redirect-following SSRF with `Authorization` token leak (High)

**Location:** `artifacts/scripts/guard_status_validator.py:448-450` (`urllib.request.Request` + bare `urllib.request.urlopen`), token attached at 434-441.

**Description.** `collect_github_pr_files` builds a request with `Authorization: Bearer <GITHUB_TOKEN/GH_TOKEN>` (434-441) and issues it with `urllib.request.urlopen(request, timeout=30)` (450). No custom `OpenerDirector`/`HTTPRedirectHandler` is installed (grep confirms no `build_opener`/`install_opener`/redirect override in the file), so Python's default `HTTPRedirectHandler` follows 301/302/303/307/308 automatically. Verified on the runtime interpreter (Python 3.11.15) that `HTTPRedirectHandler.redirect_request` strips only `content-length`/`content-type` and **re-attaches every other header — including `Authorization` — to the redirect target Request**. Host validation (`normalize_api_base_url`, 339-356) runs **once on the base URL only**; the redirect `Location` is never re-validated.

Attack path: the `API Base URL` is taken from a *code artifact's* `## Diff Evidence` section (guard_status_validator.py:682, evidence parsed from the markdown the implementer authored). An attacker who can land a code artifact (or who controls/compromises any allowlisted GitHub Enterprise host) can point at an allowlisted host that returns `302 Location: http://169.254.169.254/latest/meta-data/...` (cloud metadata) or any internal host. `urlopen` follows it, the bearer token is forwarded to the internal/attacker endpoint, and the internal response is then parsed as the "provider" file list.

**PoC / bypass sketch.**
```
# Code artifact ## Diff Evidence (api.github.com is on the allowlist by default):
- Evidence Type: github-pr
- API Base URL: https://api.github.com   # passes normalize_api_base_url
# ...but if api.github.com (or an allowlisted GHE host the attacker controls) responds:
HTTP/1.1 302 Found
Location: http://169.254.169.254/latest/meta-data/iam/security-credentials/
# urlopen follows it; Authorization: Bearer <token> is re-sent to 169.254.169.254;
# the metadata response is read (capped at 128 KiB) and parsed as the PR file list.
```
Internal-host reachability (SSRF) is achievable even with the allowlist intact, because the *first hop* host is allowlisted and only the redirect target is internal.

**Existing mitigation.** Response size cap of `MAX_DIFF_EVIDENCE_REPLAY_BYTES + 1` (451, 458-459); 30 s timeout; host allowlist on the base URL (348-355). None of these stop redirect-based SSRF or token forwarding.

**Recommended fix.** Install a custom opener that (a) refuses redirects entirely (raise on 3xx) — the GitHub files API does not need them — or (b) re-runs `normalize_api_base_url`-style host validation on every redirect target AND drops the `Authorization` header on any cross-host hop. Simplest: build an opener with a `HTTPRedirectHandler` subclass whose `redirect_request` returns `None` (no auto-redirect) and treat a 3xx as an error. Additionally block link-local/loopback/private IP literals (169.254.0.0/16, 127.0.0.0/8, 10/8, 172.16/12, 192.168/16, ::1, fc00::/7) for the resolved target.

## F-02 — Host allowlist not enforced per-request / not on redirect target (Medium)

**Location:** `artifacts/scripts/guard_status_validator.py:431-433` (validation once before the page loop), loop 443-481.

**Description.** `normalize_api_base_url` is called a single time (431) and the validated `base_url` is reused for every page (444-447). The allowlist is therefore an *entry* check, not an invariant maintained per outbound request. Combined with F-01 the redirect target is never checked. Even absent redirects, this couples allowlist safety to the assumption that `urlopen` contacts exactly the host in `base_url` — an assumption broken by redirects and by any future change to URL construction.

**PoC / bypass sketch.** Same redirect chain as F-01; the per-page loop never re-validates.

**Existing mitigation.** Default allowlist is the single host `api.github.com` (167); env override `CONSILIUM_ALLOWED_GITHUB_API_HOSTS` is parsed safely (323-336).

**Recommended fix.** Validate the *effective* host immediately before each `urlopen`, and after any redirect (see F-01 fix). Consider pinning the connection host rather than trusting `urlopen` to honor it.

## F-03 — Secret scanner echoes the matched secret into its own output (Medium)

**Location:** `artifacts/scripts/repo_security_scan.py:388-390` (structured patterns), `394-408` (generic), `369` (`excerpt.strip()`), `476-479` & `471` (text/JSON render), `483-503` (SARIF), `527`/`569` (print to stdout).

**Description.** For every match, `excerpt` is set to the **entire source line** containing the secret (389 `text.splitlines()[line_number-1]`; 406 passes the full `line`). `Finding.excerpt` is then printed verbatim by `render_findings` (479 `f"  {finding.excerpt}"`), included in JSON (`asdict`, 471), and — for SAST — flows to SARIF. So a tool whose purpose is to *find* leaked secrets will itself **reproduce the matched secret in its report, on the console, and in any CI log / SARIF artifact** that captures its output. A real GitHub PAT or AWS key found in a file is re-emitted in plaintext into logs that are frequently more widely readable than the source.

**PoC / bypass sketch.** Run `repo_security_scan.py secrets --json` over a tree containing `ghp_<real40chars>`; the JSON `excerpt` field contains the full token; the human output prints the whole line. CI captures it.

**Existing mitigation.** `dedupe_findings` (457-466) and placeholder filtering reduce volume, not exposure. None mask the value.

**Recommended fix.** Redact the captured secret group in the excerpt before building the `Finding` (e.g. replace `match.group("secret")` with `<redacted:NN chars, sha256 prefix>`), or store only an offset + length + masked preview. Never emit the raw matched secret. Apply to both structured (388-390) and generic (399-407) paths.

## F-04 — Structured-secret false-negative gaps (Medium)

**Location:** `artifacts/scripts/repo_security_scan.py:82-88` (`STRUCTURED_SECRET_PATTERNS`).

**Description.** The structured set covers only GitHub PAT (classic + fine-grained), AWS access-key-id, OpenAI `sk-`, and PEM private-key blocks. Notable formats it misses entirely (no rule, and they will not reliably hit the generic `key/secret/token = "..."` assignment rule because they often appear bare or under other variable names):
- **GitHub Actions / app tokens:** `ghs_` is matched by the classic charset `gh[pousr]_` (the `s` is included) — OK — but **GitHub refresh tokens `ghr_`** are covered too; however `github_pat_` fine-grained is matched. (These are covered; listed for completeness.)
- **Slack tokens** `xox[baprs]-...`, **Slack webhooks** `https://hooks.slack.com/services/...`.
- **Google API keys** `AIza[0-9A-Za-z\-_]{35}`, **GCP service-account JSON** (`"private_key": "-----BEGIN PRIVATE KEY-----` is caught by the PEM rule, but `"type": "service_account"` + `private_key_id` is not).
- **Stripe** `sk_live_` / `rk_live_` (NOT matched by the `sk-` OpenAI rule, which requires a hyphen `sk-`, whereas Stripe uses underscore `sk_`).
- **AWS secret access key** (the 40-char base64 secret half) — only the *access key ID* `AKIA...` is detected; the secret value is invisible.
- **JWTs** (`eyJ...` three base64url segments), **generic high-entropy base64/hex blobs** in config (no rule; only caught if assigned to a `key/secret/token`-named field via the generic rule).
- **Azure / npm (`npm_`) / PyPI (`pypi-`) / Twilio / SendGrid (`SG.`)** tokens.

Because `AKIA` matches only the ID, an `AKIA...` + adjacent 40-char secret leak reports the ID but never the more sensitive secret value.

**PoC / bypass sketch.** A file containing `slack_bot = "xoxb-2222-...."` or `STRIPE=sk_live_abcdef...` (no `key/secret/token` substring in the variable on the latter if named e.g. `STRIPE`) passes the scan clean: structured rules don't match, and the generic rule requires the variable name to contain api_key/token/secret/password.

**Existing mitigation.** Generic assignment rule (77-80) catches `*key/token/secret/password = "16+ chars"` with entropy >= 3.0, which covers *some* of the above when the variable is conventionally named.

**Recommended fix.** Add high-confidence prefixed rules: `xox[baprs]-`, `AIza[0-9A-Za-z_\-]{35}`, `sk_live_`/`rk_live_`/`pk_live_`, `SG\.[\w\-]{22}\.[\w\-]{43}`, `npm_[A-Za-z0-9]{36}`, `pypi-AgEI`, JWT `eyJ[A-Za-z0-9_-]+\.eyJ...`. Add an AWS-secret heuristic (40-char base64 near an `AKIA`). Keep them prefix-anchored to hold the low-FP discipline.

## F-05 — Generic-secret gate misses low-entropy and unquoted secrets (Low)

**Location:** `artifacts/scripts/repo_security_scan.py:77-80, 351-365`.

**Description.** (1) `GENERIC_SECRET_ASSIGNMENT` requires the value to be **quoted** (`["'] ... ["']`) and >= 16 chars; unquoted assignments (`API_KEY=abcdef...` in `.env`/shell, common) are not matched. (2) `generic_secret_is_actionable` requires `shannon_entropy >= 3.0` (365); a 16-char secret drawn from a small alphabet (e.g. lowercase-hex of a short value, or a structured password like `Summer2024!Summer`) can fall below 3.0 and be dropped as non-actionable. (3) `is_placeholder_secret` treats anything containing the substring `"test"` (PLACEHOLDER_MARKERS, 61-75) as a placeholder — a real secret that merely contains `test` (e.g. `prod-attestation-key-9f3a...`) is suppressed.

**PoC / bypass sketch.** `.env` line `API_KEY=deadbeefdeadbeef` (unquoted) → no match. Or `password = "aaaabbbbccccdddd"` → entropy ~2.0 → dropped. Or `token = "attestation-7f3a91c2e5"` → contains `test` substring? no; but `token = "latest-build-key-aa11"` contains `test` → suppressed.

**Existing mitigation.** Conservative design is intentional (low FP). Structured rules cover prefixed tokens regardless of entropy/quoting.

**Recommended fix.** Also scan unquoted `name=value` in `.env`/shell; lower or remove the entropy floor for clearly-named secret fields; make placeholder markers word-boundary anchored (`\btest\b`) rather than substring, so `attestation`/`latest` don't suppress real hits.

## F-06 — Provider response trust + no scheme-downgrade guard (Low)

**Location:** `artifacts/scripts/guard_status_validator.py:464-481`.

**Description.** The provider JSON is trusted to enumerate changed files; `filename` is normalized (`normalize_path_token`, 476) but the *set* of files defines scope-drift pass/fail, so a tampered/compromised provider (reachable via F-01/F-02) can shape the verdict. Separately, `normalize_api_base_url` permits both `http` and `https` (343); a `http://` allowlisted host sends the bearer token in cleartext. No guard prevents an `https` base URL from redirecting down to `http` (the default redirect handler allows scheme downgrade), compounding F-01.

**Existing mitigation.** JSON shape is validated (464-475); size capped (458). Snapshot SHA256 must match the provider set (690-693), so a *silent* mismatch is caught — but a provider that returns exactly the attacker's snapshot passes.

**Recommended fix.** Require `https` for non-loopback hosts (reject `http` unless host is an explicitly-allowlisted local dev host); forbid https→http downgrade on redirect (folds into F-01 fix).

## F-07 — `0.0.0.0` bind rule is advisory-only (Info)

**Location:** `artifacts/scripts/repo_security_scan.py:221-227` (`sast-bind-all-interfaces`, severity `low`), emitted only via the advisory `sast` subcommand (439-454, `emit_sast` always returns 0, 520-527).

**Description.** The repo's own scanner *can* flag `"0.0.0.0"` binds but only as a non-enforcing `low`/`note` SAST finding; it does not fail a gate. Acceptable given no production server binds `0.0.0.0` in scope (the only HTTP server is loopback test fixture, F-cleared), but noting that an introduced `0.0.0.0` listener would not be blocked by CI on this rule alone.

**Recommended fix.** None required for current code; if a real listener is ever added, promote this to an enforcing rule.

---

## Notes on the embedded server (run_red_team_suite.py)

- `run_red_team_suite.py:19` imports `BaseHTTPRequestHandler, ThreadingHTTPServer` but does not instantiate a server in `main` (315-348). The live server is the `github_pr_files_server` context manager in `red_team/helpers.py:226-265`, used by red-team cases (case_builders.py:498, 761, 864, ...). Bind is `("127.0.0.1", 0)` — loopback, ephemeral. Handler serves only the canned `/repos/<owner>/<repo>/pulls/<n>/files` path (helpers.py:229-252), 404s everything else, suppresses access logging (254-255). Daemon thread, deterministic shutdown. No request body parsing, no file serving, no auth. Cleared.
