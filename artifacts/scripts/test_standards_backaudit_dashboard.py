"""Full-coverage, fixture-driven unit tests for standards_backaudit_dashboard.py.

Honesty-focused: the core assertions prove the dashboard never conflates a clean machine
re-run (`formal-delta`) with a met qualitative bar (no naked `passed`/`conformant`), that the
caveat is ALWAYS emitted (markdown + JSON), that completion time is multi-source with
fail-closed conflict/unknown, that the guard re-run argv is the EXACT non-mutating allowlist
(read-only invariant), that the risk lattice PROMOTES on a security hit and defaults to triage
(never silent low), and that `reviewed` is a structure-only attestation.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import standards_backaudit_dashboard as dash

TAIPEI = timezone(timedelta(hours=8))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _inst(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


_CATEGORIES = ["dual-review", "ssdf", "fail-closed", "security-gate", "dispatch", "lifecycle", "write-scope"]

_TIMELINE = {
    "schema_version": 1,
    "description": "test",
    "maintenance": {"living_ssot": True, "rule": "x", "categories": _CATEGORIES},
    "events": [
        {"introduced_at": "2026-01-01T10:00:00+08:00", "event": "e1", "standard": "s1",
         "ref": "R1", "commit": "aaa", "category": "dual-review"},
        # same DAY as the next, two hours earlier -> D1 instant ordering must not collapse them
        {"introduced_at": "2026-02-01T10:00:00+08:00", "event": "e2", "standard": "s2",
         "ref": "R2", "commit": "bbb", "category": "ssdf"},
        {"introduced_at": "2026-02-01T12:00:00+08:00", "event": "e3", "standard": "s3",
         "ref": "R3", "commit": "ccc", "category": "fail-closed"},
    ],
}


def _events():
    return [
        dash.UpliftEvent(_inst("2026-01-01T10:00:00+08:00"), "e1", "s1", "R1", "aaa", "dual-review"),
        dash.UpliftEvent(_inst("2026-02-01T10:00:00+08:00"), "e2", "s2", "R2", "bbb", "ssdf"),
        dash.UpliftEvent(_inst("2026-02-01T12:00:00+08:00"), "e3", "s3", "R3", "ccc", "fail-closed"),
    ]


# --------------------------------------------------------------------------- #
# to_instant (D1) + timeline load (fail-closed)
# --------------------------------------------------------------------------- #
def test_to_instant_aware_naive_none():
    assert dash.to_instant("2026-01-01T10:00:00+08:00").utcoffset() == timedelta(hours=8)
    naive = dash.to_instant("2026-01-01T10:00:00")          # localised to Taipei
    assert naive.tzinfo is not None and naive.utcoffset() == timedelta(hours=8)
    assert dash.to_instant("not-a-date") is None


def test_load_timeline_valid(tmp_path):
    p = tmp_path / "tl.json"
    _write(p, json.dumps(_TIMELINE))
    events, cats = dash.load_timeline(p)
    assert [e.ref for e in events] == ["R1", "R2", "R3"]          # ascending by instant
    assert cats == frozenset(_CATEGORIES)


def test_load_timeline_orders_same_day_by_instant(tmp_path):
    """R2 (10:00) must precede R3 (12:00) on the same day — instant, not date."""
    shuffled = json.loads(json.dumps(_TIMELINE))
    shuffled["events"] = list(reversed(shuffled["events"]))
    p = tmp_path / "tl.json"
    _write(p, json.dumps(shuffled))
    events, _ = dash.load_timeline(p)
    assert [e.ref for e in events] == ["R1", "R2", "R3"]


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(schema_version=2),
    lambda d: d["maintenance"].update(categories="nope"),
    lambda d: d["maintenance"].update(categories=[]),
    lambda d: d.update(events="nope"),
    lambda d: d.update(events=[]),
    lambda d: d["events"].append("not-an-object"),
    lambda d: d["events"][0].pop("standard"),
    lambda d: d["events"][0].update(introduced_at="garbage"),
    lambda d: d["events"][0].update(category="not-in-vocab"),
])
def test_load_timeline_invalid_fail_closed(tmp_path, mutate):
    d = json.loads(json.dumps(_TIMELINE))
    mutate(d)
    p = tmp_path / "bad.json"
    _write(p, json.dumps(d))
    with pytest.raises(ValueError):
        dash.load_timeline(p)


def test_uplift_event_as_dict_roundtrips_fields():
    e = _events()[0]
    d = e.as_dict()
    assert d["ref"] == "R1" and d["category"] == "dual-review" and d["commit"] == "aaa"
    assert d["introduced_at"].startswith("2026-01-01T10:00:00")


# --------------------------------------------------------------------------- #
# completion (D2 multi-source priority; D7 conflict / unknown fail-closed)
# --------------------------------------------------------------------------- #
def test_artifact_last_updated_instant(tmp_path):
    p = tmp_path / "a.md"
    _write(p, "# X\n\n## Metadata\n- Last Updated: 2026-01-15T09:00:00+08:00\n")
    assert dash.artifact_last_updated_instant(p) == _inst("2026-01-15T09:00:00+08:00")
    assert dash.artifact_last_updated_instant(tmp_path / "missing.md") is None
    _write(tmp_path / "b.md", "no metadata here")
    assert dash.artifact_last_updated_instant(tmp_path / "b.md") is None
    # impl-review (D2/D7): a pre-metadata prose `Last Updated` must NOT spoof the instant; only
    # the `## Metadata` block is trusted (and the block ends at the next `## ` header).
    _write(tmp_path / "spoof.md",
           "- Last Updated: 2099-01-01T00:00:00+08:00 (quoted)\n\n## Metadata\n"
           "- Last Updated: 2026-02-02T08:00:00+08:00\n\n## Body\nprose\n")
    assert dash.artifact_last_updated_instant(tmp_path / "spoof.md") == _inst("2026-02-02T08:00:00+08:00")
    # ambiguous: two DISTINCT Last Updated in metadata -> fail closed (None)
    _write(tmp_path / "ambig.md",
           "## Metadata\n- Last Updated: 2026-01-01T00:00:00+08:00\n- Last Updated: 2026-03-03T00:00:00+08:00\n")
    assert dash.artifact_last_updated_instant(tmp_path / "ambig.md") is None
    # metadata block carries no Last Updated (a later out-of-block one is ignored) -> None
    _write(tmp_path / "nolu.md",
           "## Metadata\n- Owner: Claude\n## Body\n- Last Updated: 2030-01-01T00:00:00+08:00\n")
    assert dash.artifact_last_updated_instant(tmp_path / "nolu.md") is None


def _repo_with_completion(tmp_path, task_id, *, verify=None, decision=None):
    if verify:
        _write(tmp_path / "artifacts" / "verify" / f"{task_id}.verify.md",
               f"## Metadata\n- Last Updated: {verify}\n")
    if decision:
        _write(tmp_path / "artifacts" / "decisions" / f"{task_id}.decision.md",
               f"## Metadata\n- Last Updated: {decision}\n")


def test_completion_priority_verify_over_decision(tmp_path):
    _repo_with_completion(tmp_path, "TASK-1", verify="2026-01-15T18:00:00+08:00",
                          decision="2026-01-10T18:00:00+08:00")
    c = dash.resolve_completion("TASK-1", tmp_path, _events(), git_instant=lambda r, p: None)
    assert c.kind == "resolved" and c.source == "verify"
    assert c.instant == _inst("2026-01-15T18:00:00+08:00")
    # verify+decision both pre-R2/R3 (no straddle) -> they agree
    assert {s for s, _ in c.candidates} == {"verify", "decision"}


def test_completion_falls_back_to_git(tmp_path):
    c = dash.resolve_completion("TASK-2", tmp_path, _events(),
                                git_instant=lambda r, p: _inst("2026-01-15T00:00:00+08:00"))
    assert c.kind == "resolved" and c.source == "git"


def test_completion_unknown_fail_closed(tmp_path):
    c = dash.resolve_completion("TASK-3", tmp_path, _events(), git_instant=lambda r, p: None)
    assert c.kind == dash.COMPLETION_UNKNOWN and c.instant is None


def test_completion_conflict_straddle_fail_closed(tmp_path):
    """verify=2026-01-15 (pre R2/R3) but git=2026-02-15 (post) -> sources straddle -> conflict."""
    _repo_with_completion(tmp_path, "TASK-4", verify="2026-01-15T10:00:00+08:00")
    c = dash.resolve_completion("TASK-4", tmp_path, _events(),
                                git_instant=lambda r, p: _inst("2026-02-15T10:00:00+08:00"))
    assert c.kind == dash.COMPLETION_CONFLICT and c.instant is None


def test_completion_single_candidate_never_conflicts(tmp_path):
    _repo_with_completion(tmp_path, "TASK-5", verify="2026-01-15T10:00:00+08:00")
    c = dash.resolve_completion("TASK-5", tmp_path, _events(), git_instant=lambda r, p: None)
    assert c.kind == "resolved"


def test_theoretical_delta_instant_compare(tmp_path):
    c = dash.Completion("resolved", _inst("2026-01-15T00:00:00+08:00"), "verify")
    delta = dash.theoretical_delta(c, _events())
    assert [e.ref for e in delta] == ["R2", "R3"]                 # R1 (Jan 1) predates completion
    # no-delta + non-resolved branches
    assert dash.theoretical_delta(dash.Completion("resolved", _inst("2027-01-01T00:00:00+08:00"), "verify"), _events()) == []
    assert dash.theoretical_delta(dash.Completion(dash.COMPLETION_UNKNOWN, None, None), _events()) == []


# --------------------------------------------------------------------------- #
# formal-delta: read-only argv allowlist (D4/D10) + output parsing
# --------------------------------------------------------------------------- #
def test_build_guard_argv_exact_four(tmp_path):
    argv = dash.build_guard_argv(tmp_path / "guard_status_validator.py", "TASK-9")
    assert len(argv) == 4
    assert argv[1].endswith("guard_status_validator.py")
    assert argv[2] == "--task-id" and argv[3] == "TASK-9"


def test_assert_readonly_guard_argv():
    # exact read-only ALLOWLIST shape (forward and windows path separators)
    dash.assert_readonly_guard_argv(["python", "x/guard_status_validator.py", "--task-id", "TASK-1"])
    dash.assert_readonly_guard_argv(["python", "x\\guard_status_validator.py", "--task-id", "TASK-1"])
    # wrong shape / position / script -> reject (impl-review: allowlist, not denylist)
    for bad in (
        ["python", "x/guard_status_validator.py", "--task-id", "T", "--auto-classify"],  # len != 4
        ["python", "x/guard_status_validator.py", "--reconcile", "T"],                    # pos-2 not --task-id
        ["python", "x/other_script.py", "--task-id", "T"],                                # not the guard script
        ["python", "x/guard_status_validator.py", "--task-id"],                           # too short
    ):
        with pytest.raises(ValueError):
            dash.assert_readonly_guard_argv(bad)
    # defence-in-depth: a mutating flag smuggled in =value / prefix form (that a token denylist
    # would miss) is still rejected
    for smuggled in ("--override=reason", "--override-approver=alice", "--write-transition=x", "--reconcile"):
        with pytest.raises(ValueError):
            dash.assert_readonly_guard_argv(["python", "guard_status_validator.py", "--task-id", smuggled])


def test_parse_guard_output_all_branches():
    assert dash.parse_guard_output(0, "[OK] Validation passed\n", "").status == dash.FORMAL_CLEAN
    r = dash.parse_guard_output(0, "[OK] x\n[WARN] premortem missing\n", "")
    assert r.status == dash.FORMAL_WARN and r.warns == ["[WARN] premortem missing"]
    assert dash.parse_guard_output(1, "[FAIL] boom\n", "").status == dash.FORMAL_FAIL
    # rc 0 but a FAIL line present -> still a fail (fail-closed)
    assert dash.parse_guard_output(0, "[FAIL] sneaky\n", "").status == dash.FORMAL_FAIL
    # FAIL only on stderr
    assert dash.parse_guard_output(1, "", "[FAIL] usage\n").status == dash.FORMAL_FAIL
    # unexpected rc -> formal-error (visible, fail-closed)
    assert dash.parse_guard_output(2, "", "[FAIL] --task-id required\n").status == dash.FORMAL_ERROR


def test_rerun_guard_status_passes_exact_argv(tmp_path):
    seen = {}

    def fake_invoke(argv, cwd):
        seen["argv"] = list(argv)
        seen["cwd"] = cwd
        return 0, "[OK] x\n[WARN] w\n", ""

    res = dash.rerun_guard_status("TASK-7", tmp_path, tmp_path / "scripts", invoke=fake_invoke)
    assert res.status == dash.FORMAL_WARN
    assert seen["argv"][2:] == ["--task-id", "TASK-7"]
    assert seen["argv"][1].endswith("guard_status_validator.py")
    assert len(seen["argv"]) == 4                                  # no mutating flag ever
    assert seen["cwd"] == tmp_path


# --------------------------------------------------------------------------- #
# risk lattice (D8/D12/D14) — promote on security hit, default to triage
# --------------------------------------------------------------------------- #
def test_extract_files_changed_variants():
    assert dash.extract_files_changed("") == []
    assert dash.extract_files_changed("# x\nno section here\n") == []
    text = (
        "## Files Changed\n\n"
        "- artifacts/scripts/release_gate.py（NEW，source-only）\n"
        "* docs/foo.md — note\n"
        "- `artifacts/scripts/sbom_gate.py` (modified)\n"
        "not-a-bullet line\n"
        "## Next Section\n"
        "- artifacts/should/not/appear.py\n"
    )
    paths = dash.extract_files_changed(text)
    assert "artifacts/scripts/release_gate.py" in paths
    assert "docs/foo.md" in paths
    assert "artifacts/scripts/sbom_gate.py" in paths
    assert all("should/not" not in p for p in paths)              # stops at next "## "


def test_path_is_security_sensitive():
    assert dash._path_is_security_sensitive("artifacts/scripts/release_gate.py")
    assert dash._path_is_security_sensitive("artifacts/scripts/guard_status_validator.py")
    assert dash._path_is_security_sensitive(".well-known/security.txt")
    assert not dash._path_is_security_sensitive("docs/orchestration.md")


def _write_task(tmp_path, task_id, *, task_text="", plan_text="", code_text=None):
    _write(tmp_path / "artifacts" / "tasks" / f"{task_id}.task.md", task_text or "# t\n")
    if plan_text:
        _write(tmp_path / "artifacts" / "plans" / f"{task_id}.plan.md", plan_text)
    if code_text is not None:
        _write(tmp_path / "artifacts" / "code" / f"{task_id}.code.md", code_text)


def test_classify_risk_not_applicable_without_delta(tmp_path):
    r = dash.classify_risk("TASK-1", tmp_path, has_delta=False)
    assert r.tier == dash.RISK_NOT_APPLICABLE


def test_classify_risk_promotes_on_keyword(tmp_path):
    _write_task(tmp_path, "TASK-2", task_text="objective: release-signing and gpg signature verification")
    r = dash.classify_risk("TASK-2", tmp_path, has_delta=True)
    assert r.tier == dash.RISK_HIGH and r.score >= 1 and r.keyword_hits


def test_classify_risk_promotes_on_security_path(tmp_path):
    _write_task(tmp_path, "TASK-3", task_text="something neutral",
                code_text="## Files Changed\n- artifacts/scripts/sast_gate.py\n")
    r = dash.classify_risk("TASK-3", tmp_path, has_delta=True)
    assert r.tier == dash.RISK_HIGH and r.path_hits


def test_classify_risk_triage_no_code(tmp_path):
    _write_task(tmp_path, "TASK-4", task_text="completely benign refactor of formatting")
    r = dash.classify_risk("TASK-4", tmp_path, has_delta=True)
    assert r.tier == dash.RISK_TRIAGE_NEEDED and "no code artifact" in r.note


def test_classify_risk_triage_unparseable_code(tmp_path):
    _write_task(tmp_path, "TASK-5", task_text="benign", code_text="# code\nno files changed header\n")
    r = dash.classify_risk("TASK-5", tmp_path, has_delta=True)
    assert r.tier == dash.RISK_TRIAGE_NEEDED and "unparseable" in r.note


def test_classify_risk_triage_map_miss(tmp_path):
    _write_task(tmp_path, "TASK-6", task_text="benign",
                code_text="## Files Changed\n- docs/orchestration.md\n")
    r = dash.classify_risk("TASK-6", tmp_path, has_delta=True)
    assert r.tier == dash.RISK_TRIAGE_NEEDED and "map-miss" in r.note


# --------------------------------------------------------------------------- #
# reviewed: structured record (D5/D9) — structure attested, not quality
# --------------------------------------------------------------------------- #
_GOOD_RECORD = (
    "## Back-Audit Re-Review: TASK-900\n"
    "- Reviewed-Task: TASK-900\n"
    "- Bar: 2026-06-08 dual-review+SSDF+fail-closed\n"
    "- Reviewers: codex, gemini\n"
    "- Codex-Evidence: artifacts/verify/TASK-1087.verify.md#codex-900\n"
    "- Gemini-Evidence: artifacts/verify/TASK-1087.verify.md#gemini-900\n"
    "- Verdict: robust at completion bar; one forward backlog item\n"
)


def test_parse_review_records_valid():
    recs = dash.parse_review_records(_GOOD_RECORD, "TASK-1087.decision.md")
    assert len(recs) == 1
    assert recs[0].reviewed_task == "TASK-900"
    assert "codex" in recs[0].reviewers and "gemini" in recs[0].reviewers


def test_parse_review_records_requires_all_fields():
    missing_bar = _GOOD_RECORD.replace("- Bar: 2026-06-08 dual-review+SSDF+fail-closed\n", "")
    assert dash.parse_review_records(missing_bar, "d.md") == []
    only_codex = _GOOD_RECORD.replace("- Reviewers: codex, gemini\n", "- Reviewers: codex\n")
    assert dash.parse_review_records(only_codex, "d.md") == []


def test_parse_review_records_rejects_blank_fields():
    # impl-review (D9 anti-forgery): a blank / whitespace-only Bar / evidence must NOT yield a
    # record, and a blank field must NOT capture the next line as its value (single-line regex).
    for line in (
        "- Bar: 2026-06-08 dual-review+SSDF+fail-closed\n",
        "- Codex-Evidence: artifacts/verify/TASK-1087.verify.md#codex-900\n",
        "- Gemini-Evidence: artifacts/verify/TASK-1087.verify.md#gemini-900\n",
    ):
        label = line.split(":", 1)[0]
        blanked = _GOOD_RECORD.replace(line, f"{label}:   \n")          # whitespace-only value
        assert dash.parse_review_records(blanked, "d.md") == [], f"blank accepted: {label!r}"
    # a bare `Bar:` (empty) must not swallow the following `Reviewers:` line
    bare = _GOOD_RECORD.replace("- Bar: 2026-06-08 dual-review+SSDF+fail-closed\n", "- Bar:\n")
    assert dash.parse_review_records(bare, "d.md") == []


def test_parse_review_records_multiple_blocks():
    two = _GOOD_RECORD + _GOOD_RECORD.replace("TASK-900", "TASK-901")
    recs = dash.parse_review_records(two, "d.md")
    assert {r.reviewed_task for r in recs} == {"TASK-900", "TASK-901"}


def test_find_review_record(tmp_path):
    dec = tmp_path / "artifacts" / "decisions"
    _write(dec / "TASK-1087.decision.md", _GOOD_RECORD)
    assert dash.find_review_record("TASK-900", dec).reviewed_task == "TASK-900"
    assert dash.find_review_record("TASK-999", dec) is None
    assert dash.find_review_record("TASK-900", tmp_path / "no-such-dir") is None


# --------------------------------------------------------------------------- #
# qualitative status priority
# --------------------------------------------------------------------------- #
def test_qualitative_status_priority():
    ev = _events()
    res = dash.Completion("resolved", _inst("2026-01-15T00:00:00+08:00"), "verify")
    unk = dash.Completion(dash.COMPLETION_UNKNOWN, None, None)
    conf = dash.Completion(dash.COMPLETION_CONFLICT, None, None)
    rec = dash.ReviewRecord("TASK-900", "bar", ["codex", "gemini"], "x", "y", "d.md")
    assert dash.qualitative_status_for(unk, [], None) == dash.COMPLETION_UNKNOWN
    assert dash.qualitative_status_for(conf, [], None) == dash.COMPLETION_CONFLICT
    assert dash.qualitative_status_for(res, ev, rec) == dash.REVIEWED       # review overrides pending
    assert dash.qualitative_status_for(res, [], None) == dash.CURRENT_BAR
    assert dash.qualitative_status_for(res, ev, None) == dash.QUALITATIVE_REVIEW_PENDING


# --------------------------------------------------------------------------- #
# end-to-end run() — honesty, exit codes, output (guard seam monkeypatched)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def fake_repo(tmp_path, monkeypatch):
    """A repo with two tasks; guard + git seams monkeypatched (no real subprocess)."""
    _write(tmp_path / "docs" / "standards-uplift-timeline.json", json.dumps(_TIMELINE))
    # OLD task: completed 2026-01-15 (predates R2/R3), security keyword -> risk-high, guard WARN
    _write(tmp_path / "artifacts" / "status" / "TASK-100.status.json", json.dumps({"task_id": "TASK-100", "state": "done"}))
    _write(tmp_path / "artifacts" / "verify" / "TASK-100.verify.md", "## Metadata\n- Last Updated: 2026-01-15T10:00:00+08:00\n")
    _write(tmp_path / "artifacts" / "tasks" / "TASK-100.task.md", "objective: release-signing gpg signature gate\n")
    # NEW task: completed 2027 (after every standard) -> current-bar, guard clean
    _write(tmp_path / "artifacts" / "status" / "TASK-200.status.json", json.dumps({"task_id": "TASK-200", "state": "done"}))
    _write(tmp_path / "artifacts" / "verify" / "TASK-200.verify.md", "## Metadata\n- Last Updated: 2027-01-01T10:00:00+08:00\n")
    _write(tmp_path / "artifacts" / "tasks" / "TASK-200.task.md", "neutral cleanup\n")

    def fake_invoke(argv, cwd):
        # the audited task id is the last argv element
        if argv[-1] == "TASK-100":
            return 0, "[OK] Validation passed\n[WARN] TASK-100.plan.md: premortem missing field\n", ""
        return 0, "[OK] Validation passed\n", ""

    monkeypatch.setattr(dash, "_invoke_guard", fake_invoke)
    monkeypatch.setattr(dash, "_git_first_commit_instant", lambda root, rel: None)
    return tmp_path


def test_run_json_honesty_and_axes(fake_repo, capsys):
    code = dash.run(["--root", str(fake_repo), "--json"])
    assert code == dash.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    # caveat present in JSON
    assert "machine-decidable" in payload["caveat"] and "passed" in payload["caveat"]
    statuses = {t["task_id"]: t for t in payload["tasks"]}
    assert statuses["TASK-100"]["qualitative_status"] == dash.QUALITATIVE_REVIEW_PENDING
    assert statuses["TASK-100"]["formal_delta"]["status"] == dash.FORMAL_WARN
    assert statuses["TASK-100"]["risk"]["tier"] == dash.RISK_HIGH
    assert statuses["TASK-200"]["qualitative_status"] == dash.CURRENT_BAR
    assert statuses["TASK-200"]["formal_delta"]["status"] == dash.FORMAL_CLEAN
    # vocabulary never contains a naked "passed"/"conformant" status
    all_status_values = {t["qualitative_status"] for t in payload["tasks"]}
    assert "passed" not in all_status_values and "conformant" not in all_status_values
    # backlog risk-ranked, TASK-100 present
    assert payload["backlog"][0]["task_id"] == "TASK-100"


def test_run_markdown_caveat_and_backlog(fake_repo, capsys):
    code = dash.run(["--root", str(fake_repo)])
    assert code == dash.EXIT_OK
    out = capsys.readouterr().out
    assert "Standards-Drift Back-Audit Dashboard" in out
    assert "NOT machine-decidable" in out                       # caveat in markdown
    assert "TASK-100" in out and "qualitative-review-pending" in out


def test_run_markdown_empty_backlog_branch(fake_repo, capsys):
    code = dash.run(["--root", str(fake_repo), "--task", "TASK-200"])
    assert code == dash.EXIT_OK
    out = capsys.readouterr().out
    assert "empty" in out.lower()                                # backlog-empty rendering branch


def test_run_fail_on_formal_delta_exits_2(fake_repo):
    assert dash.run(["--root", str(fake_repo), "--fail-on-formal-delta"]) == dash.EXIT_FORMAL_DELTA


def test_run_fail_on_formal_delta_clean_subset_exits_0(fake_repo):
    assert dash.run(["--root", str(fake_repo), "--task", "TASK-200", "--fail-on-formal-delta"]) == dash.EXIT_OK


def test_run_completion_cell_unknown(tmp_path, monkeypatch, capsys):
    _write(tmp_path / "docs" / "standards-uplift-timeline.json", json.dumps(_TIMELINE))
    _write(tmp_path / "artifacts" / "status" / "TASK-300.status.json", json.dumps({"state": "done"}))
    _write(tmp_path / "artifacts" / "tasks" / "TASK-300.task.md", "neutral\n")  # no verify/decision
    monkeypatch.setattr(dash, "_invoke_guard", lambda a, c: (0, "[OK] x\n", ""))
    monkeypatch.setattr(dash, "_git_first_commit_instant", lambda r, p: None)
    code = dash.run(["--root", str(tmp_path)])
    assert code == dash.EXIT_OK
    out = capsys.readouterr().out
    assert dash.COMPLETION_UNKNOWN in out


def test_run_timeline_not_found(tmp_path):
    _write(tmp_path / "artifacts" / "status" / ".keep", "")
    assert dash.run(["--root", str(tmp_path), "--timeline", str(tmp_path / "nope.json")]) == dash.EXIT_ERROR


def test_run_timeline_invalid(tmp_path):
    _write(tmp_path / "docs" / "standards-uplift-timeline.json", json.dumps({"schema_version": 99}))
    assert dash.run(["--root", str(tmp_path)]) == dash.EXIT_ERROR


def test_run_status_dir_missing(tmp_path):
    _write(tmp_path / "docs" / "standards-uplift-timeline.json", json.dumps(_TIMELINE))
    assert dash.run(["--root", str(tmp_path)]) == dash.EXIT_ERROR


def test_default_timeline_path():
    assert dash.default_timeline_path(Path("/x")).name == "standards-uplift-timeline.json"


# --------------------------------------------------------------------------- #
# Audit aggregation helpers
# --------------------------------------------------------------------------- #
def test_build_audit_filter_and_backlog_ranking(fake_repo):
    events, _ = dash.load_timeline(fake_repo / "docs" / "standards-uplift-timeline.json")
    audit = dash.build_audit(fake_repo, events, now=_inst("2026-06-08T12:00:00+08:00"))
    assert len(audit.tasks) == 2
    assert [t.task_id for t in audit.by_status(dash.CURRENT_BAR)] == ["TASK-200"]
    # backlog has only the open obligation, risk-high first
    assert [t.task_id for t in audit.backlog] == ["TASK-100"]
    # filter
    one = dash.build_audit(fake_repo, events, task_filter=["task-200"], now=_inst("2026-06-08T12:00:00+08:00"))
    assert [t.task_id for t in one.tasks] == ["TASK-200"]
