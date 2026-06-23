# Guard Mutation-Testing Report

_Generated: 2026-06-23T01:10:12+08:00 · runtime: 52.7s · bounds: max_mutants=200, max_minutes=7.0_

Mutation testing applies small semantic mutations (a guard becoming too loose/strict) and checks whether the focused test suite **fails**. A **survived** mutant is a test blind spot: the guard could be weakened and no test would notice — the actionable output here.

## Per-module mutation score

| Module | Focused tests | Baseline pass | Mutants | Killed | Survived | Score |
|---|---|---:|---:|---:|---:|---:|
| `sast_gate.py` | test_sast_gate.py | 47 | 35 | 31 | **4** | 88.6% |
| `security_txt_gate.py` | test_security_txt_gate.py | 43 | 48 | 40 | **8** | 83.3% |
| `release_gate.py` | test_release_gate.py | 52 | 54 | 46 | **8** | 85.2% |
| **TOTAL** | | | 137 | 117 | **20** | 85.4% |

## Survived mutants (blind spots) — 20 total

| File:Line | Operator | Original → Mutated | Note |
|---|---|---|---|
| `sast_gate.py:36` | num_inc | `1 -> 2` |  |
| `sast_gate.py:37` | num_inc | `2 -> 3` |  |
| `sast_gate.py:37` | num_zero | `2 -> 0` |  |
| `sast_gate.py:197` | const_bool | `True -> False` |  |
| `security_txt_gate.py:39` | num_inc | `1 -> 2` |  |
| `security_txt_gate.py:40` | num_inc | `2 -> 3` |  |
| `security_txt_gate.py:40` | num_zero | `2 -> 0` |  |
| `security_txt_gate.py:149` | cmp_flip | `<= -> <` |  |
| `security_txt_gate.py:152` | cmp_flip | `> -> >=` |  |
| `security_txt_gate.py:168` | const_bool | `True -> False` |  |
| `security_txt_gate.py:172` | num_inc | `365 -> 366` |  |
| `security_txt_gate.py:172` | num_zero | `365 -> 0` |  |
| `release_gate.py:41` | num_inc | `1 -> 2` |  |
| `release_gate.py:42` | num_inc | `2 -> 3` |  |
| `release_gate.py:42` | num_zero | `2 -> 0` |  |
| `release_gate.py:215` | const_bool | `True -> False` |  |
| `release_gate.py:216` | const_bool | `True -> False` |  |
| `release_gate.py:224` | num_zero | `1 -> 0` |  |
| `release_gate.py:169` | num_inc | `12 -> 13` |  |
| `release_gate.py:169` | num_zero | `12 -> 0` |  |

## Interpretation

- **Killed** mutants confirm a real assertion guards that behavior.
- **Survived** mutants are blind spots: a maintainer (or attacker via a subtle PR) could flip that operator/constant/regex anchor and the suite stays green. Each row is a candidate for a new, targeted test.
- Line coverage was ~100% on these files; mutation score is materially lower, demonstrating coverage != mutation adequacy.
