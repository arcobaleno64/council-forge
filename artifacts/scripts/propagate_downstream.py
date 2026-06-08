#!/usr/bin/env python3
"""propagate_downstream.py — push council-forge SSOT updates into downstream repos.

The mutating complement of drift_dashboard.py. When the source template/ evolves
(a guard fix, a schema update, a prompt tweak), this refreshes the downstream's copy
of the affected council-forge-owned governance files so the downstream stays in sync
with the SSOT — WITHOUT ever touching the project's own files.

Release-integrity (PS.2) safety model (P8-D2):
- DRY-RUN BY DEFAULT. ``--apply`` is required to write anything.
- ``--apply`` is a TWO-PHASE, fail-closed operation:
    (I) PREFLIGHT, before ANY file is written, for ALL targets:
        * the source template/ tree MUST match the published release manifest
          (``.well-known/release-manifest.json``); a mismatch / missing manifest -> refuse
          (run snapshot_manifest.py generate first). There is NO ``--skip`` bypass.
        * each target's durable snapshot marker (``.council-forge/release-snapshot.json``)
          must be absent or a valid council-forge release-snapshot — a malformed / foreign
          file there fails closed WITHOUT overwriting (no clobbering a downstream's own file).
      Any preflight failure aborts before a single byte is written (no partial application
      from a detectable cause).
    (II) APPLY, only if every target passed preflight:
        * each content file is copied PER-FILE ATOMICALLY (copy2 -> temp in the same dir ->
          os.replace), so an interruption never leaves a half-written / corrupted file;
        * a durable ``.council-forge/release-snapshot.json`` is written atomically, recording
          the released snapshot root + the propagated files' digests, so the acquirer durably
          holds the verifier for the snapshot it received (PS.2.1).
  HONESTY BOUNDARY: this does NOT provide cross-repo / cross-file transactional atomicity. A
  mid-apply I/O interruption can leave a downstream with SOME files updated (each individually
  intact) and others not. That state is benign and recoverable WITHOUT a bespoke rollback: the
  downstream is a git repo (git diff/checkout) and the operation is idempotent (re-run
  completes it) and manifest-verifiable. A full cross-target staged-transaction rollback is a
  defined follow-up, not implemented here (it would re-implement git for git-tracked output).

Source-only (a downstream terminal repo never propagates onward), so NOT mirrored into
template/ and NOT in EXACT_SYNC_FILES — same discipline as scaffold_downstream.py /
drift_dashboard.py / snapshot_manifest.py.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from drift_dashboard import (
    DRIFTED,
    MISSING,
    classify_downstream,
    default_template_root,
    parse_downstream_arg,
    template_has_placeholder,
)
from snapshot_manifest import ALGORITHM, compute_manifest, diff_manifest, sha256_file

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1

# The durable per-snapshot marker written into each downstream (PS.2.1 "available to
# acquirers"). Its own schema const lets us tell a council-forge-owned marker from a
# coincidental same-path file and refuse to clobber the latter.
MARKER_REL = ".council-forge/release-snapshot.json"
MARKER_SCHEMA = "council-forge/release-snapshot@1"

# Where council-forge publishes the manifest of its propagated template/ snapshot.
PUBLISHED_MANIFEST_REL = Path(".well-known") / "release-manifest.json"


@dataclass
class PropagationPlan:
    name: str
    path: str
    refresh: List[str] = field(default_factory=list)        # drifted -> overwrite from template
    add: List[str] = field(default_factory=list)            # missing (non-placeholder) -> restore
    skipped_placeholder: List[str] = field(default_factory=list)  # missing but placeholder -> manual
    applied: bool = False
    propagated: List[dict] = field(default_factory=list)    # [{path, sha256}] actually written
    released_root: Optional[str] = None

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


def atomic_copy(src: Path, dst: Path) -> None:
    """Copy src -> dst atomically: write a temp in dst's dir, then os.replace (same volume)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / (dst.name + ".cf-tmp")
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_text(dst: Path, text: str) -> None:
    """Write text -> dst atomically (temp in dst's dir, then os.replace)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / (dst.name + ".cf-tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def apply_plan(template_root: Path, downstream_root: Path, plan: PropagationPlan) -> None:
    """Per-file ATOMIC copy template -> downstream for every refreshed/added file. Mutating."""
    propagated: List[dict] = []
    for rel in plan.refresh + plan.add:
        src = template_root / rel
        atomic_copy(src, downstream_root / rel)
        propagated.append({"path": rel, "sha256": sha256_file(src)})
    plan.propagated = sorted(propagated, key=lambda entry: entry["path"])
    plan.applied = True


def check_marker_ownership(downstream_root: Path) -> Optional[str]:
    """Return an error if an existing snapshot marker is NOT a council-forge release-snapshot.

    Absent -> None (we will create it). A valid council-forge marker -> None (we will update
    it). A malformed / foreign file at that path -> error (refuse to clobber a downstream file).
    """
    marker = downstream_root / MARKER_REL
    if not marker.exists():
        return None
    try:
        existing = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return f"existing {MARKER_REL} is malformed/unreadable — refusing to overwrite a non-council-forge file"
    if not (isinstance(existing, dict) and existing.get("schema") == MARKER_SCHEMA):
        return f"existing {MARKER_REL} is not a council-forge release-snapshot — refusing to overwrite"
    return None


def write_marker(downstream_root: Path, released_root: Optional[str], propagated: List[dict]) -> None:
    """Atomically write the durable per-snapshot marker into the downstream."""
    marker = {
        "schema": MARKER_SCHEMA,
        "released_snapshot_root": released_root,
        "algorithm": ALGORITHM,
        "propagated": propagated,
    }
    atomic_write_text(downstream_root / MARKER_REL, json.dumps(marker, indent=2, ensure_ascii=False) + "\n")


def preflight_manifest(template_root: Path):
    """Verify the source tree matches the published manifest. Returns (error, released_root)."""
    published_path = template_root.parent / PUBLISHED_MANIFEST_REL
    if not published_path.is_file():
        return (f"published manifest not found: {published_path} — run snapshot_manifest.py generate", None)
    try:
        published = json.loads(published_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (f"cannot read published manifest: {exc}", None)
    if not isinstance(published, dict):
        return ("published manifest is not a JSON object", None)
    if diff_manifest(published, compute_manifest(template_root)):
        return ("published manifest does not match the template snapshot — run snapshot_manifest.py generate", None)
    return (None, published.get("root"))


def render_markdown(plans: Sequence[PropagationPlan], apply: bool, released_root: Optional[str] = None) -> str:
    verb = "Applied" if apply else "Would change (dry-run)"
    lines: List[str] = ["# council-forge Downstream Propagation", "", f"Mode: {verb}", ""]
    if apply and released_root:
        lines.append(f"Released snapshot root: `{released_root}`")
        lines.append("")
    lines.append("| Downstream | refresh | add | skipped-placeholder |")
    lines.append("|---|---:|---:|---:|")
    for plan in plans:
        lines.append(f"| {plan.name} | {len(plan.refresh)} | {len(plan.add)} | {len(plan.skipped_placeholder)} |")
    for plan in plans:
        if not (plan.refresh or plan.add or plan.skipped_placeholder):
            continue
        lines.append("")
        lines.append(f"## {plan.name}")
        for label, items in (("refresh", plan.refresh), ("add", plan.add), ("skipped-placeholder", plan.skipped_placeholder)):
            if items:
                lines.append(f"### {label} ({len(items)})")
                lines.extend(f"- {rel}" for rel in items)
    lines.append("")
    return "\n".join(lines)


def build_json(plans: Sequence[PropagationPlan], apply: bool, released_root: Optional[str] = None) -> dict:
    return {
        "mode": "apply" if apply else "dry-run",
        "released_snapshot_root": released_root,
        "downstreams": [
            {
                "name": plan.name,
                "path": plan.path,
                "applied": plan.applied,
                "refresh": plan.refresh,
                "add": plan.add,
                "skipped_placeholder": plan.skipped_placeholder,
            }
            for plan in plans
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

    targets = []  # (downstream_root, plan)
    for spec in args.downstream:
        name, path = parse_downstream_arg(spec)
        if not path.is_dir():
            print(f"[FAIL] downstream path does not exist: {path}", file=sys.stderr)
            return EXIT_ERROR
        targets.append((path, plan_propagation(template_root, path, name, args.add_missing)))

    released_root: Optional[str] = None
    if args.apply:
        # (I) PREFLIGHT — before any write, for all targets. Any failure aborts cleanly.
        manifest_error, released_root = preflight_manifest(template_root)
        if manifest_error is not None:
            print(f"[FAIL] {manifest_error}", file=sys.stderr)
            return EXIT_ERROR
        for downstream_root, plan in targets:
            marker_error = check_marker_ownership(downstream_root)
            if marker_error is not None:
                print(f"[FAIL] {plan.name}: {marker_error}", file=sys.stderr)
                return EXIT_ERROR
        # (II) APPLY — every target passed preflight.
        for downstream_root, plan in targets:
            apply_plan(template_root, downstream_root, plan)
            write_marker(downstream_root, released_root, plan.propagated)
            plan.released_root = released_root

    plans = [plan for _, plan in targets]
    if args.json:
        print(json.dumps(build_json(plans, args.apply, released_root), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(plans, args.apply, released_root))
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
