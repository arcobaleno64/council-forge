# Security Audit 02 — ReDoS / Catastrophic Backtracking Review

- **Scope**: Regular-expression Denial of Service across workflow scripts that run against untrusted artifact contents, markdown, git data, and secret-scan targets.
- **Method**: Enumerated every `re.*` pattern in `artifacts/scripts/**`, flagged nested/overlapping quantifiers and unbounded `.*`/`.+` around backtracking-prone groups, and empirically confirmed super-linear blowup with a throwaway Python timing harness (`re` + `time.perf_counter`, modest inputs, no added dependencies).
- **Engine note**: All patterns use the stdlib `re` backtracking engine (no `re2`). There is no global per-match timeout, so a single pathological line hangs the process.
- **Threat model**: Artifact `.md`/`.json` files are authored by agents and human/PR contributors and are **untrusted**. The guard runs in pre-commit and in CI (`run_precommit_check.py`, `guard_status_validator.py`). Files are size-capped at `MAX_ARTIFACT_FILE_BYTES = 512 * 1024` (`guard_helpers/io.py:35,78`) — but the confirmed payloads hang at **2 KB–15 KB**, far below that ceiling, so the cap is not a mitigation.

---

## Summary Table

| ID | Pattern | File:Line | Severity | Empirical worst case | Attacker-controllable |
|----|---------|-----------|----------|----------------------|-----------------------|
| REDOS-01 | `RESEARCH_SOURCES_ENTRY_PATTERN` | `guard_status_validator.py:174-176` | **Critical** | ~2 KB line → **15.2 s**; exponential (×8 per input doubling) | Yes — `## Sources` line in any `*.research.md` |
| REDOS-02 | `CITATION_PATTERN` (paren branch) | `guard_helpers/markers.py:7-16` and `guard_status_validator.py:137-146` (literal-identical, asserted by `test_guard_units.py:104`) | **High** | 10 KB → 1.47 s; 40 KB → 23.8 s (quadratic); `(a.a)*n` variant exponential (15 KB → 12.8 s) | Yes — each `## Confirmed Facts` item in any `*.research.md` |
| REDOS-03 | `extract_section` section body `(.*?)` w/ `re.DOTALL` | `guard_helpers/parsers.py:39` | Low (cleared-with-note) | Linear in practice; lazy quantifier with anchored follower | Yes, but not super-linear |
| REDOS-04 | `ROW_PATTERN` (9× adjacent `[^|]+`) | `validate_scorecard_deltas.py:10-12` | Low (cleared) | 60 KB → 2.5 ms (linear) | Yes, but `.match` anchored at `^`, single failing run |
| REDOS-05 | `GENERIC_SECRET_ASSIGNMENT` `[^"'\n]{16,}` | `repo_security_scan.py:77-80` | Low (cleared) | 200 KB → 5.7 ms (linear) | Yes, but linear |

---

## REDOS-01 — RESEARCH_SOURCES_ENTRY_PATTERN (Critical)

**File:Line**: `artifacts/scripts/guard_status_validator.py:174-176`
Invoked at `guard_status_validator.py:876` — `RESEARCH_SOURCES_ENTRY_PATTERN.match(line)` is run **per non-empty line** of the `## Sources` section of every `*.research.md` (`validate_research_citations`, lines 865-900).

```python
RESEARCH_SOURCES_ENTRY_PATTERN = re.compile(
    r"^\[(\d+)\]\s+.+\..+(?:https?://\S+|[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]{1,10})\s+\(\d{4}-\d{2}-\d{2}\s+retrieved\)$"
)
```

**Why it backtracks**: The fragment `.+\..+` is the textbook ambiguous-overlap construct — two greedy `.+` separated by a single literal `.`, with `.` itself matched by `.+`. For an input with `k` dots, the engine can partition them in `O(2^k)`-ish ways. The trailing required suffix `(?:url|path)\s+\(YYYY-MM-DD retrieved\)$` never matches the adversarial input, so the engine exhausts the entire partition space before failing. The inner alternative `[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]{1,10}` adds a *third* dot-consuming greedy group, compounding the blowup.

