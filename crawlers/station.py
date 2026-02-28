import requests
import json
import os
from datetime import datetime
from config import BASE_URL, DATA_DIR
from auth import auth_header

def fetch_stations():
    url = f"{BASE_URL}/Station"
    params = {"$format": "JSON"}
    resp = requests.get(url, headers=auth_header(), params=params)
    resp.raise_for_status()
    return resp.json()

def save_stations(data):
    date_dir = os.path.join(DATA_DIR, "static")
    os.makedirs(date_dir, exist_ok=True)
    filename = os.path.join(date_dir, "stations.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return filename

def crawl_stations():
    try:
        data = fetch_stations()
        path = save_stations(data)
        print(f"[{datetime.now()}] Stations saved: {path}")
    except Exception as e:
        print(f"[{datetime.now()}] Stations ERROR: {e}")

if __name__ == "__main__":
    crawl_stations()
