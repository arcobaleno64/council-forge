#!/usr/bin/env python3
"""Prompt-injection detector for the orchestrator's untrusted-input surface.

This operationalises TASK-1021 Rule-3 / Rule-4: external or research-sourced
content (research notes, tavily raw captures, work-product markdown that quotes
external material) must never be treated as system-level / governance-authoritative
instructions. Those rules are policy; this script is the automated enforcement.

It scans artifact markdown for *high-confidence* injection shapes — instruction
overrides, role/system impersonation, system-prompt or credential exfiltration,
workflow-gate subversion (the novel attack class for an AI workflow orchestrator),
command coercion, smuggled invisible Unicode, and markdown exfil beacons — and
fails closed on any unjustified finding.

Design follows repo convention (cf. repo_security_scan.py):
  * pattern table of (rule_id, category, severity, regex, message)
  * Finding dataclass, truncated excerpt
  * --root scan, exit 0 (clean) / 1 (findings) / 2 (scan error, fail-closed)
  * a reviewed `<!-- pi-ok: reason -->` line marker exempts a known-safe line
    (the analogue of `# redos-ok:` in regex_safety_audit.py)
  * `calibrate` subcommand measures precision/recall against the labelled
    adversarial corpus and fails closed on any missed attack or false positive.

Pure stdlib — no install step, safe as a fail-closed CI gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

# In-repo justification marker (line-scoped). Mirrors `# redos-ok:`.
PI_OK_MARKER = "pi-ok:"

# Negation context that flips an otherwise-suspicious directive into benign
# policy prose ("do NOT skip the premortem", "請勿略過驗證"). Applied to the
# workflow-subversion rules, which describe gates that legitimate docs also name.
NEGATION_RE = re.compile(
    r"(?:do\s+not|don'?t|never|must\s+not|cannot|can'?t|should\s+not|"
    r"請勿|不得|不可|不要|禁止|嚴禁)\s*$",
    re.IGNORECASE,
)
NEGATION_LOOKBACK = 24


def _build_hidden_unicode_class() -> "re.Pattern[str]":
    """Character class for invisible / bidi / tag codepoints used to smuggle
    hidden instructions. Built from explicit codepoints so the *source* of this
    file contains no literal invisible characters. U+200D (ZWJ) is deliberately
    excluded — it appears in legitimate emoji sequences."""
    ranges = [
        (0x200B, 0x200C),   # ZWSP, ZWNJ (token-break smuggling)
        (0x200E, 0x200F),   # LRM, RLM
        (0x202A, 0x202E),   # bidi embeddings + LRO/RLO override
        (0x2060, 0x2064),   # word joiner + invisible math operators
        (0x2066, 0x2069),   # bidi isolates
        (0xFEFF, 0xFEFF),   # interior ZWNBSP / BOM
        (0xE0000, 0xE007F),  # Unicode tag block (invisible instruction smuggling)
    ]
    parts = []
    for lo, hi in ranges:
        lo_esc = f"\\U{lo:08X}"
        hi_esc = f"\\U{hi:08X}"
        parts.append(lo_esc if lo == hi else f"{lo_esc}-{hi_esc}")
    return re.compile("[" + "".join(parts) + "]")


HIDDEN_UNICODE_RE = _build_hidden_unicode_class()


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    severity: str
    pattern: "re.Pattern[str]"
    message: str
    negatable: bool = False


# Each entry is a high-confidence shape. Bounds use [^.\n]{0,N} so a match stays
# within a sentence/line and cannot blow up (linear; safe under regex_safety_audit).
INJECTION_RULES: List[Rule] = [
    # --- instruction override -------------------------------------------------
    Rule(
        "PI-OVERRIDE", "override", "high",
        re.compile(
            r"\b(ignore|disregard|forget)\b[^.\n]{0,40}\b(previous|prior|above|preceding|earlier)\b"
            r"[^.\n]{0,30}\b(instruction|instructions|prompt|prompts|context|message|messages|rule|rules)\b",
            re.IGNORECASE,
        ),
        "instruction-override directive aimed at the reading agent",
    ),
    Rule(
        "PI-OVERRIDE-ZH", "override", "high",
        re.compile(
            r"(忽略|無視|忽視|略過)[^。\n]{0,12}(先前|以上|上述|之前|前面|前述)[^。\n]{0,8}"
            r"(指令|指示|提示|規則|訊息|內容)"
        ),
        "instruction-override directive (Chinese)",
    ),
    # --- role / system impersonation -----------------------------------------
    Rule(
        "PI-ROLE", "role_override", "high",
        re.compile(r"\byou\s+are\s+now\s+(?:an?|the)\s+(?!ready\b)", re.IGNORECASE),
        "role-override ('you are now a/an/the ...')",
    ),
    Rule(
        "PI-ROLE-NEWINSTR", "role_override", "high",
        re.compile(r"\bnew\s+(?:system\s+)?(?:instructions?|prompt|directives?|rules?)\s*[:：]", re.IGNORECASE),
        "injected 'new instructions:' header",
    ),
    Rule(
        "PI-ROLE-ZH", "role_override", "high",
        re.compile(r"(?:你|您)現在是[^。\n]{0,12}(管理者|管理員|最高權限|root|系統|owner|擁有者|超級)"),
        "role-escalation directive (Chinese)",
    ),
    # --- system-prompt exfiltration ------------------------------------------
    Rule(
        "PI-EXFIL-PROMPT", "exfil_prompt", "high",
        re.compile(
            r"\b(print|reveal|repeat|output|show|dump|disclose|display|echo)\b[^.\n]{0,50}"
            r"\b(system\s+prompt|system\s+message|initial\s+instructions|these\s+instructions|"
            r"the\s+instructions\s+above|prompt\s+above|the\s+text\s+above)\b",
            re.IGNORECASE,
        ),
        "system-prompt exfiltration attempt",
    ),
    Rule(
        "PI-EXFIL-PROMPT-ZH", "exfil_prompt", "high",
        re.compile(r"(輸出|印出|顯示|洩漏|透露|複述|重複|揭露)[^。\n]{0,20}(系統提示|系統訊息|系統指令|初始指令|你的指令)"),
        "system-prompt exfiltration attempt (Chinese)",
    ),
    # --- credential exfiltration ---------------------------------------------
    Rule(
        "PI-EXFIL-SECRET", "exfil_secret", "high",
        re.compile(
            r"\b(print|cat|read|output|send|upload|exfiltrate|reveal|dump|include|email|post|leak)\b[^.\n]{0,60}"
            r"(\.env\b|secrets?\b|api[_\-\s]?keys?\b|credentials?\b|private\s+keys?\b|"
            r"access\s+tokens?\b|auth\s+tokens?\b)",
            re.IGNORECASE,
        ),
        "credential / secret exfiltration attempt",
    ),
    Rule(
        "PI-EXFIL-SECRET-ZH", "exfil_secret", "high",
        re.compile(r"(輸出|印出|傳送|上傳|洩漏|讀取|送出|顯示|揭露)[^。\n]{0,30}(環境變數|密鑰|金鑰|憑證|私鑰|密碼)"),
        "credential / secret exfiltration attempt (Chinese)",
    ),
    # --- workflow-gate subversion (orchestrator-specific) ---------------------
    Rule(
        "PI-WORKFLOW-COMPLETE", "workflow_subversion", "high",
        re.compile(
            r"\b(mark|set|flag)\b[^.\n]{0,40}\b(complete|completed|verified|done|approved|passed)\b"
            r"[^.\n]{0,60}\b(without|skip|skipping|bypass|bypassing|no\s+need)\b",
            re.IGNORECASE,
        ),
        "forces completion while bypassing verification",
        negatable=True,
    ),
    Rule(
        "PI-WORKFLOW-BYPASS", "workflow_subversion", "high",
        re.compile(
            r"\b(skip|bypass|disable|override|circumvent|turn\s+off)\b[^.\n]{0,30}"
            r"\b(the\s+)?(premortem|verification|verify|guard|guards|validator|gate|gates|"
            r"build\s+guarantee|state\s+machine|workflow\s+gate|review\s+process)\b",
            re.IGNORECASE,
        ),
        "subverts a workflow gate (premortem / verification / guard)",
        negatable=True,
    ),
    Rule(
        "PI-WORKFLOW-ZH", "workflow_subversion", "high",
        re.compile(r"(略過|跳過|繞過|停用|關閉)[^。\n]{0,16}(premortem|guard|驗證|驗收|測試|複查|審查|狀態機|前驗屍)"),
        "subverts a workflow gate (Chinese)",
        negatable=True,
    ),
    # --- command / tool coercion ---------------------------------------------
    Rule(
        "PI-CMD", "command_injection", "high",
        re.compile(
            r"\b(run|execute|exec|eval)\b[^.\n]{0,40}"
            r"(\bcurl\b|\bwget\b|rm\s+-rf|bash\s+-c|sh\s+-c|powershell|os\.system|subprocess\.|\|\s*(?:bash|sh)\b)",
            re.IGNORECASE,
        ),
        "command-execution coercion",
    ),
    # --- smuggled invisible Unicode (language-agnostic) ----------------------
    Rule(
        "PI-HIDDEN-UNICODE", "hidden_unicode", "high",
        HIDDEN_UNICODE_RE,
        "smuggled invisible/bidi/tag Unicode (instruction-hiding channel)",
    ),
    # --- markdown exfiltration beacon ----------------------------------------
    Rule(
        "PI-BEACON", "markdown_beacon", "high",
        re.compile(r"!\[[^\]]*\]\(\s*https?://[^)\s]*\?[^)\s]*=[^)\s]*\)", re.IGNORECASE),
        "markdown image beacon with query string (data-exfil channel)",
    ),
    # --- hidden instructions in HTML comments --------------------------------
    Rule(
        "PI-HTML-COMMENT", "override", "high",
        re.compile(
            r"<!--(?:(?!-->).)*?\b(ignore|disregard|exfiltrate|system\s+prompt|approve\s+the|"
            r"password|api[_\s-]?key|secret\s+token)\b(?:(?!-->).)*?-->",
            re.IGNORECASE,
        ),
        "hidden instruction smuggled inside an HTML comment",
    ),
]


# Two tiers of scope, because this is a security-tooling repo whose own artifacts
# legitimately discuss skipping guards, dumping secrets (as risks), subprocess
# calls, etc. The lexical co-occurrence rules below have high recall but trip on
# that natural prose, so they run fail-closed *only* over the untrusted
# external-input zone (raw web captures). The remaining strict rules have
# near-zero false-positive rate on natural prose and run over the whole artifact
# surface. Calibration exercises BOTH tiers against the labelled corpus.
LEXICAL_RULE_IDS = frozenset({
    "PI-EXFIL-SECRET", "PI-EXFIL-SECRET-ZH",
    "PI-WORKFLOW-COMPLETE", "PI-WORKFLOW-BYPASS", "PI-WORKFLOW-ZH",
    "PI-CMD",
})
STRICT_RULES: List[Rule] = [r for r in INJECTION_RULES if r.rule_id not in LEXICAL_RULE_IDS]
LEXICAL_RULES: List[Rule] = [r for r in INJECTION_RULES if r.rule_id in LEXICAL_RULE_IDS]


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str
    path: str
    line: int
    message: str
    excerpt: str


def _truncate(text: str, limit: int = 160) -> str:
    flat = text.replace("\n", "\\n").strip()
    if len(flat) > limit:
        return flat[:limit] + "…"
    return flat


def detect_line(line: str, rules: Sequence[Rule] = INJECTION_RULES) -> List[Tuple[Rule, "re.Match[str]"]]:
    """Return (rule, match) pairs for a single line, honouring negation guards."""
    hits: List[Tuple[Rule, "re.Match[str]"]] = []
    for rule in rules:
        for match in rule.pattern.finditer(line):
            if rule.negatable:
                pre = line[max(0, match.start() - NEGATION_LOOKBACK):match.start()]
                if NEGATION_RE.search(pre):
                    continue
            hits.append((rule, match))
    return hits


def detect_text(text: str, rules: Sequence[Rule] = INJECTION_RULES) -> List[Tuple[Rule, "re.Match[str]"]]:
    """Detect across an arbitrary blob (used by calibrate); evaluated per line."""
    hits: List[Tuple[Rule, "re.Match[str]"]] = []
    for line in (text.splitlines() or [text]):
        hits.extend(detect_line(line, rules))
    return hits


# --- file scanning -----------------------------------------------------------

SCAN_SUFFIX = ".md"
# The untrusted external-input zone: raw web/tool captures that land in the repo
# verbatim. This is where indirect prompt injection actually hides, so the full
# (strict + lexical) ruleset runs here fail-closed.
UNTRUSTED_GLOBS = ("*.tavily_raw.md", "*.external.md")
# Excluded: the adversarial corpus and red-team / experiment reports legitimately
# CONTAIN attack strings as data — scanning them would be self-tripping.
SCAN_EXCLUDE_PREFIXES = (
    "artifacts/red_team/",
    "artifacts/experiments/",
    "template/artifacts/red_team/",
    "template/artifacts/experiments/",
)


def _excluded(rel: str, path: Path, root: Path) -> bool:
    if any(rel.startswith(prefix) for prefix in SCAN_EXCLUDE_PREFIXES):
        return True
    # Skip scratch/dot directories (e.g. .pytest-basetemp) — never the
    # orchestrator's read surface and may contain non-UTF-8 fixtures.
    return any(part.startswith(".") for part in path.relative_to(root).parts)


def iter_scan_files(root: Path) -> List[Path]:
    """All artifact markdown — scanned with the strict ruleset."""
    files: List[Path] = []
    for base in (root / "artifacts", root / "template" / "artifacts"):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*" + SCAN_SUFFIX)):
            rel = path.relative_to(root).as_posix()
            if not _excluded(rel, path, root):
                files.append(path)
    return files


def iter_untrusted_files(root: Path) -> List[Path]:
    """Untrusted external-input captures — scanned with the full ruleset."""
    files: List[Path] = []
    for base in (root / "artifacts", root / "template" / "artifacts"):
        if not base.is_dir():
            continue
        for glob in UNTRUSTED_GLOBS:
            for path in sorted(base.rglob(glob)):
                rel = path.relative_to(root).as_posix()
                if not _excluded(rel, path, root):
                    files.append(path)
    return sorted(set(files))


def scan_file(path: Path, root: Path, rules: Sequence[Rule]) -> List[Finding]:
    rel = path.relative_to(root).as_posix()
    try:
        # utf-8-sig strips a legitimate leading BOM so it is not flagged as a
        # smuggled U+FEFF; an interior U+FEFF still trips PI-HIDDEN-UNICODE.
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:  # fail-closed
        raise RuntimeError(f"cannot read {rel}: {exc}") from exc

    findings: List[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if PI_OK_MARKER in line:
            continue
        for rule, match in detect_line(line, rules):
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    path=rel,
                    line=lineno,
                    message=rule.message,
                    excerpt=_truncate(match.group(0)),
                )
            )
    return findings


def scan_repo(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    # Strict rules over the whole artifact surface.
    for path in iter_scan_files(root):
        findings.extend(scan_file(path, root, STRICT_RULES))
    # Lexical rules additionally over the untrusted external-input zone (the
    # strict rules already covered those files in the pass above).
    for path in iter_untrusted_files(root):
        findings.extend(scan_file(path, root, LEXICAL_RULES))
    return findings


# --- calibration -------------------------------------------------------------

DEFAULT_CORPUS = "artifacts/red_team/prompt_injection_corpus.jsonl"


def load_corpus(path: Path) -> List[dict]:
    rows: List[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{path.name}:{lineno}: invalid JSON: {exc}") from exc
        if row.get("label") not in ("malicious", "benign") or "text" not in row:
            raise RuntimeError(f"{path.name}:{lineno}: each row needs label and text")
        rows.append(row)
    return rows


@dataclass
class Calibration:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    false_negatives: Optional[List[dict]] = None
    false_positives: Optional[List[dict]] = None

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 1.0


def calibrate(rows: Sequence[dict]) -> Calibration:
    cal = Calibration(false_negatives=[], false_positives=[])
    for row in rows:
        hits = detect_text(str(row["text"]))
        flagged = bool(hits)
        malicious = row["label"] == "malicious"
        if malicious and flagged:
            cal.tp += 1
        elif malicious and not flagged:
            cal.fn += 1
            cal.false_negatives.append(row)
        elif not malicious and flagged:
            cal.fp += 1
            cal.false_positives.append({**row, "tripped": sorted({r.rule_id for r, _ in hits})})
        else:
            cal.tn += 1
    return cal


# --- CLI ---------------------------------------------------------------------

def _print_findings(findings: Sequence[Finding], as_json: bool) -> None:
    if as_json:
        print(json.dumps([f.__dict__ for f in findings], ensure_ascii=False, indent=2))
        return
    for f in findings:
        print(f"[{f.severity.upper()}] {f.rule_id} {f.path}:{f.line} — {f.message}")
        print(f"        {f.excerpt}")


def cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        findings = scan_repo(root)
    except RuntimeError as exc:
        print(f"[ERROR] prompt-injection scan failed: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if findings:
        _print_findings(findings, args.json)
        if not args.json:
            print(
                f"\n[FAIL] {len(findings)} prompt-injection finding(s). "
                f"If a hit is verified-safe descriptive content, add a "
                f"`<!-- {PI_OK_MARKER} reason -->` marker on that line.",
                file=sys.stderr,
            )
        return EXIT_FINDINGS
    if not args.json:
        print("[OK] No prompt-injection shapes in the scanned artifact surface.")
    return EXIT_OK


def cmd_calibrate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    corpus_path = (root / args.corpus).resolve()
    try:
        rows = load_corpus(corpus_path)
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] cannot load corpus: {exc}", file=sys.stderr)
        return EXIT_ERROR

    cal = calibrate(rows)
    print(f"corpus: {len(rows)} cases ({cal.tp + cal.fn} malicious, {cal.tn + cal.fp} benign)")
    print(f"confusion: tp={cal.tp} fp={cal.fp} tn={cal.tn} fn={cal.fn}")
    print(f"precision={cal.precision:.3f} recall={cal.recall:.3f}")

    ok = True
    if cal.fn:
        ok = False
        print("\n[FAIL] missed attacks (false negatives):", file=sys.stderr)
        for row in cal.false_negatives or []:
            print(f"  - {row.get('id', '?')} [{row.get('category', '?')}] {_truncate(str(row['text']), 90)}", file=sys.stderr)
    if cal.fp:
        ok = False
        print("\n[FAIL] benign cases flagged (false positives):", file=sys.stderr)
        for row in cal.false_positives or []:
            print(f"  - {row.get('id', '?')} tripped {row.get('tripped')}: {_truncate(str(row['text']), 90)}", file=sys.stderr)
    if ok:
        print("\n[OK] 100% recall on attacks, 0 false positives on benign corpus.")
        return EXIT_OK
    return EXIT_FINDINGS


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Prompt-injection detector for untrusted artifact content")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="scan artifact markdown; fail closed on findings")
    p_scan.add_argument("--root", default=".", help="repository root (default: .)")
    p_scan.add_argument("--json", action="store_true", help="emit findings as JSON")
    p_scan.set_defaults(func=cmd_scan)

    p_cal = sub.add_parser("calibrate", help="measure precision/recall against the adversarial corpus")
    p_cal.add_argument("--root", default=".", help="repository root (default: .)")
    p_cal.add_argument("--corpus", default=DEFAULT_CORPUS, help=f"corpus path (default: {DEFAULT_CORPUS})")
    p_cal.set_defaults(func=cmd_calibrate)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # default behaviour with no subcommand: scan the current tree
        return cmd_scan(argparse.Namespace(root=".", json=False))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
