#!/usr/bin/env python3
"""standards_backaudit_dashboard.py — read-only conformance back-audit over standards drift.

council-forge's governance bar has risen over time (dual-review gate, SSDF recognition,
fail-closed discipline, dispatch / lifecycle / write-scope guards — see
``docs/standards-uplift-timeline.json``). Tasks completed under an OLDER bar were never
judged against today's standards. For each task this dashboard reports, across FOUR
deliberately-separated axes:

1. completion   — WHEN the task completed, derived from multiple sources with a fixed
                  priority (verify-date > decision-date > git first-commit instant) and a
                  fail-closed conflict rule: if the sources straddle a standard's
                  introduction instant, the task is ``completion-conflict`` and is NOT
                  compared; with no reliable source it is ``completion-unknown``. The bare
                  ``status.last_updated`` is deliberately NOT used (it can reflect a later
                  repair / migration / waiver edit, not the original completion).
2. formal-delta — the MACHINE axis (fail-closed): re-run TODAY's ``guard_status_validator``
                  on the task's existing artifacts and report ``[WARN]`` / ``[FAIL]``. The
                  re-run argv is EXACTLY ``[python, guard_status_validator.py, --task-id, T]``
                  — a non-mutating allowlist; any mutating flag (--auto-classify / --reconcile
                  / --write-transition / --override*) is rejected, so the back-audit can never
                  rewrite an old task's artifacts.
3. risk         — a fail-SAFE lattice: a security/crypto/auth signal (keyword in task/plan,
                  or a code ``Files Changed`` path in the security-sensitive map) PROMOTES the
                  task to ``risk-high`` (a candidate for qualitative re-review). The ABSENCE
                  of a positive signal on a task that still carries a theoretical delta does
                  NOT silently rank it low — it becomes ``risk-triage-needed``. ``low-risk`` is
                  reserved for an explicit benign classification and is NEVER auto-assigned.
4. qualitative  — the headline HONEST status. A task whose completion predates a standard
                  carries that standard as a *theoretical qualitative delta* and is
                  ``qualitative-review-pending`` until re-judged by an actual codex+gemini dual
                  review. It only becomes ``reviewed`` when a STRUCTURED decision record exists
                  (references the task, names both reviewers, carries each reviewer's evidence
                  ref, a bar id) — and even then the machine attests only that the *structure*
                  exists, NOT that the review's qualitative judgement is correct (see below).

HONESTY — ``machine-green != quality-met`` (the whole point; commander, 2026-06-08):

- A clean ``formal-delta`` (today's guards pass on an old task's artifacts) is NOT a
  statement that the task meets today's QUALITATIVE bar. Whether an old mechanism would pass
  today's dual-review / SSDF / fail-closed bar is NOT machine-decidable. The two axes are
  reported separately and the caveat is ALWAYS emitted (markdown header + JSON ``caveat``).
- No status in the vocabulary is a naked ``passed`` / ``conformant``. A ``reviewed`` status is
  a *structure* attestation, never a quality attestation — this is the recursive corollary of
  the core precept: the machine ultimately cannot verify quality, so ``reviewed`` still carries
  a human-acknowledgement boundary and a missing structured record stays
  ``qualitative-review-pending``.

Read-only: this tool WRITES nothing and MUTATES nothing. It only reads artifacts, reads the
timeline SSOT, and re-runs read-only sub-commands (today's guard with a non-mutating argv;
``git log``). It never touches an old task's task/plan/code/status/decision/verify artifact.

Source-only upstream-governance tool (a downstream terminal repo does not back-audit further
repos), so this file is NOT mirrored into ``template/`` and is NOT part of EXACT_SYNC_FILES —
same discipline as ssdf_conformance_dashboard.py / drift_dashboard.py / propagate_downstream.py.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from repo_health_dashboard import (
    TAIPEI,
    get_task_id,
    load_status,
    parse_datetime,
)

# --- exit codes ---------------------------------------------------------------------
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_FORMAL_DELTA = 2

# --- qualitative status vocabulary (NO naked "passed" / "conformant") ----------------
CURRENT_BAR = "current-bar"                          # completed after every recorded standard
QUALITATIVE_REVIEW_PENDING = "qualitative-review-pending"  # predates a standard; needs dual review
REVIEWED = "reviewed"                                # structured re-review record exists (structure only)
COMPLETION_CONFLICT = "completion-conflict"          # sources straddle a standard -> fail-closed
COMPLETION_UNKNOWN = "completion-unknown"            # no reliable completion source -> fail-closed
QUALITATIVE_STATUSES = (
    CURRENT_BAR, QUALITATIVE_REVIEW_PENDING, REVIEWED, COMPLETION_CONFLICT, COMPLETION_UNKNOWN,
)
# Statuses that represent an open qualitative obligation (go on the backlog).
_BACKLOG_STATUSES = frozenset({QUALITATIVE_REVIEW_PENDING, COMPLETION_CONFLICT, COMPLETION_UNKNOWN})

# --- formal-delta vocabulary (machine axis, fail-closed) -----------------------------
FORMAL_CLEAN = "formal-clean"      # rc 0, no WARN
FORMAL_WARN = "formal-warn"        # rc 0, >=1 WARN
FORMAL_FAIL = "formal-fail"        # rc 1 or any FAIL line
FORMAL_ERROR = "formal-error"      # unexpected rc (e.g. usage error) -> visible, fail-closed
FORMAL_DELTA_STATUSES = frozenset({FORMAL_WARN, FORMAL_FAIL, FORMAL_ERROR})

# --- risk lattice (fail-safe; a security hit PROMOTES, it never demotes) -------------
RISK_HIGH = "risk-high"                  # positive security/crypto/auth signal -> promote
RISK_TRIAGE_NEEDED = "risk-triage-needed"  # qual delta but no positive signal -> human triage
RISK_LOW = "low-risk"                    # reserved: ONLY an explicit benign classification
RISK_NOT_APPLICABLE = "risk-not-applicable"  # no qualitative delta to risk-rank

# Completion-time source priority (D2/D7). status.last_updated is intentionally absent.
COMPLETION_SOURCE_PRIORITY = ("verify", "decision", "git")

# guard re-run: the EXACT non-mutating argv contract (D4/D10).
GUARD_SCRIPT = "guard_status_validator.py"
# Any of these in the re-run argv means the back-audit could mutate an old artifact -> reject.
MUTATING_GUARD_FLAGS = frozenset({
    "--auto-classify", "--reconcile", "--write-transition",
    "--override", "--override-approver", "--from-state", "--to-state",
})

# Security-sensitive code paths (fnmatch, case-insensitive). A code "Files Changed" hit here
# PROMOTES the task to risk-high. Over-promotion is the safe direction (D12/D14).
SECURITY_PATH_PATTERNS = (
    "*gate*.py", "*guard_*", "*sign*", "*crypto*", "*secret*", "*release*",
    ".well-known/*", "*sast*", "*sca*", "*sbom*", "*security*", "*auth*", "*sigstore*",
)
# Security keywords (substring, lowercased) scanned over task + plan text. Full words chosen
# so the signal is meaningful while staying fail-safe (real security work uses these terms).
SECURITY_KEYWORDS = (
    "security", "crypto", "cryptograph", "encryption", "decrypt",
    "authentication", "authorization", "authz", "authn", "oauth",
    "signing", "signature", "sign-off", "gpg", "sigstore",
    "secret", "credential", "password", "token",
    "vulnerabilit", "cve", "sbom", "sast", "secret-scan", "supply-chain",
    "release-integrity", "release-signing", "fail-closed", "disclosure",
    "certificate", "ssrf", "injection", "sandbox",
)

CAVEAT = (
    "This is a STANDARDS-DRIFT back-audit. `formal-delta` (machine, fail-closed) is re-running "
    "today's guards on an older task's artifacts. A clean machine result is NOT 'quality met': "
    "the qualitative delta -- whether a mechanism would pass today's dual-review / SSDF bar -- "
    "is NOT machine-decidable and stays `qualitative-review-pending` until re-judged by dual "
    "review. `reviewed` attests only that a structured review record EXISTS, never that the "
    "review's judgement is correct. No 'passed' claim without a bar/when/review citation."
)

# Horizontal-whitespace-only field matcher (NOT `\s*`, which would consume newlines and let a
# blank field capture the NEXT line — an anti-forgery / completion-spoof bypass; impl-review).
_LAST_UPDATED_RE = re.compile(  # redos-ok: anchored ^...$; [^\S\r\n] fills are horizontal-WS-only (newline-bounded) around literal field delimiters — linear; intentional anti-spoof design
    r"^[-*]?[^\S\r\n]*Last Updated[^\S\r\n]*:[^\S\r\n]*([^\r\n]*?)[^\S\r\n]*$",
    re.IGNORECASE | re.MULTILINE,
)
_TASK_ID_RE = re.compile(r"\bTASK-\d+\b")


def _metadata_block(text: str) -> str:
    """The lines under the canonical ``## Metadata`` header (until the next ``## `` header).

    Completion time is read ONLY from this block so a stray ``Last Updated:`` in prose, a
    changelog snippet, or an embedded historical quote cannot spoof the instant (impl-review).
    """
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip().lower() == "## metadata")
    except StopIteration:
        return ""
    out: List[str] = []
    for ln in lines[start + 1:]:
        if ln.strip().startswith("## "):
            break
        out.append(ln)
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Timeline SSOT (fail-closed load)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class UpliftEvent:
    instant: datetime
    event: str
    standard: str
    ref: str
    commit: str
    category: str

    def as_dict(self) -> dict:
        return {
            "introduced_at": self.instant.isoformat(),
            "event": self.event,
            "standard": self.standard,
            "ref": self.ref,
            "commit": self.commit,
            "category": self.category,
        }


_EVENT_REQUIRED_FIELDS = ("introduced_at", "event", "standard", "ref", "commit", "category")


def to_instant(dt_str: str) -> Optional[datetime]:
    """parse_datetime (reused) + localise a naive value to Taipei so all compares are instants."""
    dt = parse_datetime(dt_str)
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TAIPEI)
    return dt


def load_timeline(path: Path) -> Tuple[List[UpliftEvent], frozenset]:
    """Load + structurally validate the standards-uplift SSOT (fail-closed on bad vocab).

    Returns (events sorted ascending by instant, controlled-category set). Any structural
    defect — bad schema_version, empty/missing events, a missing required field, an
    unparseable introduced_at, or a category outside the controlled vocabulary — raises
    ValueError rather than silently dropping the event (an under-counted delta is a lie).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"standards-uplift-timeline: unsupported schema_version {data.get('schema_version')!r}")
    categories = data.get("maintenance", {}).get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("standards-uplift-timeline: maintenance.categories must be a non-empty list")
    category_set = frozenset(categories)
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("standards-uplift-timeline: 'events' must be a non-empty list")
    out: List[UpliftEvent] = []
    for raw in events:
        if not isinstance(raw, dict):
            raise ValueError(f"standards-uplift-timeline: event is not an object: {raw!r}")
        missing = [f for f in _EVENT_REQUIRED_FIELDS if not str(raw.get(f, "")).strip()]
        if missing:
            raise ValueError(f"standards-uplift-timeline: event {raw.get('ref')!r} missing required field(s): {missing}")
        instant = to_instant(raw["introduced_at"])
        if instant is None:
            raise ValueError(f"standards-uplift-timeline: event {raw['ref']!r} has unparseable introduced_at {raw['introduced_at']!r}")
        if raw["category"] not in category_set:
            raise ValueError(
                f"standards-uplift-timeline: event {raw['ref']!r} category {raw['category']!r} "
                f"not in controlled vocabulary {sorted(category_set)}"
            )
        out.append(UpliftEvent(instant, raw["event"], raw["standard"], raw["ref"], raw["commit"], raw["category"]))
    out.sort(key=lambda e: e.instant)
    return out, category_set


