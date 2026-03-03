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

    # ── 首末班車時間表（供查詢用）──
    tt_df, _ = dp._load_timetable()
    if not tt_df.empty:
        first_trains = (tt_df[tt_df["StopSeq"] == 1]
                        [["TrainNo", "TrainTypeSimple", "StartingStationID",
                           "EndingStationID", "ScheduledDep", "Direction", "TripLine"]]
                        .rename(columns={"ScheduledDep": "FirstDep",
                                         "StartingStationID": "FromStationID",
                                         "EndingStationID": "ToStationID"})
                        .drop_duplicates(subset=["TrainNo"]))
        last_trains = (tt_df[tt_df["IsTerminal"] == 1]
                       [["TrainNo", "ScheduledArr"]]
                       .rename(columns={"ScheduledArr": "LastArr"})
                       .drop_duplicates(subset=["TrainNo"]))
        train_schedule = first_trains.merge(last_trains, on="TrainNo", how="left")

        # 合併車站名稱（起迄站）
        sname = {}
        if os.path.exists(stations_path):
            for s in stations_data.get("Stations", []):
                sname[s.get("StationID")] = s.get("StationName", {}).get("Zh_tw", "")
        train_schedule["FromStation"] = train_schedule["FromStationID"].map(sname)
        train_schedule["ToStation"]   = train_schedule["ToStationID"].map(sname)

        sched_path = os.path.join(DATA_DIR, "train_schedule.csv")
        train_schedule.to_csv(sched_path, index=False, encoding="utf-8-sig")
        print(f"train_schedule.csv 匯出完成（{len(train_schedule)} 班次）")
else:
    print("無資料可匯出")

