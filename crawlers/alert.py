"""
Alert 異常通報爬蟲。

# 資料界接來源：https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/Alert
# 提供臺鐵即時異常通報資料（行車事故、設備故障、天候影響等通報內文與發布時間），
# 存檔至 data/alerts/YYYY-MM-DD/HHMMSS.json
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