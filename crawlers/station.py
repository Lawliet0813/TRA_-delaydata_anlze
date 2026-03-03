"""
Station 靜態車站資料爬蟲。

# 資料界接來源：https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/Station
# 提供臺鐵各車站靜態基本資料（車站代碼、中文站名、經緯度座標等），
# 為靜態資料，存檔至 data/static/stations.json（固定覆寫）。
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
