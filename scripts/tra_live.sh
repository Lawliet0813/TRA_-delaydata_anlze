#!/bin/zsh
# tra_live.sh - StationLiveBoard 即時抓取（每 10 分鐘）
# Raw JSON 只存本機，不推 GitHub。

set -euo pipefail

PROJECT="/Volumes/MacAPPs/MEPA27課程資料/社會科學研究方法（一）：量化研究方法/期末報告/tra_delay_crawler"
PYTHON="$PROJECT/venv/bin/python"
LOG="$HOME/Library/Logs/tra_live_local.log"
ENV_FILE="$PROJECT/.env"

# 時間守衛：僅在台灣 06:00-23:59 執行（macOS 已是 CST）
HOUR=$(date +%H)
if (( HOUR < 6 )); then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SKIP] 時間窗口外 hour=$HOUR" >> "$LOG"
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [START] live crawl" >> "$LOG"

# 載入 TDX 憑證
set -a
source "$ENV_FILE"
set +a

# 執行爬蟲
cd "$PROJECT"
"$PYTHON" main.py live >> "$LOG" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') [DONE] live crawl" >> "$LOG"
