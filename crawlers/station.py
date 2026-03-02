"""
Station 靜態車站資料爬蟲。

對應 TDX /Station 端點，存檔至 data/static/stations.json（固定覆寫）。
"""

from crawlers.base import BaseCrawler


class StationCrawler(BaseCrawler):
    endpoint = "/Station"
    save_subdir = "static"
    root_key = "Stations"
    timestamp_file = False
    fixed_filename = "stations.json"


# ── 向後相容函數介面 ──────────────────────────────────────────

_crawler = StationCrawler()

def fetch_stations() -> dict:
    return _crawler.fetch()

def crawl_stations() -> None:
    _crawler.crawl()


if __name__ == "__main__":
    crawl_stations()
