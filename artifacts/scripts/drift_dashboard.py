#!/usr/bin/env python3
"""drift_dashboard.py — read-only steady-state drift detector for council-forge downstreams.

For each downstream terminal repo, compare its council-forge-owned governance files
against the source ``template/`` and classify every template file as:

- ``in-sync``         : downstream copy matches template (line-ending normalised).
- ``drifted``         : downstream copy differs (council-forge moved on, or the
                        downstream edited a governance file it should not have).
- ``missing``         : template file has no downstream copy and is NOT a known
                        reconciliation prune -> a genuine gap.
- ``optional-absent`` : template file is absent but is a known brownfield-reconciliation
                        prune (README.zh-TW.md / LICENSE / TASK-9xx seeds /
                        council-forge workflows) -> intentional, not a gap.
- ``instantiated``    : template file carries instantiation placeholders
                        ({{PROJECT_NAME}} ...), so its downstream content legitimately
                        varies per repo and is not exact-compared.

Read-only: writes nothing, mutates nothing. Source-only tool — a downstream *terminal*
repo never dashboards further repos, so this script is intentionally NOT mirrored into
``template/`` and is NOT part of EXACT_SYNC_FILES (same discipline as
scaffold_downstream.py).

Design note (why no per-downstream instantiation parameters are needed): the drift
surface that matters is the governance *machinery* — guard scripts, schemas, docs,
prompts — none of which carry placeholders, so they are compared directly. The handful
of files that DO carry placeholders (CLAUDE.md / README / repository-profile.json) are
detected via the template text itself and reported as ``instantiated`` rather than
exact-compared, so the dashboard never needs to know each downstream's PROJECT_NAME.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from scaffold_downstream import (
    find_leftover_instantiation_keys,
    is_text_file,
    iter_files,
)

# Classification labels
IN_SYNC = "in-sync"
DRIFTED = "drifted"
MISSING = "missing"
OPTIONAL_ABSENT = "optional-absent"
INSTANTIATED = "instantiated"
BROWNFIELD_OWNED = "brownfield-owned"

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_DRIFT = 2

# A retrofitted (brownfield) downstream carries this marker (scaffold_downstream
# --retrofit writes it; see council-forge TASK-1074).
BROWNFIELD_MARKER = ".council-forge-brownfield"

# In a brownfield downstream these template files are owned by the project itself
# (its pre-existing agent guide / ignore rules / README / CLAUDE), so their content
# legitimately differs from the template and must NOT be reported as drift. This is the
# dashboard-side complement of TASK-1074's BROWNFIELD_PROJECT_OWNED_FILES, extended with
# AGENTS.md and .gitignore (which every repo customises and which carry no placeholder,
# so they would otherwise be false-positive drift).
BROWNFIELD_OWNED_FILES = frozenset(
    {
        "CLAUDE.md",
        "README.md",
        "README.zh-TW.md",
        "AGENTS.md",
        ".gitignore",
    }
)

# Files commonly removed during brownfield reconciliation; their absence in a downstream
# is intentional (see the Verso/Vero/Sentinel/LINE-BOT retrofits), not a drift gap.
OPTIONAL_ABSENT_EXACT = frozenset(
    {
        "README.zh-TW.md",
        "LICENSE",
    }
)
COUNCIL_FORGE_WORKFLOWS = frozenset(
    {
        ".github/workflows/quarterly-threat-model.yml",
        ".github/workflows/security-scan.yml",
        ".github/workflows/weekly-council-audit.yml",
        ".github/workflows/workflow-guards.yml",
    }
)

# Directories never walked when counting a downstream's project-owned files (build
# output, dependencies, VCS, tooling state). Keeps the walk off multi-GB trees.
IGNORED_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "dist-ssr",
        "build",
        "target",
        "bin",
        "obj",
        "publish",
        ".omc",
        ".playwright-mcp",
        ".vs",
        ".vscode",
        ".idea",
        "gen",
    }
)


def is_optional_absent(rel: str) -> bool:
    """True if a missing template file ``rel`` is a known reconciliation prune. Pure."""
    if rel in OPTIONAL_ABSENT_EXACT or rel in COUNCIL_FORGE_WORKFLOWS:
        return True
    name = rel.rsplit("/", 1)[-1]
    return rel.startswith("artifacts/") and name.startswith("TASK-9")


def normalised_bytes(path: Path) -> bytes:
    """Content for comparison: text files are line-ending normalised (LF), binary as-is.

    This stops a downstream working tree that uses CRLF (git autocrlf) from being
    reported as drift when only line endings differ.
    """
    if is_text_file(path):
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    return path.read_bytes()


def template_has_placeholder(path: Path) -> bool:
    """True if the template file carries any instantiation placeholder. Pure-ish (reads)."""
    if not is_text_file(path):
        return False
    return bool(find_leftover_instantiation_keys(path.read_text(encoding="utf-8")))


def classify_file(template_file: Path, downstream_file: Path, rel: str, brownfield: bool) -> str:
    """Classify one template file against its downstream counterpart."""
    if not downstream_file.exists():
        return OPTIONAL_ABSENT if is_optional_absent(rel) else MISSING
    if template_has_placeholder(template_file):
        return INSTANTIATED
    if brownfield and rel in BROWNFIELD_OWNED_FILES:
        return BROWNFIELD_OWNED
    if normalised_bytes(template_file) == normalised_bytes(downstream_file):
        return IN_SYNC
    return DRIFTED


@dataclass
class DownstreamReport:
    name: str
    path: str
    brownfield: bool = False
    verdicts: Dict[str, List[str]] = field(default_factory=dict)
    project_owned: int = 0

    def add(self, status: str, rel: str) -> None:
        self.verdicts.setdefault(status, []).append(rel)

    def count(self, status: str) -> int:
        return len(self.verdicts.get(status, ()))

    @property
    def owned_total(self) -> int:
        return sum(len(v) for v in self.verdicts.values())

    @property
    def has_problems(self) -> bool:
        return self.count(DRIFTED) > 0 or self.count(MISSING) > 0

    @property
    def overall(self) -> str:
        return "DRIFT DETECTED" if self.has_problems else "IN SYNC"


def count_project_owned(downstream_root: Path, template_rel: frozenset) -> int:
    """Count downstream files that are NOT council-forge-owned, skipping ignored dirs."""
    total = 0
    stack: List[Path] = [downstream_root]
    while stack:
        current = stack.pop()
        for child in current.iterdir():
            if child.is_dir():
                if child.name in IGNORED_DIRS:
                    continue
                stack.append(child)
            elif child.is_file():
                rel = child.relative_to(downstream_root).as_posix()
                if rel not in template_rel:
                    total += 1
    return total


def classify_downstream(template_root: Path, downstream_root: Path, name: str) -> DownstreamReport:
    """Build the full classification report for one downstream repo."""
    report = DownstreamReport(name=name, path=str(downstream_root))
    brownfield = (downstream_root / BROWNFIELD_MARKER).exists()
    report.brownfield = brownfield
    template_rel = set()
    for template_file in iter_files(template_root):
        rel = template_file.relative_to(template_root).as_posix()
        template_rel.add(rel)
        status = classify_file(template_file, downstream_root / rel, rel, brownfield)
        report.add(status, rel)
    report.project_owned = count_project_owned(downstream_root, frozenset(template_rel))
    return report


def render_markdown(reports: Sequence[DownstreamReport]) -> str:
    """Human-readable dashboard."""
    lines: List[str] = ["# council-forge Downstream Drift Dashboard", ""]
    lines.append("| Downstream | Overall | in-sync | drifted | missing | optional-absent | instantiated | brownfield-owned | project-owned |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in reports:
        lines.append(
            f"| {r.name} | {r.overall} | {r.count(IN_SYNC)} | {r.count(DRIFTED)} | "
            f"{r.count(MISSING)} | {r.count(OPTIONAL_ABSENT)} | {r.count(INSTANTIATED)} | "
            f"{r.count(BROWNFIELD_OWNED)} | {r.project_owned} |"
        )
    for r in reports:
        if not r.has_problems:
            continue
        lines.append("")
        lines.append(f"## {r.name}: {r.overall}")
        for status in (DRIFTED, MISSING):
            items = r.verdicts.get(status, [])
            if items:
                lines.append(f"### {status} ({len(items)})")
                lines.extend(f"- {rel}" for rel in items)
    lines.append("")
    return "\n".join(lines)


def build_json(reports: Sequence[DownstreamReport]) -> List[dict]:
    """Machine-readable report."""
    return [
        {
            "name": r.name,
            "path": r.path,
            "brownfield": r.brownfield,
            "overall": r.overall,
            "counts": {
                IN_SYNC: r.count(IN_SYNC),
                DRIFTED: r.count(DRIFTED),
                MISSING: r.count(MISSING),
                OPTIONAL_ABSENT: r.count(OPTIONAL_ABSENT),
                INSTANTIATED: r.count(INSTANTIATED),
                BROWNFIELD_OWNED: r.count(BROWNFIELD_OWNED),
            },
            "project_owned": r.project_owned,
            "drifted": r.verdicts.get(DRIFTED, []),
            "missing": r.verdicts.get(MISSING, []),
        }
        for r in reports
    ]


def default_template_root() -> Path:
    """The template/ directory of the source repo this script ships in."""
    return Path(__file__).resolve().parents[2] / "template"


def parse_downstream_arg(value: str) -> Tuple[str, Path]:
    """Parse ``NAME=PATH`` (or bare ``PATH``, name = basename)."""
    if "=" in value:
        name, _, path = value.partition("=")
        return name or Path(path).name, Path(path)
    return Path(value).name, Path(value)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only drift dashboard for council-forge downstream repos."
    )
    parser.add_argument(
        "--downstream",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="A downstream repo to scan (repeatable).",
    )
    parser.add_argument("--template-root", default="", help="Override the template/ source dir.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit non-zero (2) if any downstream has drifted or missing files.",
    )
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not args.downstream:
        print("[FAIL] at least one --downstream NAME=PATH is required", file=sys.stderr)
        return EXIT_ERROR
    template_root = Path(args.template_root) if args.template_root else default_template_root()
    if not template_root.is_dir():
        print(f"[FAIL] template root does not exist: {template_root}", file=sys.stderr)
        return EXIT_ERROR

    reports: List[DownstreamReport] = []
    for spec in args.downstream:
        name, path = parse_downstream_arg(spec)
        if not path.is_dir():
            print(f"[FAIL] downstream path does not exist: {path}", file=sys.stderr)
            return EXIT_ERROR
        reports.append(classify_downstream(template_root, path, name))

    if args.json:
        print(json.dumps(build_json(reports), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(reports))

    if args.fail_on_drift and any(r.has_problems for r in reports):
        return EXIT_DRIFT
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
