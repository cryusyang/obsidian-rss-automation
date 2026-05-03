#!/data/data/com.termux/files/usr/bin/bash
set -u

REPO_DIR="${REPO_DIR:-/data/data/com.termux/files/home/storage/documents/obsidian-notes}"
INPUT_PATH="A-🔴INPUTS/(C)-🟡RSS/Input"
LOG_FILE="${LOG_FILE:-$HOME/scripts/obsidian_sync.log}"

cd "$REPO_DIR" || {
  termux-notification --title "Obsidian 同步" --content "仓库目录不存在: $REPO_DIR" --priority high
  termux-vibrate -d 300
  exit 1
}

git add "$INPUT_PATH"

if git diff --cached --quiet; then
  PULL_OUT=$(git pull --no-rebase origin main 2>&1)
  PULL_CODE=$?
  printf "\n[%s] push/no-change pull\n%s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$PULL_OUT" >> "$LOG_FILE"
  if [ "$PULL_CODE" -eq 0 ]; then
    termux-notification \
      --title "Obsidian 同步 OK" \
      --content "Input 无变更，已拉取远端更新" \
      --priority low
    termux-vibrate -d 50
    exit 0
  fi
  termux-notification \
    --title "Obsidian 同步失败" \
    --content "拉取失败: $(printf "%s\n" "$PULL_OUT" | tail -1)" \
    --priority high
  termux-vibrate -d 500
  exit 1
fi

CHANGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
git commit -m "update: reading progress $(date +%Y-%m-%d_%H:%M)"

PULL_OUT=$(git pull --no-rebase origin main 2>&1)
PULL_CODE=$?
printf "\n[%s] push/after-commit pull\n%s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$PULL_OUT" >> "$LOG_FILE"
if [ "$PULL_CODE" -ne 0 ]; then
  termux-notification \
    --title "Obsidian 同步失败" \
    --content "提交后拉取失败，请手动检查冲突: $(printf "%s\n" "$PULL_OUT" | tail -1)" \
    --priority high
  termux-vibrate -d 500
  exit 1
fi

PUSH_OUT=$(git push origin main 2>&1)
PUSH_CODE=$?
printf "\n[%s] push\n%s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$PUSH_OUT" >> "$LOG_FILE"

if [ "$PUSH_CODE" -eq 0 ]; then
  termux-notification \
    --title "Obsidian 同步 OK" \
    --content "推送成功，${CHANGED} 个文件已同步" \
    --priority default
  termux-vibrate -d 100
else
  termux-notification \
    --title "Obsidian 同步失败" \
    --content "推送失败: $(printf "%s\n" "$PUSH_OUT" | tail -1)" \
    --priority high
  termux-vibrate -d 500
  exit 1
fi
