#!/usr/bin/env python3
"""scaffold_downstream.py — one-stop generator for council-forge downstream terminal repos.

Turns the manual BOOTSTRAP_PROMPT.md procedure into a single, deterministic,
idempotent command:

    copy template/ -> scoped placeholder substitution -> mark downstream
    (no .council-forge-source-repo) -> refresh repository profile ->
    run the downstream-mode guard chain -> report.

Source-only tool: a downstream *terminal* repo never regenerates further repos,
so this script is intentionally NOT mirrored into template/ and is NOT part of
EXACT_SYNC_FILES. It lives only in the source template repo (council-forge).

Placeholder discipline (see TASK-1072): the substitution map contains ONLY the
project-instantiation keys. Per-task template keys ({{TASK_ID}}, {{NNNN}},
{{TITLE}}, {{N}}, {{INCIDENT_ID}}) are never in the map, so they survive
untouched. Files whose basename starts with ``test_`` and ends in ``.py`` are
skipped entirely because they embed instantiation keys as literal test fixtures.
After substitution a post-check scans every non-skipped file for any remaining
instantiation placeholder and fails loudly rather than emitting a downstream repo
with a literal ``{{ORG}}`` in it.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Project-instantiation keys, resolved ONCE at scaffold time. Per-task template
# keys are deliberately absent so they survive substitution.
INSTANTIATION_KEYS: Tuple[str, ...] = (
    "PROJECT_NAME",
    "REPO_NAME",
    "REPO",
    "ORG",
    "UPSTREAM_ORG",
    "AUTHOR",
    "YEAR",
)

SOURCE_REPO_SENTINEL = ".council-forge-source-repo"

LEFTOVER_RE = re.compile(r"\{\{(" + "|".join(INSTANTIATION_KEYS) + r")\}\}")

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_TARGET_NOT_EMPTY = 2
EXIT_LEFTOVER_PLACEHOLDER = 3
EXIT_GUARD_FAILED = 4


@dataclass
class ScaffoldConfig:
    target: Path
    template_root: Path
    project_name: str
    repo_name: str
    project_summary: str
    owner: str
    upstream_org: str
    author: str
    year: str
    topics: Optional[str] = None
    git_init: bool = False
    force: bool = False


@dataclass
class ScaffoldResult:
    target: Path
    copied_files: int = 0
    substituted_files: int = 0
    leftovers: Dict[str, List[str]] = field(default_factory=dict)
    guard_results: Dict[str, int] = field(default_factory=dict)

    @property
    def has_leftovers(self) -> bool:
        return bool(self.leftovers)

    @property
    def guards_ok(self) -> bool:
        return all(code == 0 for code in self.guard_results.values())


def build_substitution_map(config: ScaffoldConfig) -> Dict[str, str]:
    """Map ``{{KEY}}`` -> value for every instantiation key. Pure."""
    values = {
        "PROJECT_NAME": config.project_name,
        "REPO_NAME": config.repo_name,
        "REPO": config.repo_name,
        "ORG": config.owner,
        "UPSTREAM_ORG": config.upstream_org,
        "AUTHOR": config.author,
        "YEAR": config.year,
    }
    return {f"{{{{{key}}}}}": values[key] for key in INSTANTIATION_KEYS}


def is_text_file(path: Path) -> bool:
    """Return True if the file decodes as UTF-8 (treat decode failure as binary)."""
    try:
        path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return True


def should_substitute(path: Path) -> bool:
    """A file is substitution-eligible unless it is a ``test_*.py`` fixture or binary."""
    if path.name.startswith("test_") and path.suffix == ".py":
        return False
    return is_text_file(path)


def substitute_text(text: str, mapping: Dict[str, str]) -> str:
    """Replace every instantiation placeholder. Per-task keys are not in the map. Pure."""
    for placeholder, value in mapping.items():
        text = text.replace(placeholder, value)
    return text


def find_leftover_instantiation_keys(text: str) -> List[str]:
    """Return the sorted set of instantiation keys still present as ``{{KEY}}``. Pure."""
    return sorted({match.group(1) for match in LEFTOVER_RE.finditer(text)})


def iter_files(root: Path) -> List[Path]:
    """All regular files under root (sorted for determinism)."""
    return sorted(p for p in root.rglob("*") if p.is_file())


def copy_template(template_root: Path, target: Path, force: bool) -> int:
    """Copy the template tree into target. Returns the copied file count.

    Refuses a non-empty existing target unless ``force`` is set.
    """
    if not template_root.is_dir():
        raise FileNotFoundError(f"template_root does not exist: {template_root}")
    if target.exists() and any(target.iterdir()):
        if not force:
            raise FileExistsError(
                f"target is not empty: {target} (pass force=True to overwrite)"
            )
        shutil.rmtree(target)
    shutil.copytree(template_root, target)
    return len(iter_files(target))


def apply_substitutions(
    target: Path, mapping: Dict[str, str]
) -> Tuple[int, Dict[str, List[str]]]:
    """Substitute instantiation keys in every eligible file under target.

    Returns ``(substituted_file_count, leftovers)`` where ``leftovers`` maps a
    POSIX-relative path to the list of instantiation keys still present.
    """
    substituted = 0
    leftovers: Dict[str, List[str]] = {}
    for path in iter_files(target):
        if not should_substitute(path):
            continue
        original = path.read_text(encoding="utf-8")
        updated = substitute_text(original, mapping)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            substituted += 1
        remaining = find_leftover_instantiation_keys(updated)
        if remaining:
            leftovers[path.relative_to(target).as_posix()] = remaining
    return substituted, leftovers


def run_repository_profile(config: ScaffoldConfig) -> int:
    """Refresh the downstream repo's .github/repository-profile.json via its own tool."""
    script = config.target / "artifacts" / "scripts" / "update_repository_profile.py"
    profile_path = config.target / ".github" / "repository-profile.json"
    cmd = [
        sys.executable,
        str(script),
        "--project-name",
        config.project_name,
        "--project-summary",
        config.project_summary,
        "--profile-path",
        str(profile_path),
    ]
    if config.topics:
        cmd += ["--topics", config.topics]
    return subprocess.run(cmd, cwd=config.target).returncode


