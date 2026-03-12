# 台鐵誤點研究專案狀態

> 最後更新：2026-03-03
> 專案路徑：`tra_delay_crawler/`
> Git 儲存庫：https://github.com/Lawliet0813/TRA_-delaydata_anlze
> Streamlit 雲端版：https://tra-delaydataanlze-cwvejankcpdrlhgtsdsjbf.streamlit.app/

---

## 系統架構狀態

### 資料蒐集（GitHub Actions 雲端排程）✅ 運作中

| 任務 | 頻率 | 狀態 |
|------|------|------|
| StationLiveBoard | 每 10 分鐘（台灣時間 06–24 時） | ✅ 正常 |
| Alert 異常通報 | 每 60 分鐘 | ✅ 正常 |
| Timetable + Station | 每日 06:00 | ✅ 正常 |
| export_csv.py | 每次 crawl 後自動執行 | ✅ 正常 |

> 本機 launchd 排程（`~/Library/LaunchAgents/com.lawliet.tra.*`）因 `~/tra_crawler_runner/` 目錄不存在已停擺，雲端 Actions 為唯一資料來源。

### 資料流向

```
TDX API
  │ 每 10 分鐘（GitHub Actions ubuntu-latest）
  ▼
data/station_live/YYYY-MM-DD/HHMMSS.json
  │ export_csv.py
  ▼
data/processed_data.csv        ← Streamlit 雲端版主要讀取
data/research_dataset.csv      ← OLS 迴歸頁讀取
data/stations_coords.csv       ← 地圖座標補充
data/train_schedule.csv        ← 首末班時間查詢（新）
  │ raw.githubusercontent.com
  ▼
Streamlit 雲端版（儀表板）
```

### 主要模組完成度

| 模組 | 檔案 | 狀態 | 備註 |
|------|------|------|------|
| 爬蟲核心 | `crawlers/station_live.py` | ✅ | StationLiveBoard，每 10 分鐘 |
| 舊爬蟲 | `crawlers/live_board.py` | ⚠️ 廢棄中 | TrainLiveBoard，逐步停用 |
| 時刻表 | `crawlers/timetable.py` | ✅ | DailyTrainTimetable，每日一次 |
| 車站靜態 | `crawlers/station.py` | ✅ | Station + StationClass |
| 異常通報 | `crawlers/alert.py` | ✅ | Alert，每 60 分鐘 |
| 資料處理 | `processor.py` | ⚠️ | IsTerminal / StopSeq join 待驗證（見已知問題） |
| 匯出腳本 | `export_csv.py` | ✅ | 新增 train_schedule.csv 輸出 |
| 儀表板 | `app.py` | ✅ | 雙口徑準點率 + 日期篩選 + 圖表說明 |

---

## 研究變數完成度

### 應變數

| 變數 | 欄位 | 狀態 | 說明 |
|------|------|------|------|
| Y1 | `IsDelayed` | ✅ | DelayTime ≥ 2 分鐘（本研究全站口徑） |
| Y1b | `IsDelayed_Official` | ✅ | DelayTime ≥ 5 分鐘（台鐵官方口徑，僅終點站） |
| Y2 | `DelayTime` | ✅ | TDX 直接回傳，單位：分鐘 |

### 自變數

| 代號 | 欄位 | 狀態 | 說明 |
|------|------|------|------|
| X1 | `TrainType` | ✅ | 車種（自強/區間快/區間/莒光/傾斜式自強/其他） |
| X2 | `StopSeq` | ❌ | 停靠順序。目前 CSV 全為 NaN，時刻表 join 未成功寫入 CSV |
| X3 | `Period` | ✅ | 時段（尖峰/離峰/深夜），由 ScheduledArr 衍生 |
| X4 | `IsHoliday` | ✅ | 假日旗標（0/1） |
| X4b | `HolidayType` | ✅ | 細分：平日 / 週末 / 國定假日 |
| X5 | `MixIndex` | ⚠️ | 同站同小時車種混合度。需 StopSeq 才能正確聚合 |
| X5b | `SpeedDiff` | ⚠️ | 速差指標（最快最慢運轉時分差）。同上 |
| X6 | `StationGrade` | ❌ | 站等級（特等～招呼）。CSV 全為 NaN，Station API join 未生效 |
| X7 | `SideTrackCount` | ❌ | 側線數。待填寫 `data/static/station_structure.csv` |
| X8 | `IsDouble` | ❌ | 單複線別。待填寫 `data/static/station_structure.csv` |
| X9 | `PrevDelay` | ✅ | 前站誤點分鐘數（依 TrainNo + StopSeq 計算） |
| X10 | `Direction` | ✅ | 行駛方向（0=順行基→高，1=逆行高→基） |
| X11 | `TripLine` | ✅ | 路線別（0=山線，1=海線，2=成追線） |

