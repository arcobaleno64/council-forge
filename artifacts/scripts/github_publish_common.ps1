#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Shared helper functions for GitHub publish scripts (wiki, release).
.DESCRIPTION
    Provides unified auth probing, owner/repo resolution, gh CLI checks,
    and standardised exit codes for push-wiki.ps1 and publish-release.ps1.
#>

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
$script:EXIT_OK              = 0
$script:EXIT_AUTH_MISSING    = 10
$script:EXIT_GH_CLI_MISSING  = 11
$script:EXIT_WIKI_NOT_INIT   = 12
$script:EXIT_REMOTE_UNREACHABLE = 13
$script:EXIT_PRECONDITION_FAIL  = 14
$script:EXIT_PUBLISH_FAIL       = 20

# ---------------------------------------------------------------------------
# Resolve owner/repo from git remote
# ---------------------------------------------------------------------------
function Get-OwnerRepo {
    [CmdletBinding()]
    param(
        [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
    )
    Push-Location $RepoRoot
    try {
        $remote = git remote get-url origin 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Cannot read git remote 'origin'."
        }
        # Match https://github.com/OWNER/REPO or git@github.com:OWNER/REPO
        if ($remote -match 'github\.com[:/]([^/]+)/([^/.]+)') {
            return @{ Owner = $Matches[1]; Repo = $Matches[2] }
        }
        throw "Cannot parse owner/repo from remote: $remote"
    }
    finally { Pop-Location }
}

# ---------------------------------------------------------------------------
# Auth probe: GH_TOKEN / GITHUB_TOKEN env var, then gh auth status
# Returns the token string or $null.
# ---------------------------------------------------------------------------
function Test-GitHubAuth {
    [CmdletBinding()]
    param()

    # 1. Environment variables (CI-friendly)
    foreach ($varName in @('GH_TOKEN', 'GITHUB_TOKEN')) {
        $val = [System.Environment]::GetEnvironmentVariable($varName)
        if ($val) {
            Write-Verbose "Auth: using $varName environment variable."
            return $val
        }
    }

    # 2. gh CLI auth
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        $null = gh auth status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Verbose "Auth: using gh CLI credential store."
            return '__GH_CLI__'
        }
    }

    return $null
}

# ---------------------------------------------------------------------------
# Check gh CLI availability
# ---------------------------------------------------------------------------
function Test-GhCli {
    [CmdletBinding()]
    param()
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Warning "gh CLI is not installed or not in PATH."
        return $false
    }
    return $true
}

# ---------------------------------------------------------------------------
# Check remote reachability via git ls-remote
# ---------------------------------------------------------------------------
function Test-RemoteReachable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Url
    )
    $null = git ls-remote --exit-code $Url 2>&1
    return ($LASTEXITCODE -eq 0)
}

# ---------------------------------------------------------------------------
# True repository root (TASK-1089 / FB-2)
# `Split-Path -Parent $PSScriptRoot` only yields artifacts/; the release surface
# (.well-known/release-manifest.json, template/) lives at the REAL repo root.
# ---------------------------------------------------------------------------
function Get-RepoRoot {
    [CmdletBinding()]
    param([string]$StartDir = $PSScriptRoot)
    Push-Location $StartDir
    try {
        $root = git rev-parse --show-toplevel 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Cannot determine repository root (git rev-parse --show-toplevel failed): $root"
        }
        return (@($root)[0]).Trim()
    }
    finally { Pop-Location }
}

# ---------------------------------------------------------------------------
# Release-integrity gate (TASK-1089 / FB-2): couple verification to publish.
# Mirrors the CI release-integrity job's STRUCTURAL integrity: the published
# manifest must match the template snapshot (tree<->manifest, catches a stale but
# structurally-valid manifest) AND pass the structural gate (schema/algo/digests).
# Throws (fail-closed) on either failure.
# ---------------------------------------------------------------------------
function Invoke-ReleaseIntegrityGate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$ScriptDir
    )
    $manifest = Join-Path $RepoRoot '.well-known/release-manifest.json'
    $templateRoot = Join-Path $RepoRoot 'template'
    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        throw "release-integrity: manifest not found: $manifest (fail-closed)."
    }
    # 1. tree<->manifest consistency (a stale manifest that no longer matches template/ fails here).
    $null = & python (Join-Path $ScriptDir 'snapshot_manifest.py') verify --template-root $templateRoot --manifest $manifest 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "release-integrity: published manifest does not match the template snapshot (fail-closed)."
    }
    # 2. structural gate (schema / algorithm allowlist / digests / min-entries).
    $null = & python (Join-Path $ScriptDir 'release_gate.py') --file $manifest --format checksums 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "release-integrity: structural gate failed on the manifest (fail-closed)."
    }
}

# ---------------------------------------------------------------------------
# Signing TRIAD state (TASK-1089 / FB-2): pinned fingerprint + detached signature
# + published public key. Used to decide armed-vs-unprovisioned exactly like CI.
# ---------------------------------------------------------------------------
function Get-SigningTriadState {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $pin = [System.Environment]::GetEnvironmentVariable('EXPECTED_SIGNING_FINGERPRINT')
    $sig = Join-Path $RepoRoot '.well-known/release-manifest.json.asc'
    $pub = Join-Path $RepoRoot '.well-known/release-signing.pub'
    $hasPin = -not [string]::IsNullOrWhiteSpace($pin)
    $hasSig = Test-Path -LiteralPath $sig -PathType Leaf
    $hasPub = Test-Path -LiteralPath $pub -PathType Leaf
    $present = 0
    if ($hasPin) { $present++ }
    if ($hasSig) { $present++ }
    if ($hasPub) { $present++ }
    return @{
        Pin = $pin; HasPin = $hasPin
        SigPath = $sig; HasSig = $hasSig
        PubPath = $pub; HasPub = $hasPub
        Present = $present
    }
}

