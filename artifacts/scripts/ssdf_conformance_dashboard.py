#!/usr/bin/env python3
"""ssdf_conformance_dashboard.py — read-only per-downstream SSDF mechanism-overlay view.

For each council-forge downstream, this reports — per SSDF practice — whether the
council-forge MECHANISM that maps to that practice (per ``docs/ssdf-mapping.md``) is
actually present (overlaid) in the downstream, using THREE ORTHOGONAL axes:

1. applicability  — is the mechanism file propagable (lives in ``template/``) or a
                    source-only upstream-governance tool (lives only at root)?
2. actual-overlay — for a propagable mechanism, REUSES ``drift_dashboard.classify_file``
                    (so placeholder / brownfield / prune semantics are honoured, not
                    re-implemented) and maps its verdict to a conformance status.
3. declared       — the *intended* enablement state from ``enablement-matrix.json`` (the
                    SSOT). This is a SEPARATE column for context; it NEVER overrides the
                    actual ``status``.

HONESTY (this is the whole point — see council-forge P8-E / TASK-1085):

- This is NOT an SSDLC conformance certifier. ``overlaid`` means the mechanism FILE is
  present and in-sync, NOT that the practice is enforced in that downstream's pipeline.
- The status vocabulary deliberately has NO ``covered`` and NO ``n-a`` (``n-a`` is only a
  *declared* value). A propagable-but-absent mechanism is honestly ``not-propagated``
  even when the downstream declares ``native-enforcing`` — declared never hides actual.
- ``not-overlaid`` marks a council-forge CI workflow (currently only PW.4's
  ``security-scan.yml``) that is by-design pruned downstream; it is still COUNTED by
  ``--fail-on-gap`` so a real mechanism absence is never silently ignored.

Read-only: writes nothing, mutates nothing, never touches the mapping/SSOT/downstream.
Source-only tool (a downstream terminal repo does not dashboard further repos), so this
file is NOT mirrored into ``template/`` and is NOT part of EXACT_SYNC_FILES — same
discipline as scaffold_downstream.py / drift_dashboard.py / propagate_downstream.py /
ssdf_mapping_validator.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ssdf_mapping_validator import parse_mapping
from drift_dashboard import (
    BROWNFIELD_MARKER,
    classify_file,
    default_template_root,
    parse_downstream_arg,
)
# drift_dashboard classification constants (imported by value so an upstream rename
# surfaces as an ImportError here rather than a silent mismatch).
from drift_dashboard import (
    IN_SYNC,
    DRIFTED,
    MISSING,
    OPTIONAL_ABSENT,
    INSTANTIATED,
    BROWNFIELD_OWNED,
)

# ---- conformance status vocabulary (7 values; NO "covered", NO "n-a") -------------
UPSTREAM_GOVERNED = "upstream-governed"  # mechanism is source-only (root, not template/)
OVERLAID = "overlaid"                    # propagable + present & in-sync (or instantiated)
PROJECT_OWNED = "project-owned"          # brownfield-owned file the project legitimately keeps
DRIFTED_STATUS = "drifted"               # propagable + present but differs
NOT_PROPAGATED = "not-propagated"        # propagable + absent (stale snapshot, awaiting propagate)
NOT_OVERLAID = "not-overlaid"            # council-forge CI workflow, by-design pruned downstream
UNMAPPED = "unmapped"                    # mapping row carries no mechanism path

# Statuses that --fail-on-gap counts as a gap.
GAP_STATUSES = frozenset({NOT_PROPAGATED, DRIFTED_STATUS, NOT_OVERLAID})

# Exhaustive map from a classify_file verdict to a conformance status. A verdict NOT in
# this map is a hard failure (fail-closed): a new drift category must be classified
# deliberately, never silently swallowed.
_VERDICT_TO_STATUS: Dict[str, str] = {
    IN_SYNC: OVERLAID,
    INSTANTIATED: OVERLAID,
    BROWNFIELD_OWNED: PROJECT_OWNED,
    DRIFTED: DRIFTED_STATUS,
    MISSING: NOT_PROPAGATED,
    OPTIONAL_ABSENT: NOT_OVERLAID,
}

# ---- practice -> security dimension(s) (conservative; unmapped practices = governance) --
PRACTICE_TO_DIMENSIONS: Dict[str, Tuple[str, ...]] = {
    "PW.4": ("sca",),
    "PW.7": ("sast",),
    "PS.3": ("sbom",),
    "PS.2": ("release-integrity",),
    "RV.1": ("secret-scan", "disclosure"),
}
GOVERNANCE = "governance"  # declared bucket for practices with no security dimension

# The controlled, REQUIRED set of security dimensions, derived from the practice mapping
# itself. load_enablement validates the SSOT against THIS set (not against the JSON's own
# self-declared dimension list) so a downstream cannot silently drop/rename a dimension
# (e.g. delete `sast`) and later be emitted as `sast=unknown`. (codex impl-review)
REQUIRED_DIMENSIONS = frozenset(d for dims in PRACTICE_TO_DIMENSIONS.values() for d in dims)

# Conservatism order: lower index = weaker/less-covered enablement. Used to flag the
# most-conservative state when a practice maps to multiple dimensions (e.g. RV.1).
_CONSERVATISM: Tuple[str, ...] = (
    "n-a",
    "template-only-frozen",
    "local-precommit",
    "opt-in-ci",
    "native-enforcing",
    "enforced-self",
)

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_GAP = 2

_LINE_SUFFIX_RE = re.compile(r":(\d+)$")

CAVEAT = (
    "This dashboard reports per-downstream MECHANISM-OVERLAY coverage against "
    "council-forge's SSDF mapping. It is NOT an SSDLC conformance certification: "
    "`overlaid` means the governance mechanism file is present and in-sync, NOT that "
    "the practice is enforced in that downstream's pipeline. `not-overlaid` marks a "
    "council-forge CI workflow (e.g. security-scan.yml) that is by-design NOT propagated "
    "downstream -- read the `declared` column for how that downstream is expected to "
    "cover it. The `declared` column is the INTENDED enablement (enablement-matrix.json), "
    "NOT observed runtime enforcement -- it NEVER overrides the actual `status`."
)


def mechanism_repo_path(ref: str) -> str:
    """Repo-relative path part of a mechanism ref, stripping ``#anchor`` and ``:line``.

    council-forge mapping mechanism refs are mostly plain paths; a few may carry a
    ``#heading`` or ``:line`` suffix. This is a small, deliberately-new helper (NOT a
    reuse of ssdf_mapping_validator.resolve_ref, which returns only a bool). Pure.
    """
    if not ref:
        return ""
    rest = ref
    if "#" in rest:
        rest = rest.split("#", 1)[0]
    m = _LINE_SUFFIX_RE.search(rest)
    if m:
        rest = rest[: m.start()]
    return rest.strip()


def verdict_to_status(verdict: str) -> str:
    """Map a classify_file verdict to a conformance status; unknown -> hard fail."""
    try:
        return _VERDICT_TO_STATUS[verdict]
    except KeyError as exc:  # fail-closed: a new drift category must be classified
        raise ValueError(f"unmapped classify_file verdict: {verdict!r}") from exc


def load_enablement(path: Path) -> dict:
    """Load + structurally validate the enablement SSOT (fail-closed on bad vocab)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"enablement-matrix.json: unsupported schema_version {data.get('schema_version')!r}")
    dimensions = data.get("dimensions")
    states = data.get("enablement_states")
    repos = data.get("repos")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("enablement-matrix.json: 'dimensions' must be a non-empty list")
    if len(dimensions) != len(set(dimensions)):
        raise ValueError("enablement-matrix.json: 'dimensions' contains duplicates")
    if set(dimensions) != REQUIRED_DIMENSIONS:
        raise ValueError(
            "enablement-matrix.json: 'dimensions' must be exactly the practice-mapped set "
            f"{sorted(REQUIRED_DIMENSIONS)} (a missing / extra / renamed dimension is rejected)"
        )
    if not isinstance(states, dict) or not states:
        raise ValueError("enablement-matrix.json: 'enablement_states' must be a non-empty object")
    if not isinstance(repos, dict) or not repos:
        raise ValueError("enablement-matrix.json: 'repos' must be a non-empty object")
    dim_set = set(dimensions)
    state_set = set(states)
    unknown_conservatism = state_set - set(_CONSERVATISM)
    if unknown_conservatism:
        raise ValueError(f"enablement-matrix.json: states not in conservatism order: {sorted(unknown_conservatism)}")
    for repo, spec in repos.items():
        rdims = spec.get("dimensions")
        if not isinstance(rdims, dict) or set(rdims) != dim_set:
            raise ValueError(f"enablement-matrix.json: repo {repo!r} must declare exactly dimensions {sorted(dim_set)}")
        for dim, cell in rdims.items():
            state = cell.get("state") if isinstance(cell, dict) else None
            if state not in state_set:
                raise ValueError(f"enablement-matrix.json: repo {repo!r} dim {dim!r} has unknown state {state!r}")
    return data


