"""
CLI 入口：python main.py <task>

可用任務：
  live      - StationLiveBoard（每 10 分鐘排程）
  alert     - 營運通阻資料（每 60 分鐘排程，獨立排程）
  timetable - DailyTrainTimetable/Today（每日一次）
  station   - 更新靜態資料（車站、車種、路線網路）
  all       - 全部資料
  legacy    - 舊 TrainLiveBoard（向後相容，逐步廢棄）
"""

import sys
from crawlers.station_live import crawl_station_live
from crawlers.alert import crawl_alerts
from crawlers.daily_timetable import crawl_daily_timetable
from crawlers.station import crawl_stations
from crawlers.train_type import crawl_train_types
from crawlers.line_network import crawl_line_network
from crawlers.shape import crawl_shape
from crawlers.live_board import crawl_live_board


def print_help():
    print("使用方式: python main.py <task>")
    print("可用的 task:")
    print("  live      - 抓取即時到離站資訊 (StationLiveBoard)，每 10 分鐘")
    print("  alert     - 抓取營運通阻資料 (Alert)，每 60 分鐘")
    print("  timetable - 抓取當日營運時刻表 (DailyTrainTimetable/Today)")
    print("  station   - 更新靜態資料 (Station + TrainType + LineNetwork)")
    print("  all       - 抓取全部資料")
    print("  legacy    - 抓取舊 TrainLiveBoard（逐步廢棄）")


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "live"

    if task == "live":
        crawl_station_live()
    elif task == "alert":
        crawl_alerts()
    elif task == "timetable":
        crawl_daily_timetable()
    elif task == "station":
        crawl_stations()
        crawl_train_types()
        crawl_line_network()
        crawl_shape()
    elif task == "all":
        crawl_station_live()
        crawl_alerts()
        crawl_daily_timetable()
        crawl_stations()
        crawl_train_types()
        crawl_line_network()
        crawl_shape()
    elif task == "legacy":
        crawl_live_board()
        crawl_alerts()
    elif task in ("-h", "--help", "help"):
        print_help()
    else:
        print(f"未知的 task: {task}")
        print_help()