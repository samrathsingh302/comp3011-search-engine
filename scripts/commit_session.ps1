# scripts/commit_session.ps1
# Runs pytest. Only commits if every test passes and the coverage gate holds.
# Usage:
#   .\scripts\commit_session.ps1 "feat(crawler): add config and URL normalisation"

param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = "Stop"

$pytest = if (Test-Path ".\.venv\Scripts\pytest.exe") {
    ".\.venv\Scripts\pytest.exe"
} else {
    "pytest"
}

Write-Host "Running tests via $pytest ..." -ForegroundColor Cyan
& $pytest
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests or coverage gate failed (exit $LASTEXITCODE). Not committing." -ForegroundColor Red
    exit 1
}

Write-Host "Tests green. Staging and committing ..." -ForegroundColor Green
git add -A
git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    Write-Host "Nothing to commit, or the commit step failed." -ForegroundColor Yellow
    exit 1
}

# Auto-push to origin if a remote is configured. Network failure is a warning,
# not an error: the commit already exists locally and can be pushed later.
$hasRemote = (git remote 2>$null) -ne $null
if ($hasRemote) {
    Write-Host "Pushing to origin ..." -ForegroundColor Cyan
    git push
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed; commit is safe locally. Run 'git push' manually when ready." -ForegroundColor Yellow
    }
} else {
    Write-Host "No remote configured; skipping push." -ForegroundColor DarkGray
}

Write-Host "`nRecent commits:" -ForegroundColor Cyan
git log --oneline -5