def _most_conservative(states: Sequence[str]) -> str:
    """The weakest (lowest conservatism index) of the given states."""
    return min(states, key=lambda s: _CONSERVATISM.index(s))


def declared_for(practice: str, repo: str, enablement: dict) -> str:
    """The declared-enablement description for a practice in a repo (independent of status).

    Practices with no security dimension are ``governance`` (implicitly expected of all
    downstreams). Multi-dimension practices (RV.1) list every dimension's state and flag
    the most-conservative one.
    """
    dims = PRACTICE_TO_DIMENSIONS.get(practice)
    if not dims:
        return GOVERNANCE
    repo_spec = enablement.get("repos", {}).get(repo)
    if not repo_spec:
        return "unknown-repo"
    rdims = repo_spec.get("dimensions", {})
    parts: List[str] = []
    states: List[str] = []
    for dim in dims:
        state = rdims.get(dim, {}).get("state", "unknown")
        states.append(state)
        parts.append(f"{dim}={state}")
    if len(dims) == 1:
        return parts[0]
    return f"{', '.join(parts)} (most-conservative: {_most_conservative(states)})"


@dataclass
class PracticeVerdict:
    practice: str
    title: str
    mechanism_ref: str
    mechanism_path: str
    applicability: str  # "propagable" | "source-only" | "unmapped"
    status: str
    declared: str


