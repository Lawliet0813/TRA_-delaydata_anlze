import sys
from crawlers.live_board import crawl_live_board
from crawlers.alert import crawl_alerts
from crawlers.timetable import crawl_timetable

def print_help():
    print("使用方式: python main.py <task>")
    print("可用的 task:")
    print("  live      - 抓取即時到離站資訊 (TrainLiveBoard) 及營運通告 (Alert) (建議排程：每 1-3 分鐘)")
    print("  timetable - 抓取當日完整時刻表 (DailyTrainTimetable) (建議排程：每日一次)")
    print("  all       - 抓取全部資料")

if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "live"

    if task == "live":
        crawl_live_board()
        crawl_alerts()       # Alert 順便一起抓
    elif task == "timetable":
        crawl_timetable()
    elif task == "all":
        crawl_live_board()
        crawl_alerts()
        crawl_timetable()
    elif task in ("-h", "--help", "help"):
        print_help()
    else:
        print(f"未知的 task: {task}")
        print_help()