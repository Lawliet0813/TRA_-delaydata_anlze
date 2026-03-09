#!/bin/zsh
# tra_hourly.sh - Alert 抓取 + CSV 匯出 + 推送處理後 CSV 到 GitHub（每小時整點）
# 只推 processed CSV，不推 raw JSON。

set -euo pipefail

PROJECT="/Volumes/MacAPPs/MEPA27課程資料/社會科學研究方法（一）：量化研究方法/期末報告/tra_delay_crawler"
PYTHON="$PROJECT/venv/bin/python"
PUSH_DIR="$HOME/tra_git_push"
LOG="$HOME/Library/Logs/tra_hourly_local.log"
ENV_FILE="$PROJECT/.env"

# 時間守衛：僅在台灣 06:00-23:59 執行
HOUR=$(date +%H)
if (( HOUR < 6 )); then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SKIP] 時間窗口外 hour=$HOUR" >> "$LOG"
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [START] hourly: alert + export + push" >> "$LOG"

# 載入 TDX 憑證
set -a
source "$ENV_FILE"
set +a

cd "$PROJECT"

# 1. 抓取 Alert 資料（存到 data/alerts/YYYY-MM-DD/HHMMSS.json，本機）
echo "$(date '+%Y-%m-%d %H:%M:%S') [1/3] 抓取 alerts..." >> "$LOG"
"$PYTHON" main.py alert >> "$LOG" 2>&1

# 2. 匯出 CSV（讀取 station_live + alerts + timetable，產生 processed_data.csv 等）
echo "$(date '+%Y-%m-%d %H:%M:%S') [2/3] 匯出 CSV..." >> "$LOG"
"$PYTHON" export_csv.py >> "$LOG" 2>&1

# 3. 推送處理後的 CSV 到 GitHub（透過獨立 push clone）
echo "$(date '+%Y-%m-%d %H:%M:%S') [3/3] 推送 CSVs 到 GitHub..." >> "$LOG"

if [ ! -d "$PUSH_DIR" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $PUSH_DIR 不存在，請先執行：" >> "$LOG"
    echo "  git clone https://github.com/Lawliet0813/TRA_-delaydata_anlze.git ~/tra_git_push" >> "$LOG"
    exit 1
fi

cd "$PUSH_DIR"
git pull --rebase origin main >> "$LOG" 2>&1

# 只複製處理後的 CSV（不含 raw JSON）
for CSV in processed_data.csv research_dataset.csv stations_coords.csv train_schedule.csv; do
    SRC="$PROJECT/data/$CSV"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$PUSH_DIR/data/$CSV"
    fi
done

# output/ 資料夾的 CSV
if [ -d "$PROJECT/data/output" ]; then
    mkdir -p "$PUSH_DIR/data/output"
    cp "$PROJECT/data/output/"*.csv "$PUSH_DIR/data/output/" 2>/dev/null || true
fi

git add data/processed_data.csv \
        data/research_dataset.csv \
        data/stations_coords.csv \
        data/train_schedule.csv \
        data/output/ >> "$LOG" 2>&1

git diff --cached --quiet || {
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
    git commit -m "🤖 hourly: export+alert ${TIMESTAMP}" >> "$LOG" 2>&1
    git push origin main >> "$LOG" 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S') [PUSHED] CSVs 已推上 GitHub" >> "$LOG"
}

echo "$(date '+%Y-%m-%d %H:%M:%S') [DONE] hourly complete" >> "$LOG"
