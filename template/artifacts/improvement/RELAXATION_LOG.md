# Relaxation Log

本檔只記事實，不重述規則正文；規則面說明與 gate 語意請回看 [`.github/memory-bank/workflow-gates.md`](../../.github/memory-bank/workflow-gates.md)。

## Rules

- 每筆只寫 date / rule location / before / after / trigger task / root cause classification / provenance。
- citation 必須能以 repo grep 直驗；查無者明寫 `provenance: unrecorded`。
- 累積達 3 筆以上時，當次 closure 升級 architect review。
- 本檔記錄之 intervention telemetry（實際放寬案例）與 `guard_calibration_matrix.py` 量測之 evaluation telemetry（FP/FN）為兩種不同來源，不得合併成單一治理指標（Goodhart's Law，TASK-1108）。
- 任一案例若構成治理規則之建制變動（CI gate、guard 定義、telemetry schema、model 角色、escalation 規則、pass/fail 門檻、report 格式或 prompt 政策之變更），該案例前後之 telemetry 不得直接比較，須附加正規化說明或「不可比較」但書（Lucas Critique，TASK-1109）。

## Cases

### YYYY-MM-DD — `<rule-name>`

- Rule Location: `<path:line>`
- Before: `<before summary>`
- After: `<after summary>`
- Trigger Task: `<TASK-XXX>`
- Root Cause Classification: `<classification>`
- Provenance: `<path:line>` or `provenance: unrecorded`
