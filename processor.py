import json
import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime, date

# ── 雲端模式偵測 ──────────────────────────────────────────────
# 若環境變數 STREAMLIT_CLOUD=1，則從 GitHub raw 讀取 CSV
CLOUD_MODE = os.environ.get("STREAMLIT_CLOUD", "0") == "1"
GITHUB_RAW_BASE = os.environ.get(
    "GITHUB_RAW_BASE",
    "https://raw.githubusercontent.com/Lawliet0813/TRA_-delaydata_anlze/main/data"
)

# ══════════════════════════════════════════════════════════════
#  常數定義
# ══════════════════════════════════════════════════════════════

# 車種簡化對照：統一歸為五類
def _simplify_type(type_name: str) -> str:
    if not type_name: return "其他"
    if '太魯閣' in type_name or '普悠瑪' in type_name: return "傾斜式自強"
    if '自強' in type_name: return "自強"
    if '區間快' in type_name: return "區間快"
    if '區間' in type_name: return "區間"
    if '莒光' in type_name: return "莒光"
    return "其他"

# 時段分類（參照 Notion 研究設計）
def _get_period(time_str: str) -> str:
    try:
        h = int(str(time_str).split(":")[0])
        if (6 <= h < 9) or (17 <= h < 20): return "尖峰"
        if 0 <= h < 6: return "深夜"
        return "離峰"
    except:
        return "未知"

# 國定假日（114學年度，115/02/28 起至 115/06/30）
_NATIONAL_HOLIDAYS = {
    '2026-02-28', '2026-04-03', '2026-04-04',
    '2026-05-01', '2026-05-31', '2026-06-06',
}

def _holiday_type(date_str: str) -> str:
    """回傳 '平日' / '週末' / '國定假日' / '連假'"""
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        if date_str in _NATIONAL_HOLIDAYS: return "國定假日"
        if d.weekday() >= 5: return "週末"
        return "平日"
    except:
        return "未知"

def _is_holiday(date_str: str) -> int:
    return 0 if _holiday_type(date_str) == "平日" else 1


# ══════════════════════════════════════════════════════════════
#  時刻表衍生變數計算
# ══════════════════════════════════════════════════════════════

def _time_to_minutes(t: str) -> float:
    """將 HH:MM 轉為距午夜分鐘數，處理跨日（>= 24:00）"""
    try:
        h, m = map(int, t.split(":"))
        return h * 60 + m
    except:
        return np.nan