# --------------------------------------------------------------------------- #
# Completion time (D2 multi-source + priority; D7 conflict / unknown fail-closed)
# --------------------------------------------------------------------------- #
@dataclass
class Completion:
    kind: str                                   # "resolved" | "conflict" | "unknown"
    instant: Optional[datetime]                 # the primary completion instant when resolved
    source: Optional[str]                        # which COMPLETION_SOURCE_PRIORITY produced it
    candidates: List[Tuple[str, str]] = field(default_factory=list)  # [(source, iso)] for evidence


def artifact_last_updated_instant(path: Path) -> Optional[datetime]:
    """The ``Last Updated:`` instant from the artifact's ``## Metadata`` block, or None.

    Fail-closed (D2/D7): only the canonical metadata block is trusted, and a missing OR
    ambiguous (multiple DISTINCT values) ``Last Updated`` yields None rather than a guessed
    completion instant — a wrong completion time would silently weaken the straddle/conflict
    check.
    """
    if not path.is_file():
        return None
    values = {v.strip() for v in _LAST_UPDATED_RE.findall(_metadata_block(path.read_text(encoding="utf-8")))}
    values.discard("")
    if len(values) != 1:
        return None
    return to_instant(next(iter(values)))


def _git_first_commit_instant(repo_root: Path, relpath: str) -> Optional[datetime]:  # pragma: no cover - thin subprocess seam
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--reverse", "--format=%cI", "--", relpath],
            capture_output=True, text=True, check=False, shell=False,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            return to_instant(line)
    return None


