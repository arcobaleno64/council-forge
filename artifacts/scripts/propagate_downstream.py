#!/usr/bin/env python3
"""propagate_downstream.py — push council-forge SSOT updates into downstream repos.

The mutating complement of drift_dashboard.py. When the source template/ evolves
(a guard fix, a schema update, a prompt tweak), this refreshes the downstream's copy
of the affected council-forge-owned governance files so the downstream stays in sync
with the SSOT — WITHOUT ever touching the project's own files.

Safety model:
- DRY-RUN BY DEFAULT. It writes nothing and only reports what *would* change. Pass
  ``--apply`` to actually copy template -> downstream.
- It acts ONLY on files drift_dashboard classifies as ``drifted`` (and, with
  ``--add-missing``, ``missing``). By that classification it can NEVER touch:
    * project-owned files (not in the template at all),
    * brownfield-owned files (the project's own CLAUDE/README/AGENTS.md/.gitignore),
    * instantiated files (template files carrying {{PLACEHOLDER}}s),
    * optional-absent files (README.zh-TW / LICENSE / TASK-9xx seeds / council-forge
      workflows that the downstream intentionally pruned — these are NEVER re-added).
- ``--add-missing`` restores only non-placeholder missing files; a missing file whose
  template carries placeholders is skipped (copying it raw would leave literal
  ``{{PLACEHOLDER}}`` in the downstream) and reported for manual re-scaffold.

Source-only (a downstream terminal repo never propagates onward), so NOT mirrored into
template/ and NOT in EXACT_SYNC_FILES — same discipline as scaffold_downstream.py /
drift_dashboard.py. Reuses drift_dashboard's classifier rather than re-deriving drift.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from drift_dashboard import (
    DRIFTED,
    MISSING,
    classify_downstream,
    default_template_root,
    parse_downstream_arg,
    template_has_placeholder,
)

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1


@dataclass
class PropagationPlan:
    name: str
    path: str
    refresh: List[str] = field(default_factory=list)        # drifted -> overwrite from template
    add: List[str] = field(default_factory=list)            # missing (non-placeholder) -> restore
    skipped_placeholder: List[str] = field(default_factory=list)  # missing but placeholder -> manual
    applied: bool = False

    @property
    def change_count(self) -> int:
        return len(self.refresh) + len(self.add)


def plan_propagation(
    template_root: Path, downstream_root: Path, name: str, add_missing: bool
) -> PropagationPlan:
    """Compute (but do not apply) what propagation would change for one downstream."""
    report = classify_downstream(template_root, downstream_root, name)
    plan = PropagationPlan(name=name, path=str(downstream_root))
    plan.refresh = list(report.verdicts.get(DRIFTED, []))
    if add_missing:
        for rel in report.verdicts.get(MISSING, []):
            if template_has_placeholder(template_root / rel):
                plan.skipped_placeholder.append(rel)
            else:
                plan.add.append(rel)
    return plan


def apply_plan(template_root: Path, downstream_root: Path, plan: PropagationPlan) -> None:
    """Copy template -> downstream for every file the plan refreshes or adds. Mutating."""
    for rel in plan.refresh + plan.add:
        src = template_root / rel
        dst = downstream_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    plan.applied = True


def render_markdown(plans: Sequence[PropagationPlan], apply: bool) -> str:
    verb = "Applied" if apply else "Would change (dry-run)"
    lines: List[str] = ["# council-forge Downstream Propagation", "", f"Mode: {verb}", ""]
    lines.append("| Downstream | refresh | add | skipped-placeholder |")
    lines.append("|---|---:|---:|---:|")
    for p in plans:
        lines.append(f"| {p.name} | {len(p.refresh)} | {len(p.add)} | {len(p.skipped_placeholder)} |")
    for p in plans:
        if not (p.refresh or p.add or p.skipped_placeholder):
            continue
        lines.append("")
        lines.append(f"## {p.name}")
        for label, items in (("refresh", p.refresh), ("add", p.add), ("skipped-placeholder", p.skipped_placeholder)):
            if items:
                lines.append(f"### {label} ({len(items)})")
                lines.extend(f"- {rel}" for rel in items)
    lines.append("")
    return "\n".join(lines)


def build_json(plans: Sequence[PropagationPlan], apply: bool) -> dict:
    return {
        "mode": "apply" if apply else "dry-run",
        "downstreams": [
            {
                "name": p.name,
                "path": p.path,
                "applied": p.applied,
                "refresh": p.refresh,
                "add": p.add,
                "skipped_placeholder": p.skipped_placeholder,
            }
            for p in plans
        ],
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Propagate council-forge SSOT updates into downstream repos (dry-run by default)."
    )
    parser.add_argument("--downstream", action="append", default=[], metavar="NAME=PATH",
                        help="A downstream repo to update (repeatable).")
    parser.add_argument("--template-root", default="", help="Override the template/ source dir.")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry-run).")
    parser.add_argument("--add-missing", action="store_true",
                        help="Also restore non-placeholder council-forge-owned files that are missing.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
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

    plans: List[PropagationPlan] = []
    for spec in args.downstream:
        name, path = parse_downstream_arg(spec)
        if not path.is_dir():
            print(f"[FAIL] downstream path does not exist: {path}", file=sys.stderr)
            return EXIT_ERROR
        plan = plan_propagation(template_root, path, name, args.add_missing)
        if args.apply:
            apply_plan(template_root, path, plan)
        plans.append(plan)

    if args.json:
        print(json.dumps(build_json(plans, args.apply), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(plans, args.apply))
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
