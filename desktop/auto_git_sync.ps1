$repos = @(
    "D:\yancey\yanceyPKM"
)

$logFile = "$PSScriptRoot\git_sync_log.txt"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

foreach ($repo in $repos) {
    if (-Not (Test-Path $repo)) {
        "[$date] [ERROR] Path not found: $repo" | Out-File -Append $logFile
        continue
    }

    Set-Location $repo

    $pullResult = git pull --no-rebase origin main 2>&1
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Pull failed: $repo" | Out-File -Append $logFile
        "[$date] [FAIL] Detail: $pullResult" | Out-File -Append $logFile
        continue
    }

    git add -A

    $cached = git diff --cached --name-only
    if (-not $cached) {
        "[$date] [SKIP] No changes after pull: $repo" | Out-File -Append $logFile
        continue
    }

    git commit -m "Auto sync: $date"
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Commit failed: $repo" | Out-File -Append $logFile
        continue
    }

    $pushResult = git push origin main 2>&1
    if ($LASTEXITCODE -eq 0) {
        "[$date] [OK] Push success: $repo" | Out-File -Append $logFile
    } else {
        "[$date] [FAIL] Push failed: $repo" | Out-File -Append $logFile
        "[$date] [FAIL] Detail: $pushResult" | Out-File -Append $logFile
    }
}
