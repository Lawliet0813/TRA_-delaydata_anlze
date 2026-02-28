import requests
import json
import os
from datetime import datetime
from config import BASE_URL, DATA_DIR
from auth import auth_header

def fetch_alerts():
    url = f"{BASE_URL}/Alert"
    params = {"$format": "JSON"}
    resp = requests.get(url, headers=auth_header(), params=params)
    resp.raise_for_status()
    return resp.json()

def save_alerts(data):
    now = datetime.now()
    date_dir = os.path.join(DATA_DIR, "alerts", now.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    filename = os.path.join(date_dir, f"{now.strftime('%H%M%S')}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return filename

def crawl_alerts():
    try:
        data = fetch_alerts()
        path = save_alerts(data)
        print(f"[{datetime.now()}] Alerts saved: {path}")
    except Exception as e:
        print(f"[{datetime.now()}] Alerts ERROR: {e}")