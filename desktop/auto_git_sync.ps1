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

    # Step 1: Stash any local uncommitted changes so pull can run cleanly
    $localChanges = git status --porcelain 2>&1
    $hasLocal = ($null -ne $localChanges) -and ("$localChanges".Trim() -ne "")

    $stashed = $false
    if ($hasLocal) {
        git stash push -m "auto-sync $date" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $stashed = $true
            "[$date] [INFO] Stashed local changes" | Out-File -Append $logFile
        } else {
            "[$date] [WARN] Stash failed, attempting pull anyway" | Out-File -Append $logFile
        }
    }

    # Step 2: Always pull remote changes (merge, no rebase)
    $pullResult = git pull origin main --no-rebase 2>&1
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Pull failed: $pullResult" | Out-File -Append $logFile
        if ($stashed) { git stash pop 2>&1 | Out-Null }
        continue
    }
    "[$date] [OK] Pull done: $($pullResult | Select-Object -Last 1)" | Out-File -Append $logFile

    # Step 3: Restore stashed local changes
    if ($stashed) {
        $popResult = git stash pop 2>&1
        if ($LASTEXITCODE -ne 0) {
            "[$date] [WARN] Stash pop conflict: $popResult" | Out-File -Append $logFile
        }
    }

    # Step 4: Commit and push any local changes
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
