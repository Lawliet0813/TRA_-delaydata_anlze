"""
Shape 路線幾何爬蟲：抓取 TRA 各路線的 WKT LineString。
對應 TDX /Shape 端點，存檔至 data/static/shape.json（靜態，路線不常變動）。
"""
from crawlers.base import BaseCrawler


class ShapeCrawler(BaseCrawler):
    endpoint = "/Shape"
    save_subdir = "static"
    root_key = "Shapes"
    timestamp_file = False
    fixed_filename = "shape.json"


def crawl_shape():
    return ShapeCrawler().crawl()


if __name__ == "__main__":
    crawl_shape()
