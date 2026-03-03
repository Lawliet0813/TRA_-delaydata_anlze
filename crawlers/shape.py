"""
Shape 路線幾何爬蟲：抓取 TRA 各路線的 WKT LineString。

# 資料界接來源：https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/Shape
# 提供臺鐵各路線的地理幾何軌跡資料（WKT LineString 格式），
# 用於地圖上疊加路線走向，為靜態資料，存檔至 data/static/shape.json。
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
