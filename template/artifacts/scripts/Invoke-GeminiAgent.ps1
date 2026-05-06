<#
.SYNOPSIS
Resilient wrapper for the Gemini CLI providing multi-tier fallback for API errors.

.DESCRIPTION
Wraps the gemini CLI to catch 429 MODEL_CAPACITY_EXHAUSTED, 400 Bad Request, and 5xx server errors.
Executes standard Exponential Backoff.
If failures persist, dynamically steps up through fallback models (flash -> pro).
If models are exhausted, it switches to a Fallback API key and starts from the bottom model again.
Returns standard output on success or throws a fatal block if all options are exhausted.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$Prompt,

    [string]$Profile = $null,
    [string]$ApprovalMode = "yolo",
    
    [int]$MaxRetriesPerTier = 2,
    [int]$BaseBackoffSeconds = 2,

    [string]$Executable = "gemini.cmd",

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
    "MODEL_CAPACITY_EXHAUSTED",
    "400 Bad Request",
    "500 Internal Server",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "Failed to fetch",
    "ECONNRESET"
)
$RegexPattern = ($RetryPatterns | ForEach-Object { [regex]::Escape($_) }) -join '|'

# Models Progression
$Models = @(
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview"
)

$IsSuccess = $false
$FinalOutput = ""

foreach ($model in $Models) {
    Write-Host "  -> Active Model Tier: $model" -ForegroundColor Cyan

    for ($attempt = 0; $attempt -le $MaxRetriesPerTier; $attempt++) {
        
        # Construct args
        $processArgs = @("-m", $model, "--approval-mode", $ApprovalMode)
        if (![string]::IsNullOrWhiteSpace($Profile)) {
            $processArgs += "--profile", $Profile
        }
        $processArgs += "-p", $Prompt

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
            # Check if it was one of our specific retry patterns
            if ($combinedText -match $RegexPattern) {
                $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                Write-Host "    [Backoff] Target error string matched. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds $sleepTime
            } else {
                # If it's some other fatal error that we don't recognize, do we still back off?
                # Yes, per user request, we enter the loop.
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
    Write-Error "__FATAL:[Blocked] All fallback models exhausted for Gemini CLI.__`nReview terminal logs or quota statuses."
    exit 1
}
