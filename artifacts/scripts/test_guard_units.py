"""Backward-compatible shim for TASK-1054 split guard unit tests.

Also hosts TASK-1061 CITATION_PATTERN / RESEARCH_SOURCES_ENTRY_PATTERN
relaxation unit tests at module level so pytest auto-collects them under
the standard `pytest artifacts/scripts/` invocation.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _requested_directly() -> bool:
    this_file = Path(__file__).resolve()
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            continue
        try:
            if Path(arg).resolve() == this_file:
                return True
        except OSError:
            continue
    return False


if _requested_directly():
    from test_artifact_schema_migration import *  # noqa: F401,F403
    from test_decision_registry_and_red_team import *  # noqa: F401,F403
    from test_guard_contract_validator import *  # noqa: F401,F403
    from test_guard_status_validator_artifacts import *  # noqa: F401,F403
    from test_guard_status_validator_core import *  # noqa: F401,F403
    from test_guard_status_validator_state import *  # noqa: F401,F403
    from test_prompt_regression_validator import *  # noqa: F401,F403
    from test_repository_and_pdca import *  # noqa: F401,F403
    from test_validate_context_stack import *  # noqa: F401,F403
    from test_workflow_constants import *  # noqa: F401,F403


# --- TASK-1061: CITATION_PATTERN / RESEARCH_SOURCES_ENTRY_PATTERN relaxation ---

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import guard_status_validator as _gsv  # noqa: E402
from guard_helpers import markers as _gm  # noqa: E402


class TestCitationPatternRelaxation:
    def test_citation_pattern_accepts_extended_extensions(self):
        p = _gsv.CITATION_PATTERN
        for ext_sample in (
            "`pytest.ini`",
            "`pyproject.toml`",
            "`.github/workflows/x.yml`",
            "`config.cfg`",
            "`run.sh`",
            "`docs/X.yaml`",
        ):
            assert p.search(f"per {ext_sample}"), f"should accept extended ext: {ext_sample!r}"

    def test_citation_pattern_accepts_chinese_paren_wrap(self):
        p = _gsv.CITATION_PATTERN
        for sample in (
            "fact （source: docs/X.md:42）",
            "fact （artifacts/scripts/X.py）",
            "fact （Source: docs/Y.md）",
        ):
            assert p.search(sample), f"should accept chinese-paren wrap: {sample!r}"

    def test_citation_pattern_accepts_bare_path_line(self):
        p = _gsv.CITATION_PATTERN
        for sample in (
            "per artifacts/scripts/test_guard_units.py:10610",
            "see docs/X.md",
            "ref artifacts/scripts/Y.py:42",
        ):
            assert p.search(sample), f"should accept bare path:line: {sample!r}"

    def test_citation_pattern_rejects_prose_period(self):
        p = _gsv.CITATION_PATTERN
        for sample in (
            "Python 3.14 released today",
            "section 5.7 covers it",
            "version v1.2.3 is current",
            "圖 1.2 顯示",
            "100.0 percent coverage",
        ):
            assert not p.search(sample), f"should NOT match prose: {sample!r}"

    def test_research_sources_entry_pattern_accepts_repo_path(self):
        sample = '[1] council-forge. "spec." docs/schemas/artifact-spec-research.md (2026-05-08 retrieved)'
        assert _gsv.research_source_entry_matches(sample), f"should accept repo-path source entry: {sample!r}"

    def test_research_sources_entry_pattern_still_accepts_url(self):
        sample = '[2] OWASP. "ReDoS." https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS (2026-05-08 retrieved)'
        assert _gsv.research_source_entry_matches(sample), f"should still accept URL source entry: {sample!r}"

    def test_research_sources_entry_pattern_rejects_title_without_period(self):
        # REDOS-01 fix preserves the prior `.+\..+` requirement that the title
        # region carry a period (the URL's own dot does not satisfy it).
        sample = '[1] Author "Title" https://example.com (2026-01-15 retrieved)'
        assert not _gsv.research_source_entry_matches(sample), (
            f"title without a period must be rejected: {sample!r}"
        )

    def test_research_sources_entry_pattern_rejects_non_entry_lines(self):
        for sample in ("https://bare.com", "just plain text",
                       "https://bare.com (2026-01 retrieved)"):
            assert not _gsv.research_source_entry_matches(sample), (
                f"non-entry line must be rejected: {sample!r}"
            )

    def test_research_sources_entry_pattern_is_linear_no_redos(self):
        # REDOS-01: a ~40 KB pathological `## Sources` line previously hung for
        # tens of seconds. The linear replacement must complete near-instantly.
        import time as _time
        payload = "[1] " + "a." * 20000 + " x"
        start = _time.perf_counter()
        result = _gsv.research_source_entry_matches(payload)
        elapsed = _time.perf_counter() - start
        assert result is False
        assert elapsed < 1.0, f"ReDoS regression: match took {elapsed:.2f}s on {len(payload)}B line"

    def test_citation_pattern_dual_site_consistency(self):
        # R4 mitigation: guard_status_validator.py and guard_helpers/markers.py
        # must keep CITATION_PATTERN literal-identical.
        assert _gsv.CITATION_PATTERN.pattern == _gm.CITATION_PATTERN.pattern, (
            "CITATION_PATTERN drift between guard_status_validator and guard_helpers.markers"
        )
