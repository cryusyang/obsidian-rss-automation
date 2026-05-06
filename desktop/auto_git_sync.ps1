$repos = @(
    "D:\yancey\yanceyPKM"
)

$logFile = "$PSScriptRoot\git_sync_log.txt"

foreach ($repo in $repos) {
    $date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    if (-Not (Test-Path $repo)) {
        "[$date] [ERROR] Path not found: $repo" | Out-File -Append $logFile
        continue
    }

    Set-Location $repo

    # Step 1: Pull remote changes (merge, no rebase)
    # No stash needed — local notes and remote RSS articles are in separate folders
    $pullResult = git pull origin main --no-rebase 2>&1
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Pull failed: $pullResult" | Out-File -Append $logFile
        continue
    }
    "[$date] [OK] Pull: $($pullResult | Select-Object -Last 1)" | Out-File -Append $logFile

    # Step 2: Commit and push any local changes
    git add -A
    $cached = git diff --cached --name-only 2>&1
    if (-not $cached) {
        "[$date] [SKIP] No local changes to push" | Out-File -Append $logFile
        continue
    }

    git commit -m "Auto sync: $date" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Commit failed" | Out-File -Append $logFile
        continue
    }

    $pushResult = git push origin main 2>&1
    if ($LASTEXITCODE -eq 0) {
        "[$date] [OK] Pushed local changes" | Out-File -Append $logFile
    } else {
        "[$date] [FAIL] Push failed: $pushResult" | Out-File -Append $logFile
    }
}
