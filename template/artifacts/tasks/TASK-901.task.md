# Task: TASK-901 Layered Mail Security Filtering

## Metadata
- Task ID: TASK-901
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-10T15:21:52.4196845+08:00

## Objective
在 Wino-Mail 中加入 layered mail security filtering，新增 `IMailSecurityService` 作為可重用的 domain/service security layer。第一版只實際接到 `mail reader`，但設計必須可重用到 `preview` 與 `notifications`。

## Background
目前 Wino-Mail 的 mail reader 渲染流程是由 `MailRenderingPageViewModel` 透過 `IMimeFileService.GetMailRenderModel(...)` 取得 HTML，再交由 `WebView2` 顯示。現有流程只有基礎的圖片與樣式移除，尚未形成完整的 HTML sanitization、external resource blocking、以及 link protection 層。

## Inputs
- User requirement: layered security approach for rendered mail content
- `external/Wino-Mail/Wino.Core.Domain/Interfaces/IMailService.cs`
- `external/Wino-Mail/Wino.Core.Domain/Interfaces/IMimeFileService.cs`
- `external/Wino-Mail/Wino.Services/MimeFileService.cs`
- `external/Wino-Mail/Wino.Mail.ViewModels/MailRenderingPageViewModel.cs`
- `external/Wino-Mail/Wino.Mail/Views/MailRenderingPage.xaml`
- `external/Wino-Mail/Wino.Mail/Views/MailRenderingPage.xaml.cs`

## Constraints
- Do not implement attachment scanning
- Service layer must not contain UI logic
- ViewModel must not duplicate filtering logic
- Security baseline takes precedence over rendering preferences such as `RenderImages`, `RenderStyles`, and `RenderPlaintextLinks`
- First delivery only wires the feature into `mail reader`
- Sanitized output must remain reusable for `preview` and `notifications`

## Acceptance Criteria
- [ ] `IMailSecurityService` exists in the domain/service layer
- [ ] Service outputs sanitized mail content as pure data without UI decisions
- [ ] Service handles HTML sanitization, external resource stripping, and basic link normalization/protection
- [ ] ViewModel exposes `SanitizedContent`, `HasBlockedContent`, and `SecurityWarnings`
- [ ] UI shows a warning banner when content is blocked or rewritten
- [ ] UI shows placeholders for blocked external images
- [ ] Filtering logic exists in one reusable service pipeline and is not duplicated in ViewModel
- [ ] First implementation is wired into `mail reader` without breaking MVVM separation of concerns

## Dependencies
- `template/artifacts/scripts/Invoke-GeminiAgent.ps1`
- Gemini CLI access for research phase

## Out of Scope
- Attachment scanning
- Actual wiring for `preview` or `notifications` in this task
- Broad refactors outside the mail rendering security pipeline

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Intake completed. Research dispatch attempted via `template/artifacts/scripts/Invoke-GeminiAgent.ps1` but is currently blocked because the environment does not provide `GEMINI_API_KEY` or `GEMINI_FALLBACK_API_KEY`.
