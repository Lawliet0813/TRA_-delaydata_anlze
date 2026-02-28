import requests
import json
import os
from datetime import datetime
from config import BASE_URL, DATA_DIR
from auth import auth_header

def fetch_train_live_board():
    """抓取全線列車即時到離站資料"""
    url = f"{BASE_URL}/TrainLiveBoard"
    params = {"$format": "JSON"}
    resp = requests.get(url, headers=auth_header(), params=params)
    resp.raise_for_status()
    return resp.json()

def save_live_board(data):
    """以時間戳存檔"""
    now = datetime.now()
    date_dir = os.path.join(DATA_DIR, "live_board", now.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    filename = os.path.join(date_dir, f"{now.strftime('%H%M%S')}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return filename

def crawl_live_board():
    """爬取 + 儲存"""
    try:
        data = fetch_train_live_board()
        path = save_live_board(data)
        print(f"[{datetime.now()}] LiveBoard saved: {path} ({len(data.get('TrainLiveBoards', []))} records)")
    except Exception as e:
        print(f"[{datetime.now()}] LiveBoard ERROR: {e}")