### 新增欄位（本次開發）

| 欄位 | 狀態 | 說明 |
|------|------|------|
| `IsTerminal` | ❌ 待驗證 | 已改以時刻表 EndingStationID 判定，但 CSV 仍顯示全 0，需 Actions 重跑後確認 |
| `FirstDep` | ❌ 待產生 | 始發站出發時間，processor.py 已加但 CSV 尚未包含 |
| `LastArr` | ❌ 待產生 | 終點站到站時間，同上 |

> `IsTerminal`、`FirstDep`、`LastArr`、`train_schedule.csv` 均需等 **下一次 GitHub Actions 執行** 後才會出現在雲端資料。

---

## 已知問題

### 🔴 高優先

| # | 問題 | 原因 | 解法狀態 |
|---|------|------|----------|
| 1 | `StopSeq` 在 CSV 全為 NaN | `build_research_dataset()` 裡時刻表 join 需 TrainNo 型別一致（str vs int），雖有 join 但寫入前被截斷 | ⏳ 已修改 processor.py，待下次 Actions 驗證 |
| 2 | `IsTerminal` 全為 0 | 舊邏輯用 CrawlTime 末筆判定，已改為時刻表 EndingStationID 比對 | ⏳ 待 Actions 驗證 |
| 3 | `StationGrade`（X6）全為 NaN | Station API join 欄位名稱對不上（`StationClass` vs `StationGrade`），需確認 | 🔍 未修正 |

### 🟡 中優先

| # | 問題 | 說明 |
|---|------|------|
| 4 | `train_schedule.csv` 尚未產生 | export_csv.py 已加入，等 Actions 跑後才會出現在 repo |
| 5 | `station_structure.csv` 未填寫 | X7（SideTrackCount）、X8（IsDouble）需手動填入 237 站資料 |
| 6 | Streamlit 雲端版「系統設定」頁顯示目錄不存在 | 雲端無本機 data/ 目錄，需在雲端模式下改顯示提示而非報錯 |

### 🟢 低優先

| # | 問題 | 說明 |
|---|------|------|
| 7 | 本機 launchd 排程停擺 | `~/tra_crawler_runner/` 目錄不存在。目前雲端 Actions 已足夠，可暫時不處理 |
| 8 | `live_board.py` 舊爬蟲並存 | 與 `station_live.py` 邏輯重疊，應逐步移除 |

---

## 儀表板頁面狀態

| 頁面 | 狀態 | 功能 |
|------|------|------|
| ⬡ 首頁 | ✅ | 研究說明、系統狀態 |
| ◈ 資料總覽 | ✅ | KPI、車種/時段/假日圖表、逐日趨勢 |
| ◎ 準點率分析 | ✅ | 台鐵官方口徑 vs 本研究全站口徑、首末班查詢 |
| ◉ 車站熱力圖 | ✅ | 密度熱力圖 / 氣泡誤點圖 / 車站位置 |
| ≋ OLS 迴歸 | ✅ | OLS + Logit，係數圖 + statsmodels summary |
| ⚠ 異常通報 | ✅ | Alert 資料列表 |
| ⚙ 系統設定 | ⚠️ | 雲端模式下「目錄狀況」顯示錯誤（已知問題 #6） |

---

## 近期開發歷程

| 日期 | Commit | 說明 |
|------|--------|------|
| 2026-03-03 | `8f2ef8a` | feat: 官方準點率 + 首末班查詢 + 統一準點率名詞 |
| 2026-03-03 | `bff0527` | feat: 日期篩選器 + 各頁圖表說明（expander） |
| 2026-03-03 | `c18978b` | fix: 地圖分頁 KeyError（StationName merge 缺失） |
| 2026-03-03 | `785e644` | fix: 熱力圖改用 Plotly API，移除 Mapbox token 依賴 |
| 2026-03-03 | `0002ec9` | Initial plan（專案初始化） |

---

## 下一步待辦

- [ ] 確認 Actions 重跑後 `IsTerminal`、`StopSeq`、`FirstDep`、`LastArr` 是否正確出現在 CSV
- [ ] 修正 `StationGrade`（X6）的 join 欄位名稱問題
- [ ] 填寫 `station_structure.csv`（X7 側線數、X8 單複線）
- [ ] 修正「系統設定」頁雲端模式顯示問題
- [ ] 累積足夠資料後（建議 >5,000 筆）正式執行迴歸分析並撰寫期末報告
