"""
當日時刻表爬蟲：抓取 DailyTrainTimetable/Today。
比 GeneralTrainTimetable 更精確（含臨時加開/停駛、Direction、TripLine）。
建議排程：每日 06:00 抓取一次，取代 GeneralTrainTimetable。
"""

from crawlers.base import BaseCrawler


class DailyTimetableCrawler(BaseCrawler):
    endpoint = "/DailyTrainTimetable/Today"
    save_subdir = "timetable"
    root_key = "TrainTimetables"

    def _build_save_path(self):
        """依日期存檔：timetable/daily_2026-03-01.json"""
        import os
        from datetime import datetime
        from config import DATA_DIR
        target_dir = os.path.join(DATA_DIR, self.save_subdir)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"daily_{datetime.now().strftime('%Y-%m-%d')}.json")


def crawl_daily_timetable():
    return DailyTimetableCrawler().crawl()