# ---------------------------------------------------------------------------
# Signer binding (TASK-1089 / FB-2): given GnuPG --status-fd lines, return $true ONLY if a
# VALIDSIG line binds to the pinned fingerprint by EXACT field equality — mirror of the CI awk
#   $1=='[GNUPG:]' && $2=='VALIDSIG' && ($3==want || $NF==want)
# ($3 = signing-key fpr, $NF = primary-key fpr, to allow subkey signing). NOT a substring/regex
# match: gpg --verify exits 0 on ANY good signature from ANY imported key, so this exact binding
# is what rejects an attacker key appended to the bundle. Pure -> unit-testable without gpg.
# ---------------------------------------------------------------------------
function Test-PinnedValidSig {
    [CmdletBinding()]
    param(
        [string[]]$StatusLines,
        [Parameter(Mandatory)][string]$Want
    )
    foreach ($line in @($StatusLines)) {
        $fields = @(-split $line)
        if ($fields.Count -ge 3 -and $fields[0] -eq '[GNUPG:]' -and $fields[1] -eq 'VALIDSIG') {
            if ($fields[2] -eq $Want -or $fields[-1] -eq $Want) { return $true }
        }
    }
    return $false
}

# ---------------------------------------------------------------------------
# Assert the release-manifest signature (TASK-1089 / FB-2), mirroring the CI
# release-integrity job's gpg logic:
#   - triad ZERO present -> 'unprovisioned' (caller decides; default fail-closed
#     unless an explicit operator opt-in).
#   - ANY member present -> ARMED: ALL three must be present + a VALIDSIG bound to
#     the pinned 40-hex fingerprint by EXACT field equality, else THROW (fail-closed).
#     Removing a signature/pubkey or unsetting the pin after provisioning therefore
#     CANNOT silently disable enforcement.
# Returns 'verified' | 'unprovisioned'; throws on any ARMED failure.
# ---------------------------------------------------------------------------
function Assert-ReleaseSignature {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $triad = Get-SigningTriadState -RepoRoot $RepoRoot
    if ($triad.Present -eq 0) {
        return 'unprovisioned'
    }
    # ARMED: all members required, else fail closed (no silent disable).
    if (-not $triad.HasPin) { throw "release signing ARMED but EXPECTED_SIGNING_FINGERPRINT is not set (fail-closed)." }
    if (-not $triad.HasSig) { throw "release signing ARMED but detached signature is missing: $($triad.SigPath) (fail-closed)." }
    if (-not $triad.HasPub) { throw "release signing ARMED but public key is missing: $($triad.PubPath) (fail-closed)." }
    # Validate the pin FIRST (input validation before any tool check): normalize case + STRICTLY
    # require a full 40-hex fingerprint. A weak/mistyped/regex-metacharacter pin (".*", a short
    # key-id) is rejected here regardless of whether gpg is present, so it can never be treated as
    # a pattern that accepts ANY valid signature.
    $want = $triad.Pin.Trim().ToUpperInvariant()
    if ($want -notmatch '^[0-9A-F]{40}$') {
        throw "EXPECTED_SIGNING_FINGERPRINT must be a full 40-hex fingerprint (fail-closed): '$($triad.Pin)'."
    }
    if (-not (Get-Command gpg -ErrorAction SilentlyContinue)) { throw "release signing ARMED but gpg is not available (fail-closed)." }
    $manifest = Join-Path $RepoRoot '.well-known/release-manifest.json'
    # Isolated keyring (no ambient trust); verify+import of a PUBLIC key needs no gpg-agent.
    $gnupgHome = Join-Path ([System.IO.Path]::GetTempPath()) ("cfrs-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 12))
    New-Item -ItemType Directory -Path $gnupgHome -Force | Out-Null
    $prevHome = $env:GNUPGHOME
    try {
        $env:GNUPGHOME = $gnupgHome
        $null = & gpg --batch --import $triad.PubPath 2>&1
        if ($LASTEXITCODE -ne 0) { throw "release signing: failed to import the public key (fail-closed)." }
        # CAPTURE-then-check: the gpg return code is checked DIRECTLY (NOT through a pipe into the
        # matcher), so a degraded/bad signature cannot be masked by a status stream that merely
        # contains a matching VALIDSIG line.
        $status = & gpg --batch --status-fd 1 --verify $triad.SigPath $manifest 2>$null
        if ($LASTEXITCODE -ne 0) { throw "release signing: gpg --verify failed (bad / missing / degraded signature) (fail-closed)." }
        # Bind to the PINNED signer by EXACT FIELD EQUALITY (see Test-PinnedValidSig); gpg --verify
        # exits 0 on ANY good signature from ANY imported key, so this rejects an attacker key
        # appended to the bundle / a substituted signature.
        if (-not (Test-PinnedValidSig -StatusLines $status -Want $want)) {
            throw "release signing: no VALIDSIG bound to the pinned fingerprint $want (signer mismatch) (fail-closed)."
        }
        return 'verified'
    }
    finally {
        $env:GNUPGHOME = $prevHome
        Remove-Item -LiteralPath $gnupgHome -Recurse -Force -ErrorAction SilentlyContinue
    }
}
