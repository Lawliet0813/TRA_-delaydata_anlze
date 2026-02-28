import requests
import json
import os
from datetime import datetime
from config import BASE_URL, DATA_DIR
from auth import auth_header

def fetch_daily_timetable():
    url = f"{BASE_URL}/DailyTrainTimetable/Today"
    params = {"$format": "JSON"}
    resp = requests.get(url, headers=auth_header(), params=params)
    resp.raise_for_status()
    return resp.json()

def save_timetable(data):
    now = datetime.now()
    date_dir = os.path.join(DATA_DIR, "timetable")
    os.makedirs(date_dir, exist_ok=True)
    filename = os.path.join(date_dir, f"{now.strftime('%Y-%m-%d')}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return filename

def crawl_timetable():
    try:
        data = fetch_daily_timetable()
        path = save_timetable(data)
        print(f"[{datetime.now()}] Timetable saved: {path}")
    except Exception as e:
        print(f"[{datetime.now()}] Timetable ERROR: {e}")