@dataclass
class DownstreamConformance:
    name: str
    path: str
    brownfield: bool
    verdicts: List[PracticeVerdict] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for v in self.verdicts if v.status == status)

    @property
    def gap_count(self) -> int:
        return sum(1 for v in self.verdicts if v.status in GAP_STATUSES)

    @property
    def has_gap(self) -> bool:
        return self.gap_count > 0


def classify_practice(
    practice: str,
    row,
    template_root: Path,
    downstream_root: Path,
    brownfield: bool,
    repo_name: str,
    enablement: dict,
) -> PracticeVerdict:
    """Compute the three-axis verdict for one practice against one downstream."""
    ref = row.mechanism
    path = mechanism_repo_path(ref)
    declared = declared_for(practice, repo_name, enablement)
    if not path:
        return PracticeVerdict(practice, row.title, ref, path, "unmapped", UNMAPPED, declared)
    template_file = template_root / path
    if not template_file.is_file():
        # mechanism not propagated via template/ -> source-only upstream governance
        return PracticeVerdict(practice, row.title, ref, path, "source-only", UPSTREAM_GOVERNED, declared)
    verdict = classify_file(template_file, downstream_root / path, path, brownfield)
    status = verdict_to_status(verdict)
    return PracticeVerdict(practice, row.title, ref, path, "propagable", status, declared)


def classify_downstream(
    rows: dict,
    template_root: Path,
    downstream_root: Path,
    name: str,
    enablement: dict,
) -> DownstreamConformance:
    brownfield = (downstream_root / BROWNFIELD_MARKER).exists()
    report = DownstreamConformance(name=name, path=str(downstream_root), brownfield=brownfield)
    for practice in sorted(rows):
        report.verdicts.append(
            classify_practice(practice, rows[practice], template_root, downstream_root, brownfield, name, enablement)
        )
    return report


