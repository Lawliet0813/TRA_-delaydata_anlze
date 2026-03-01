"""
車種定義爬蟲：抓取 TRA TrainType 對照表（靜態，每月更新即可）。
"""

from crawlers.base import BaseCrawler


class TrainTypeCrawler(BaseCrawler):
    endpoint = "/TrainType"
    save_subdir = "static"
    root_key = "TrainTypes"
    timestamp_file = False
    fixed_filename = "train_types.json"


def crawl_train_types():
    return TrainTypeCrawler().crawl()