**Adversarial input**: a single `## Sources` line such as
`[1] ` + `"a."` repeated `N` times + ` x`
(i.e. `[1] a.a.a.a.…a. x`). The `^\[(\d+)\]\s+` prefix matches, then the dot-heavy body forces catastrophic partitioning, and the missing `(YYYY-MM-DD retrieved)` tail guarantees total backtracking.

**Empirical timing** (this machine, `re.search`):

| input | line length | time |
|-------|-------------|------|
| N=200 | 406 B | 124 ms |
| N=400 | 806 B | 985 ms |
| N=600 | 1.2 KB | 3.27 s |
| N=800 | 1.6 KB | 7.72 s |
| N=1000 | 2.0 KB | **15.2 s** |

Doubling the input (~406 B → ~806 B) multiplies time by ~8 — super-polynomial. A line is only ~2 KB to reach 15 s; the 512 KB file cap permits lines orders of magnitude larger, making a multi-minute / effectively-unbounded hang trivial.

**Attacker-controllability**: **High.** Any contributor who can land a `*.research.md` (PR, agent output) controls `## Sources` line content verbatim. The guard runs in pre-commit/CI, so this is a one-line DoS of the validation gate.

**Recommended fix**:
- Replace `.+\..+` with a non-ambiguous, possessive-emulated form. Anchor each segment to a bounded, non-overlapping char class, e.g. parse the line by splitting on whitespace and validating fields independently rather than one mega-regex.
- If a single regex is kept, remove the redundant greedy spans: match the author/title with `[^\n]*?` only where a unique following anchor exists, and make the URL/path alternative the sole dot-consumer. Add atomic grouping via the `(?>...)` emulation trick (`(?=(?P<a>...))(?P=a)`) around `.+\..+`.
- Bounded quantifiers (`{1,512}`) would cap the blast radius but do not eliminate the ambiguity; prefer restructuring.
- Strategic option: route guard regexes through `re2` (would require a dependency — out of scope per constraints) or wrap matches in a per-line length guard (reject lines > a few hundred chars before regex).

---

## REDOS-02 — CITATION_PATTERN paren branch (High)

**File:Line**: `artifacts/scripts/guard_helpers/markers.py:7-16` (canonical) and a literal-identical copy at `guard_status_validator.py:137-146`. `test_guard_units.py:104` asserts the two stay byte-identical, so any fix must be applied to **both**.
Invoked at `guard_status_validator.py:1084` — `CITATION_PATTERN.search(item)` runs **per `## Confirmed Facts` item** of every `*.research.md` (`validate_research_artifact`, lines 1081-1085).

```python
CITATION_PATTERN = re.compile(
    r"(?:"
    r"https?://\S+"
    r"|`gh api [^`]+`"
    r"|`[^`\n]+\.(?:md|json|txt|py|ps1|csproj|ini|toml|yml|yaml|cfg|sh)[^`\n]*`"
    r"|[（(](?:[Ss]ource:\s*)?[^)）\n]*?[A-Za-z0-9_./\\-]+\.(?:md|json|txt|py|ps1|csproj|ini|toml|yml|yaml|cfg|sh)(?::\d+)?[^)）\n]*[)）]"
    r"|\b[A-Za-z0-9_./\\-]+\.(?:md|json|txt|py|ps1|csproj|ini|toml|yml|yaml|cfg|sh)(?::\d+)?\b"
    r")",
    re.IGNORECASE,
)
```

**Why it backtracks**: The 4th alternation branch (the parenthesised-citation branch) has the shape
`[（(] … [^)）\n]*? <required path-with-extension> [^)）\n]* [)）]`.
It contains a lazy `[^)）\n]*?` and a greedy `[^)）\n]*` on **both sides** of a required group whose char class `[A-Za-z0-9_./\\-]+` overlaps heavily with `[^)）\n]`. When an opening paren is present but no closing `)`/`）` ever appears (so the branch must ultimately fail), the engine tries every split of the long run between the lazy prefix, the path group, and the greedy suffix, then re-tries from the next position via `search`. The overlapping classes plus the `(?::\d+)?` optional make each position quadratic, and the `a.a` form (many embedded extension-like dots) pushes it toward exponential.

**Adversarial inputs** (a single `## Confirmed Facts` item):
- `"(" + "a/"*N` — open paren, path-ish run, never closes → quadratic.
- `"(" + "a.a"*N` — open paren, dense extension-bait dots, never closes → exponential.

