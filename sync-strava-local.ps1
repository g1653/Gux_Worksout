param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $SyncArgs
)

$ErrorActionPreference = "Stop"
$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Create .venv and install requirements-strava.txt first; see README-CN.md."
}
Push-Location $PSScriptRoot
try {
    & $pythonPath "run_page\strava_sync.py" @SyncArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Strava sync failed. See the error above."
    }
} finally {
    # Refreshing locally may invalidate the token used by scheduled jobs.
    # Preserve the new credentials even if a later activity request fails.
    $ghCommand = Get-Command gh -ErrorAction SilentlyContinue
    $ghPath = if ($ghCommand) { $ghCommand.Source } else {
        Join-Path $env:LOCALAPPDATA 'Programs\GitHub CLI\bin\gh.exe'
    }
    if ((Test-Path -LiteralPath $ghPath) -and (Test-Path -LiteralPath '.env')) {
        & $ghPath secret set --repo g1653/Gux_Worksout --env-file .env
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'Local tokens were saved, but updating GitHub Secrets failed. Retry gh secret set --repo g1653/Gux_Worksout --env-file .env before cloud sync.'
        }
    }
    Pop-Location
}
