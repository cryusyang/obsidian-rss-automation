#!/data/data/com.termux/files/usr/bin/bash
set -u

REPO_DIR="${REPO_DIR:-/data/data/com.termux/files/home/storage/documents/yanceyPKM}"
LOG_FILE="${LOG_FILE:-$HOME/scripts/obsidian_sync.log}"

cd "$REPO_DIR" || {
  termux-notification --title "Obsidian 同步" --content "仓库目录不存在: $REPO_DIR" --priority high
  termux-vibrate -d 300
  exit 1
}

OUTPUT=$(git pull --no-rebase origin main 2>&1)
EXIT_CODE=$?
printf "\n[%s] pull\n%s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$OUTPUT" >> "$LOG_FILE"

if [ "$EXIT_CODE" -eq 0 ]; then
  CHANGED=$(printf "%s\n" "$OUTPUT" | grep -cE '^\s+(create|delete|modify)' 2>/dev/null || true)
  termux-notification \
    --title "Obsidian 同步 OK" \
    --content "拉取成功，共变更 ${CHANGED} 个文件" \
    --priority default
  termux-vibrate -d 100
else
  termux-notification \
    --title "Obsidian 同步失败" \
    --content "拉取失败: $(printf "%s\n" "$OUTPUT" | tail -1)" \
    --priority high
  termux-vibrate -d 500
  exit 1
fi
