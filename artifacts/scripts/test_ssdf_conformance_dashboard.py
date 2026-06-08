"""Unit tests for ssdf_conformance_dashboard.py — full-coverage, in-process, fixture-driven.

Honesty-focused: the core assertions prove the dashboard never conflates mechanism
presence with practice enforcement (no `covered`), that `declared` NEVER overrides the
actual overlay `status`, that all 6 classify_file verdicts map explicitly (unknown ->
hard fail), and that the optional-absent council-forge-workflow case is honestly counted
as a gap rather than silently ignored.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import ssdf_conformance_dashboard as dc
from ssdf_mapping_validator import CANONICAL_SET
from scaffold_downstream import iter_files


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


_MAPPING_ROWS = [
    # practice, title, status, mechanism, evidence, waiver
    ("P.OVL", "Overlaid", "covered", "mech_ovl.py", "ev.md", "-"),
    ("P.DRIFT", "Drifted", "covered", "mech_drift.py", "ev.md", "-"),
    ("P.MISS", "Missing", "covered", "mech_miss.py", "ev.md", "-"),
    ("PS.1", "SourceOnly", "covered", "source_only.py", "ev.md", "-"),
    ("PW.4", "SCA", "partial", ".github/workflows/security-scan.yml", "ev.md", "-"),
    ("PW.7", "SAST", "partial", "mech_sast.py", "ev.md", "-"),
    ("P.BF", "Brownfield", "covered", "CLAUDE.md", "ev.md", "-"),
    ("P.INST", "Instantiated", "covered", "inst.md", "ev.md", "-"),
    ("P.UNMAP", "Unmapped", "gap", "", "ev.md", "see roadmap"),
    ("RV.1", "Multi", "partial", "mech_rv1.py", "ev.md", "-"),
]


def _write_mapping(path: Path, rows=_MAPPING_ROWS, *, malformed: bool = False) -> None:
    lines = [
        "# Mapping",
        "",
        "| Practice | Title | Status | Mechanism | Evidence | Gap/Waiver |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    if malformed:
        lines.append("| only | three | cols |")
    _write(path, "\n".join(lines) + "\n")


def _enablement_dict() -> dict:
    states = {
        "enforced-self": "self",
        "opt-in-ci": "ci",
        "template-only-frozen": "frozen",
        "local-precommit": "local",
        "native-enforcing": "native",
        "n-a": "na",
    }
    dims = ["secret-scan", "sca", "sast", "sbom", "release-integrity", "disclosure"]

    def cell(s):
        return {"state": s, "rationale": ""}

    return {
        "schema_version": 1,
        "description": "test",
        "dimensions": dims,
        "enablement_states": states,
        "repos": {
            "TestRepo": {
                "stack": "x",
                "ci": "y",
                "dimensions": {
                    "secret-scan": cell("opt-in-ci"),
                    "sca": cell("local-precommit"),
                    "sast": cell("native-enforcing"),
                    "sbom": cell("opt-in-ci"),
                    "release-integrity": cell("opt-in-ci"),
                    "disclosure": cell("n-a"),
                },
            }
        },
    }


@pytest.fixture()
def env(tmp_path: Path):
    """Build template/, a brownfield downstream, a mapping file and an enablement file."""
    template = tmp_path / "template"
    _write(template / "mech_ovl.py", "A\n")
    _write(template / "mech_drift.py", "A\n")
    _write(template / "mech_miss.py", "A\n")          # absent downstream -> not-propagated
    _write(template / "mech_sast.py", "A\n")          # absent downstream -> not-propagated
    _write(template / "mech_rv1.py", "A\n")
    _write(template / "CLAUDE.md", "TPL-CLAUDE\n")     # brownfield-owned (no placeholder)
    _write(template / "inst.md", "# {{PROJECT_NAME}}\n")  # placeholder -> instantiated
    _write(template / ".github" / "workflows" / "security-scan.yml", "ci\n")  # optional-absent
    # source_only.py deliberately NOT in template -> upstream-governed

    down = tmp_path / "downstream"
    _write(down / "mech_ovl.py", "A\n")               # in-sync -> overlaid
    _write(down / "mech_drift.py", "B\n")             # differs -> drifted
    _write(down / "mech_rv1.py", "A\n")               # in-sync -> overlaid
    _write(down / "CLAUDE.md", "DOWNSTREAM-CLAUDE\n")  # differs + brownfield -> project-owned
    _write(down / "inst.md", "# MyProject\n")          # template placeholder -> instantiated -> overlaid
    _write(down / dc.BROWNFIELD_MARKER, "{}\n")        # brownfield marker

    mapping = tmp_path / "ssdf-mapping.md"
    _write_mapping(mapping)
    enablement = tmp_path / "enablement-matrix.json"
    _write(enablement, json.dumps(_enablement_dict()))

    return {
        "tmp": tmp_path,
        "template": template,
        "down": down,
        "mapping": mapping,
        "enablement": enablement,
    }


def _argv(env, *, name="TestRepo", json_out=False, fail_on_gap=False, downstream=None):
    argv = [
        "--downstream", f"{name}={downstream or env['down']}",
        "--template-root", str(env["template"]),
        "--mapping", str(env["mapping"]),
        "--enablement", str(env["enablement"]),
    ]
    if json_out:
        argv.append("--json")
    if fail_on_gap:
        argv.append("--fail-on-gap")
    return argv


def _status_of(payload: dict, practice: str) -> str:
    pr = next(p for p in payload["downstreams"][0]["practices"] if p["practice"] == practice)
    return pr["status"]


def _declared_of(payload: dict, practice: str) -> str:
    pr = next(p for p in payload["downstreams"][0]["practices"] if p["practice"] == practice)
    return pr["declared"]


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def test_mechanism_repo_path():
    assert dc.mechanism_repo_path("") == ""
    assert dc.mechanism_repo_path("a/b.py") == "a/b.py"
    assert dc.mechanism_repo_path("docs/x.md#a-heading") == "docs/x.md"
    assert dc.mechanism_repo_path("docs/x.md:42") == "docs/x.md"
    assert dc.mechanism_repo_path("docs/x.md#sec:5") == "docs/x.md"  # strip # then :line


def test_verdict_to_status_all_six():
    from drift_dashboard import IN_SYNC, INSTANTIATED, BROWNFIELD_OWNED, DRIFTED, MISSING, OPTIONAL_ABSENT
    assert dc.verdict_to_status(IN_SYNC) == dc.OVERLAID
    assert dc.verdict_to_status(INSTANTIATED) == dc.OVERLAID
    assert dc.verdict_to_status(BROWNFIELD_OWNED) == dc.PROJECT_OWNED
    assert dc.verdict_to_status(DRIFTED) == dc.DRIFTED_STATUS
    assert dc.verdict_to_status(MISSING) == dc.NOT_PROPAGATED
    assert dc.verdict_to_status(OPTIONAL_ABSENT) == dc.NOT_OVERLAID


def test_verdict_to_status_unknown_fails_closed():
    with pytest.raises(ValueError):
        dc.verdict_to_status("a-brand-new-drift-category")


def test_most_conservative():
    assert dc._most_conservative(["enforced-self", "n-a"]) == "n-a"
    assert dc._most_conservative(["opt-in-ci", "native-enforcing"]) == "opt-in-ci"
    assert dc._most_conservative(["enforced-self"]) == "enforced-self"


def test_declared_for_governance_single_multi_unknown():
    en = _enablement_dict()
    assert dc.declared_for("P.OVL", "TestRepo", en) == "governance"
    assert dc.declared_for("PW.4", "TestRepo", en) == "sca=local-precommit"
    assert dc.declared_for("RV.1", "TestRepo", en) == (
        "secret-scan=opt-in-ci, disclosure=n-a (most-conservative: n-a)"
    )
    assert dc.declared_for("PW.4", "NoSuchRepo", en) == "unknown-repo"


def test_practice_to_dimensions_subset_of_canonical():
    # D5: every practice in the dashboard mapping table is a real canonical SSDF practice.
    assert set(dc.PRACTICE_TO_DIMENSIONS).issubset(CANONICAL_SET)


# --------------------------------------------------------------------------- #
# enablement SSOT loading (fail-closed)
# --------------------------------------------------------------------------- #
def test_load_enablement_valid(env):
    data = dc.load_enablement(env["enablement"])
    assert data["schema_version"] == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(schema_version=2),
        lambda d: d.update(dimensions="not-a-list"),
        lambda d: d.update(dimensions=[]),
        # H1 (codex impl-review): a dropped / extra / duplicate top-level dimension must be
        # rejected against the practice-mapped REQUIRED set, not silently accepted.
        lambda d: d.update(dimensions=[x for x in d["dimensions"] if x != "sast"]),  # missing
        lambda d: d.update(dimensions=d["dimensions"] + ["extra-dim"]),              # extra
        lambda d: d.update(dimensions=d["dimensions"] + ["sca"]),                    # duplicate
        lambda d: d.update(enablement_states="nope"),
        lambda d: d.update(repos="nope"),
        lambda d: d.update(repos={}),
        lambda d: d["enablement_states"].update({"weird-extra-state": "x"}),
        lambda d: d["repos"]["TestRepo"].update(dimensions={"secret-scan": {"state": "opt-in-ci"}}),
        lambda d: d["repos"]["TestRepo"]["dimensions"].update({"sca": {"state": "bogus"}}),
        lambda d: d["repos"]["TestRepo"]["dimensions"].update({"sca": "not-a-dict"}),
    ],
)
def test_load_enablement_invalid(tmp_path, mutate):
    d = _enablement_dict()
    mutate(d)
    p = tmp_path / "bad.json"
    _write(p, json.dumps(d))
    with pytest.raises(ValueError):
        dc.load_enablement(p)


# --------------------------------------------------------------------------- #
# Three-axis classification (honesty core)
# --------------------------------------------------------------------------- #
def test_all_statuses_classified(env, capsys):
    code = dc.run(_argv(env, json_out=True))
    assert code == dc.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert _status_of(payload, "P.OVL") == dc.OVERLAID            # in-sync
    assert _status_of(payload, "P.INST") == dc.OVERLAID           # instantiated -> overlaid
    assert _status_of(payload, "P.DRIFT") == dc.DRIFTED_STATUS    # differs
    assert _status_of(payload, "P.MISS") == dc.NOT_PROPAGATED     # absent (missing)
    assert _status_of(payload, "PS.1") == dc.UPSTREAM_GOVERNED    # source-only (not in template)
    assert _status_of(payload, "PW.4") == dc.NOT_OVERLAID         # optional-absent workflow
    assert _status_of(payload, "P.BF") == dc.PROJECT_OWNED        # brownfield-owned
    assert _status_of(payload, "P.UNMAP") == dc.UNMAPPED          # empty mechanism
    # vocabulary never includes "covered"
    statuses = {p["status"] for p in payload["downstreams"][0]["practices"]}
    assert "covered" not in statuses
    assert "n-a" not in statuses  # n-a is a declared value only, never a status


def test_declared_never_overrides_actual(env, capsys):
    """D1: PW.7 declares sast=native-enforcing but its mechanism is absent -> not-propagated."""
    dc.run(_argv(env, json_out=True))
    payload = json.loads(capsys.readouterr().out)
    assert _status_of(payload, "PW.7") == dc.NOT_PROPAGATED
    assert "native-enforcing" in _declared_of(payload, "PW.7")


def test_applicability_recorded(env, capsys):
    dc.run(_argv(env, json_out=True))
    payload = json.loads(capsys.readouterr().out)
    by = {p["practice"]: p["applicability"] for p in payload["downstreams"][0]["practices"]}
    assert by["PS.1"] == "source-only"
    assert by["P.OVL"] == "propagable"
    assert by["P.UNMAP"] == "unmapped"


def test_unknown_verdict_hard_fails(env, monkeypatch):
    monkeypatch.setattr(dc, "classify_file", lambda *a, **k: "totally-new-verdict")
    with pytest.raises(ValueError):
        dc.run(_argv(env))


# --------------------------------------------------------------------------- #
# Output + caveat + exit semantics
# --------------------------------------------------------------------------- #
# The three honesty claims the caveat MUST carry in BOTH markdown and JSON.
_CAVEAT_CLAIMS = (
    "NOT an SSDLC conformance certification",          # not a certifier
    "NOT that the practice is enforced",               # overlaid != enforced
    "NEVER overrides the actual `status`",             # declared never overrides actual
)


def test_markdown_caveat_present(env, capsys):
    code = dc.run(_argv(env))
    assert code == dc.EXIT_OK
    out = capsys.readouterr().out
    assert "SSDF Conformance Dashboard" in out
    for claim in _CAVEAT_CLAIMS:
        assert claim in out, f"markdown caveat missing claim: {claim!r}"


def test_json_caveat_and_structure(env, capsys):
    dc.run(_argv(env, json_out=True))
    payload = json.loads(capsys.readouterr().out)
    for claim in _CAVEAT_CLAIMS:
        assert claim in payload["caveat"], f"json caveat missing claim: {claim!r}"
    d0 = payload["downstreams"][0]
    assert d0["name"] == "TestRepo"
    assert d0["brownfield"] is True
    assert d0["gaps"] >= 1
    assert set(d0["summary"]) == set(dc._SUMMARY_ORDER)


def test_fail_on_gap_exits_2(env):
    assert dc.run(_argv(env, fail_on_gap=True)) == dc.EXIT_GAP


def test_fail_on_gap_clean_downstream_exits_0(env):
    """A greenfield full-copy downstream (every template file verbatim) has no gaps."""
    clean = env["tmp"] / "clean"
    for tf in iter_files(env["template"]):
        rel = tf.relative_to(env["template"])
        _write(clean / rel, tf.read_text(encoding="utf-8"))
    assert dc.run(_argv(env, fail_on_gap=True, downstream=clean)) == dc.EXIT_OK


def test_fail_on_gap_isolates_not_overlaid(tmp_path, capsys):
    """A downstream whose ONLY gap is `not-overlaid` (a pruned council-forge workflow) must
    still trip --fail-on-gap. Isolates not-overlaid so removing it from GAP_STATUSES fails."""
    template = tmp_path / "t"
    _write(template / "mech_ok.py", "A\n")
    _write(template / ".github" / "workflows" / "security-scan.yml", "ci\n")
    down = tmp_path / "d"
    _write(down / "mech_ok.py", "A\n")  # in-sync -> overlaid
    # security-scan.yml absent downstream -> optional-absent -> not-overlaid (the ONLY gap)
    mapping = tmp_path / "m.md"
    _write_mapping(mapping, rows=[
        ("P.OK", "Ok", "covered", "mech_ok.py", "ev", "-"),
        ("PW.4", "SCA", "partial", ".github/workflows/security-scan.yml", "ev", "-"),
    ])
    enablement = tmp_path / "e.json"
    _write(enablement, json.dumps(_enablement_dict()))
    base = ["--downstream", f"Iso={down}", "--template-root", str(template),
            "--mapping", str(mapping), "--enablement", str(enablement)]
    assert dc.run(base + ["--json"]) == dc.EXIT_OK
    d0 = json.loads(capsys.readouterr().out)["downstreams"][0]
    assert d0["summary"][dc.NOT_OVERLAID] == 1
    assert d0["summary"][dc.NOT_PROPAGATED] == 0
    assert d0["summary"][dc.DRIFTED_STATUS] == 0
    assert d0["gaps"] == 1  # the single gap is the not-overlaid one
    assert dc.run(base + ["--fail-on-gap"]) == dc.EXIT_GAP


# --------------------------------------------------------------------------- #
# run() error branches
# --------------------------------------------------------------------------- #
def test_run_requires_downstream():
    assert dc.run(["--mapping", "x"]) == dc.EXIT_ERROR


def test_run_bad_template_root(env):
    argv = _argv(env)
    i = argv.index("--template-root")
    argv[i + 1] = str(env["tmp"] / "no-such-template")
    assert dc.run(argv) == dc.EXIT_ERROR


def test_run_bad_mapping(env):
    argv = _argv(env)
    i = argv.index("--mapping")
    argv[i + 1] = str(env["tmp"] / "no-mapping.md")
    assert dc.run(argv) == dc.EXIT_ERROR


def test_run_bad_enablement_path(env):
    argv = _argv(env)
    i = argv.index("--enablement")
    argv[i + 1] = str(env["tmp"] / "no-enable.json")
    assert dc.run(argv) == dc.EXIT_ERROR


def test_run_mapping_parse_error(env):
    _write_mapping(env["mapping"], malformed=True)
    assert dc.run(_argv(env)) == dc.EXIT_ERROR


def test_run_enablement_invalid(env):
    _write(env["enablement"], json.dumps({"schema_version": 99}))
    assert dc.run(_argv(env)) == dc.EXIT_ERROR


def test_run_bad_downstream_path(env):
    argv = [
        "--downstream", f"Ghost={env['tmp'] / 'ghost'}",
        "--template-root", str(env["template"]),
        "--mapping", str(env["mapping"]),
        "--enablement", str(env["enablement"]),
    ]
    assert dc.run(argv) == dc.EXIT_ERROR


def test_default_paths_point_at_real_files():
    assert dc.default_enablement_path().name == "enablement-matrix.json"
    assert dc.default_mapping_path().name == "ssdf-mapping.md"


# --------------------------------------------------------------------------- #
# CP-3: README <-> SSOT exact state-token parity (single source of truth)
# --------------------------------------------------------------------------- #
def _parse_readme_state_matrix(text: str) -> dict:
    lines = text.splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("### State matrix"))
    header_i = next(i for i in range(idx, len(lines)) if lines[i].strip().startswith("| Repo |"))
    header = [c.strip() for c in lines[header_i].strip().strip("|").split("|")]
    dims = header[1:]
    out: dict = {}
    for l in lines[header_i + 2:]:  # +2 skips the separator row
        if not l.strip().startswith("|"):
            break
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        out[cells[0]] = dict(zip(dims, cells[1:]))
    return out


def test_readme_state_matrix_matches_ssot():
    """The README State matrix token table must equal enablement-matrix.json exactly."""
    enablement = json.loads(dc.default_enablement_path().read_text(encoding="utf-8"))
    readme = (dc.default_enablement_path().parent / "README.md").read_text(encoding="utf-8")
    matrix = _parse_readme_state_matrix(readme)
    repos = enablement["repos"]
    dims = enablement["dimensions"]
    assert set(matrix) == set(repos), "README repos differ from SSOT repos"
    for repo, row in matrix.items():
        assert set(row) == set(dims), f"{repo}: README dimension columns differ from SSOT"
        for dim, token in row.items():
            ssot_state = repos[repo]["dimensions"][dim]["state"]
            assert token == ssot_state, (
                f"README state {repo}/{dim}={token!r} != SSOT {ssot_state!r} (single-source-of-truth drift)"
            )
