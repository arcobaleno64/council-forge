<#
.SYNOPSIS
Resilient wrapper for the Codex CLI providing task-scale model selection and multi-tier fallback for API errors.

.DESCRIPTION
Wraps the codex CLI to catch 429 Too Many Requests, 400 Bad Request, and 5xx server errors.
Selects the default model and reasoning effort from the task scale unless explicitly overridden.
Executes standard Exponential Backoff.
If failures persist, dynamically steps through the fallback models for the selected task scale.
If models are exhausted, it switches to a Fallback API key and starts from the top model again.
Returns standard output on success or throws a fatal block if all options are exhausted.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$Prompt,

    [string]$ApprovalMode = "full-auto",

    [ValidateSet("tiny", "docs-only", "standard", "high-risk", "cross-module", "critical", "security", "architecture")]
    [string]$TaskScale = "standard",

    [ValidateSet("auto", "fixed", "fallback")]
    [string]$ModelPolicy = "auto",

    [string]$Model = "",
    
    [string]$ReasoningEffort = "",

    [int]$MaxRetriesPerTier = 2,
    [int]$BaseBackoffSeconds = 2,

    [string]$Executable = "codex.cmd",

    # Layer A of TASK-1057 sub-agent write scope guard.
    # Empty array (default) = guard skipped, backward compatible.
    # Element ending in '/' = directory prefix match; else exact file match.
    # Paths use forward slash (git convention).
    [string[]]$AllowedPaths = @(),
    [switch]$AutoRestore = $false,
    # TASK-1059: deprecated forward of -AutoRestore for backward-compat;
    # caller should migrate to -AutoRestore. Removed in a later task.
    [switch]$AutoRestoreLegacy = $false
)

# Core Error Patterns to Catch
$RetryPatterns = @(
    "429",
    "Too Many Requests",
    "RateLimitError",
    "400 Bad Request",
    "500 Internal Server",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "Failed to fetch",
    "ECONNRESET"
)
$RegexPattern = ($RetryPatterns | ForEach-Object { [regex]::Escape($_) }) -join '|'

function Get-TaskScaleProfile {
    param([string]$Scale)

    # TASK-1053 Layer 4: tier ladder v2 -- 3 tiers x effort=high.
    # Mapping of legacy 8-value ValidateSet preserved for backward compat.
    switch ($Scale) {
        { $_ -in @("tiny", "docs-only") } {
            return @{
                Effort = "high"
                Models = @("gpt-5.4-mini", "gpt-5.4", "gpt-5.5")
            }
        }
        "standard" {
            return @{
                Effort = "high"
                Models = @("gpt-5.4", "gpt-5.5", "gpt-5.4-mini")
            }
        }
        { $_ -in @("high-risk", "cross-module", "critical", "security", "architecture") } {
            return @{
                Effort = "high"
                Models = @("gpt-5.5", "gpt-5.4", "gpt-5.4-mini")
            }
        }
    }
}

# region TASK-1059 helpers: stash-based pre-dispatch baseline (Option B per
# artifacts/decisions/TASK-1057.decision.md). Replaces the prior git-status-only
# baseline that destroyed user pre-existing modifications.

function Test-PathInAllowed {
    param(
        [string]$Path,
        [string[]]$Allowed
    )
    foreach ($a in $Allowed) {
        $aNorm = $a -replace '\\', '/'
        if ($aNorm.EndsWith('/')) {
            if ($Path.StartsWith($aNorm)) { return $true }
        } else {
            if ($Path -eq $aNorm) { return $true }
        }
    }
    return $false
}

