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

# ── 準點率判定門檻 ──────────────────────────────────────────
# OFFICIAL_DELAY_THRESHOLD : 台鐵官方終點站口徑（5 分鐘）
# RESEARCH_DELAY_THRESHOLD : 本研究路網站間口徑（2 分鐘，參考日本/英國高標準）
OFFICIAL_DELAY_THRESHOLD = 5   # 單位：分鐘
RESEARCH_DELAY_THRESHOLD = 2   # 單位：分鐘

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
                "Direction": info.get("Direction", np.nan),
                "TripLine": info.get("TripLine", np.nan),
                "StartingStationID": info.get("StartingStationID", ""),
                "EndingStationID": info.get("EndingStationID", ""),
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
        self._line_network_df = None # 路線網路快取
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
        # 優先用 DailyTrainTimetable（daily_*.json），其次用 GeneralTrainTimetable
        daily_files = glob.glob(os.path.join(self.data_dir, "timetable", "daily_*.json"))
        general_files = glob.glob(os.path.join(self.data_dir, "timetable", "*.json"))
        general_files = [f for f in general_files if "daily_" not in os.path.basename(f)]
        files = daily_files if daily_files else general_files
        if not files:
            return pd.DataFrame(), pd.DataFrame()
        latest = max(files, key=os.path.getmtime)
        self._timetable_df, self._mix_df = build_timetable_features(latest)
        return self._timetable_df, self._mix_df

    def _load_train_types(self):
        """載入 TrainType 對照表，回傳 {TrainTypeID: {code, name_zh, simple}} dict。"""
        path = os.path.join(self.data_dir, "static", "train_types.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {}
        for t in data.get("TrainTypes", []):
            tid = t.get("TrainTypeID", "")
            code = str(t.get("TrainTypeCode", ""))
            name_zh = t.get("TrainTypeName", {}).get("Zh_tw", "")
            result[tid] = {
                "code": code,
                "name_zh": name_zh,
                "simple": _simplify_type(name_zh),
            }
        return result

    def _load_stations(self):
        if self._stations_df is not None:
            return self._stations_df

        # 雲端模式：優先從 stations_coords.csv，fallback 到 stations.json
        if CLOUD_MODE:
            from datetime import datetime as _dt
            import urllib.request
            cache_busting = int(_dt.now().timestamp())
            try:
                url = f"{GITHUB_RAW_BASE}/stations_coords.csv?v={cache_busting}"
                df = pd.read_csv(url, dtype={"StationID": str})
                if not df.empty and "Lat" in df.columns:
                    self._stations_df = df[["StationID", "StationName", "Lat", "Lon"]]
                    return self._stations_df
            except Exception:
                pass
            try:
                url = f"{GITHUB_RAW_BASE}/static/stations.json?v={cache_busting}"
                with urllib.request.urlopen(url) as resp:
                    data = json.loads(resp.read().decode())
                records = [{"StationID": s.get("StationID"),
                            "StationName": s.get("StationName", {}).get("Zh_tw"),
                            "Lat": s.get("StationPosition", {}).get("PositionLat"),
                            "Lon": s.get("StationPosition", {}).get("PositionLon")}
                           for s in data.get("Stations", [])]
                self._stations_df = pd.DataFrame(records)
                return self._stations_df
            except Exception:
                self._stations_df = pd.DataFrame()
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

    def _load_line_network(self):
        """載入 LineNetwork，建構每條路線的站序與累積里程對照。"""
        if self._line_network_df is not None:
            return self._line_network_df
        path = os.path.join(self.data_dir, "static", "line_network.json")
        if not os.path.exists(path):
            self._line_network_df = pd.DataFrame()
            return self._line_network_df
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = []
        for line in data.get("LineNetworks", []):
            line_id = line.get("LineID")
            line_name = line.get("LineName", {}).get("Zh_tw", "")
            segs = line.get("LineSegments", [])
            cum_km = 0.0
            # 第一站
            if segs:
                records.append({
                    "LineID": line_id, "LineName": line_name,
                    "StationID": segs[0].get("FromStationID"),
                    "StationOrder": 0, "CumulativeKM": 0.0,
                })
            for i, seg in enumerate(segs):
                cum_km += seg.get("Distance", 0)
                records.append({
                    "LineID": line_id, "LineName": line_name,
                    "StationID": seg.get("ToStationID"),
                    "StationOrder": i + 1, "CumulativeKM": round(cum_km, 1),
                })
        self._line_network_df = pd.DataFrame(records)
        return self._line_network_df

    def get_line_network(self):
        return self._load_line_network()

    def _load_shape(self) -> dict:
        import re, urllib.request

        def _parse_shape_data(data) -> dict:
            shapes = {}
            for s in data.get("Shapes", []):
                line_id = s.get("LineID", "")
                line_name = s.get("LineName", {}).get("Zh_tw", line_id)
                geom = s.get("Geometry", "")
                coords_str = re.findall(r"LINESTRING\((.+)\)", geom, re.IGNORECASE)
                if not coords_str:
                    continue
                try:
                    pairs = [
                        (float(c.strip().split()[0]), float(c.strip().split()[1]))
                        for c in coords_str[0].split(",")
                        if len(c.strip().split()) >= 2
                    ]
                    if not pairs:
                        continue
                    lons, lats = zip(*pairs)
                    shapes[line_id] = {"lons": list(lons), "lats": list(lats), "name": line_name}
                except Exception:
                    continue
            return shapes

        # 雲端模式：從 GitHub raw 讀取
        if CLOUD_MODE:
            from datetime import datetime as _dt
            cache_busting = int(_dt.now().timestamp())
            try:
                url = f"{GITHUB_RAW_BASE}/static/shape.json?v={cache_busting}"
                with urllib.request.urlopen(url) as resp:
                    data = json.loads(resp.read().decode())
                return _parse_shape_data(data)
            except Exception:
                return {}

        path = os.path.join(self.data_dir, "static", "shape.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _parse_shape_data(data)

    def get_shape(self) -> dict:
        return self._load_shape()

    def get_station_order_for_train(self, station_ids: list) -> pd.DataFrame:
        """
        給定一組 StationID，找出最匹配的路線並回傳站序。
        用途：車次追蹤頁面依地理順序排列停靠站。
        """
        ln = self._load_line_network()
        if ln.empty:
            return pd.DataFrame()

        # 找哪條路線包含最多該車次的站
        best_line = None
        best_count = 0
        for line_id, group in ln.groupby("LineID"):
            matched = len(set(station_ids) & set(group["StationID"]))
            if matched > best_count:
                best_count = matched
                best_line = line_id

        if not best_line:
            return pd.DataFrame()

        line_df = ln[ln["LineID"] == best_line].copy()
        result = line_df[line_df["StationID"].isin(station_ids)]
        return result.sort_values("StationOrder")

    def _parse_raw_json(self, data_subdir: str, root_key: str,
                        date_str=None) -> pd.DataFrame:
        """
        統一解析 data/<data_subdir>/<date>/<time>.json 格式的即時資料。
        StationLiveBoard 直接含有 ScheduleArrivalTime / ScheduleDepartureTime，
        不需再 join 時刻表取得表定到站時間。
        """
        pattern = os.path.join(self.data_dir, data_subdir,
                               date_str if date_str else "*", "*.json")
        files = glob.glob(pattern)
        if not files:
            return pd.DataFrame()

        records = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                date_folder = os.path.basename(os.path.dirname(f))
                crawl_time = os.path.basename(f).replace(".json", "")
                for r in data.get(root_key, []):
                    # ScheduleArrivalTime 格式為 HH:MM:SS，取前 5 碼統一為 HH:MM
                    arr_raw = r.get("ScheduleArrivalTime", "")
                    arr_hhmm = arr_raw[:5] if arr_raw else ""
                    dep_raw = r.get("ScheduleDepartureTime", "")
                    dep_hhmm = dep_raw[:5] if dep_raw else ""
                    records.append({
                        "Date": date_folder,
                        "CrawlTime": crawl_time,
                        "TrainNo": r.get("TrainNo"),
                        "StationID": r.get("StationID"),
                        "StationName": r.get("StationName", {}).get("Zh_tw"),
                        "TrainTypeRaw": r.get("TrainTypeName", {}).get("Zh_tw", ""),
                        "Direction": r.get("Direction", np.nan),
                        "TripLine": r.get("TripLine", np.nan),
                        "EndingStationID": r.get("EndingStationID", ""),
                        "ScheduleArrivalTime": arr_hhmm,
                        "ScheduleDepartureTime": dep_hhmm,
                        "RunningStatus": r.get("RunningStatus", 0),
                        "UpdateTime": r.get("UpdateTime", ""),
                        "DelayTime": r.get("DelayTime", 0),
                    })
            except:
                pass

        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)

        # 去重複：同日同車次同車站只保留最後一筆
        df = df.sort_values("CrawlTime").drop_duplicates(
            subset=["Date", "TrainNo", "StationID"], keep="last")
        return df


    def _enrich_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """為解析後的 DataFrame 加上基本分類變數。
        表定到站時間直接使用 StationLiveBoard 的 ScheduleArrivalTime，
        不需 join GeneralTrainTimetable（SKILL 規範第3點）。
        """
        df["TrainType"] = df["TrainTypeRaw"].apply(_simplify_type)

        # Y1：官方口徑（終點站 5 分鐘）— 主要依變數
        df["IsDelayed"] = (df["DelayTime"] >= OFFICIAL_DELAY_THRESHOLD).astype(int)
        # Y1b：研究口徑（路網站間 2 分鐘）— 輔助比較用
        df["IsDelayed_Research"] = (df["DelayTime"] >= RESEARCH_DELAY_THRESHOLD).astype(int)

        # ScheduledArr 直接從 API 欄位取得，統一欄位名稱
        df["ScheduledArr"] = df["ScheduleArrivalTime"] if "ScheduleArrivalTime" in df.columns else ""

        # Period 由 ScheduledArr 衍生
        df["Period"] = df["ScheduledArr"].apply(_get_period)
        df["IsHoliday"] = df["Date"].apply(_is_holiday)
        df["HolidayType"] = df["Date"].apply(_holiday_type)
        return df


    # ── 全台原始資料（儀表板用）────────────────────────────────

    def parse_live_board(self, date_str=None):
        """讀取全台 live_board，回傳基本清理後的 DataFrame（供儀表板總覽用）
        雲端模式：直接讀 GitHub raw CSV，不解析 JSON。
        """
        if CLOUD_MODE or not os.path.exists(self.data_dir):
            from datetime import datetime
            cache_busting = int(datetime.now().timestamp())
            url = f"{GITHUB_RAW_BASE}/processed_data.csv?v={cache_busting}"
            try:
                df = pd.read_csv(url)
                # 雲端模式：若 CSV 不含座標欄位，嘗試從 stations_coords.csv 補充
                if df.empty:
                    return df
                if "Lat" not in df.columns or df["Lat"].isna().all():
                    coords_url = f"{GITHUB_RAW_BASE}/stations_coords.csv?v={cache_busting}"
                    try:
                        coords_df = pd.read_csv(coords_url, dtype={"StationID": str})
                        if not coords_df.empty and "Lat" in coords_df.columns:
                            df["StationID"] = df["StationID"].astype(str)
                            df = df.merge(coords_df[["StationID", "Lat", "Lon"]], on="StationID", how="left")
                    except Exception:
                        pass
                return df
            except Exception as e:
                return pd.DataFrame()

        df = self._parse_raw_json("live_board", "TrainLiveBoards", date_str)
        if df.empty:
            return df

        df = self._enrich_base_features(df)

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


    # ── StationLiveBoard 解析（新核心）────────────────────────

    def parse_station_live(self, date_str=None):
        """讀取 station_live 資料夾，回傳與 parse_live_board 相同結構的 DataFrame。"""
        if CLOUD_MODE or not os.path.exists(self.data_dir):
            return self.parse_live_board(date_str)

        df = self._parse_raw_json("station_live", "StationLiveBoards", date_str)
        if df.empty:
            return df

        df = self._enrich_base_features(df)

        # 終點站標記
        terminal_map = self.get_terminal_stations()
        df["ScheduledTerminalID"] = df["TrainNo"].map(terminal_map)
        df_sorted = df.sort_values(["Date", "TrainNo", "CrawlTime"])
        last_idx = df_sorted.groupby(["Date", "TrainNo"]).tail(1).index
        df["IsLastRecord"] = df.index.isin(last_idx).astype(int)
        df["IsTerminal"] = df["IsLastRecord"]

        # 座標合併
        stations = self._load_stations()
        if not stations.empty:
            df = df.merge(stations[["StationID", "Lat", "Lon"]],
                          on="StationID", how="left")
        return df


    # ── 研究用資料集（含完整自變數）────────────────────────────

    def build_research_dataset(self, date_str=None):
        """
        建構研究用資料集（分析單位1：車次×車站）。
        Y1 IsDelayed（官方 5 分鐘口徑）、Y2 DelayTime（連續）
        雲端模式：直接讀 GitHub raw processed_data.csv。
        """
        if CLOUD_MODE or not os.path.exists(self.data_dir):
            from datetime import datetime
            cache_busting = int(datetime.now().timestamp())
            for fname in ["processed_data.csv", "research_dataset.csv"]:
                url = f"{GITHUB_RAW_BASE}/{fname}?v={cache_busting}"
                try:
                    df = pd.read_csv(url)
                    if not df.empty:
                        return df
                except Exception:
                    pass
            return pd.DataFrame()

        df = self._parse_raw_json("station_live", "StationLiveBoards", date_str)
        if df.empty:
            return df

        df = self._enrich_base_features(df)

        # 星期、月份
        def safe_date(ds):
            try: return datetime.strptime(ds, "%Y-%m-%d")
            except: return None
        df["_dt"] = df["Date"].apply(safe_date)
        df["Weekday"] = df["_dt"].apply(lambda d: d.weekday() if d else np.nan)
        df["Month"] = df["_dt"].apply(lambda d: d.month if d else np.nan)
        df.drop(columns=["_dt"], inplace=True)

        # ── 終點站標記：EndingStationID 直接來自 LiveBoard ──
        df["IsTerminal"] = (
            df["StationID"].astype(str) == df["EndingStationID"].astype(str)
        ).astype(int)

        # ── StopSeq、RunMin、MixIndex：仍需 GeneralTimetable 計算 ──
        tt_df, mix_df = self._load_timetable()
        if not tt_df.empty:
            tt_merge = tt_df[["TrainNo", "StationID", "StopSeq", "RunMin"]].drop_duplicates(
                subset=["TrainNo", "StationID"])
            df = df.merge(tt_merge, on=["TrainNo", "StationID"], how="left")

            # 首末班時間
            first_dep = tt_df[tt_df["StopSeq"] == 1].groupby("TrainNo")["ScheduledDep"].first()
            last_arr = tt_df[tt_df["IsTerminal"] == 1].groupby("TrainNo")["ScheduledArr"].first()
            df["FirstDep"] = df["TrainNo"].map(first_dep)
            df["LastArr"] = df["TrainNo"].map(last_arr)
        else:
            df["StopSeq"] = np.nan
            df["RunMin"] = np.nan
            df["FirstDep"] = np.nan
            df["LastArr"] = np.nan

        if not mix_df.empty:
            df["_ArrHour"] = df["ScheduledArr"].apply(
                lambda t: int(t.split(":")[0]) if isinstance(t, str) and ":" in t else -1)
            df = df.merge(mix_df, left_on=["StationID", "_ArrHour"],
                          right_on=["StationID", "ArrHour"], how="left")
            df.drop(columns=["_ArrHour", "ArrHour"], errors="ignore", inplace=True)
        else:
            df["MixIndex"] = np.nan
            df["SpeedDiff"] = np.nan

        # ── PrevDelay（X9）──
        df = df.sort_values(["Date", "TrainNo", "StopSeq"])
        df["PrevDelay"] = df.groupby(["Date", "TrainNo"])["DelayTime"].shift(1).fillna(0)

        # ── X6 StationClass：從 stations.json 合併 ──
        stations = self._load_stations()
        if not stations.empty and "StationClass" in stations.columns:
            df = df.merge(stations[["StationID", "StationClass"]], on="StationID", how="left")
        else:
            df["StationClass"] = np.nan

        # ── X7 X8：station_structure.csv 手動填 ──
        static_path = os.path.join(self.data_dir, "static", "station_structure.csv")
        if os.path.exists(static_path):
            struct = pd.read_csv(static_path, dtype={"StationID": str})
            df = df.merge(struct, on="StationID", how="left")
        else:
            df["SideTrackCount"] = np.nan
            df["IsDouble"] = np.nan

        # ── 整理輸出欄位 ──
        cols = [
            "Date", "Weekday", "Month",
            "TrainNo", "TrainType", "Direction", "TripLine",
            "StationID", "StationName", "StopSeq",
            "ScheduledArr", "FirstDep", "LastArr",
            "Period", "IsHoliday", "HolidayType",
            "IsTerminal", "RunMin",
            "StationClass", "SideTrackCount", "IsDouble",
            "MixIndex", "SpeedDiff",
            "PrevDelay", "DelayTime", "IsDelayed", "IsDelayed_Research"
        ]
        df = df[[c for c in cols if c in df.columns]].reset_index(drop=True)
        return df

    def export_research_csv(self):
        """
        產生三個分析單位的 CSV，輸出至 data/output/：
        1. processed_data.csv   — 車次×車站（主要）
        2. train_level.csv      — 車次終點誤點
        3. station_level.csv    — 車站平均誤點
        """
        df = self.build_research_dataset()
        if df.empty:
            print("無資料可匯出")
            return None

        out_dir = os.path.join(self.data_dir, "output")
        os.makedirs(out_dir, exist_ok=True)

        # 1. 車次×車站
        out1 = os.path.join(out_dir, "processed_data.csv")
        df.to_csv(out1, index=False, encoding="utf-8-sig")
        print(f"[1] processed_data.csv：{len(df)} 筆")

        # 2. 車次終點（IsTerminal==1 那筆）
        train_df = df[df["IsTerminal"] == 1].copy()
        out2 = os.path.join(out_dir, "train_level.csv")
        train_df.to_csv(out2, index=False, encoding="utf-8-sig")
        print(f"[2] train_level.csv：{len(train_df)} 筆")

        # 3. 車站平均
        agg_dict = {
            "AvgDelay": ("DelayTime", "mean"),
            "DelayRate": ("IsDelayed", "mean"),
            "TotalObs": ("DelayTime", "count"),
        }
        if "StationName" in df.columns:
            agg_dict["StationName"] = ("StationName", "first")
        station_df = df.groupby("StationID").agg(**agg_dict).reset_index()
        out3 = os.path.join(out_dir, "station_level.csv")
        station_df.to_csv(out3, index=False, encoding="utf-8-sig")
        print(f"[3] station_level.csv：{len(station_df)} 站")

        return out_dir


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