def build_timetable_features(timetable_path: str) -> pd.DataFrame:
    """
    從時刻表 JSON 計算每個【班次 × 車站】的結構性特徵：
    - StopSeq       : 停靠順序（從 1 開始）
    - TrainTypeSimple: 簡化車種
    - ScheduledArr  : 表定到站時間（HH:MM）
    - ScheduledDep  : 表定開車時間
    - DwellMin      : 停站時分（分鐘）
    - RunMin        : 本區間運轉時分（與前站之差）
    - IsTerminal    : 是否為終點站（0/1）
    
    以及每個【車站 × 時段】的車種混合度：
    - MixIndex      : 同站同小時內行駛的不同車種數
    - SpeedDiff     : 同站同小時內最快與最慢車種運轉時分差（分鐘）
    """
    with open(timetable_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for train in data.get("TrainTimetables", []):
        info = train.get("TrainInfo", {})
        train_no = info.get("TrainNo")
        type_raw = info.get("TrainTypeName", {}).get("Zh_tw", "")
        type_simple = _simplify_type(type_raw)
        stops = train.get("StopTimes", [])
        n = len(stops)

        for i, stop in enumerate(stops):
            arr_str = stop.get("ArrivalTime", "")
            dep_str = stop.get("DepartureTime", "")
            arr_min = _time_to_minutes(arr_str)
            dep_min = _time_to_minutes(dep_str)

            # 與前站的運轉時分
            if i > 0:
                prev_dep = _time_to_minutes(stops[i-1].get("DepartureTime", ""))
                run_min = arr_min - prev_dep if not np.isnan(arr_min) and not np.isnan(prev_dep) else np.nan
            else:
                run_min = np.nan

            records.append({
                "TrainNo": train_no,
                "TrainTypeRaw": type_raw,
                "TrainTypeSimple": type_simple,
                "StationID": stop.get("StationID"),
                "StopSeq": stop.get("StopSequence", i + 1),
                "ScheduledArr": arr_str,
                "ScheduledDep": dep_str,
                "ArrMinute": arr_min,
                "DepMinute": dep_min,
                "DwellMin": dep_min - arr_min if not np.isnan(dep_min) and not np.isnan(arr_min) else 0,
                "RunMin": run_min,
                "IsTerminal": 1 if i == n - 1 else 0,
            })

    df = pd.DataFrame(records)
    if df.empty:
        return df, pd.DataFrame()

    # ── 車種混合度 & 速差指標（以小時為單位，依站聚合）──
    df["ArrHour"] = df["ArrMinute"].apply(lambda x: int(x // 60) if not np.isnan(x) else -1)
    mix_df = df.groupby(["StationID", "ArrHour"]).agg(
        MixIndex=("TrainTypeSimple", "nunique"),
        SpeedDiff=("RunMin", lambda x: x.max() - x.min() if x.count() > 1 else 0)
    ).reset_index()

    return df, mix_df


# ══════════════════════════════════════════════════════════════
#  DataProcessor 主類別
# ══════════════════════════════════════════════════════════════

class DataProcessor:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._timetable_df = None    # 時刻表快取
        self._mix_df = None          # 混合度快取
        self._stations_df = None     # 站點快取
        self.reason_definitions = {
            "號誌通信故障": "號誌顯示異常、聯鎖失效、通信系統斷路或無線電故障。",
            "車輛故障": "機車頭或動力車組引擎、馬達、韌機或空調設備失效。",
            "電力設備故障": "電車線斷線、變電站跳電、集電弓受損或受流異常。",
            "軌道道岔故障": "道岔無法轉位、軌道裂縫、路基下陷或轉轍器異常。",
            "天候災害": "豪雨淹水、地震限速、颱風強風、落雷影響或土石流。",
            "平交道事故": "公路車輛闖越平交道、撞擊事故或避難引導。",
            "外物入侵/死傷": "行人或動物闖入軌道、路樹倒塌、雜物掉落電車線。",
            "旅客因素": "旅客急救、車門被夾、人潮擁擠上下車緩慢、拉緊急開關。",
            "施工影響": "配合鐵路工程、路線維修作業、電車線更新工程。",
            "運轉調度": "列車待避、交會、等候接駁、路線更換或編組調整。",
            "其他": "無法歸類之隨機因素、他局延誤接續等。"
        }

    # ── 快取載入 ─────────────────────────────────────────────

    def _load_timetable(self):
        if self._timetable_df is not None:
            return self._timetable_df, self._mix_df
        files = glob.glob(os.path.join(self.data_dir, "timetable", "*.json"))
        if not files:
            return pd.DataFrame(), pd.DataFrame()
        latest = max(files, key=os.path.getmtime)
        self._timetable_df, self._mix_df = build_timetable_features(latest)
        return self._timetable_df, self._mix_df

    def _load_stations(self):
        if self._stations_df is not None:
            return self._stations_df
        path = os.path.join(self.data_dir, "static", "stations.json")
        if not os.path.exists(path):
            self._stations_df = pd.DataFrame()
            return self._stations_df
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = [{"StationID": s.get("StationID"),
                    "StationName": s.get("StationName", {}).get("Zh_tw"),
                    "Lat": s.get("StationPosition", {}).get("PositionLat"),
                    "Lon": s.get("StationPosition", {}).get("PositionLon")}
                   for s in data.get("Stations", [])]
        self._stations_df = pd.DataFrame(records)
        return self._stations_df

    def get_terminal_stations(self):
        tt, _ = self._load_timetable()
        if tt.empty: return {}
        terminals = tt[tt["IsTerminal"] == 1][["TrainNo", "StationID"]]
        return dict(zip(terminals["TrainNo"], terminals["StationID"]))

    def get_stations_data(self):
        return self._load_stations()


    # ── 全台原始資料（儀表板用）────────────────────────────────

    def parse_live_board(self, date_str=None):
        """讀取全台 live_board，回傳基本清理後的 DataFrame（供儀表板總覽用）
        雲端模式：直接讀 GitHub raw CSV，不解析 JSON。
        """
        if CLOUD_MODE or not os.path.exists(self.data_dir):
            url = f"{GITHUB_RAW_BASE}/processed_data.csv"
            try:
                df = pd.read_csv(url)
                return df
            except Exception as e:
                return pd.DataFrame()

        pattern = os.path.join(self.data_dir, "live_board",
                               date_str if date_str else "*", "*.json")
        files = glob.glob(pattern)
        if not files: return pd.DataFrame()

        records = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                date_folder = os.path.basename(os.path.dirname(f))
                crawl_time = os.path.basename(f).replace(".json", "")
                for r in data.get("TrainLiveBoards", []):
                    records.append({
                        "Date": date_folder,
                        "CrawlTime": crawl_time,
                        "TrainNo": r.get("TrainNo"),
                        "StationID": r.get("StationID"),
                        "StationName": r.get("StationName", {}).get("Zh_tw"),
                        "TrainTypeRaw": r.get("TrainTypeName", {}).get("Zh_tw"),
                        "UpdateTime": r.get("UpdateTime", ""),
                        "ArrivalDelay": r.get("DelayTime", 0),
                    })
            except:
                pass

        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df = df.sort_values("CrawlTime").drop_duplicates(
            subset=["Date", "TrainNo", "StationID"], keep="last")

        df["TrainType"] = df["TrainTypeRaw"].apply(_simplify_type)
        df["IsDelayed"] = (df["ArrivalDelay"] >= 5).astype(int)

        # 從時刻表合併表定到站時間
        tt, _ = self._load_timetable()
        if not tt.empty:
            sched = tt[["TrainNo", "StationID", "ScheduledArr"]].drop_duplicates(
                subset=["TrainNo", "StationID"])
            df = df.merge(sched, on=["TrainNo", "StationID"], how="left")
        else:
            df["ScheduledArr"] = ""

        df["Period"] = df["ScheduledArr"].apply(_get_period)
        df["IsHoliday"] = df["Date"].apply(_is_holiday)
        df["HolidayType"] = df["Date"].apply(_holiday_type)

        # 終點站標記
        # TDX LiveBoard 特性：列車到終點後即從 API 消失，無法直接比對終點站 ID
        # 改用「同一班次當天最後一筆抓取記錄」作為接近終點的代理觀測值
        terminal_map = self.get_terminal_stations()
        df["ScheduledTerminalID"] = df["TrainNo"].map(terminal_map)
        df_sorted = df.sort_values(["Date", "TrainNo", "CrawlTime"])
        last_idx = df_sorted.groupby(["Date", "TrainNo"]).tail(1).index
        df["IsLastRecord"] = df.index.isin(last_idx).astype(int)
        df["IsTerminal"] = df["IsLastRecord"]  # 保留欄位名稱供舊頁面相容

        # 座標合併
        stations = self._load_stations()
        if not stations.empty:
            df = df.merge(stations[["StationID", "Lat", "Lon"]],
                          on="StationID", how="left")
        return df


    # ── 研究用資料集（含完整自變數）────────────────────────────

    def build_research_dataset(self, date_str=None):
        """
        建構全台研究用資料集，對應 Notion 研究設計：
        Y₁ IsDelayed（0/1）、Y₂ DelayTime（連續）
        ...
        雲端模式：直接讀 GitHub raw research_dataset.csv。
        """
        if CLOUD_MODE or not os.path.exists(self.data_dir):
            # 先嘗試 research_dataset，fallback 到 processed_data
            for fname in ["research_dataset.csv", "processed_data.csv"]:
                url = f"{GITHUB_RAW_BASE}/{fname}"
                try:
                    df = pd.read_csv(url)
                    if not df.empty:
                        return df
                except Exception:
                    pass
            return pd.DataFrame()
        pattern = os.path.join(self.data_dir, "live_board",
                               date_str if date_str else "*", "*.json")
        files = glob.glob(pattern)
        if not files: return pd.DataFrame()

        records = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                date_folder = os.path.basename(os.path.dirname(f))
                crawl_time = os.path.basename(f).replace(".json", "")
                for r in data.get("TrainLiveBoards", []):
                    records.append({
                        "Date": date_folder,
                        "CrawlTime": crawl_time,
                        "TrainNo": r.get("TrainNo"),
                        "StationID": r.get("StationID"),
                        "StationName": r.get("StationName", {}).get("Zh_tw"),
                        "TrainTypeRaw": r.get("TrainTypeName", {}).get("Zh_tw", ""),
                        "UpdateTime": r.get("UpdateTime", ""),
                        "DelayTime": r.get("DelayTime", 0),
                    })
            except:
                pass

        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)

        # 去重複
        df = df.sort_values("CrawlTime").drop_duplicates(
            subset=["Date", "TrainNo", "StationID"], keep="last")

        # ── 基本分類變數 ──
        df["TrainType"] = df["TrainTypeRaw"].apply(_simplify_type)
        df["IsDelayed"] = (df["DelayTime"] >= 5).astype(int)

        # 從時刻表合併表定到站時間
        tt_df, mix_df = self._load_timetable()
        if not tt_df.empty:
            sched = tt_df[["TrainNo", "StationID", "ScheduledArr"]].drop_duplicates(
                subset=["TrainNo", "StationID"])
            df = df.merge(sched, on=["TrainNo", "StationID"], how="left")
        else:
            df["ScheduledArr"] = ""

        df["Period"] = df["ScheduledArr"].apply(_get_period)
        df["IsHoliday"] = df["Date"].apply(_is_holiday)
        df["HolidayType"] = df["Date"].apply(_holiday_type)
        df["IsDelayed"] = (df["DelayTime"] >= 5).astype(int)

        # 星期、月份
        def safe_date(date_str):
            try: return datetime.strptime(date_str, "%Y-%m-%d")
            except: return None
        df["_dt"] = df["Date"].apply(safe_date)
        df["Weekday"] = df["_dt"].apply(lambda d: d.weekday() if d else np.nan)  # 0=週一
        df["Month"] = df["_dt"].apply(lambda d: d.month if d else np.nan)
        df.drop(columns=["_dt"], inplace=True)


        # ── 合併時刻表特徵（StopSeq、MixIndex、SpeedDiff）──
        if not tt_df.empty:
            tt_merge = tt_df[["TrainNo", "StationID", "StopSeq",
                               "IsTerminal", "RunMin"]].drop_duplicates(
                subset=["TrainNo", "StationID"])
            df = df.merge(tt_merge, on=["TrainNo", "StationID"], how="left")
        else:
            df["StopSeq"] = np.nan
            df["IsTerminal"] = 0
            df["RunMin"] = np.nan

        if not mix_df.empty:
            # 用到站小時合併混合度
            df["_ArrHour"] = df["ScheduledArr"].apply(
                lambda t: int(t.split(":")[0]) if isinstance(t, str) and ":" in t else -1)
            df = df.merge(mix_df, left_on=["StationID", "_ArrHour"],
                          right_on=["StationID", "ArrHour"], how="left")
            df.drop(columns=["_ArrHour", "ArrHour"], errors="ignore", inplace=True)
        else:
            df["MixIndex"] = np.nan
            df["SpeedDiff"] = np.nan

        # ── 前站誤點（PrevDelay）──
        df = df.sort_values(["Date", "TrainNo", "StopSeq"])
        df["PrevDelay"] = df.groupby(["Date", "TrainNo"])["DelayTime"].shift(1).fillna(0)

        # ── 靜態結構變數（預留欄位，由手動表填入）──
        static_path = os.path.join(self.data_dir, "static", "station_structure.csv")
        if os.path.exists(static_path):
            struct = pd.read_csv(static_path, dtype={"StationID": str})
            df = df.merge(struct, on="StationID", how="left")
        else:
            df["StationGrade"] = np.nan   # X₆ 待填
            df["SideTrackCount"] = np.nan # X₇ 待填
            df["IsDouble"] = np.nan       # X₈ 待填

        # ── 整理輸出欄位 ──
        cols = [
            "Date", "Weekday", "Month",
            "TrainNo", "TrainType",
            "StationID", "StationName", "StopSeq",
            "ScheduledArr", "Period", "IsHoliday", "HolidayType",
            "IsTerminal", "RunMin",
            "StationGrade", "SideTrackCount", "IsDouble",
            "MixIndex", "SpeedDiff",
            "PrevDelay", "DelayTime", "IsDelayed"
        ]
        df = df[[c for c in cols if c in df.columns]].reset_index(drop=True)
        return df

    def export_research_csv(self):
        df = self.build_research_dataset()
        if df.empty:
            print("無資料可匯出"); return None
        out = os.path.join(self.data_dir, "research_dataset.csv")
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"研究資料集已匯出：{out}（{len(df)} 筆）")
        return out


    # ── 異常通報解析 ─────────────────────────────────────────

    def parse_alerts(self, date_str=None):
        pattern = os.path.join(self.data_dir, "alerts",
                               date_str if date_str else "*", "*.json")
        files = glob.glob(pattern)
        if not files: return pd.DataFrame()
        records = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                for r in data.get("Alerts", []):
                    desc = r.get("Description", "")
                    cat = "其他"
                    if any(k in desc for k in ["號誌", "電力", "設備", "故障"]): cat = "設備故障"
                    elif any(k in desc for k in ["天候", "豪雨", "地震", "颱風"]): cat = "天候災害"
                    elif any(k in desc for k in ["旅客", "救護"]): cat = "旅客因素"
                    elif any(k in desc for k in ["調度", "待避", "交會"]): cat = "運轉調度"
                    elif any(k in desc for k in ["平交道"]): cat = "平交道事故"
                    elif any(k in desc for k in ["施工", "維修"]): cat = "施工影響"
                    records.append({
                        "PublishTime": r.get("PublishTime"),
                        "Category": cat,
                        "Description": desc
                    })
            except:
                pass
        return pd.DataFrame(records).drop_duplicates()

