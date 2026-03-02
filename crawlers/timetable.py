"""
GeneralTrainTimetable 時刻表爬蟲。

對應 TDX /DailyTrainTimetable/Today 端點，
存檔至 data/timetable/YYYY-MM-DD.json（每日一檔）。
"""

from datetime import datetime

from crawlers.base import BaseCrawler
from config import BASE_URL
from auth import auth_header
import requests


class TimetableCrawler(BaseCrawler):
    endpoint = "/DailyTrainTimetable/Today"
    save_subdir = "timetable"
    root_key = "TrainTimetables"
    timestamp_file = False
    fixed_filename = ""  # 動態產生，覆寫 _build_save_path

    def _build_save_path(self) -> str:
        """時刻表以日期命名（每天一檔）。"""
        import os
        from config import DATA_DIR
        target_dir = os.path.join(DATA_DIR, self.save_subdir)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"{datetime.now().strftime('%Y-%m-%d')}.json")


# ── 向後相容函數介面 ──────────────────────────────────────────

_crawler = TimetableCrawler()

def fetch_daily_timetable() -> dict:
    return _crawler.fetch()

def crawl_timetable() -> None:
    _crawler.crawl()