function Save-PreDispatchState {
    # Stash tracked-modified + untracked files so dispatch runs on a clean tree
    # and post-dispatch git status reflects only sub-agent writes.
    # Returns the stash ref string, or $null if nothing was stashed.
    $rawStatus = & git status --porcelain --untracked-files=all 2>&1
    $hasChanges = $false
    foreach ($line in $rawStatus) {
        if (-not [string]::IsNullOrWhiteSpace($line)) { $hasChanges = $true; break }
    }
    if (-not $hasChanges) {
        Write-Host "[GUARD] Pre-dispatch: working tree clean; no stash needed." -ForegroundColor DarkGray
        return $null
    }
    $timestamp = Get-Date -Format 'yyyyMMddHHmmss'
    $stashMsg = "TASK-1057 pre-dispatch $timestamp"
    & git stash push -u -m $stashMsg 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[GUARD] FATAL: git stash push -u failed (exit=$LASTEXITCODE); aborting dispatch." -ForegroundColor Red
        Write-Error "__GUARD_FATAL:[TASK-1057] Pre-dispatch stash failed; cannot establish baseline.__"
        exit 4
    }
    $stashListLine = (& git stash list --max-count=1) | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($stashListLine)) {
        Write-Host "[GUARD] WARN: stash push reported success but stash list empty; treating as no-stash." -ForegroundColor DarkYellow
        return $null
    }
    $stashRef = ($stashListLine -split ': ', 2)[0]
    Write-Host "[GUARD] Pre-dispatch state stashed at $stashRef" -ForegroundColor DarkCyan
    return $stashRef
}

function Restore-PostDispatchDelta {
    # Targeted restore for the supplied violations list only; never operates on
    # the full repo (root cause of the TASK-1057 destruction incident).
    param(
        [string[]]$Violations
    )
    foreach ($v in $Violations) {
        & git ls-files --error-unmatch $v 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            & git checkout HEAD -- $v 2>$null | Out-Null
            Write-Host "  Restored tracked (sub-agent write): $v" -ForegroundColor Yellow
        } else {
            if (Test-Path $v) {
                Remove-Item -Path $v -Force -Recurse -ErrorAction SilentlyContinue
                Write-Host "  Deleted untracked (sub-agent write): $v" -ForegroundColor Yellow
            }
        }
    }
}

function Pop-PreDispatchState {
    # Restore user pre-dispatch state from stash. Conflict -> exit 3 fail-safe;
    # stash entry is preserved (not dropped) for manual resolution.
    param([string]$StashRef)
    if ([string]::IsNullOrWhiteSpace($StashRef)) { return 0 }
    $popOutput = & git stash pop $StashRef 2>&1
    $popExit = $LASTEXITCODE
    $hasConflict = ($popOutput | Out-String) -match 'CONFLICT \('
    if ($popExit -ne 0 -or $hasConflict) {
        Write-Host "[FATAL] git stash pop conflict (exit=$popExit); user pre-dispatch state preserved at $StashRef." -ForegroundColor Red
        Write-Host "        Manual resolution: git stash list ; then git stash apply $StashRef ; resolve conflicts ; git stash drop $StashRef" -ForegroundColor Red
        return 3
    }
    Write-Host "[GUARD] User pre-dispatch state restored from $StashRef." -ForegroundColor DarkCyan
    return 0
}

# endregion TASK-1059 helpers

# TASK-1059: forward deprecated -AutoRestoreLegacy to -AutoRestore.
if ($AutoRestoreLegacy) {
    if ($AutoRestore) {
        Write-Host "[DEPRECATED] -AutoRestore and -AutoRestoreLegacy both set; -AutoRestore wins." -ForegroundColor DarkYellow
    } else {
        Write-Host "[DEPRECATED] -AutoRestoreLegacy maps to -AutoRestore for backward-compat; expect removal in a later task." -ForegroundColor DarkYellow
        $AutoRestore = $true
    }
}

$Profile = Get-TaskScaleProfile -Scale $TaskScale
$EffectiveReasoningEffort = if ([string]::IsNullOrWhiteSpace($ReasoningEffort)) { $Profile.Effort } else { $ReasoningEffort }
$Models = @($Profile.Models)

if (![string]::IsNullOrWhiteSpace($Model)) {
    if ($ModelPolicy -eq "fixed") {
        $Models = @($Model)
    } else {
        $Models = @($Model) + ($Models | Where-Object { $_ -ne $Model })
    }
}