def resolve_completion(
    task_id: str,
    root: Path,
    events: Sequence[UpliftEvent],
    *,
    git_instant=None,
) -> Completion:
    """Multi-source completion with priority + fail-closed conflict (D2/D7).

    candidates, by priority: verify-date, decision-date, git first-commit instant. The bare
    status.last_updated is intentionally excluded. If >=2 candidates straddle ANY standard's
    introduction instant (one is pre-standard, another is not), the sources disagree on
    "completed before/after that standard" -> completion-conflict (do not compare). With no
    candidate -> completion-unknown.
    """
    git_instant = git_instant if git_instant is not None else _git_first_commit_instant
    raw: Dict[str, Optional[datetime]] = {
        "verify": artifact_last_updated_instant(root / "artifacts" / "verify" / f"{task_id}.verify.md"),
        "decision": artifact_last_updated_instant(root / "artifacts" / "decisions" / f"{task_id}.decision.md"),
        "git": git_instant(root, f"artifacts/tasks/{task_id}.task.md"),
    }
    candidates = [(src, dt) for src in COMPLETION_SOURCE_PRIORITY if (dt := raw[src]) is not None]
    if not candidates:
        return Completion(COMPLETION_UNKNOWN, None, None, [])
    evidence = [(src, dt.isoformat()) for src, dt in candidates]
    instants = [dt for _, dt in candidates]
    lo, hi = min(instants), max(instants)
    # straddle: some standard instant s satisfies lo < s <= hi -> candidates disagree on s.
    if lo != hi and any(lo < e.instant <= hi for e in events):
        return Completion(COMPLETION_CONFLICT, None, None, evidence)
    primary_src, primary_dt = candidates[0]  # highest-priority available source
    return Completion("resolved", primary_dt, primary_src, evidence)