def run_downstream_guards(target: Path) -> Dict[str, int]:
    """Run the downstream repo's own guard chain (downstream mode auto-detected)."""
    scripts = target / "artifacts" / "scripts"
    invocations = {
        "contract": [sys.executable, str(scripts / "guard_contract_validator.py"), "--root", str(target)],
        "prompt_regression": [sys.executable, str(scripts / "prompt_regression_validator.py"), "--root", str(target)],
    }
    results: Dict[str, int] = {}
    for name, cmd in invocations.items():
        results[name] = subprocess.run(cmd, cwd=target).returncode
    return results


def git_init(target: Path) -> int:
    """Initialise a git repo in target (some guards use git for scope evidence)."""
    return subprocess.run(["git", "init", str(target)]).returncode


def scaffold(config: ScaffoldConfig) -> ScaffoldResult:
    """Orchestrate the full greenfield scaffold against config.target."""
    result = ScaffoldResult(target=config.target)
    result.copied_files = copy_template(config.template_root, config.target, config.force)

    sentinel = config.target / SOURCE_REPO_SENTINEL
    if sentinel.exists():  # defensive: template must never carry the source marker
        sentinel.unlink()

    mapping = build_substitution_map(config)
    result.substituted_files, result.leftovers = apply_substitutions(config.target, mapping)
    if result.has_leftovers:
        return result  # caller maps this to EXIT_LEFTOVER_PLACEHOLDER

    run_repository_profile(config)
    if config.git_init:
        git_init(config.target)
    result.guard_results = run_downstream_guards(config.target)
    return result


