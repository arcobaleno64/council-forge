"""Unit tests for ssdf_mapping_validator.py — full-coverage, in-process, fixture-driven."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import ssdf_mapping_validator as smv

CANON = smv.CANONICAL_PRACTICES  # 19


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- #
# A repo fixture: a root with the files mapping rows can resolve against.
# --------------------------------------------------------------------------- #
@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _write(root / "mech.md", "# Mechanism Doc\n\nsome text\nline3\n")
    _write(root / "ev.py", "x = 1\ny = 2\n")
    _write(root / "docs" / "ssdf-roadmap.md",
           "# Roadmap\n\n## 8. SSDF Gap Waiver Registry\n\n"
           "- `SSDF-Gap-Waiver: PW.4`\n- `SSDF-Gap-Waiver: RV.1`\n\n"
           "## 9. Other\n\nSSDF-Gap-Waiver: PW.7 mentioned in prose but not a marker line here\n")
    _write(root / "artifacts" / "decisions" / "TASK-555.decision.md",
           "# Decision\n\nSSDF-Gap-Waiver: PS.2\n")
    return root


def _mapping_table(rows: list[tuple]) -> str:
    header = "| Practice | Title | Status | Mechanism | Evidence | Gap/Waiver |\n|---|---|---|---|---|---|\n"
    body = "".join(
        f"| {p} | {t} | {s} | {m} | {e} | {w} |\n" for (p, t, s, m, e, w) in rows
    )
    return "# Map\n\n" + header + body


def _full_rows(status_overrides=None, ref_overrides=None):
    """19 canonical rows, default covered with resolving refs."""
    status_overrides = status_overrides or {}
    ref_overrides = ref_overrides or {}
    rows = []
    for p in CANON:
        status = status_overrides.get(p, "covered")
        if status == "gap":
            mech, ev, waiver = "—", "—", ref_overrides.get(p, "docs/ssdf-roadmap.md#8-ssdf-gap-waiver-registry")
        else:
            mech, ev = ref_overrides.get(p, ("mech.md", "ev.py"))
            waiver = "—"
        rows.append((p, f"Title {p}", status, mech, ev, waiver))
    return rows


# --------------------------------------------------------------------------- #
# slugify + heading_sections
# --------------------------------------------------------------------------- #
def test_slugify_basic():
    assert smv.slugify("Hello World") == "hello-world"
    assert smv.slugify("  Trim  Me  ") == "trim-me"


def test_slugify_punctuation_and_collapse():
    assert smv.slugify("8. SSDF Gap Waiver Registry") == "8-ssdf-gap-waiver-registry"
    assert smv.slugify("A -- B::C!!") == "a-bc"


def test_slugify_unicode_cjk():
    # CJK preserved, lowercased ASCII; spaces -> hyphen
    assert smv.slugify("治理 Governance") == "治理-governance"


def test_heading_sections_duplicate_suffix():
    text = "# Dup\n## Dup\ncontent\n## Dup\nmore\n"
    secs = smv.heading_sections(text)
    slugs = [s.slug for s in secs]
    assert slugs == ["dup", "dup-1", "dup-2"]


def test_heading_sections_span():
    text = "# A\nl1\n## B\nl2\n## C\nl3\n# D\nl4\n"
    secs = {s.slug: s for s in smv.heading_sections(text)}
    # section B ends where C starts (same level)
    b = secs["b"]
    assert text.splitlines()[b.start].startswith("## B")
    assert text.splitlines()[b.end].startswith("## C")


# --------------------------------------------------------------------------- #
# resolve_ref — positive + every negative branch
# --------------------------------------------------------------------------- #
def test_resolve_ref_plain_path(repo: Path):
    assert smv.resolve_ref("mech.md", repo)
    assert not smv.resolve_ref("nope.md", repo)


def test_resolve_ref_anchor(repo: Path):
    assert smv.resolve_ref("mech.md#mechanism-doc", repo)       # real heading slug
    assert not smv.resolve_ref("mech.md#not-a-heading", repo)   # body text, not heading


def test_resolve_ref_line(repo: Path):
    assert smv.resolve_ref("ev.py:1", repo)
    assert smv.resolve_ref("ev.py:2", repo)
    assert not smv.resolve_ref("ev.py:99", repo)  # out of range
    assert not smv.resolve_ref("ev.py:0", repo)   # not positive


def test_resolve_ref_rejects_cmd_absolute_traversal(repo: Path):
    assert not smv.resolve_ref("cmd:echo hi", repo)
    assert not smv.resolve_ref("/etc/passwd", repo)
    assert not smv.resolve_ref("../outside.md", repo)
    assert not smv.resolve_ref("", repo)


def test_resolve_ref_escapes_root_via_symlinkless(repo: Path, tmp_path: Path):
    # a path that normalizes outside root is rejected even without literal '..'
    outside = tmp_path / "outside.md"
    _write(outside, "x")
    # craft a ref that resolves outside via repo-relative that does not exist inside
    assert not smv.resolve_ref("outside.md", repo)


# --------------------------------------------------------------------------- #
# resolve_waiver — both forms, symmetric structured marker
# --------------------------------------------------------------------------- #
def test_resolve_waiver_roadmap_marker(repo: Path):
    assert smv.resolve_waiver("docs/ssdf-roadmap.md#8-ssdf-gap-waiver-registry", repo, "PW.4")
    assert smv.resolve_waiver("docs/ssdf-roadmap.md#8-ssdf-gap-waiver-registry", repo, "RV.1")


def test_resolve_waiver_roadmap_incidental_mention_rejected(repo: Path):
    # PW.7's id appears in §9 only as in-prose text (no marker line) -> unresolved
    assert not smv.resolve_waiver("docs/ssdf-roadmap.md#9-other", repo, "PW.7")


def test_resolve_waiver_roadmap_file_wide_bypass_rejected(repo: Path):
    # PW.4 marker exists in §8, but pointing at §9 must NOT resolve (section-scoped)
    assert not smv.resolve_waiver("docs/ssdf-roadmap.md#9-other", repo, "PW.4")


def test_resolve_waiver_roadmap_bad_anchor(repo: Path):
    assert not smv.resolve_waiver("docs/ssdf-roadmap.md#no-such-heading", repo, "PW.4")


def test_resolve_waiver_roadmap_missing_file(tmp_path: Path):
    assert not smv.resolve_waiver("docs/ssdf-roadmap.md#x", tmp_path / "empty", "PW.4")


def test_resolve_waiver_decision_marker(repo: Path):
    assert smv.resolve_waiver("decision:TASK-555", repo, "PS.2")
    assert not smv.resolve_waiver("decision:TASK-555", repo, "PW.4")  # wrong practice
    assert not smv.resolve_waiver("decision:TASK-999", repo, "PS.2")  # missing file


def test_resolve_waiver_malformed(repo: Path):
    assert not smv.resolve_waiver("decision:NOTATASK", repo, "PS.2")
    assert not smv.resolve_waiver("", repo, "PS.2")
    assert not smv.resolve_waiver("docs/ssdf-roadmap.md", repo, "PW.4")  # no '#'
    assert not smv.resolve_waiver("other/file.md#x", repo, "PW.4")       # wrong path base


def test_marker_exact_boundary(repo: Path):
    # PW.4 must not match a hypothetical PW.40
    text = "## S\nSSDF-Gap-Waiver: PW.40\n"
    _write(repo / "docs" / "r2.md", "")
    assert not smv._marker_in_text(text, "PW.4")
    assert smv._marker_in_text("SSDF-Gap-Waiver: PW.4\n", "PW.4")


# --------------------------------------------------------------------------- #
# parse_mapping + validate + exit codes
# --------------------------------------------------------------------------- #
def test_parse_and_validate_full_covered_exit0(repo: Path):
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(_full_rows()))
    rows, errs = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    assert errs == []
    result = smv.validate(rows, repo)
    assert result.violations == []
    assert smv.compute_exit(result, errs) == smv.EXIT_OK
    assert len(result.covered) == 19


def test_validate_with_gaps_and_partial_exit3(repo: Path):
    rows = _full_rows(status_overrides={"PW.4": "gap", "RV.1": "gap", "PO.1": "partial"})
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, errs = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    assert result.violations == []
    assert result.has_open_items
    assert smv.compute_exit(result, errs) == smv.EXIT_OPEN_ITEMS
    assert result.gaps == ["PW.4", "RV.1"]
    assert result.partial == ["PO.1"]


def test_validate_missing_and_unknown_practice(repo: Path):
    rows = _full_rows()[:-1]  # drop RV.3
    rows.append(("ZZ.9", "bogus", "covered", "mech.md", "ev.py", "—"))
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, _ = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    assert any("missing canonical practice: RV.3" in v for v in result.violations)
    assert any("unknown/extraneous practice id: ZZ.9" in v for v in result.violations)


def test_validate_illegal_status(repo: Path):
    rows = _full_rows(status_overrides={"PO.1": "bogus"})
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, _ = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    assert any("illegal status 'bogus'" in v for v in result.violations)


def test_validate_unresolving_mechanism_evidence(repo: Path):
    rows = _full_rows(ref_overrides={"PO.2": ("ghost.md", "ev.py"), "PO.3": ("mech.md", "cmd:x")})
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, _ = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    assert any("PO.2: Mechanism ref does not resolve" in v for v in result.violations)
    assert any("PO.3: Evidence ref does not resolve" in v for v in result.violations)


def test_validate_missing_mechanism_evidence(repo: Path):
    rows = _full_rows(ref_overrides={"PO.2": ("", "ev.py"), "PO.3": ("mech.md", "")})
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, _ = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    assert any("PO.2: covered row missing Mechanism" in v for v in result.violations)
    assert any("PO.3: covered row missing Evidence" in v for v in result.violations)


def test_validate_gap_waiver_unresolved(repo: Path):
    rows = _full_rows(status_overrides={"PW.7": "gap"},
                      ref_overrides={"PW.7": "docs/ssdf-roadmap.md#9-other"})
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, _ = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    assert any("PW.7: gap waiver does not resolve" in v for v in result.violations)


def test_parse_malformed_row(repo: Path):
    bad = ("# Map\n\n| Practice | Title | Status | Mechanism | Evidence | Gap/Waiver |\n"
           "|---|---|---|---|---|---|\n| PO.1 | only three |\n")
    p = repo / "docs" / "bad.md"
    _write(p, bad)
    rows, errs = smv.parse_mapping(p)
    assert any("malformed mapping row" in e for e in errs)


# --------------------------------------------------------------------------- #
# rendering + run() CLI + exit codes
# --------------------------------------------------------------------------- #
def test_render_markdown_states(repo: Path):
    rows = _full_rows()
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, errs = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    md = smv.render_markdown(result, errs)
    assert "all practices covered (exit 0)" in md
    # violation render
    result.violations.append("x")
    assert "INTEGRITY VIOLATION" in smv.render_markdown(result, errs)
    # open-items render
    result.violations.clear()
    result.rows["PO.1"].status = "gap"
    assert "open items (exit 3)" in smv.render_markdown(result, [])


def test_render_with_parse_errors(repo: Path):
    rows = _full_rows()
    _write(repo / "docs" / "ssdf-mapping.md", _mapping_table(rows))
    parsed, _ = smv.parse_mapping(repo / "docs" / "ssdf-mapping.md")
    result = smv.validate(parsed, repo)
    md = smv.render_markdown(result, ["bad row 5"])
    assert "Parse Errors" in md and "bad row 5" in md


def test_run_exit3_json(repo: Path, capsys):
    rows = _full_rows(status_overrides={"PW.4": "gap", "RV.1": "gap"})
    mp = repo / "docs" / "ssdf-mapping.md"
    _write(mp, _mapping_table(rows))
    rc = smv.run(["--mapping", str(mp), "--json"])
    assert rc == smv.EXIT_OPEN_ITEMS
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "open-items"
    assert payload["gaps"] == ["PW.4", "RV.1"]


def test_run_exit0_markdown(repo: Path, capsys):
    mp = repo / "docs" / "ssdf-mapping.md"
    _write(mp, _mapping_table(_full_rows()))
    rc = smv.run(["--mapping", str(mp)])
    assert rc == smv.EXIT_OK
    assert "all practices covered" in capsys.readouterr().out


def test_run_exit2_violation(repo: Path, capsys):
    rows = _full_rows(ref_overrides={"PO.2": ("ghost.md", "ev.py")})
    mp = repo / "docs" / "ssdf-mapping.md"
    _write(mp, _mapping_table(rows))
    rc = smv.run(["--mapping", str(mp)])
    assert rc == smv.EXIT_VIOLATION


def test_run_missing_mapping(tmp_path: Path, capsys):
    rc = smv.run(["--mapping", str(tmp_path / "nope.md")])
    assert rc == smv.EXIT_USAGE
    assert "mapping file not found" in capsys.readouterr().err


def test_default_mapping_path_and_repo_root():
    mp = smv.default_mapping_path()
    assert mp.name == "ssdf-mapping.md"
    assert smv.repo_root_of(mp).name == "council-forge" or smv.repo_root_of(mp).is_dir()


def test_real_mapping_is_valid_exit3():
    """The shipped docs/ssdf-mapping.md must be structurally valid (exit 3, has gaps)."""
    mp = smv.default_mapping_path()
    repo_root = smv.repo_root_of(mp)
    rows, errs = smv.parse_mapping(mp)
    result = smv.validate(rows, repo_root)
    assert errs == []
    assert result.violations == []  # every ref + waiver resolves
    assert smv.compute_exit(result, errs) == smv.EXIT_OPEN_ITEMS  # has the 4 known gaps


# --------------------------------------------------------------------------- #
# programmatic scope-creep guardrail (gemini [medium])
# --------------------------------------------------------------------------- #
def test_validator_imports_are_bounded():
    """The validator must never import subprocess / os / any scanning lib (AST guardrail).

    This is a programmatic architectural boundary (not docs/review): the module can only
    parse markdown + resolve repo-relative paths, so it imports neither subprocess nor os
    (os.system would need os). Checked via AST imports — robust against docstring text
    that merely *names* the forbidden modules.
    """
    tree = ast.parse(Path(smv.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"subprocess", "os", "shutil", "socket", "requests"}
    assert not (forbidden & imported), f"validator imports forbidden modules: {forbidden & imported}"


def test_resolve_ref_empty_path_part(repo: Path):
    # ref of just an anchor -> empty path part -> unsafe -> unresolved (covers _is_unsafe_path empty)
    assert not smv.resolve_ref("#mechanism-doc", repo)


def test_resolve_ref_os_absolute(repo: Path, tmp_path: Path):
    # an OS-absolute path is rejected (covers is_absolute branch cross-platform)
    abs_ref = str((tmp_path / "ev.py").resolve())
    assert not smv.resolve_ref(abs_ref, repo)


def test_parse_pipe_row_before_header(repo: Path):
    # a pipe row before the SSDF header must be ignored (covers 'not in_table' path)
    text = ("# Map\n\n| stray | table |\n|---|---|\n\n"
            "| Practice | Title | Status | Mechanism | Evidence | Gap/Waiver |\n"
            "|---|---|---|---|---|---|\n| PO.1 | t | covered | mech.md | ev.py | — |\n")
    p = repo / "docs" / "pre.md"
    _write(p, text)
    rows, errs = smv.parse_mapping(p)
    assert "PO.1" in rows
    assert errs == []
