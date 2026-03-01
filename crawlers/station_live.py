"""
StationLiveCrawler — 新核心即時爬蟲。

對應 TDX /StationLiveBoard 端點，每 3 分鐘抓取全台各站即時到離站資訊。
存檔至 data/raw/station_live/YYYY-MM-DD/HHMMSS.json
"""

from crawlers.base import BaseCrawler


class StationLiveCrawler(BaseCrawler):
    endpoint = "/StationLiveBoard"
    save_subdir = "station_live"
    root_key = "StationLiveBoards"
    timestamp_file = True


# ── 向後相容的函數介面（供 SKILL 測試指令使用）──────────────

_crawler = StationLiveCrawler()

def fetch_station_live_board() -> dict:
    """直接呼叫 API 回傳 JSON dict。"""
    return _crawler.fetch()

def crawl_station_live() -> None:
    """fetch + save + log。"""
    _crawler.crawl()
