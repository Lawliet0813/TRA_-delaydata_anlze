"""
路線網路爬蟲：抓取 TRA LineNetwork 資料（靜態，每週更新即可）。
"""

from crawlers.base import BaseCrawler


class LineNetworkCrawler(BaseCrawler):
    endpoint = "/LineNetwork"
    save_subdir = "static"
    root_key = "LineNetworks"
    timestamp_file = False
    fixed_filename = "line_network.json"


def crawl_line_network():
    return LineNetworkCrawler().crawl()
