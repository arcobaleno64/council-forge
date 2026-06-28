#!/usr/bin/env python3
"""Stop hook: closure-phase reminder (advisory, never blocks).

Addresses the documented manual touchpoint where PROCESS_LEDGER / improvement
updates are easy to forget at task end. Opt-in via .claude/settings.json.example.
"""
import sys

if __name__ == "__main__":
    print(
        "[closure] Before marking a task done: ensure Build Guarantee evidence "
        "(commit hash / CI log / test result), update artifacts/improvement/PROCESS_LEDGER.md, "
        "and run guard_status_validator + guard_contract_validator. No artifact = not done.",
        file=sys.stderr,
    )
    sys.exit(0)
