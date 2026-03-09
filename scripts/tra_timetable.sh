#!/bin/zsh
# tra_timetable.sh - 每日時刻表抓取 + 推送（每日 06:05）

set -euo pipefail

PROJECT="/Volumes/MacAPPs/MEPA27課程資料/社會科學研究方法（一）：量化研究方法/期末報告/tra_delay_crawler"
PYTHON="$PROJECT/venv/bin/python"
PUSH_DIR="$HOME/tra_git_push"
LOG="$HOME/Library/Logs/tra_timetable_local.log"
ENV_FILE="$PROJECT/.env"

echo "$(date '+%Y-%m-%d %H:%M:%S') [START] timetable crawl" >> "$LOG"

# 載入 TDX 憑證
set -a
source "$ENV_FILE"
set +a

cd "$PROJECT"

# 1. 抓取今日時刻表（存到 data/timetable/daily_YYYY-MM-DD.json，本機）
echo "$(date '+%Y-%m-%d %H:%M:%S') [1/2] 抓取時刻表..." >> "$LOG"
"$PYTHON" main.py timetable >> "$LOG" 2>&1

# 2. 推送時刻表 JSON 到 GitHub
echo "$(date '+%Y-%m-%d %H:%M:%S') [2/2] 推送時刻表到 GitHub..." >> "$LOG"

if [ ! -d "$PUSH_DIR" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $PUSH_DIR 不存在，請先執行：" >> "$LOG"
    echo "  git clone https://github.com/Lawliet0813/TRA_-delaydata_anlze.git ~/tra_git_push" >> "$LOG"
    exit 1
fi

TODAY=$(date '+%Y-%m-%d')
SRC_JSON="$PROJECT/data/timetable/daily_${TODAY}.json"

if [ ! -f "$SRC_JSON" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] 找不到時刻表：$SRC_JSON" >> "$LOG"
    exit 0
fi

cd "$PUSH_DIR"
git pull --rebase origin main >> "$LOG" 2>&1

mkdir -p "$PUSH_DIR/data/timetable"
cp "$SRC_JSON" "$PUSH_DIR/data/timetable/daily_${TODAY}.json"

git add "data/timetable/daily_${TODAY}.json" >> "$LOG" 2>&1
git diff --cached --quiet || {
    git commit -m "📅 daily: timetable ${TODAY}" >> "$LOG" 2>&1
    git push origin main >> "$LOG" 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S') [PUSHED] 時刻表 ${TODAY} 已推上 GitHub" >> "$LOG"
}

echo "$(date '+%Y-%m-%d %H:%M:%S') [DONE] timetable complete" >> "$LOG"
