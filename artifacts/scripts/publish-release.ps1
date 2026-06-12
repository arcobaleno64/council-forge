#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Create a GitHub Release via gh CLI.
.DESCRIPTION
    Preflight checks (auth, gh CLI, tag existence, duplicate release) then
    creates a release. Uses shared helpers from github_publish_common.ps1.
.PARAMETER Tag
    The git tag to release (e.g. v0.4.0). Must already exist.
.PARAMETER Title
    Release title. Defaults to the tag name.
.PARAMETER NotesFile
    Path to a markdown file containing release notes.
    If omitted, gh will auto-generate notes.
.PARAMETER Draft
    Create the release as a draft.
.PARAMETER PreRelease
    Mark the release as pre-release.
.PARAMETER AllowUnsigned
    Explicitly opt in to publishing an UNSIGNED release when release signing is not yet
    provisioned (the signing triad — pinned fingerprint + detached signature + public key —
    is entirely absent). This NEVER overrides a failed structural-integrity gate, nor an ARMED
    signing failure (a partially-provisioned or invalid signature always fails closed).
.PARAMETER WhatIf
    Run all preflight checks (including release-integrity + signature verification) but skip
    actual release creation.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Tag,
    [string]$Title,
    [string]$NotesFile,
    [switch]$Draft,
    [switch]$PreRelease,
    [switch]$AllowUnsigned,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$scriptDir = $PSScriptRoot
$repoRoot  = Split-Path -Parent $scriptDir

# Load shared helpers
. (Join-Path $scriptDir 'github_publish_common.ps1')

# ---------------------------------------------------------------------------
# 1. Preflight
# ---------------------------------------------------------------------------
Write-Host "=== Preflight ===" -ForegroundColor Cyan

# 1a. gh CLI required
if (-not (Test-GhCli)) {
    Write-Error "gh CLI is required for release creation."
    exit $EXIT_GH_CLI_MISSING
}
Write-Host "[OK] gh CLI available." -ForegroundColor Green

# 1b. Auth probe
$auth = Test-GitHubAuth
if (-not $auth) {
    Write-Error "GitHub auth not found. Set GH_TOKEN / GITHUB_TOKEN or run 'gh auth login'."
    exit $EXIT_AUTH_MISSING
}
Write-Host "[OK] GitHub auth detected." -ForegroundColor Green

# 1c. Resolve owner/repo
$ownerRepo = Get-OwnerRepo -RepoRoot $repoRoot
$owner = $ownerRepo.Owner
$repo  = $ownerRepo.Repo
Write-Host "[OK] Repository: $owner/$repo" -ForegroundColor Green

# 1d. Tag must exist
Push-Location $repoRoot
$tagExists = git tag -l $Tag
Pop-Location
if (-not $tagExists) {
    Write-Error "Tag '$Tag' does not exist. Create it first with: git tag $Tag"
    exit $EXIT_PRECONDITION_FAIL
}
Write-Host "[OK] Tag '$Tag' exists." -ForegroundColor Green

# 1e. Check for existing release with same tag
$existingRelease = gh release view $Tag --repo "$owner/$repo" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Error "Release for tag '$Tag' already exists. Delete it first or use a different tag."
    exit $EXIT_PRECONDITION_FAIL
}
Write-Host "[OK] No existing release for '$Tag'." -ForegroundColor Green

# 1f. Notes file (if specified)
if ($NotesFile -and -not (Test-Path $NotesFile)) {
    Write-Error "Notes file not found: $NotesFile"
    exit $EXIT_PRECONDITION_FAIL
}

# 1g. Release-integrity gate (TASK-1089 / FB-2): the published manifest MUST match the template
#     snapshot AND pass the structural gate BEFORE we publish. Fail-closed. Uses the TRUE repo
#     root (git rev-parse), not artifacts/.
$releaseRoot = Get-RepoRoot
try {
    Invoke-ReleaseIntegrityGate -RepoRoot $releaseRoot -ScriptDir $scriptDir
}
catch {
    Write-Error "Release-integrity verification failed: $($_.Exception.Message)"
    exit $EXIT_PRECONDITION_FAIL
}
Write-Host "[OK] Release-integrity verified (manifest matches template snapshot + structural gate)." -ForegroundColor Green

# 1h. Release-signing verification (TASK-1089 / FB-2), mirroring the CI release-integrity job.
#     ARMED triad -> must verify against the pinned signer or FAIL CLOSED (never overridable).
#     Unprovisioned (triad empty) -> FAIL CLOSED by default; publish UNSIGNED only with -AllowUnsigned.
try {
    $sigState = Assert-ReleaseSignature -RepoRoot $releaseRoot
}
catch {
    Write-Error "Release-signing verification failed: $($_.Exception.Message)"
    exit $EXIT_PRECONDITION_FAIL
}
if ($sigState -eq 'verified') {
    Write-Host "[OK] Release-manifest signature verified against the pinned signer." -ForegroundColor Green
}
elseif ($sigState -eq 'unprovisioned') {
    if (-not $AllowUnsigned) {
        Write-Error "Release signing is not provisioned. Provision signing (see docs/security/release-signing.md), or pass -AllowUnsigned to explicitly publish an UNSIGNED release."
        exit $EXIT_PRECONDITION_FAIL
    }
    Write-Warning "[WARN] Publishing an UNSIGNED release per explicit -AllowUnsigned (signing not provisioned); manifest integrity was still enforced."
}

Write-Host "=== Preflight PASSED ===" -ForegroundColor Green
if ($WhatIf) {
    Write-Host "WhatIf: Skipping actual release creation." -ForegroundColor Yellow
    exit $EXIT_OK
}

# ---------------------------------------------------------------------------
# 2. Create release
# ---------------------------------------------------------------------------
$ghArgs = @('release', 'create', $Tag, '--repo', "$owner/$repo")

if ($Title)      { $ghArgs += @('--title', $Title) }
else             { $ghArgs += @('--title', $Tag) }

if ($NotesFile)  { $ghArgs += @('--notes-file', $NotesFile) }
else             { $ghArgs += '--generate-notes' }

if ($Draft)      { $ghArgs += '--draft' }
if ($PreRelease) { $ghArgs += '--prerelease' }

Write-Host "Creating release..." -ForegroundColor Cyan
gh @ghArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create release."
    exit $EXIT_PUBLISH_FAIL
}

Write-Host "Release '$Tag' created successfully." -ForegroundColor Green
Write-Host "View at: https://github.com/$owner/$repo/releases/tag/$Tag" -ForegroundColor Cyan