**Empirical timing** (this machine, `re.search`):

| variant | input | length | time |
|---------|-------|--------|------|
| `(` + `a/`×N | N=5000 | 10 KB | 1.47 s |
| `(` + `a/`×N | N=20000 | 40 KB | **23.8 s** |
| `(` + `a.a`×N | N=1000 | 3 KB | 511 ms |
| `(` + `a.a`×N | N=5000 | 15 KB | **12.8 s** |

**Attacker-controllability**: **High.** `## Confirmed Facts` item text is fully attacker-authored in any submitted `*.research.md`. A single bullet containing an unclosed parenthesis with path-like filler hangs the guard. (The 40 KB → 23.8 s point is well within the 512 KB cap.)

**Recommended fix**:
- Eliminate the two-sided unbounded fill around the required group. The closing-paren branch should consume the inner content with a single greedy negated class and let the engine match the path lazily only where anchored, e.g.
  `[（(][^)）\n]*?\.(?:md|json|…)(?::\d+)?[^)）\n]*?[)）]` — but the dual `[^)）\n]*` with an overlapping required group is the core defect; collapse to one fill segment.
- Better: require the closing paren earlier with an atomic group, or pre-check `if ')' not in item and '）' not in item: skip this branch` so the failing-no-close case never enters the quadratic loop.
- Bound the fills (`[^)）\n]{0,256}`) to cap blast radius.
- Apply identically to both copies (markers.py and guard_status_validator.py) to keep the asserted invariant.

---

## REDOS-03 — extract_section lazy DOTALL body (Low, cleared-with-note)

**File:Line**: `artifacts/scripts/guard_helpers/parsers.py:39`
```python
match = re.search(rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
```
Also the structurally identical `## Risks\s*\n(.*?)(?=\n## |\Z)` at `classify_existing_tasks.py:28`, and the `re.sub(... (.*?) ... , flags=re.DOTALL)` family in `red_team/case_builders.py` (lines 43, 205, 226, 254, 267, 507, 727, 770, 867).

**Assessment**: `(.*?)` is lazy and is immediately followed by a lookahead anchored to `\n## ` or end-of-string. There is no second unbounded quantifier competing for the same characters, so the engine advances roughly linearly to the next heading. `re.escape(heading)` neutralises metacharacters in the heading. No nested/overlapping quantifier. **Cleared** — but noted because lazy DOTALL bodies are a frequent ReDoS source; this one is safe only because the follower is a fixed anchor.

---

## REDOS-04 — ROW_PATTERN nine adjacent [^|]+ (Low, cleared)

