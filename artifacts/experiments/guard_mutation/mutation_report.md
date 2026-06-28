# Guard Mutation-Testing Report

_Generated: 2026-06-28T05:08:59+08:00 · runtime: 40.32s · bounds: max_mutants=200, max_minutes=7.0_

Mutation testing applies small semantic mutations (a guard becoming too loose/strict) and checks whether the focused test suite **fails**. A **survived** mutant is a test blind spot: the guard could be weakened and no test would notice — the actionable output here.

## Per-module mutation score

| Module | Focused tests | Baseline pass | Mutants | Killed | Survived | Score |
|---|---|---:|---:|---:|---:|---:|
| `sast_gate.py` | test_sast_gate.py | 49 | 35 | 35 | **0** | 100.0% |
| `security_txt_gate.py` | test_security_txt_gate.py | 50 | 48 | 48 | **0** | 100.0% |
| `release_gate.py` | test_release_gate.py | 56 | 54 | 52 | **2** | 96.3% |
| **TOTAL** | | | 137 | 135 | **2** | 98.5% |

## Survived mutants (blind spots) — 2 total

| File:Line | Operator | Original → Mutated | Note |
|---|---|---|---|
| `release_gate.py:169` | num_inc | `12 -> 13` |  |
| `release_gate.py:169` | num_zero | `12 -> 0` |  |

## Interpretation

- **Killed** mutants confirm a real assertion guards that behavior.
- **Survived** mutants are blind spots: a maintainer (or attacker via a subtle PR) could flip that operator/constant/regex anchor and the suite stays green. Each row is a candidate for a new, targeted test.
- Line coverage was ~100% on these files; mutation score is materially lower, demonstrating coverage != mutation adequacy.