def theoretical_delta(completion: Completion, events: Sequence[UpliftEvent]) -> List[UpliftEvent]:
    """Standards introduced strictly AFTER a resolved completion instant (D1 instant compare)."""
    if completion.kind != "resolved" or completion.instant is None:
        return []
    return [e for e in events if completion.instant < e.instant]


# --------------------------------------------------------------------------- #
# Formal-delta: re-run today's guard, read-only argv allowlist (D4/D10)
# --------------------------------------------------------------------------- #
@dataclass
class FormalResult:
    status: str
    returncode: int
    warns: List[str] = field(default_factory=list)
    fails: List[str] = field(default_factory=list)


def build_guard_argv(guard_path: Path, task_id: str) -> List[str]:
    """The EXACT non-mutating re-run argv (D10): [python, guard_status_validator.py, --task-id, T]."""
    return [sys.executable, str(guard_path), "--task-id", task_id]


def assert_readonly_guard_argv(argv: Sequence[str]) -> None:
    """Fail-closed ALLOWLIST (not a denylist): the re-run argv MUST be exactly the read-only
    shape ``[python, guard_status_validator.py, --task-id, <task_id>]`` (D4/D10).

    An exact-shape check (length 4, ``--task-id`` at position 2, the guard script at
    position 1) structurally precludes EVERY mutating flag — exact, ``=value``, or prefix
    form (e.g. ``--override=reason``) — that a token denylist would miss. A second
    defence-in-depth scan rejects a mutating flag smuggled into any position.
    """
    argv = list(argv)
    if (
        len(argv) != 4
        or argv[2] != "--task-id"
        or not str(argv[1]).replace("\\", "/").endswith(GUARD_SCRIPT)
    ):
        raise ValueError(
            f"guard re-run argv must be exactly [python, {GUARD_SCRIPT}, --task-id, <task_id>] "
            f"(read-only allowlist); got: {argv}"
        )
    for a in argv:
        s = str(a)
        if s.startswith("--override") or any(s == f or s.startswith(f + "=") for f in MUTATING_GUARD_FLAGS):
            raise ValueError(f"refusing mutating guard flag in re-run argv: {s!r} (back-audit is read-only)")


def parse_guard_output(returncode: int, stdout: str, stderr: str) -> FormalResult:
    """Classify a guard re-run by its stable [WARN]/[FAIL] prefixes + exit code (fail-closed)."""
    warns = [ln for ln in stdout.splitlines() if ln.startswith("[WARN]")]
    fails = [ln for ln in stdout.splitlines() if ln.startswith("[FAIL]")]
    fails += [ln for ln in stderr.splitlines() if ln.startswith("[FAIL]")]
    if returncode not in (0, 1):
        return FormalResult(FORMAL_ERROR, returncode, warns, fails)
    if returncode == 1 or fails:
        return FormalResult(FORMAL_FAIL, returncode, warns, fails)
    if warns:
        return FormalResult(FORMAL_WARN, returncode, warns, fails)
    return FormalResult(FORMAL_CLEAN, returncode, warns, fails)