def dry_run_preview(template_root: Path, mapping: Dict[str, str]) -> Tuple[int, int]:
    """Report how many files would be copied / substituted, writing nothing."""
    files = iter_files(template_root)
    would_substitute = 0
    for path in files:
        if not should_substitute(path):
            continue
        text = path.read_text(encoding="utf-8")
        if substitute_text(text, mapping) != text:
            would_substitute += 1
    return len(files), would_substitute


def default_template_root() -> Path:
    """The template/ directory of the source repo this script ships in."""
    return Path(__file__).resolve().parents[2] / "template"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a council-forge downstream terminal repo from template/."
    )
    parser.add_argument("--target", required=True, help="Target root for the new downstream repo.")
    parser.add_argument("--project-name", required=True, help="{{PROJECT_NAME}} value.")
    parser.add_argument("--repo-name", required=True, help="{{REPO_NAME}} / {{REPO}} value.")
    parser.add_argument("--project-summary", required=True, help="One-line summary for the repo profile.")
    parser.add_argument("--owner", default="", help="GitHub owner -> {{ORG}} (default: --upstream-org).")
    parser.add_argument("--upstream-org", default="", help="{{UPSTREAM_ORG}} (default: --owner).")
    parser.add_argument("--author", default="", help="{{AUTHOR}} (default: --owner, then --project-name).")
    parser.add_argument("--year", default="", help="{{YEAR}} (default: current year).")
    parser.add_argument("--topics", default=None, help="Optional comma-separated repo topics.")
    parser.add_argument("--template-root", default="", help="Override the template/ source dir.")
    parser.add_argument("--git-init", action="store_true", help="git init the target after scaffold.")
    parser.add_argument("--force", action="store_true", help="Overwrite a non-empty target.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing or running guards.")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> ScaffoldConfig:
    """Resolve the default chains (owner -> upstream_org -> author; year=now)."""
    owner = args.owner or args.upstream_org
    upstream_org = args.upstream_org or args.owner
    author = args.author or owner or args.project_name
    year = args.year or str(datetime.now().year)
    template_root = Path(args.template_root) if args.template_root else default_template_root()
    return ScaffoldConfig(
        target=Path(args.target),
        template_root=template_root,
        project_name=args.project_name,
        repo_name=args.repo_name,
        project_summary=args.project_summary,
        owner=owner,
        upstream_org=upstream_org,
        author=author,
        year=year,
        topics=args.topics,
        git_init=args.git_init,
        force=args.force,
    )


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config = config_from_args(args)
    mapping = build_substitution_map(config)

    if args.dry_run:
        total, would_sub = dry_run_preview(config.template_root, mapping)
        print(f"[DRY-RUN] template={config.template_root}")
        print(f"[DRY-RUN] would copy {total} files; would substitute {would_sub} files")
        print(f"[DRY-RUN] target {config.target} NOT created")
        return EXIT_OK

    if config.target.exists() and any(config.target.iterdir()) and not config.force:
        print(f"[FAIL] target is not empty: {config.target} (use --force to overwrite)", file=sys.stderr)
        return EXIT_TARGET_NOT_EMPTY

    result = scaffold(config)
    print(f"[OK] copied {result.copied_files} files into {result.target}")
    print(f"[OK] substituted instantiation placeholders in {result.substituted_files} files")

    if result.has_leftovers:
        print("[FAIL] unresolved instantiation placeholders remain:", file=sys.stderr)
        for rel_path, keys in sorted(result.leftovers.items()):
            print(f"  {rel_path}: {', '.join('{{' + k + '}}' for k in keys)}", file=sys.stderr)
        print("Supply the missing --owner/--upstream-org/--author/--year arguments.", file=sys.stderr)
        return EXIT_LEFTOVER_PLACEHOLDER

    for name, code in result.guard_results.items():
        status = "OK" if code == 0 else "FAIL"
        print(f"[{status}] downstream guard '{name}' exit={code}")

    if not result.guards_ok:
        return EXIT_GUARD_FAILED
    return EXIT_OK


def main() -> int:  # pragma: no cover - thin CLI glue
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
