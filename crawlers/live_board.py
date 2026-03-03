"""
TrainLiveBoard 爬蟲（舊，逐步廢棄）。

# 資料界接來源：https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/TrainLiveBoard
# 提供臺鐵列車即時動態（以列車為單位的到離站資訊），已由 StationLiveBoard 取代。
已由 station_live.py (StationLiveCrawler) 取代。
保留此模組以維持向後相容，待確認新爬蟲穩定後移除。
"""

from crawlers.base import BaseCrawler


class LiveBoardCrawler(BaseCrawler):
    endpoint = "/TrainLiveBoard"
    save_subdir = "live_board"
    root_key = "TrainLiveBoards"
    timestamp_file = True


# ── 向後相容函數介面 ──────────────────────────────────────────

_crawler = LiveBoardCrawler()

def fetch_train_live_board() -> dict:
    return _crawler.fetch()

def save_live_board(data: dict) -> str:
    return _crawler.save(data)

def crawl_live_board() -> None:
    _crawler.crawl()