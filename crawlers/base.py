"""
BaseCrawler — 所有 TDX 爬蟲的統一骨架。

子類別只需定義 endpoint / save_subdir / root_key 等屬性，
fetch → save → crawl 的流程由基礎類別處理。
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime

import requests

from config import BASE_URL, DATA_DIR
from auth import auth_header


class BaseCrawler(ABC):
    """TDX API 爬蟲基礎類別。"""

    endpoint: str = ""          # 例如 "/StationLiveBoard"
    save_subdir: str = ""       # 存檔子目錄，例如 "station_live"
    root_key: str = ""          # JSON 回應的根 key，例如 "StationLiveBoards"
    timestamp_file: bool = True # True → HHMMSS.json，False → 固定檔名
    fixed_filename: str = ""    # 當 timestamp_file=False 時使用

    # ── API 呼叫 ──────────────────────────────────────────────

    def fetch(self) -> dict:
        """呼叫 TDX API 並回傳 JSON dict。"""
        url = f"{BASE_URL}{self.endpoint}"
        params = {"$format": "JSON"}
        resp = requests.get(url, headers=auth_header(), params=params)
        resp.raise_for_status()
        return resp.json()

    # ── 存檔 ──────────────────────────────────────────────────

    def _build_save_path(self) -> str:
        """依設定產生存檔完整路徑，並自動建立目錄。"""
        now = datetime.now()
        if self.timestamp_file:
            date_dir = os.path.join(DATA_DIR, self.save_subdir, now.strftime("%Y-%m-%d"))
            os.makedirs(date_dir, exist_ok=True)
            return os.path.join(date_dir, f"{now.strftime('%H%M%S')}.json")
        else:
            target_dir = os.path.join(DATA_DIR, self.save_subdir)
            os.makedirs(target_dir, exist_ok=True)
            return os.path.join(target_dir, self.fixed_filename)

    def save(self, data: dict) -> str:
        """將 JSON 資料存檔，回傳檔案路徑。"""
        path = self._build_save_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return path

    # ── 完整流程 ──────────────────────────────────────────────

    def crawl(self) -> None:
        """fetch + save + log，含基本錯誤處理。"""
        try:
            data = self.fetch()
            path = self.save(data)
            count = len(data.get(self.root_key, []))
            print(f"[{datetime.now()}] {self.__class__.__name__} saved: {path} ({count} records)")
        except Exception as e:
            print(f"[{datetime.now()}] {self.__class__.__name__} ERROR: {e}")
