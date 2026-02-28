import os
from dotenv import load_dotenv

# 取得專案根目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 載入 .env 檔案中的環境變數
load_dotenv(os.path.join(BASE_DIR, ".env"))

# TDX API 設定
CLIENT_ID = os.getenv("TDX_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("TDX_CLIENT_SECRET", "")
BASE_URL = "https://tdx.transportdata.tw/api/basic/v3/Rail/TRA"

# 資料儲存路徑
DATA_DIR = os.path.join(BASE_DIR, "data")
