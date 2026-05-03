#!/data/data/com.termux/files/usr/bin/bash
set -u

REPO_DIR="${REPO_DIR:-/data/data/com.termux/files/home/storage/documents/obsidian-notes}"
INPUT_PATH="A-🔴INPUTS/(C)-🟡RSS/Input"

cd "$REPO_DIR" || {
  termux-notification --title "Obsidian 同步" --content "仓库目录不存在: $REPO_DIR" --priority high
  termux-vibrate -d 300
  exit 1
}

PULL_OUT=$(git pull --rebase origin main 2>&1)
if [ "$?" -ne 0 ]; then
  termux-notification \
    --title "Obsidian 同步失败" \
    --content "推送前拉取失败，请手动检查冲突: $(printf "%s\n" "$PULL_OUT" | tail -1)" \
    --priority high
  termux-vibrate -d 500
  exit 1
fi

git add "$INPUT_PATH"

if git diff --cached --quiet; then
  termux-notification \
    --title "Obsidian 同步" \
    --content "Input 目录无变更，无需推送" \
    --priority low
  termux-vibrate -d 50
  exit 0
fi

CHANGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
git commit -m "update: reading progress $(date +%Y-%m-%d_%H:%M)"

if git push origin main; then
  termux-notification \
    --title "Obsidian 同步 OK" \
    --content "推送成功，${CHANGED} 个文件已同步" \
    --priority default
  termux-vibrate -d 100
else
  termux-notification \
    --title "Obsidian 同步失败" \
    --content "推送失败，请检查网络或认证" \
    --priority high
  termux-vibrate -d 500
  exit 1
fi