_SUMMARY_ORDER = (
    OVERLAID, PROJECT_OWNED, UPSTREAM_GOVERNED, NOT_PROPAGATED, DRIFTED_STATUS, NOT_OVERLAID, UNMAPPED,
)


def render_markdown(reports: Sequence[DownstreamConformance]) -> str:
    lines: List[str] = ["# council-forge Per-Downstream SSDF Conformance Dashboard", ""]
    lines.append(f"> {CAVEAT}")
    lines.append("")
    lines.append("| Downstream | " + " | ".join(_SUMMARY_ORDER) + " | gaps |")
    lines.append("|---|" + "---:|" * (len(_SUMMARY_ORDER) + 1))
    for r in reports:
        cells = " | ".join(str(r.count(s)) for s in _SUMMARY_ORDER)
        lines.append(f"| {r.name} | {cells} | {r.gap_count} |")
    for r in reports:
        lines.append("")
        bf = " (brownfield)" if r.brownfield else ""
        lines.append(f"## {r.name}{bf}")
        lines.append("")
        lines.append("| Practice | Status | Applicability | Mechanism | Declared |")
        lines.append("|---|---|---|---|---|")
        for v in r.verdicts:
            lines.append(
                f"| {v.practice} {v.title} | {v.status} | {v.applicability} | "
                f"{v.mechanism_path or '—'} | {v.declared} |"
            )
    lines.append("")
    return "\n".join(lines)


def build_json(reports: Sequence[DownstreamConformance]) -> dict:
    return {
        "caveat": CAVEAT,
        "downstreams": [
            {
                "name": r.name,
                "path": r.path,
                "brownfield": r.brownfield,
                "summary": {s: r.count(s) for s in _SUMMARY_ORDER},
                "gaps": r.gap_count,
                "practices": [
                    {
                        "practice": v.practice,
                        "title": v.title,
                        "status": v.status,
                        "applicability": v.applicability,
                        "mechanism": v.mechanism_path,
                        "declared": v.declared,
                    }
                    for v in r.verdicts
                ],
            }
            for r in reports
        ],
    }


def default_enablement_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "templates" / "security" / "enablement-matrix.json"


def default_mapping_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "ssdf-mapping.md"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only per-downstream SSDF mechanism-overlay dashboard (NOT an SSDLC certifier)."
    )
    parser.add_argument("--downstream", action="append", default=[], metavar="NAME=PATH",
                        help="A downstream repo to scan (repeatable).")
    parser.add_argument("--template-root", default="", help="Override the template/ source dir.")
    parser.add_argument("--mapping", default="", help="Override docs/ssdf-mapping.md path.")
    parser.add_argument("--enablement", default="", help="Override enablement-matrix.json path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument("--fail-on-gap", action="store_true",
                        help="Exit 2 if any downstream has a not-propagated / drifted / not-overlaid mechanism.")
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
    mapping_path = Path(args.mapping) if args.mapping else default_mapping_path()
    if not mapping_path.is_file():
        print(f"[FAIL] mapping file not found: {mapping_path}", file=sys.stderr)
        return EXIT_ERROR
    enablement_path = Path(args.enablement) if args.enablement else default_enablement_path()
    if not enablement_path.is_file():
        print(f"[FAIL] enablement matrix not found: {enablement_path}", file=sys.stderr)
        return EXIT_ERROR

    rows, parse_errors = parse_mapping(mapping_path)
    if parse_errors:
        for e in parse_errors:
            print(f"[FAIL] mapping parse error: {e}", file=sys.stderr)
        return EXIT_ERROR
    try:
        enablement = load_enablement(enablement_path)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] enablement matrix invalid: {exc}", file=sys.stderr)
        return EXIT_ERROR

    reports: List[DownstreamConformance] = []
    for spec in args.downstream:
        name, path = parse_downstream_arg(spec)
        if not path.is_dir():
            print(f"[FAIL] downstream path does not exist: {path}", file=sys.stderr)
            return EXIT_ERROR
        reports.append(classify_downstream(rows, template_root, path, name, enablement))

    if args.json:
        print(json.dumps(build_json(reports), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(reports))

    if args.fail_on_gap and any(r.has_gap for r in reports):
        return EXIT_GAP
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