Write-Host "  -> Task Scale: $TaskScale; Model Policy: $ModelPolicy; Reasoning Effort: $EffectiveReasoningEffort" -ForegroundColor Cyan

$IsSuccess = $false
$FinalOutput = ""
# TASK-1053: track last attempt's stdout for best-effort capture even when all
# tiers exhaust. Lets callers (e.g. Invoke-CodexReview.ps1) preserve content
# Codex actually produced even though the wrapper marked the dispatch failed.
$BestEffortOutput = ""

# TASK-1059: snapshot user pre-dispatch state so post-dispatch git status
# reflects only sub-agent writes, never user pre-existing modifications.
$preDispatchStashRef = $null
if ($AllowedPaths.Count -gt 0) {
    $preDispatchStashRef = Save-PreDispatchState
}

foreach ($model in $Models) {
    Write-Host "  -> Active Model Tier: $model" -ForegroundColor Cyan

    for ($attempt = 0; $attempt -le $MaxRetriesPerTier; $attempt++) {

        # TASK-1053 Layer 3: top-level -a never -s workspace-write replace deprecated --full-auto.
        # Order matters: -a / -s are top-level flags and must precede the `exec` subcommand.
        # ApprovalMode param retained as backward-compat no-op.
        $processArgs = @("-a", "never", "-s", "workspace-write", "exec", "-m", $model)
        if (![string]::IsNullOrWhiteSpace($EffectiveReasoningEffort)) {
            $processArgs += "-c", "model_reasoning_effort=`"$EffectiveReasoningEffort`""
        }

        # TASK-1053 Layer 1: switch to stdin pipe when prompt exceeds 7000 chars
        # to bypass Windows cmd.exe 8191-char command-line limit.
        $useStdinPipe = $Prompt.Length -gt 7000
        if (-not $useStdinPipe) {
            $processArgs += $Prompt
        }
        Write-Host "    [*] Attempt $($attempt+1)/$($MaxRetriesPerTier+1) (stdin_pipe=$useStdinPipe, prompt_size=$($Prompt.Length))..." -ForegroundColor Gray

        $output = $null
        $errText = ""
        $combinedText = ""
        $lastExitCode = 1

        try {
            if ($useStdinPipe) {
                $procOutput = $Prompt | & $Executable $processArgs 2>&1
            } else {
                $procOutput = $null | & $Executable $processArgs 2>&1
            }

            $stdOutLines = @()
            $stdErrLines = @()
            foreach ($line in $procOutput) {
                if ($line -is [System.Management.Automation.ErrorRecord]) {
                    $stdErrLines += $line.Exception.Message
                } else {
                    $stdOutLines += $line
                }
            }

            $outText = $stdOutLines -join "`n"
            $errText = $stdErrLines -join "`n"
            $lastExitCode = $LASTEXITCODE

            $combinedText = "$outText`n$errText"

            # TASK-1053: remember the best-effort stdout (any non-trivial content from
            # any attempt) so the caller can recover Codex output even when the wrapper
            # ultimately decides the dispatch failed.
            if (![string]::IsNullOrWhiteSpace($outText) -and $outText.Length -gt $BestEffortOutput.Length) {
                $BestEffortOutput = $outText
            }

            # Check outcome -- codex CLI 0.128 exit code is the source of truth.
            # The retry-pattern check stays only as a guard for transient errors
            # that might leak through with exit 0 (rare).
            if ($lastExitCode -eq 0 -and -not ($combinedText -match $RegexPattern)) {
                $IsSuccess = $true
                $FinalOutput = $outText
                break
            } else {
                Write-Host "    [!] Intercepted API/Execution Error (ExitCode: $lastExitCode)" -ForegroundColor Yellow
                # TASK-1053 Layer 2: dump last 30 lines of combined stdout/stderr so the
                # underlying CLI error is visible before retry/escalation.
                if (![string]::IsNullOrWhiteSpace($combinedText)) {
                    $tailLines = ($combinedText -split "`n" | Select-Object -Last 30) -join "`n"
                    Write-Host "    [stderr tail]" -ForegroundColor DarkRed
                    Write-Host $tailLines -ForegroundColor DarkRed
                }
            }

        } catch {
            Write-Host "    [!] Process Exception Caught: $($_.Exception.Message)" -ForegroundColor Red
            $combinedText = $_.Exception.Message
        }

        # Calculate backoff if not last attempt
        if ($attempt -lt $MaxRetriesPerTier) {
            if ($combinedText -match $RegexPattern) {
                $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                Write-Host "    [Backoff] Target error string matched. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds $sleepTime
            } else {
                $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                Write-Host "    [Backoff] Generic failure. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds $sleepTime
            }
        }
    } # End Attempt Loop

    if ($IsSuccess) { break }
    Write-Host "  -> Exhausted retries for $model. Escalating tier (fallback)..." -ForegroundColor Magenta
} # End Model Loop

