"""
Alert 異常通報爬蟲。

對應 TDX /Alert 端點，存檔至 data/alerts/YYYY-MM-DD/HHMMSS.json
"""

from crawlers.base import BaseCrawler


class AlertCrawler(BaseCrawler):
    endpoint = "/Alert"
    save_subdir = "alerts"
    root_key = "Alerts"
    timestamp_file = True


# ── 向後相容函數介面 ──────────────────────────────────────────

_crawler = AlertCrawler()

def fetch_alerts() -> dict:
    return _crawler.fetch()

def crawl_alerts() -> None:
    _crawler.crawl()