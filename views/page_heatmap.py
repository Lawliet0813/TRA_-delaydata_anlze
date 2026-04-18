"""
車站熱力圖 — 春節誤點的空間分布
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from views.theme import (
    PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED, TEXT_SECONDARY,
)
from views.components import kpi_card, note_card, section_title


MAP_CENTER = {"lat": 23.8, "lon": 121.0}
MAP_ZOOM = 6.5
MAP_STYLE = "carto-darkmatter"
COLOR_SCALE = [GREEN, YELLOW, RED]


def _station_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["StationID", "StationNameZh_tw"], observed=True)
        .agg(
            平均延誤=("延誤分鐘", "mean"),
            觀測數=("延誤分鐘", "size"),
            超過5分比例=("延誤分鐘", lambda s: (s > 5).mean()),
        )
        .reset_index()
    )


def _attach_coords(df: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    if coords is None or coords.empty:
        return df
    tmp = df.copy()
    tmp["StationID"] = tmp["StationID"].astype(str).str.strip().str.zfill(4)
    c = coords.copy()
    c["StationID"] = c["StationID"].astype(str).str.strip().str.zfill(4)
    return tmp.merge(c[["StationID", "Lat", "Lon"]], on="StationID", how="left")


def render(ctx: dict) -> None:
    perceived = ctx["perceived"]
    coords = ctx["stations_coords"]

    if perceived is None or perceived.empty:
        st.info("目前篩選條件下沒有資料。")
        return

    summary = _station_summary(perceived)
    summary = _attach_coords(summary, coords)

    section_title("車站熱力圖（點大小＝觀測數 / 顏色＝平均誤點）")

    with_coords = summary.dropna(subset=["Lat", "Lon"]).copy() if "Lat" in summary.columns else pd.DataFrame()
    without_coords = summary[summary["Lat"].isna()] if "Lat" in summary.columns else pd.DataFrame()

    if with_coords.empty:
        st.warning("站點座標檔（stations_coords.csv）遺失或未匹配，改以條形圖展示。")
    else:
        fig = px.scatter_mapbox(
            with_coords,
            lat="Lat",
            lon="Lon",
            size="觀測數",
            color="平均延誤",
            color_continuous_scale=COLOR_SCALE,
            hover_name="StationNameZh_tw",
            hover_data={
                "StationID": True,
                "平均延誤": ":.2f",
                "觀測數": ":,",
                "超過5分比例": ":.2%",
                "Lat": False,
                "Lon": False,
            },
            size_max=28,
            zoom=MAP_ZOOM,
            center=MAP_CENTER,
            mapbox_style=MAP_STYLE,
            height=640,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="平均分鐘"),
        )
        st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(3)
    with cols[0]:
        kpi_card("涵蓋站數", f"{len(summary):,}")
    with cols[1]:
        peak = summary.loc[summary["平均延誤"].idxmax()]
        kpi_card(
            "最惡車站",
            str(peak["StationNameZh_tw"]),
            color="red",
            sub=f"{peak['平均延誤']:.2f} 分鐘 · {int(peak['觀測數']):,} 筆",
        )
    with cols[2]:
        busy = summary.loc[summary["觀測數"].idxmax()]
        kpi_card(
            "觀測最密站",
            str(busy["StationNameZh_tw"]),
            color="blue",
            sub=f"{int(busy['觀測數']):,} 筆",
        )

    section_title("最惡 20 站排行")
    top = summary.sort_values("平均延誤", ascending=False).head(20).reset_index(drop=True)
    fig2 = px.bar(
        top,
        x="平均延誤",
        y="StationNameZh_tw",
        color="平均延誤",
        color_continuous_scale=COLOR_SCALE,
        text="平均延誤",
        orientation="h",
    )
    fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig2.update_layout(
        **PLOTLY_THEME, height=600, yaxis_title="", xaxis_title="平均誤點（分鐘）",
        showlegend=False,
    )
    fig2.update_xaxes(**AXIS_STYLE)
    fig2.update_yaxes(**AXIS_STYLE, categoryorder="total ascending")
    st.plotly_chart(fig2, use_container_width=True)

    section_title("全部車站明細")
    display = summary[[
        "StationID", "StationNameZh_tw", "觀測數", "平均延誤", "超過5分比例",
    ]].copy()
    display.columns = ["站碼", "站名", "觀測數", "平均誤點(分)", "超過 5 分比例"]
    display = display.sort_values("平均誤點(分)", ascending=False)
    st.dataframe(
        display.style.format(
            {"觀測數": "{:,}", "平均誤點(分)": "{:.2f}", "超過 5 分比例": "{:.2%}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    if not without_coords.empty:
        note_card(
            f"未匹配座標 {len(without_coords)} 站",
            "地圖未顯示這些站點；可能因 stations_coords.csv 尚未涵蓋支線站或新站碼。"
            "已列入下方明細表與排行榜。",
        )
