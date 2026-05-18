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

Write-Host "`nRecent commits:" -ForegroundColor Cyan
git log --oneline -5
