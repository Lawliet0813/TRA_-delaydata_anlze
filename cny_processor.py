"""
春節誤點分析資料載入器

直接讀取 `data/cny/` 下的 parquet / csv / json，對應昨天跑完的
`RAWdata/analysis/` 輸出。APP 所有春節頁面都透過這支載入資料。
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

import pandas as pd


CNY_PERIOD_ORDER = [
    "春節前 (除夕前3天以上)",
    "除夕前夕 (除夕前1-2天)",
    "除夕",
    "春節期間 (初一至初三)",
    "收假日 (初四至初六)",
    "春節後 (初七以上)",
]

LUNAR_NEW_YEAR_EVE = {
    2022: "2022-01-31",
    2023: "2023-01-21",
    2024: "2024-02-09",
    2025: "2025-01-28",
    2026: "2026-02-16",
}


class CNYDataStore:
    """集中管理春節分析資料載入與快取。"""

    def __init__(self, cny_dir: str):
        self.cny_dir = cny_dir

    def _path(self, filename: str) -> str:
        return os.path.join(self.cny_dir, filename)

    def load_clean(self) -> pd.DataFrame:
        """載入去重後站點級資料（指標 B 基礎）。"""
        return pd.read_parquet(self._path("clean.parquet"))

    def load_metric_official(self) -> pd.DataFrame:
        """指標 A：每 (日期, 車次) 一筆的官方 proxy。"""
        return pd.read_parquet(self._path("metric_official.parquet"))

    def load_metric_perceived(self) -> pd.DataFrame:
        """指標 B：每 (日期, 車次, 車站) 一筆的旅客感知。"""
        return pd.read_parquet(self._path("metric_perceived.parquet"))

    def load_threshold_sensitivity(self) -> pd.DataFrame:
        return pd.read_csv(self._path("threshold_sensitivity.csv"))

    def load_inferential(self) -> dict:
        with open(self._path("inferential_results.json"), "r", encoding="utf-8") as f:
            return json.load(f)

    def load_raw_year(self, year: int) -> pd.DataFrame:
        """載入單一年度原始 CSV（未清理），供資料預覽頁使用。"""
        return pd.read_csv(self._path(f"cny_{year}.csv"))

    def has_raw_csv(self, year: int) -> bool:
        return os.path.exists(self._path(f"cny_{year}.csv"))

    def load_year_from_clean(self, year: int) -> pd.DataFrame:
        """CSV 不存在時（如雲端部署）改讀 clean.parquet 的該年子集。"""
        df = self.load_clean()
        return df[df["年"] == year].copy()


def apply_cny_filters(
    df: pd.DataFrame,
    years: list[int] | None = None,
    periods: list[str] | None = None,
    train_types: list[str] | None = None,
    regions: list[str] | None = None,
) -> pd.DataFrame:
    """套用春節四維篩選；傳入 None 或空 list 代表不過濾該維度。"""
    if df is None or df.empty:
        return df
    out = df
    if years:
        out = out[out["年"].isin(years)]
    if periods and "春節節點" in out.columns:
        out = out[out["春節節點"].isin(periods)]
    if train_types and "車種" in out.columns:
        out = out[out["車種"].isin(train_types)]
    if regions and "路線區段" in out.columns:
        out = out[out["路線區段"].isin(regions)]
    return out


def summarize_by_period(df: pd.DataFrame, value_col: str = "延誤分鐘") -> pd.DataFrame:
    """彙整各春節節點的平均與樣本數。"""
    if df is None or df.empty or "春節節點" not in df.columns:
        return pd.DataFrame(columns=["春節節點", "平均", "樣本數"])
    grouped = (
        df.groupby("春節節點", observed=True)[value_col]
        .agg(["mean", "size"])
        .rename(columns={"mean": "平均", "size": "樣本數"})
        .reset_index()
    )
    grouped["春節節點"] = pd.Categorical(
        grouped["春節節點"], categories=CNY_PERIOD_ORDER, ordered=True
    )
    return grouped.sort_values("春節節點").reset_index(drop=True)


def summarize_by_year(df: pd.DataFrame, value_col: str = "延誤分鐘") -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["年", "平均", "樣本數"])
    return (
        df.groupby("年", observed=True)[value_col]
        .agg(["mean", "size"])
        .rename(columns={"mean": "平均", "size": "樣本數"})
        .reset_index()
    )


def summarize_by_station(df: pd.DataFrame) -> pd.DataFrame:
    """聚合每站的平均誤點與觀測數（熱力圖用）。"""
    if df is None or df.empty:
        return pd.DataFrame()
    cols_needed = {"StationID", "StationNameZh_tw", "延誤分鐘"}
    if not cols_needed.issubset(df.columns):
        return pd.DataFrame()
    return (
        df.groupby(["StationID", "StationNameZh_tw"], observed=True)["延誤分鐘"]
        .agg(["mean", "size"])
        .rename(columns={"mean": "平均延誤", "size": "觀測數"})
        .reset_index()
    )
