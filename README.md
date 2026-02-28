# 台鐵列車誤點影響因素之量化分析

Taiwan Railways Delay Analysis · 研究指指揮中心

國立政治大學 MEPA 程度期末報告，社會科學研究方法（一）：量化研究方法

## 研究概述

以 TDX 即時動態 API 自行蓄集全台臺鐵誤點資料，結合時刻表結構特徵，
順過 OLS 線性迨歸模型探討影響誤點分鐘數的結構性因素。

## 專案結構

```
tra_delay_crawler/
├── app.py              # Streamlit 儀表板（研究指揮中心）
├── main.py             # 排程入口（launchd 呼叫）
├── processor.py        # 資料處理與特徵工程
├── config.py           # 路徑與設定
├── auth.py             # TDX OAuth2 Token
├── crawlers/
│   ├── live_board.py    # 即時指動態抓取
│   ├── timetable.py     # 時刻表抓取
│   ├── station.py       # 車站資料抓取
│   └── alert.py         # 異常通報抓取
└── data/
    └── static/
        └── station_structure.csv  # 場站結構靜態變數
```

## 資料源

- [TDX 交通資料整合平台](https://tdx.transportdata.tw/) - 臺鐵即時動態 API
- 處理層：客成相資料、時刻表特徵、場站結構變數

## 主要自變數

| 編號 | 變數 | 說明 |
|------|------|------|
| X₂ | TrainType | 車種 |
| X₃ | Period | 時段（尖峰/離峰/深夜） |
| X₄ | Weekday | 星期 |
| X₅ | Month | 月份 |
| X₆ | StationGrade | 站等級 |
| X₇ | SideTrackCount | 側線數 |
| X₈ | IsDouble | 單複線 |
| X₉ | MixIndex | 車種混合度 |
| X₁₀ | SpeedDiff | 速差指標 |
| - | PrevDelay | 前站誤點（累積效應） |

## 安裝與執行

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 TDX 金鑰
streamlit run app.py
```

## 作者

張彥儒（NCCU MEPA，2025-2026）
