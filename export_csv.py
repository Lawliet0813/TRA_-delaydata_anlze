"""
GitHub Actions 呼叫的匯出腳本。
產生 data/processed_data.csv 和 data/research_dataset.csv 供 Streamlit Cloud 讀取。
"""
import os
import pandas as pd
from processor import DataProcessor

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

dp = DataProcessor(DATA_DIR)

# research_dataset（完整自變數版）
df = dp.build_research_dataset()
if not df.empty:
    out = os.path.join(DATA_DIR, "research_dataset.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"research_dataset.csv 匯出完成（{len(df)} 筆）")

    # processed_data（Streamlit Cloud 主要讀取來源）
    out2 = os.path.join(DATA_DIR, "processed_data.csv")
    df.to_csv(out2, index=False, encoding="utf-8-sig")
    print(f"processed_data.csv 匯出完成（{len(df)} 筆）")
else:
    print("無資料可匯出")
