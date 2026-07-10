# Relaxation Log

本檔只記事實，不重述規則正文；規則面說明與 gate 語意請回看 [`.github/memory-bank/workflow-gates.md`](../../.github/memory-bank/workflow-gates.md)。

## Rules

- 每筆只寫 date / rule location / before / after / trigger task / root cause classification / provenance。
- citation 必須能以 repo grep 直驗；查無者明寫 `provenance: unrecorded`。
- 累積達 3 筆以上時，當次 closure 升級 architect review。
- 本檔記錄之 intervention telemetry（實際放寬案例）與 `guard_calibration_matrix.py` 量測之 evaluation telemetry（FP/FN）為兩種不同來源，不得合併成單一治理指標（Goodhart's Law，TASK-1108）。
- 任一案例若構成治理規則之建制變動（CI gate、guard 定義、telemetry schema、model 角色、escalation 規則、pass/fail 門檻、report 格式或 prompt 政策之變更），該案例前後之 telemetry 不得直接比較，須附加正規化說明或「不可比較」但書（Lucas Critique，TASK-1109）。

## Cases

### 2026-05-08 — `CITATION_PATTERN`

- Rule Location: `artifacts/scripts/guard_status_validator.py:137`, `artifacts/scripts/guard_helpers/markers.py:17`
- Before: 只接受 URL、`` `gh api ...` ``、或有限副檔名的 backtick-wrapped 檔案引用。
- After: 接受 5-branch alternation，含中英括號 wrap、裸 `path:line`，並把 ext list 擴到 12 種。
- Trigger Task: `TASK-1061`
- Root Cause Classification: citation-format narrowness
- Provenance: `artifacts/research/TASK-1061.research.md:17-22`; `artifacts/verify/TASK-1061.verify.md:15,35-43`

### 2026-05-08 — `RESEARCH_SOURCES_ENTRY_PATTERN`

- Rule Location: `artifacts/scripts/guard_status_validator.py:195`
- Before: `## Sources` 條目強制要求 `https?://...`。
- After: 接受 `URL OR repo path`，允許 `docs/X.md` 這類 in-repo 來源。
- Trigger Task: `TASK-1061`
- Root Cause Classification: internal-reference friction
- Provenance: `artifacts/research/TASK-1061.research.md:18,22,60`; `artifacts/verify/TASK-1061.verify.md:16,47-49`

### 2026-05-07 — `generic` → `docs-spec` adapter

- Rule Location: `docs/schemas/artifact-spec-task.md:68`
- Before: `generic` baseline 不區分 docs-only 任務；`testing / verifying / done` 仍帶 `test` requirement。
- After: `docs-spec` 會移除 `test` requirement，並允許 `NOT_APPLICABLE_BY_ADAPTER`。
- Trigger Task: `TASK-1058`（first confirmed use）
- Root Cause Classification: provenance unrecorded
- Provenance: `docs/schemas/artifact-spec-task.md:68`; `artifacts/tasks/TASK-1058.task.md:107`; `artifacts/verify/TASK-1058.verify.md:12,17,151,155`; establishment provenance: unrecorded

### unrecorded — `available_artifacts mismatch`

- Rule Location: `artifacts/scripts/guard_status_validator.py:2159`
- Before: unrecorded
- After: `available_artifacts mismatch` 會以 warning surfaced，而非直接單獨 fail-closed。
- Trigger Task: first in-repo observation `TASK-1049`
- Root Cause Classification: provenance unrecorded
- Provenance: `artifacts/scripts/guard_status_validator.py:2159`; `artifacts/scripts/test_guard_status_validator_artifacts.py:1647`; `artifacts/code/TASK-1049.code.md:99`; establishment provenance: unrecorded
