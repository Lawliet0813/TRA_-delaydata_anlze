"""
原始資料預覽 — 以年份切換 cny_XXXX.csv；雲端部署時自動 fallback 到 clean.parquet
"""
import streamlit as st

from views.components import kpi_card, note_card, section_title


def render(ctx: dict) -> None:
    store = ctx["store"]

    section_title("選擇年份")
    year = st.selectbox("年份", [2022, 2023, 2024, 2025, 2026], index=3)

    use_raw = store.has_raw_csv(year)
    with st.spinner(("載入 cny_%d.csv ..." % year) if use_raw else "載入已清理資料（雲端模式）..."):
        if use_raw:
            df = store.load_raw_year(year)
            delay_col = "DelayTime"
            train_col = "TrainNo"
            station_col = "StationID"
        else:
            df = store.load_year_from_clean(year)
            delay_col = "延誤分鐘"
            train_col = "TrainNo"
            station_col = "StationID"

    cols = st.columns(4)
    with cols[0]:
        kpi_card("總筆數", f"{len(df):,}")
    with cols[1]:
        kpi_card("獨立車次", f"{df[train_col].nunique():,}")
    with cols[2]:
        kpi_card("獨立車站", f"{df[station_col].nunique():,}")
    with cols[3]:
        kpi_card("平均誤點", f"{df[delay_col].mean():.2f} 分")

    section_title("前 500 列預覽")
    st.dataframe(df.head(500), use_container_width=True, hide_index=True)

    if use_raw:
        note_card(
            "欄位說明",
            "TrainNo 車次 · StationID 車站代碼 · StationNameZh_tw 站名 · DelayTime 延誤分鐘 · "
            "SrcUpdateTime 觀測時戳 · UpdateTime 我方擷取時戳（Asia/Taipei）。"
            "原始資料可能對同車次同站有多筆快照，清理階段以 SrcUpdateTime 最晚者為準。",
        )
    else:
        note_card(
            "雲端部署模式",
            "為控制 repo 體積，原始 CSV 未納入版控。本頁顯示的是已完成去重清理的版本（clean.parquet），"
            "欄位已包含春節節點、車種、路線區段等衍生變項，可直接供後續分析使用。",
        )