**File:Line**: `artifacts/scripts/validate_scorecard_deltas.py:10-12`
Nine consecutive `[^|]+` / `[^|`]+` capture groups separated by literal `\|`. Adjacent same-class greedy groups can over-share characters, but each group is bounded by a mandatory literal `|` delimiter and the whole pattern is `^`-anchored via `.match`. A failing line with no pipes makes only the first group consume the run, then fails fast.

**Empirical**: 60 KB single run → 2.5 ms (linear). **Cleared.**

---

## REDOS-05 — GENERIC_SECRET_ASSIGNMENT (Low, cleared)

**File:Line**: `artifacts/scripts/repo_security_scan.py:77-80`
```python
r"...\b\s*[:=]\s*[\"'](?P<secret>[^\"'\n]{16,})[\"']"
```
Run per line (`scan_secrets`, line 395). `[^"'\n]{16,}` is a single greedy negated class with a literal-quote follower; an unterminated quote makes it consume to EOL once and fail — linear.

**Empirical**: 200 KB line → 5.7 ms (linear). **Cleared.**

---

## Cleared (no super-linear behaviour found)

The following high-density patterns were reviewed and judged linear/safe (anchored, single bounded quantifier, or fixed-width):

- `repo_security_scan.py`: all `STATIC_RULES`, `PYTHON_SAST_RULES`, and `STRUCTURED_SECRET_PATTERNS` — each is `^`-anchored or has a single bounded/possessive-like negated class; `{16,}`/`{20,}`/`{40}`/`{16}` are single, non-nested. `workflow-unpinned-action` (`:115`) uses a negative-lookahead + trailing `.+` but the `[^@\s]+/[^@\s]+` segments are pipe-/`@`-delimited and anchored — linear. `shannon_entropy` (`:337-348`) is a pure Python loop, no regex.
- `guard_status_validator.py`: `TASK_ID_PATTERN`, `TAIPEI_TIMESTAMP_PATTERN`, `COMMIT_SHA_PATTERN`, `DECISION_GATE_PATTERN`, `MAPPING_TO_PLAN_ENTRY_PATTERN` (`:179-181`, uses `[^"\n]+`), the `^- Field:\s*(.+)$` MULTILINE metadata extractors, `## Pass Fail Result\s+\n?\s*(pass|fail)\b`, `_STRICT_FLOOR_*` patterns (`:1812-1826`), `\bR(\d+)\b`, `Severity:\s*(.+)` — all single-quantifier or fixed-width.
- `build_decision_registry.py:15-22,146,193`: anchored `^...$` MULTILINE field matchers with single `.*`/`.+?` — linear.
- `validate_context_stack.py:65-72`: `see|見|詳見|Reference` followed by `[^\s`]+` (single bounded class); `FRONTMATTER_RE` `(.*?)` followed by fixed `\n---` anchor — linear.
- `ssdf_mapping_validator.py:67-70,83-85,189`: heading/table-row/separator matchers, single quantifiers; `_marker_in_text` pattern is `re.escape`-built and anchored.
- `standards_backaudit_dashboard.py:147-148,510-514`: the `[^\S\r\n]*` (horizontal-WS-only) field matchers are deliberately newline-safe and use a single inner `[^\r\n]*?` with a fixed follower — linear; the inline comment at `:145` shows this was an intentional anti-spoof design.
- `run_precommit_check.py:132,194,387,671,865`: `ISO_TS_RE` and `METADATA_KEY_RE` are anchored fixed-width / single-quantifier; `final_approver:` lookbehind-style search is bounded.
- `red_team/case_builders.py` DOTALL `re.sub` calls: same safe lazy-body-with-fixed-anchor shape as REDOS-03.
- `scaffold_downstream.py:51` (`{{(key|key|…)}}`), `sbom_gate.py:73`, `release_gate.py:54`, `workflow_constants.py:16,591` (`^[a-z0-9]+(?:-[a-z0-9]+)*$` — note: anchored both ends; the `(?:-…)*` is a classic ReDoS *shape* but here each iteration is forced to start with a literal `-`, so partitions are unique → linear; **cleared**).

---

## Recommendations (priority order)

1. **Fix REDOS-01 (Critical)** — restructure `RESEARCH_SOURCES_ENTRY_PATTERN`; remove `.+\..+` ambiguity (field-split parse, or anchored non-overlapping classes). Highest blowup, smallest trigger input (~2 KB → 15 s).
2. **Fix REDOS-02 (High)** — collapse the dual `[^)）\n]*` fills in the CITATION paren branch and/or add a `')' in item` precheck; apply to **both** identical copies (markers.py + guard_status_validator.py).
3. **Defence in depth** — add a per-line length guard before running guard regexes against artifact text (reject/skip lines beyond a few hundred chars), and/or wrap the validation entrypoint with a wall-clock budget. These bound *all* current and future regexes regardless of individual fixes.
4. The 512 KB file cap is **not** an effective ReDoS mitigation here (payloads hang at 2–40 KB); do not rely on it.

(Throwaway timing harness lived under the session scratchpad; no repo files other than this report were created or modified.)
