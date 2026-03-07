"""
排程器：定期執行資料抓取
- live      每 10 分鐘
- alert     每 60 分鐘
- timetable 每日 05:30
"""

import time
import logging
import subprocess
import sys
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("cron.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

PYTHON = sys.executable
INTERVALS = {
    "live": 10 * 60,       # 10 分鐘
    "alert": 60 * 60,      # 60 分鐘
    "timetable": 24 * 60 * 60,  # 每日一次
}


def run_task(task: str):
    logger.info(f"開始抓取: {task}")
    result = subprocess.run(
        [PYTHON, "main.py", task],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        logger.info(f"完成: {task}")
    else:
        logger.error(f"失敗: {task}\n{result.stderr}")


def main():
    now = datetime.now()
    # 初始化下次執行時間
    next_run = {
        "live": now,
        "alert": now,
        "timetable": now.replace(hour=5, minute=30, second=0, microsecond=0),
    }
    # 若今天 05:30 已過，改成明天
    if next_run["timetable"] <= now:
        next_run["timetable"] += timedelta(days=1)

    logger.info("排程器啟動")
    logger.info(f"  live:      每 10 分鐘")
    logger.info(f"  alert:     每 60 分鐘")
    logger.info(f"  timetable: 每日 05:30（下次 {next_run['timetable'].strftime('%Y-%m-%d %H:%M')}）")

    while True:
        now = datetime.now()
        for task, nxt in next_run.items():
            if now >= nxt:
                run_task(task)
                if task == "timetable":
                    next_run[task] = now.replace(hour=5, minute=30, second=0, microsecond=0) + timedelta(days=1)
                else:
                    next_run[task] = now + timedelta(seconds=INTERVALS[task])
                logger.info(f"  下次 {task}: {next_run[task].strftime('%H:%M:%S')}")
        time.sleep(30)


if __name__ == "__main__":
    main()
