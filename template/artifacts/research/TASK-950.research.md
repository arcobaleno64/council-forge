# Research: TASK-950

## Metadata
- Task ID: TASK-950
- Artifact Type: research
- Owner: Gemini
- Status: ready
- Last Updated: 2026-04-11T11:00:00+08:00

## Research Questions
- 研究角色越界時，哪些 gate / artifact 應該負責攔截與收斂？
- Codex 若提出超出 plan 的必要修改，合法流程應如何記錄？

## Confirmed Facts
- Gemini CLI 的 research 輸出必須維持 fact-only，不得把 implementation plan 或 solution design 混入 research artifact（source: `docs/subagent_roles.md`).
- Implementation 不得引入未明確映射到 plan 的修改；若發生取捨或擴大範圍，應建立 decision artifact 記錄（source: `docs/workflow_state_machine.md`; `docs/artifact_schema.md`).
- verify artifact 必須逐條對照 acceptance criteria，並以 evidence 指向上游 artifacts，因此角色越界若被修正，必須反映在 decision / improvement / verify 鏈上（source: `docs/artifact_schema.md`).

## Relevant References
- `docs/subagent_roles.md`
- `docs/workflow_state_machine.md`
- `docs/artifact_schema.md`

## Sources
[1] Arcobaleno64. "subagent_roles.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/subagent_roles.md (2026-04-15 retrieved)
[2] Arcobaleno64. "workflow_state_machine.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/workflow_state_machine.md (2026-04-15 retrieved)
[3] Arcobaleno64. "artifact_schema.md." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/artifact_schema.md (2026-04-15 retrieved)

## Uncertain Items
None

## Constraints For Implementation
- 最終 research artifact 只能保留事實、引用與 implementation constraints。
- live drill 可以描述越界事件，但不得把越界內容當成合法最終輸出保留下來。
