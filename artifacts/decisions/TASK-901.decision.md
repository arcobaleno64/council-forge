# Decision Log: TASK-901

## Metadata
- Task ID: TASK-901
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-10T15:21:52.4196845+08:00

## Decision Class
risk-acceptance

## Affected Gate
Gate_A

## Scope
Current task artifact governance and exception handling.

## Issue
`TASK-901` research phase was required to run through `template/artifacts/scripts/Invoke-GeminiAgent.ps1`, but the wrapper failed both inside and outside the sandbox because neither `GEMINI_API_KEY` nor `GEMINI_FALLBACK_API_KEY` was available in the environment.

## Options Considered
- Retry the same Gemini wrapper outside the sandbox to confirm the issue was not sandbox-specific
- Skip Gemini and perform substitute research with a different tool
- Stop the workflow and record a blocked state until Gemini credentials are provided

## Chosen Option
Stop the workflow and record `TASK-901` as blocked until Gemini credentials are available.

## Reasoning
The project workflow explicitly requires Gemini CLI as the research agent for this phase, and the user also specified the resilient Gemini wrapper as the required dispatch mechanism. Replacing it with another research path would violate the agreed workflow and produce artifacts that do not match the required gate. The wrapper was retried outside the sandbox and returned the same fatal credential error, so this is an environment prerequisite issue rather than a sandbox restriction.

## Implications
- `TASK-901` cannot legally advance from `drafted` to `researched`
- No `research` artifact can be marked `ready` yet
- Planning and coding gates remain closed
- The next required action is to make Gemini credentials available in the execution environment and rerun the research dispatch

## Expiry
None

## Linked Artifacts
- `artifacts/tasks/TASK-901.task.md`
- `artifacts/status/TASK-901.status.json`

## Follow Up
[WARN] migrated default: Decision Class defaulted to risk-acceptance.
- Provide `GEMINI_API_KEY` or `GEMINI_FALLBACK_API_KEY` in the environment used by `template/artifacts/scripts/Invoke-GeminiAgent.ps1`
- Re-run the Gemini wrapper for `TASK-901`
- Once a valid `artifacts/research/TASK-901.research.md` is produced with `Status: ready`, update status from `blocked` to `researched`

## Guard Exception
None

## Amendment (2026-06-13): Abandonment (commander ruling)

主公 2026-06-13 裁 **TASK-901 棄置（abandon）**。緣由：本 task 標的 `external/Wino-Mail/` 已自 workspace 移除（status `blocked_reason` 自原「Gemini 憑證缺」演為「Archived: Wino-Mail no longer exists」），主公決定**不 re-clone、不續做**。

workflow state machine（`WORKFLOW_STATES`）僅 8 態、無 `rejected`/`archived`/`abandoned` 終態；blocked 唯能經 Gate E improvement artifact 返前態以「解封續做」。故棄置之誠實表徵＝**留於 blocked（唯一 parked sink）**，並以本 amendment ＋ status `blocked_reason` 明標 ABANDONED、清 `next_agent`（不再候 User re-clone）。此非「done」（未完成）、非暫時 blocked（不待解），乃**永久棄置**。原 §Issue/§Follow Up 之「補 Gemini 憑證重跑」路徑隨棄置失效。
