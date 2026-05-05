#!/usr/bin/env python3
"""TASK-1037 fixture wrapper for run_quality_gates.py.

Loads the production runner via importlib and overrides detect_repo_root()
to anchor the runner at this fixture repo root instead of the real
consilium-fabri repo root. Production runner bytes are not modified.
"""
import sys
sys.dont_write_bytecode = True
import importlib.util
from pathlib import Path

WRAPPER_PATH = Path(__file__).resolve()
FIXTURE_ROOT = WRAPPER_PATH.parent
REPO_ROOT = WRAPPER_PATH.parents[5]
PROD_RUNNER = REPO_ROOT / "artifacts" / "scripts" / "run_quality_gates.py"

spec = importlib.util.spec_from_file_location("runner_under_test", str(PROD_RUNNER))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.detect_repo_root = lambda: FIXTURE_ROOT

sys.exit(mod.main(sys.argv[1:]))