def _invoke_guard(argv: Sequence[str], cwd: Path) -> Tuple[int, str, str]:  # pragma: no cover - thin subprocess seam
    proc = subprocess.run(list(argv), cwd=str(cwd), capture_output=True, text=True, check=False, shell=False)
    return proc.returncode, proc.stdout, proc.stderr


def rerun_guard_status(
    task_id: str,
    repo_root: Path,
    scripts_dir: Path,
    *,
    invoke=None,
) -> FormalResult:
    """Re-run today's guard_status_validator on an old task, read-only (D4/D10).

    cwd is the repo root so the guard's default ``--artifacts-root ./artifacts`` resolves; the
    argv carries ONLY --task-id (asserted free of any mutating flag).
    """
    invoke = invoke if invoke is not None else _invoke_guard
    argv = build_guard_argv(scripts_dir / GUARD_SCRIPT, task_id)
    assert_readonly_guard_argv(argv)
    returncode, stdout, stderr = invoke(argv, repo_root)
    return parse_guard_output(returncode, stdout, stderr)


# --------------------------------------------------------------------------- #
# Risk lattice (D8/D12/D14 — fail-safe; security hits PROMOTE)
# --------------------------------------------------------------------------- #
@dataclass
class RiskResult:
    tier: str
    score: int
    keyword_hits: List[str] = field(default_factory=list)
    path_hits: List[str] = field(default_factory=list)
    note: str = ""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def extract_files_changed(code_text: str) -> List[str]:
    """The leading path token of each bullet under a ``## Files Changed`` section."""
    if not code_text:
        return []
    lines = code_text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip().lower().startswith("## files changed"))
    except StopIteration:
        return []
    paths: List[str] = []
    for ln in lines[start + 1:]:
        stripped = ln.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith(("- ", "* ")):
            continue
        token = stripped[2:].strip()
        # cut at the first separator that introduces commentary (ascii or fullwidth)
        for sep in ("（", "(", " — ", " - ", "  ", " ", "\t", "，", ","):
            idx = token.find(sep)
            if idx > 0:
                token = token[:idx]
                break
        token = token.strip().strip("`")
        if token:
            paths.append(token)
    return paths


def _path_is_security_sensitive(path: str) -> bool:
    low = path.lower()
    return any(fnmatch.fnmatch(low, pat) for pat in SECURITY_PATH_PATTERNS)


def classify_risk(task_id: str, root: Path, has_delta: bool) -> RiskResult:
    """Risk tier for one task (D14 lattice). Security signal -> promote; no signal + delta ->
    triage (never silent low); low-risk is never auto-assigned.
    """
    if not has_delta:
        return RiskResult(RISK_NOT_APPLICABLE, 0, note="no qualitative delta to risk-rank")
    task_text = _read_text(root / "artifacts" / "tasks" / f"{task_id}.task.md")
    plan_text = _read_text(root / "artifacts" / "plans" / f"{task_id}.plan.md")
    blob = (task_text + "\n" + plan_text).lower()
    keyword_hits = sorted({k for k in SECURITY_KEYWORDS if k in blob})

    code_path = root / "artifacts" / "code" / f"{task_id}.code.md"
    code_text = _read_text(code_path)
    changed = extract_files_changed(code_text)
    path_hits = sorted({p for p in changed if _path_is_security_sensitive(p)})

    if keyword_hits or path_hits:
        score = len(keyword_hits) + 2 * len(path_hits)
        return RiskResult(RISK_HIGH, score, keyword_hits, path_hits, note="security/crypto/auth signal -> promote")
    # No positive signal but a real theoretical delta -> default to triage (D12), never silent low.
    if not code_path.is_file():
        note = "no positive security signal; no code artifact -> human triage"
    elif not changed:
        note = "no positive security signal; code 'Files Changed' unparseable -> human triage"
    else:
        note = "no positive security signal; code paths map-miss -> human triage"
    return RiskResult(RISK_TRIAGE_NEEDED, 0, keyword_hits, path_hits, note=note)


# --------------------------------------------------------------------------- #
# reviewed: structured re-review record (D5/D9 — structure attested, NOT quality)
# --------------------------------------------------------------------------- #
@dataclass
class ReviewRecord:
    reviewed_task: str
    bar: str
    reviewers: List[str]
    codex_evidence: str
    gemini_evidence: str
    decision_file: str


