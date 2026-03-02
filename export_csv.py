"""
GitHub Actions 呼叫的匯出腳本。
產生 data/processed_data.csv 和 data/research_dataset.csv 供 Streamlit Cloud 讀取。
"""
import json
import os
import pandas as pd
from processor import DataProcessor

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

dp = DataProcessor(DATA_DIR)

# research_dataset（完整自變數版）
df = dp.build_research_dataset()
if not df.empty:
    out = os.path.join(DATA_DIR, "research_dataset.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"research_dataset.csv 匯出完成（{len(df)} 筆）")

    # 合併車站座標
    stations_path = os.path.join(DATA_DIR, "static", "stations.json")
    if os.path.exists(stations_path):
        with open(stations_path, "r", encoding="utf-8") as f:
            stations_data = json.load(f)
        station_records = [
            {
                "StationID": s.get("StationID"),
                "Lat": s.get("StationPosition", {}).get("PositionLat"),
                "Lon": s.get("StationPosition", {}).get("PositionLon"),
            }
            for s in stations_data.get("Stations", [])
        ]
        stations_df = pd.DataFrame(station_records)
        if not stations_df.empty:
            df["StationID"] = df["StationID"].astype(str)
            stations_df["StationID"] = stations_df["StationID"].astype(str)
            # 若 df 已有 Lat/Lon 欄位先移除再重新 merge
            df = df.drop(columns=["Lat", "Lon"], errors="ignore")
            df = df.merge(stations_df, on="StationID", how="left")

        # 額外匯出 stations_coords.csv 供雲端模式使用
        coords_records = [
            {
                "StationID": s.get("StationID"),
                "StationName": s.get("StationName", {}).get("Zh_tw", ""),
                "Lat": s.get("StationPosition", {}).get("PositionLat"),
                "Lon": s.get("StationPosition", {}).get("PositionLon"),
            }
            for s in stations_data.get("Stations", [])
        ]
        coords_df = pd.DataFrame(coords_records)
        coords_path = os.path.join(DATA_DIR, "stations_coords.csv")
        coords_df.to_csv(coords_path, index=False, encoding="utf-8-sig")
        print(f"stations_coords.csv saved: {len(coords_df)} 站")

    # processed_data（Streamlit Cloud 主要讀取來源）
    out2 = os.path.join(DATA_DIR, "processed_data.csv")
    df.to_csv(out2, index=False, encoding="utf-8-sig")
    print(f"processed_data.csv 匯出完成（{len(df)} 筆）")
else:
    print("無資料可匯出")