# Layer A: post-dispatch write scope guard (TASK-1057, baseline-fixed by TASK-1059).
# With Save-PreDispatchState stashed user state, git status reflects only sub-agent
# writes. Empty AllowedPaths = skip (backward compatible).
$violationsFound = $false
$violationCount = 0
if ($AllowedPaths.Count -eq 0) {
    Write-Host "[GUARD] skipped (no AllowedPaths configured)" -ForegroundColor DarkGray
} else {
    Write-Host "[GUARD] Post-dispatch write scope check (stash-based baseline)..." -ForegroundColor Cyan
    $rawStatus = & git status --porcelain --untracked-files=all 2>&1
    $changedPaths = @()
    foreach ($line in $rawStatus) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $rest = $line.Substring([Math]::Min(3, $line.Length))
        if ($rest -match ' -> ') { $rest = ($rest -split ' -> ')[-1] }
        $rest = $rest.Trim().Trim('"')
        $rest = $rest -replace '\\', '/'
        if ($rest) { $changedPaths += $rest }
    }
    $violations = @()
    foreach ($p in $changedPaths) {
        if (-not (Test-PathInAllowed -Path $p -Allowed $AllowedPaths)) {
            $violations += $p
        }
    }
    if ($violations.Count -gt 0) {
        $violationsFound = $true
        $violationCount = $violations.Count
        Write-Host "[GUARD] Post-dispatch detected sub-agent writes outside AllowedPaths:" -ForegroundColor Red
        foreach ($v in $violations) { Write-Host "  - $v" -ForegroundColor Red }
        if ($AutoRestore) {
            Restore-PostDispatchDelta -Violations $violations
        } else {
            Write-Host "[GUARD] Detect-only mode (-AutoRestore not set); violations reported but not restored." -ForegroundColor DarkYellow
        }
    } else {
        Write-Host "[GUARD] Post-dispatch check OK; all changes within allowed paths." -ForegroundColor Green
    }
}

# TASK-1059: restore user pre-dispatch state. Conflict -> exit 3 fail-safe.
$popExit = Pop-PreDispatchState -StashRef $preDispatchStashRef
if ($popExit -eq 3) { exit 3 }

# TASK-1059: re-emit violation error after stash pop so guard exit reflects
# the violation outcome (not the dispatch outcome).
if ($violationsFound -and $AutoRestore) {
    Write-Error "__GUARD_VIOLATION:[TASK-1057] Sub-agent wrote $violationCount files outside AllowedPaths.__"
    exit 2
}

# Wrap up
if ($IsSuccess) {
    Write-Output $FinalOutput
    exit 0
} else {
    # TASK-1053: emit best-effort stdout (if any) before the FATAL marker so
    # callers like Invoke-CodexReview.ps1 still capture review text even when
    # the wrapper considers the dispatch failed.
    if (![string]::IsNullOrWhiteSpace($BestEffortOutput)) {
        Write-Output $BestEffortOutput
    }
    Write-Error "__FATAL:[Blocked] All fallback models exhausted for Codex CLI.__`nReview terminal logs or quota statuses."
    exit 1
}
