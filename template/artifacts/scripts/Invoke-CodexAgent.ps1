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
    [switch]$AutoRestore = $false
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

    switch ($Scale) {
        { $_ -in @("tiny", "docs-only") } {
            return @{
                Effort = "low"
                Models = @("gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.4")
            }
        }
        "standard" {
            return @{
                Effort = "medium"
                Models = @("gpt-5.3-codex", "gpt-5.4", "gpt-5.4-mini")
            }
        }
        { $_ -in @("high-risk", "cross-module") } {
            return @{
                Effort = "high"
                Models = @("gpt-5.4", "gpt-5.3-codex", "gpt-5.4-mini")
            }
        }
        { $_ -in @("critical", "security", "architecture") } {
            return @{
                Effort = "xhigh"
                Models = @("gpt-5.4", "gpt-5.3-codex", "gpt-5.4-mini")
            }
        }
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

foreach ($model in $Models) {
    Write-Host "  -> Active Model Tier: $model" -ForegroundColor Cyan

    for ($attempt = 0; $attempt -le $MaxRetriesPerTier; $attempt++) {
        
        # Construct args
        $processArgs = @("exec", "-m", $model)
        if ($ApprovalMode -eq "full-auto") {
            $processArgs += "--full-auto"
        } else {
            $processArgs += "-a", $ApprovalMode
        }
        if (![string]::IsNullOrWhiteSpace($EffectiveReasoningEffort)) {
            $processArgs += "-c", "model_reasoning_effort=`"$EffectiveReasoningEffort`""
        }
        $processArgs += $Prompt
        Write-Host "    [*] Attempt $($attempt+1)/$($MaxRetriesPerTier+1)..." -ForegroundColor Gray
        
        $output = $null
        $errText = ""
        $combinedText = ""
        $lastExitCode = 1
        
        try {
            $procOutput = $null | & $Executable $processArgs 2>&1
            
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
            
            # Check outcome
            if ($lastExitCode -eq 0 -and -not ($combinedText -match $RegexPattern)) {
                $IsSuccess = $true
                $FinalOutput = $outText
                break
            } else {
                Write-Host "    [!] Intercepted API/Execution Error (ExitCode: $lastExitCode)" -ForegroundColor Yellow
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

# Layer A: post-dispatch write scope guard (TASK-1057).
# Runs whether dispatch succeeded or failed; reports unexpected file changes.
# Empty AllowedPaths = skip (backward compatible).
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

if ($AllowedPaths.Count -eq 0) {
    Write-Host "[GUARD] skipped (no AllowedPaths configured)" -ForegroundColor DarkGray
} else {
    Write-Host "[GUARD] Post-dispatch write scope check..." -ForegroundColor Cyan
    $rawStatus = & git status --porcelain 2>&1
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
        Write-Host "[GUARD] Post-dispatch detected unexpected file changes:" -ForegroundColor Red
        foreach ($v in $violations) { Write-Host "  - $v" -ForegroundColor Red }
        if ($AutoRestore) {
            foreach ($v in $violations) {
                & git ls-files --error-unmatch $v 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    & git checkout HEAD -- $v 2>$null | Out-Null
                    Write-Host "  Restored tracked: $v" -ForegroundColor Yellow
                } else {
                    if (Test-Path $v) {
                        Remove-Item -Path $v -Force -ErrorAction SilentlyContinue
                        Write-Host "  Deleted untracked: $v" -ForegroundColor Yellow
                    }
                }
            }
        }
        Write-Error "__GUARD_VIOLATION:[TASK-1057] Sub-agent wrote files outside AllowedPaths.__"
        exit 2
    } else {
        Write-Host "[GUARD] Post-dispatch check OK; all changes within allowed paths." -ForegroundColor Green
    }
}

# Wrap up
if ($IsSuccess) {
    Write-Output $FinalOutput
    exit 0
} else {
    Write-Error "__FATAL:[Blocked] All fallback models exhausted for Codex CLI.__`nReview terminal logs or quota statuses."
    exit 1
}
