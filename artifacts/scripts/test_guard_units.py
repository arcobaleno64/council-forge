"""Backward-compatible shim for TASK-1054 split guard unit tests."""
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