# Single-line field matchers: horizontal whitespace only (NOT `\s*`), so a blank field cannot
# consume the newline and capture the NEXT line as its value (D9 anti-forgery; impl-review).
_REVIEW_FIELD_RES = {
    "reviewed_task": re.compile(r"^[-*]?[^\S\r\n]*Reviewed-Task[^\S\r\n]*:[^\S\r\n]*(TASK-\d+)[^\S\r\n]*$", re.IGNORECASE | re.MULTILINE),
    "bar": re.compile(r"^[-*]?[^\S\r\n]*Bar[^\S\r\n]*:[^\S\r\n]*([^\r\n]*?)[^\S\r\n]*$", re.IGNORECASE | re.MULTILINE),  # redos-ok: anchored ^...$, horizontal-WS-only fills — linear (anti-spoof field matcher)
    "reviewers": re.compile(r"^[-*]?[^\S\r\n]*Reviewers[^\S\r\n]*:[^\S\r\n]*([^\r\n]*?)[^\S\r\n]*$", re.IGNORECASE | re.MULTILINE),  # redos-ok: anchored ^...$, horizontal-WS-only fills — linear
    "codex_evidence": re.compile(r"^[-*]?[^\S\r\n]*Codex-Evidence[^\S\r\n]*:[^\S\r\n]*([^\r\n]*?)[^\S\r\n]*$", re.IGNORECASE | re.MULTILINE),  # redos-ok: anchored ^...$, horizontal-WS-only fills — linear
    "gemini_evidence": re.compile(r"^[-*]?[^\S\r\n]*Gemini-Evidence[^\S\r\n]*:[^\S\r\n]*([^\r\n]*?)[^\S\r\n]*$", re.IGNORECASE | re.MULTILINE),  # redos-ok: anchored ^...$, horizontal-WS-only fills — linear
}


def parse_review_records(text: str, decision_file: str) -> List[ReviewRecord]:
    """Parse all STRUCTURED back-audit re-review records in a decision artifact.

    A valid record requires Reviewed-Task, a non-empty Bar, a Reviewers list naming BOTH codex
    and gemini, and a non-empty Codex-Evidence and Gemini-Evidence. Records are delimited by the
    Reviewed-Task line; fields are matched within each delimited block so two records in one file
    do not bleed into each other.
    """
    anchors = list(_REVIEW_FIELD_RES["reviewed_task"].finditer(text))
    records: List[ReviewRecord] = []
    for i, anchor in enumerate(anchors):
        block = text[anchor.start():anchors[i + 1].start() if i + 1 < len(anchors) else len(text)]
        task = anchor.group(1).upper()
        fields: Dict[str, str] = {}
        for key in ("bar", "reviewers", "codex_evidence", "gemini_evidence"):
            m = _REVIEW_FIELD_RES[key].search(block)
            value = m.group(1).strip() if m else ""
            if not value:  # missing OR whitespace-only -> not a valid structured record (D9)
                break
            fields[key] = value
        if len(fields) != 4:
            continue
        reviewers = [r.strip().lower() for r in re.split(r"[,/+;]| and ", fields["reviewers"]) if r.strip()]
        if "codex" not in reviewers or "gemini" not in reviewers:
            continue
        records.append(ReviewRecord(task, fields["bar"], reviewers,
                                    fields["codex_evidence"], fields["gemini_evidence"], decision_file))
    return records


def find_review_record(task_id: str, decisions_dir: Path) -> Optional[ReviewRecord]:
    """The first structured re-review record for task_id across all decision artifacts, or None."""
    if not decisions_dir.is_dir():
        return None
    for path in sorted(decisions_dir.glob("*.decision.md")):
        for rec in parse_review_records(_read_text(path), path.name):
            if rec.reviewed_task == task_id:
                return rec
    return None


# --------------------------------------------------------------------------- #
# Per-task audit
# --------------------------------------------------------------------------- #
@dataclass
class TaskAudit:
    task_id: str
    completion: Completion
    delta: List[UpliftEvent]
    formal: FormalResult
    risk: RiskResult
    review: Optional[ReviewRecord]
    qualitative_status: str


def qualitative_status_for(completion: Completion, delta: Sequence[UpliftEvent], review: Optional[ReviewRecord]) -> str:
    """Headline honest status (priority: unknown > conflict > reviewed > current-bar > pending)."""
    if completion.kind == COMPLETION_UNKNOWN:
        return COMPLETION_UNKNOWN
    if completion.kind == COMPLETION_CONFLICT:
        return COMPLETION_CONFLICT
    if review is not None:
        return REVIEWED
    if not delta:
        return CURRENT_BAR
    return QUALITATIVE_REVIEW_PENDING


