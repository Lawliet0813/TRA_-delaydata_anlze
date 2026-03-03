# 📚 引用資料索引

本專案資料來源與 API 文件整理如下：

---

## 一、主要資料來源 API

### 1. TDX 運輸資料流通服務平臺（臺鐵 TRA API v3）

| 項目 | 說明 |
|------|------|
| **平台名稱** | Transport Data eXchange (TDX) 運輸資料流通服務 |
| **API 版本** | v3 |
| **涵蓋範圍** | 臺灣鐵路（TRA）車站、路網、時刻表、列車動態等 |
| **Swagger 文件** | https://tdx.transportdata.tw/webapi/File/Swagger/V3/5fa88b0c-120b-43f1-b188-c379ddb2593d |
| **線上 API 測試介面** | https://tdx.transportdata.tw/api-service/swagger/basic/5fa88b0c-120b-43f1-b188-c379ddb2593d |
| **資料格式** | JSON / XML |
| **授權方式** | OAuth 2.0（Client Credentials Flow） |

---

## 二、本專案引用之主要 API 端點

| 端點路徑 | 說明 |
|----------|------|
| `GET /v3/Rail/TRA/Network` | 取得臺鐵路網資料 |
| `GET /v3/Rail/TRA/Station` | 取得臺鐵各車站基本資料 |
| `GET /v3/Rail/TRA/GeneralTrainTimetable` | 取得全台鐵定期時刻表 |
| `GET /v3/Rail/TRA/DailyTrainTimetable/OD/{OriginStationID}/to/{DestinationStationID}/{TrainDate}` | 查詢特定站間指定日期時刻表 |
| `GET /v3/Rail/TRA/TrainLiveBoard` | 取得列車即時動態（含誤點資訊） |
| `GET /v3/Rail/TRA/StationLiveBoard/{StationID}` | 取得特定車站即時進出站動態 |

---

## 三、常用查詢參數說明

| 參數 | 說明 |
|------|------|
| `$select` | 指定回傳欄位 |
| `$filter` | OData 條件過濾 |
| `$orderby` | 排序欄位 |
| `$top` / `$skip` | 分頁控制 |
| `$count` | 回傳資料總筆數 |
| `$format` | 回傳格式（`JSON` 或 `XML`） |

---

## 四、認證方式

使用 OAuth 2.0 Client Credentials Flow 取得 Access Token：

```
POST https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
```

取得 Token 後，於每次 API 請求加上 Header：
```
Authorization: Bearer {access_token}
```

---

## 五、相關參考資源

| 資源名稱 | 連結 |
|----------|------|
| TDX 官方 Swagger 文件（臺鐵） | https://tdx.transportdata.tw/webapi/File/Swagger/V3/5fa88b0c-120b-43f1-b188-c379ddb2593d |
| TDX 線上 API 說明頁面 | https://tdx.transportdata.tw/api-service/swagger |
| TDX 官方範例程式碼（GitHub） | https://github.com/tdxmotc/SampleCode |
| 政府資料開放平臺－臺鐵時刻表 | https://data.gov.tw/dataset/161155 |
| TDX API 介接教學（HackMD） | https://hackmd.io/@hexschool/H1VfZLW4F |
| TDX 運輸資料介接指南（GitHub Pages） | https://chiajung-yeh.github.io/TDX_Guide/ |
| TDX API Python 教學範例 | https://github.com/ycpranchu/tdx-api-tutorial |
