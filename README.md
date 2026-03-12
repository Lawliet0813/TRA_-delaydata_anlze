# 台鐵列車誤點影響因素之量化分析

Taiwan Railways Delay Analysis · 研究指揮中心

國立政治大學 MEPA 期末報告，社會科學研究方法（一）：量化研究方法

## 研究概述

以 TDX 即時動態 API 自行蒐集全台臺鐵誤點資料，結合時刻表結構特徵，
透過 OLS 線性迴歸模型探討影響誤點分鐘數的結構性因素。

## 專案架構

```
tra_delay_crawler/
├── app.py              # Streamlit 儀表板（研究指揮中心，支援雲端模式）
├── main.py             # CLI 入口（python main.py live/alert/timetable）
├── processor.py        # 資料處理與特徵工程
├── export_csv.py       # 匯出 processed_data.csv（GitHub Actions 使用）
├── config.py           # 路徑與設定
├── auth.py             # TDX OAuth2 Token
├── crawlers/
│   ├── base.py          # BaseCrawler 基底類別
│   ├── station_live.py  # StationLiveBoard（核心爬蟲）
│   ├── timetable.py     # 時刻表抓取
│   ├── station.py       # 車站靜態資料
│   └── alert.py         # 異常通報
├── data/
│   ├── static/
│   │   └── station_structure.csv  # 場站結構靜態變數（X7, X8）
│   └── processed_data.csv         # 處理後資料（供 Streamlit 雲端版讀取）
└── .github/workflows/crawler.yml  # GitHub Actions 自動爬蟲排程
```

## 資料蒐集排程（GitHub Actions）

| 任務 | 頻率 |
|------|------|
| StationLiveBoard | 每 10 分鐘（台灣時間 06–24 時） |
| Alert | 每 60 分鐘 |
| Timetable + Station | 每日 06:00 |

## 主要自變數

| 編號 | 變數 | 說明 |
|------|------|------|
| X1 | TrainType | 車種（自強/區間/莒光等） |
| X2 | StopSeq | 停靠順序 |
| X3 | Period | 時段（尖峰/離峰/深夜） |
| X4 | IsHoliday | 假日旗標 |
| X5 | MixIndex | 同站同小時車種混合度 |
| X5b | SpeedDiff | 速差指標 |
| X6 | StationClass | 站等級（特等～招呼） |
| X7 | SideTrackCount | 側線數（手動填寫） |
| X8 | IsDouble | 單複線別 |
| X9 | PrevDelay | 前站誤點（累積效應） |
| X10 | Direction | 行駛方向（順/逆） |
| X11 | TripLine | 路線別（山線/海線） |

## 依變數

- **Y1 `IsDelayed`**：DelayTime ≥ 2 分鐘 → 1（binary logistic）
- **Y2 `DelayTime`**：實際誤點分鐘數（OLS）

## 安裝與執行

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 TDX 金鑰
streamlit run app.py
```

## 本機自動推送

本儲存庫內建本機 `launchd` 腳本，可自動抓取資料，並將雲端儀表板讀取的 CSV 推送至 GitHub：

```bash
zsh scripts/install_launchd.sh
```

安裝後會建立三個排程：

- `com.lawliet.tra.live`：每 10 分鐘抓 `StationLiveBoard`
- `com.lawliet.tra.alert`：每小時整點執行 `export_csv.py`，並自動 push `data/*.csv`
- `com.lawliet.tra.timetable`：每日 06:05 抓時刻表，並自動 push `data/timetable/daily_YYYY-MM-DD.json`

自動 push 會使用獨立 clone `~/tra_git_push`，避免把你工作中的程式碼修改一併提交。

## 線上展示

[Streamlit 雲端版](https://tra-delaydataanlze-cwvejankcpdrlhgtsdsjbf.streamlit.app/)