def audit_task(
    task_id: str,
    root: Path,
    scripts_dir: Path,
    decisions_dir: Path,
    events: Sequence[UpliftEvent],
    *,
    invoke_guard=None,
    git_instant=None,
) -> TaskAudit:
    completion = resolve_completion(task_id, root, events, git_instant=git_instant)
    delta = theoretical_delta(completion, events)
    formal = rerun_guard_status(task_id, root, scripts_dir, invoke=invoke_guard)
    review = find_review_record(task_id, decisions_dir)
    has_delta = bool(delta) or completion.kind in (COMPLETION_CONFLICT, COMPLETION_UNKNOWN)
    risk = classify_risk(task_id, root, has_delta)
    status = qualitative_status_for(completion, delta, review)
    return TaskAudit(task_id, completion, delta, formal, risk, review, status)


# --------------------------------------------------------------------------- #
# Whole-repo audit
# --------------------------------------------------------------------------- #
@dataclass
class Audit:
    generated_at: str
    timeline_event_count: int
    tasks: List[TaskAudit]

    def by_status(self, status: str) -> List[TaskAudit]:
        return [t for t in self.tasks if t.qualitative_status == status]

    @property
    def backlog(self) -> List[TaskAudit]:
        """Open qualitative obligations, risk-ranked (risk-high first, then score desc, then id)."""
        rank = {RISK_HIGH: 0, RISK_TRIAGE_NEEDED: 1, RISK_LOW: 2, RISK_NOT_APPLICABLE: 3}
        items = [t for t in self.tasks if t.qualitative_status in _BACKLOG_STATUSES]
        return sorted(items, key=lambda t: (rank.get(t.risk.tier, 9), -t.risk.score, t.task_id))


def discover_task_ids(status_dir: Path) -> List[str]:
    return [get_task_id(p) for p in sorted(status_dir.glob("TASK-*.status.json"))]


def build_audit(
    root: Path,
    events: Sequence[UpliftEvent],
    *,
    task_filter: Optional[Sequence[str]] = None,
    invoke_guard=None,
    git_instant=None,
    now: Optional[datetime] = None,
) -> Audit:
    status_dir = root / "artifacts" / "status"
    scripts_dir = root / "artifacts" / "scripts"
    decisions_dir = root / "artifacts" / "decisions"
    task_ids = discover_task_ids(status_dir)
    if task_filter:
        wanted = {t.upper() for t in task_filter}
        task_ids = [t for t in task_ids if t in wanted]
    audits = [
        audit_task(tid, root, scripts_dir, decisions_dir, events,
                   invoke_guard=invoke_guard, git_instant=git_instant)
        for tid in task_ids
    ]
    generated = (now or datetime.now(TAIPEI)).isoformat(timespec="seconds")
    return Audit(generated, len(events), audits)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _completion_cell(c: Completion) -> str:
    if c.kind == "resolved":
        return f"{c.instant.isoformat()} ({c.source})"
    return c.kind


def build_json(audit: Audit) -> dict:
    return {
        "caveat": CAVEAT,
        "generated_at": audit.generated_at,
        "timeline_event_count": audit.timeline_event_count,
        "summary": {
            "total": len(audit.tasks),
            "qualitative_status": {s: len(audit.by_status(s)) for s in QUALITATIVE_STATUSES},
            "formal_status": {
                s: sum(1 for t in audit.tasks if t.formal.status == s)
                for s in (FORMAL_CLEAN, FORMAL_WARN, FORMAL_FAIL, FORMAL_ERROR)
            },
            "risk_tier": {
                s: sum(1 for t in audit.tasks if t.risk.tier == s)
                for s in (RISK_HIGH, RISK_TRIAGE_NEEDED, RISK_LOW, RISK_NOT_APPLICABLE)
            },
            "backlog": len(audit.backlog),
        },
        "tasks": [
            {
                "task_id": t.task_id,
                "qualitative_status": t.qualitative_status,
                "completion": {
                    "kind": t.completion.kind,
                    "instant": t.completion.instant.isoformat() if t.completion.instant else None,
                    "source": t.completion.source,
                    "candidates": [{"source": s, "instant": i} for s, i in t.completion.candidates],
                },
                "theoretical_delta": [e.as_dict() for e in t.delta],
                "formal_delta": {
                    "status": t.formal.status,
                    "returncode": t.formal.returncode,
                    "warns": t.formal.warns,
                    "fails": t.formal.fails,
                },
                "risk": {
                    "tier": t.risk.tier,
                    "score": t.risk.score,
                    "keyword_hits": t.risk.keyword_hits,
                    "path_hits": t.risk.path_hits,
                    "note": t.risk.note,
                },
                "review": (
                    None if t.review is None else {
                        "reviewed_task": t.review.reviewed_task,
                        "bar": t.review.bar,
                        "reviewers": t.review.reviewers,
                        "codex_evidence": t.review.codex_evidence,
                        "gemini_evidence": t.review.gemini_evidence,
                        "decision_file": t.review.decision_file,
                        "machine_attestation": "structure-only; NOT a quality attestation (machine cannot verify review quality)",
                    }
                ),
            }
            for t in audit.tasks
        ],
        "backlog": [
            {"task_id": t.task_id, "qualitative_status": t.qualitative_status,
             "risk_tier": t.risk.tier, "risk_score": t.risk.score,
             "delta_standards": [e.ref for e in t.delta]}
            for t in audit.backlog
        ],
    }


