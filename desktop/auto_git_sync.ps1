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

    # Step 1: Fetch remote without touching local files
    $fetchResult = git fetch origin main 2>&1
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Fetch failed: $fetchResult" | Out-File -Append $logFile
        continue
    }

    # Check how many commits local is behind remote
    $behind = git rev-list HEAD..origin/main --count 2>&1
    $hasBehind = ($behind -match '^\d+$') -and ([int]$behind -gt 0)

    # Check if local has uncommitted changes
    $localChanges = git status --porcelain 2>&1
    $hasLocal = ($null -ne $localChanges) -and ($localChanges -ne "")

    # Step 2: Stash local changes before merging (only if remote has new commits)
    $stashed = $false
    if ($hasBehind -and $hasLocal) {
        $stashResult = git stash push -m "auto-sync $date" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $stashed = $true
            "[$date] [INFO] Stashed local changes before pull" | Out-File -Append $logFile
        } else {
            "[$date] [FAIL] Stash failed, aborting pull: $stashResult" | Out-File -Append $logFile
            continue
        }
    }

    # Step 3: Merge remote changes (no rebase)
    if ($hasBehind) {
        $mergeResult = git merge origin/main --no-rebase --no-edit 2>&1
        if ($LASTEXITCODE -ne 0) {
            "[$date] [FAIL] Merge failed: $mergeResult" | Out-File -Append $logFile
            if ($stashed) { git stash pop 2>&1 | Out-Null }
            continue
        }
        "[$date] [OK] Pulled $behind new commit(s) from remote" | Out-File -Append $logFile
    }

    # Step 4: Restore stashed local changes
    if ($stashed) {
        $popResult = git stash pop 2>&1
        if ($LASTEXITCODE -ne 0) {
            "[$date] [WARN] Stash pop failed (possible conflict): $popResult" | Out-File -Append $logFile
        }
    }

    # Step 5: Commit any local changes and push
    git add -A
    $cached = git diff --cached --name-only 2>&1
    if (-not $cached) {
        if (-not $hasBehind) {
            "[$date] [SKIP] Already up to date: $repo" | Out-File -Append $logFile
        }
        continue
    }

    git commit -m "Auto sync: $date" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        "[$date] [FAIL] Commit failed" | Out-File -Append $logFile
        continue
    }

    $pushResult = git push origin main 2>&1
    if ($LASTEXITCODE -eq 0) {
        "[$date] [OK] Pushed local changes to remote" | Out-File -Append $logFile
    } else {
        "[$date] [FAIL] Push failed: $pushResult" | Out-File -Append $logFile
    }
}
