#!/usr/bin/env python3
"""ssdf_mapping_validator.py — mapping-integrity validator for the SSDF coverage map.

This is NOT an SSDLC conformance certifier. It validates that ``docs/ssdf-mapping.md``
— council-forge's mapping of its mechanisms onto the NIST SSDF SP 800-218 v1.1
practices — is STRUCTURALLY COMPLETE and HONEST. It does not execute any security
scan and it cannot judge the qualitative efficacy of a mechanism; that is the job of
the dual adversarial review + human review. The machine check here only guarantees:

- every canonical SSDF v1.1 practice is present (no silently-dropped practice),
- each row's status is one of {covered, partial, gap},
- ``covered``/``partial`` rows cite a Mechanism AND an Evidence ref that actually
  RESOLVE to a real repo location (path[#heading-slug][:line]; no ``cmd:``, no
  absolute paths, no ``..`` traversal),
- each ``gap`` row carries a waiver whose target explicitly declares the waiver with a
  structured ``SSDF-Gap-Waiver: <practice_id>`` marker (so a gap is a deliberate,
  auditable backlog item, not an incidental mention).

Exit semantics are deliberately honest so a green CI run can NEVER be read as
"SSDLC conformant":

- ``0`` = structurally valid AND all 19 practices are ``covered`` (full coverage),
- ``3`` = structurally valid but has open items (>=1 ``partial`` or ``gap``),
- ``2`` = integrity violation (missing practice / bad status / unresolvable ref/waiver),
- ``1`` = usage / IO error.

Source-only (a downstream terminal repo does not own the SSDF mapping program), so this
file is NOT mirrored into ``template/`` and is NOT part of EXACT_SYNC_FILES — same
discipline as scaffold_downstream.py / drift_dashboard.py / propagate_downstream.py.

NOTE (scope boundary, enforced by test_validator_imports_are_bounded): this module must
never import subprocess / os.system / any security-scanning library. It only parses
markdown and resolves repo-relative references. It is a mapping checker, not a scanner.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Canonical NIST SSDF SP 800-218 v1.1 practices (verified against the official
# publication on 2026-06-07: https://doi.org/10.6028/NIST.SP.800-218 ). PW.3 was
# REMOVED in v1.1, so it is intentionally absent. 19 practices total.
CANONICAL_PRACTICES: Tuple[str, ...] = (
    "PO.1", "PO.2", "PO.3", "PO.4", "PO.5",
    "PS.1", "PS.2", "PS.3",
    "PW.1", "PW.2", "PW.4", "PW.5", "PW.6", "PW.7", "PW.8", "PW.9",
    "RV.1", "RV.2", "RV.3",
)
CANONICAL_SET = frozenset(CANONICAL_PRACTICES)

VALID_STATUS = frozenset({"covered", "partial", "gap"})

ROADMAP_REL = "docs/ssdf-roadmap.md"
DECISION_PREFIX = "decision:"

# Exit codes
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_VIOLATION = 2
EXIT_OPEN_ITEMS = 3

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_LINE_SUFFIX_RE = re.compile(r":(\d+)$")


def slugify(heading: str) -> str:
    """GitHub-compatible heading slug, with an explicitly documented algorithm.

    1. strip surrounding whitespace; 2. lowercase; 3. drop every char that is not a
    word char (Unicode letters/digits/underscore, incl. CJK), whitespace, or hyphen;
    4. collapse whitespace runs to a single hyphen; 5. collapse hyphen runs; 6. strip
    leading/trailing hyphens. Duplicate headings are disambiguated by the caller
    (see ``heading_sections``) with ``-1``/``-2`` suffixes in document order.
    """
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


@dataclass
class Section:
    level: int
    slug: str
    start: int  # 0-based line index of the heading
    end: int    # exclusive 0-based line index where the section ends


def heading_sections(text: str) -> List[Section]:
    """Parse markdown headings into sections with GitHub-style duplicate suffixing.

    A section spans from its heading line until the next heading of the same or higher
    level (i.e. ``<=`` level number), or end of file.
    """
    lines = text.splitlines()
    raw: List[Tuple[int, str, int]] = []  # (level, base_slug, line_index)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            raw.append((len(m.group(1)), slugify(m.group(2)), i))
    # disambiguate duplicate slugs in document order
    seen: Dict[str, int] = {}
    sections: List[Section] = []
    for idx, (level, base, line_i) in enumerate(raw):
        if base in seen:
            seen[base] += 1
            slug = f"{base}-{seen[base]}"
        else:
            seen[base] = 0
            slug = base
        # end = next heading with level <= this level, else EOF
        end = len(lines)
        for level2, _b2, line2 in raw[idx + 1:]:
            if level2 <= level:
                end = line2
                break
        sections.append(Section(level=level, slug=slug, start=line_i, end=end))
    return sections


def _is_unsafe_path(path_part: str) -> bool:
    """Reject absolute paths and any parent traversal."""
    if not path_part:
        return True
    p = Path(path_part)
    if p.is_absolute():
        return True
    return ".." in p.parts


def resolve_ref(ref: str, repo_root: Path) -> bool:
    """Resolve a mechanism/evidence ref to a real repo location. Pure-ish (reads files).

    Accepts ``path``, ``path#heading-slug``, ``path:line`` (and combinations). Rejects
    ``cmd:``/non-path, absolute paths, and ``..`` traversal. ``#anchor`` must match a
    real heading slug; ``:line`` must be a positive line within the file.
    """
    if not ref or ref.startswith("cmd:"):
        return False
    rest = ref
    line_no: Optional[int] = None
    anchor: Optional[str] = None
    if "#" in rest:
        rest, anchor = rest.split("#", 1)
    m = _LINE_SUFFIX_RE.search(rest)
    if m:
        line_no = int(m.group(1))
        rest = rest[: m.start()]
    path_part = rest.strip()
    if _is_unsafe_path(path_part):
        return False
    target = (repo_root / path_part).resolve()
    try:
        target.relative_to(repo_root.resolve())
    except ValueError:
        return False  # escaped repo root
    if not target.is_file():
        return False
    if anchor is not None:
        anchor = anchor.strip()
        text = target.read_text(encoding="utf-8")
        slugs = {sec.slug for sec in heading_sections(text)}
        if anchor not in slugs:
            return False
    if line_no is not None:
        text = target.read_text(encoding="utf-8")
        n_lines = len(text.splitlines())
        if line_no < 1 or line_no > n_lines:
            return False
    return True


def _marker_in_text(text: str, practice_id: str) -> bool:
    """True if a structured ``SSDF-Gap-Waiver: <practice_id>`` marker is in text.

    The marker must be its own line-anchored declaration (so an incidental in-prose
    mention does not count), but may carry markdown decoration: an optional leading
    list bullet (``-``/``*``) and optional surrounding backticks. The practice id is
    bounded by end-of-line so ``PW.4`` never matches ``PW.40``.
    """
    pattern = re.compile(
        r"^\s*[-*]?\s*`?SSDF-Gap-Waiver:\s*" + re.escape(practice_id) + r"`?\s*$",
        re.MULTILINE,
    )
    return bool(pattern.search(text))


def resolve_waiver(ref: str, repo_root: Path, practice_id: str) -> bool:
    """Resolve a gap waiver. Both forms require an explicit structured marker.

    - ``decision:TASK-NNNN`` -> artifacts/decisions/TASK-NNNN.decision.md exists AND
      contains ``SSDF-Gap-Waiver: <practice_id>``.
    - ``docs/ssdf-roadmap.md#anchor`` -> file exists, anchor is a real heading slug,
      and the marker appears WITHIN that anchor's section (not file-wide, not as an
      incidental mention).
    """
    if not ref:
        return False
    if ref.startswith(DECISION_PREFIX):
        task = ref[len(DECISION_PREFIX):].strip()
        if not re.fullmatch(r"TASK-\d+", task):
            return False
        decision = repo_root / "artifacts" / "decisions" / f"{task}.decision.md"
        if not decision.is_file():
            return False
        return _marker_in_text(decision.read_text(encoding="utf-8"), practice_id)
    if "#" not in ref:
        return False
    path_part, anchor = ref.split("#", 1)
    if path_part.strip() != ROADMAP_REL:
        return False
    anchor = anchor.strip()
    roadmap = repo_root / ROADMAP_REL
    if not roadmap.is_file():
        return False
    text = roadmap.read_text(encoding="utf-8")
    lines = text.splitlines()
    for sec in heading_sections(text):
        if sec.slug == anchor:
            section_text = "\n".join(lines[sec.start: sec.end])
            return _marker_in_text(section_text, practice_id)
    return False


@dataclass
class MappingRow:
    practice: str
    title: str
    status: str
    mechanism: str
    evidence: str
    waiver: str


@dataclass
class ValidationResult:
    rows: Dict[str, MappingRow]
    violations: List[str] = field(default_factory=list)

    @property
    def covered(self) -> List[str]:
        return sorted(p for p, r in self.rows.items() if r.status == "covered")

    @property
    def partial(self) -> List[str]:
        return sorted(p for p, r in self.rows.items() if r.status == "partial")

    @property
    def gaps(self) -> List[str]:
        return sorted(p for p, r in self.rows.items() if r.status == "gap")

    @property
    def has_open_items(self) -> bool:
        return bool(self.partial or self.gaps)


def parse_mapping(path: Path) -> Tuple[Dict[str, MappingRow], List[str]]:
    """Parse the 6-column mapping table. Returns (rows, parse_errors)."""
    errors: List[str] = []
    rows: Dict[str, MappingRow] = {}
    text = path.read_text(encoding="utf-8")
    in_table = False
    header_cols = ["practice", "title", "status", "mechanism", "evidence", "gap/waiver"]
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = _TABLE_ROW_RE.match(line)
        if not m:
            in_table = False
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        lowered = [c.lower() for c in cells]
        if lowered[:6] == header_cols:
            in_table = True
            continue
        if _SEPARATOR_RE.match(line):
            continue
        if not in_table:
            continue
        if len(cells) < 6:
            errors.append(f"line {lineno}: malformed mapping row (expected 6 columns): {line.strip()}")
            continue
        practice = cells[0]
        rows[practice] = MappingRow(
            practice=practice, title=cells[1], status=cells[2].lower(),
            mechanism=cells[3], evidence=cells[4], waiver=cells[5],
        )
    return rows, errors


def validate(rows: Dict[str, MappingRow], repo_root: Path) -> ValidationResult:
    """Run integrity checks (A)-(D). Returns a ValidationResult with violations."""
    result = ValidationResult(rows=rows)
    # (A) canonical completeness
    present = set(rows)
    missing = sorted(CANONICAL_SET - present)
    extra = sorted(present - CANONICAL_SET)
    for p in missing:
        result.violations.append(f"missing canonical practice: {p}")
    for p in extra:
        result.violations.append(f"unknown/extraneous practice id: {p}")
    for practice in sorted(present & CANONICAL_SET):
        row = rows[practice]
        # (B) status legality
        if row.status not in VALID_STATUS:
            result.violations.append(f"{practice}: illegal status '{row.status}'")
            continue
        if row.status in ("covered", "partial"):
            # (C) mechanism + evidence both resolve
            if not row.mechanism:
                result.violations.append(f"{practice}: {row.status} row missing Mechanism")
            elif not resolve_ref(row.mechanism, repo_root):
                result.violations.append(f"{practice}: Mechanism ref does not resolve: {row.mechanism}")
            if not row.evidence:
                result.violations.append(f"{practice}: {row.status} row missing Evidence")
            elif not resolve_ref(row.evidence, repo_root):
                result.violations.append(f"{practice}: Evidence ref does not resolve: {row.evidence}")
        elif row.status == "gap":
            # (D) waiver resolves with structured marker
            if not resolve_waiver(row.waiver, repo_root, practice):
                result.violations.append(
                    f"{practice}: gap waiver does not resolve (need SSDF-Gap-Waiver: {practice} "
                    f"in the referenced target): {row.waiver}"
                )
    return result


def render_markdown(result: ValidationResult, parse_errors: List[str]) -> str:
    lines = ["# SSDF Mapping Integrity Report", ""]
    if parse_errors or result.violations:
        lines.append("Status: INTEGRITY VIOLATION (exit 2)")
    elif result.has_open_items:
        lines.append("Status: mapping structurally valid; open items (exit 3)")
    else:
        lines.append("Status: mapping structurally valid; all practices covered (exit 0)")
    lines.append("")
    lines.append(f"- covered: {len(result.covered)}")
    lines.append(f"- partial ({len(result.partial)}): {', '.join(result.partial) or '-'}")
    lines.append(f"- gaps ({len(result.gaps)}): {', '.join(result.gaps) or '-'}")
    if parse_errors:
        lines.append("")
        lines.append("## Parse Errors")
        lines.extend(f"- {e}" for e in parse_errors)
    if result.violations:
        lines.append("")
        lines.append("## Integrity Violations")
        lines.extend(f"- {v}" for v in result.violations)
    lines.append("")
    return "\n".join(lines)


def build_json(result: ValidationResult, parse_errors: List[str], code: int) -> dict:
    return {
        "exit": code,
        "status": (
            "violation" if code == EXIT_VIOLATION
            else "open-items" if code == EXIT_OPEN_ITEMS
            else "full-coverage"
        ),
        "covered_count": len(result.covered),
        "partial": result.partial,
        "gaps": result.gaps,
        "parse_errors": parse_errors,
        "violations": result.violations,
    }


def default_mapping_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "ssdf-mapping.md"


def repo_root_of(mapping_path: Path) -> Path:
    # mapping lives at <root>/docs/ssdf-mapping.md
    return mapping_path.resolve().parents[1]


def compute_exit(result: ValidationResult, parse_errors: List[str]) -> int:
    if parse_errors or result.violations:
        return EXIT_VIOLATION
    if result.has_open_items:
        return EXIT_OPEN_ITEMS
    return EXIT_OK


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate SSDF mapping integrity (NOT an SSDLC conformance certifier)."
    )
    parser.add_argument("--mapping", default="", help="Path to docs/ssdf-mapping.md.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    mapping_path = Path(args.mapping) if args.mapping else default_mapping_path()
    if not mapping_path.is_file():
        print(f"[FAIL] mapping file not found: {mapping_path}", file=sys.stderr)
        return EXIT_USAGE
    repo_root = repo_root_of(mapping_path)
    rows, parse_errors = parse_mapping(mapping_path)
    result = validate(rows, repo_root)
    code = compute_exit(result, parse_errors)
    if args.json:
        print(json.dumps(build_json(result, parse_errors, code), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(result, parse_errors))
    return code


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