def render_markdown(audit: Audit) -> str:
    j = build_json(audit)
    s = j["summary"]
    lines: List[str] = ["# council-forge Standards-Drift Back-Audit Dashboard", ""]
    lines.append(f"> {CAVEAT}")
    lines.append("")
    lines.append(f"Generated: {audit.generated_at} | timeline events: {audit.timeline_event_count} | tasks: {s['total']}")
    lines.append("")
    lines.append("## Qualitative status (honest; NOT a `passed` claim)")
    lines.append("")
    lines.append("| status | count |")
    lines.append("|---|---:|")
    for st in QUALITATIVE_STATUSES:
        lines.append(f"| {st} | {s['qualitative_status'][st]} |")
    lines.append("")
    lines.append("## Formal-delta (machine axis, fail-closed — a clean result is NOT 'quality met')")
    lines.append("")
    lines.append("| formal status | count |")
    lines.append("|---|---:|")
    for st in (FORMAL_CLEAN, FORMAL_WARN, FORMAL_FAIL, FORMAL_ERROR):
        lines.append(f"| {st} | {s['formal_status'][st]} |")
    lines.append("")
    lines.append("## Risk-ranked qualitative-delta backlog (needs codex+gemini dual review)")
    lines.append("")
    if audit.backlog:
        lines.append("| Task | qualitative status | risk | score | standards predating completion |")
        lines.append("|---|---|---|---:|---|")
        for t in audit.backlog:
            standards = ", ".join(e.ref for e in t.delta) or "—"
            lines.append(f"| {t.task_id} | {t.qualitative_status} | {t.risk.tier} | {t.risk.score} | {standards} |")
    else:
        lines.append("_(empty — every task either completed at the current bar or has been reviewed)_")
    lines.append("")
    lines.append("## All tasks")
    lines.append("")
    lines.append("| Task | qualitative | completion | formal | risk | Δ |")
    lines.append("|---|---|---|---|---|---:|")
    for t in audit.tasks:
        lines.append(
            f"| {t.task_id} | {t.qualitative_status} | {_completion_cell(t.completion)} | "
            f"{t.formal.status} | {t.risk.tier} | {len(t.delta)} |"
        )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def default_timeline_path(root: Path) -> Path:
    return root / "docs" / "standards-uplift-timeline.json"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only standards-drift back-audit dashboard (machine-green != quality-met)."
    )
    parser.add_argument("--root", default=".", help="Repository root. Default: .")
    parser.add_argument("--timeline", default="", help="Override standards-uplift-timeline.json path.")
    parser.add_argument("--task", action="append", default=[], metavar="TASK-XXXX",
                        help="Restrict to this task id (repeatable). Default: all tasks.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument("--fail-on-formal-delta", action="store_true",
                        help="Exit 2 if any task has a formal-warn / formal-fail / formal-error (visibility gate).")
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    timeline_path = Path(args.timeline) if args.timeline else default_timeline_path(root)
    if not timeline_path.is_file():
        print(f"[FAIL] standards-uplift timeline not found: {timeline_path}", file=sys.stderr)
        return EXIT_ERROR
    try:
        events, _categories = load_timeline(timeline_path)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] standards-uplift timeline invalid: {exc}", file=sys.stderr)
        return EXIT_ERROR

    status_dir = root / "artifacts" / "status"
    if not status_dir.is_dir():
        print(f"[FAIL] artifacts/status not found under root: {root}", file=sys.stderr)
        return EXIT_ERROR

    audit = build_audit(root, events, task_filter=args.task or None)

    if args.json:
        print(json.dumps(build_json(audit), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(audit))

    if args.fail_on_formal_delta and any(t.formal.status in FORMAL_DELTA_STATUSES for t in audit.tasks):
        return EXIT_FORMAL_DELTA
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
