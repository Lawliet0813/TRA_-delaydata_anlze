import time
import requests
from config import CLIENT_ID, CLIENT_SECRET

_token_cache = {"token": None, "expires_at": 0}

def get_token():
    """取得 Access Token，自動快取與重新取得"""
    now = time.time()
    # 提前 60 秒刷新 token
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("尚未設定 TDX_CLIENT_ID 或 TDX_CLIENT_SECRET，請檢查 .env 檔案。")

    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    resp = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
    
    if resp.status_code != 200:
        raise RuntimeError(f"取得 Token 失敗: {resp.status_code} - {resp.text}")
        
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 86400)
    return _token_cache["token"]

def auth_header():
    return {"Authorization": f"Bearer {get_token()}"}