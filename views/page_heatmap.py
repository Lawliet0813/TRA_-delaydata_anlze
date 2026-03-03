"""
站點熱力圖 (Heatmap) — Full-bleed Map + Stats Panel
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from views.theme import PLOTLY_THEME, AXIS_STYLE, COLORS, BLUE, GREEN, TEXT_SECONDARY, TEXT_MUTED, BORDER
from views.components import page_header, kpi_card, section_title


MAP_CENTER  = {"lat": 23.8, "lon": 121.0}
MAP_ZOOM    = 6.5
MAP_STYLE   = "carto-darkmatter"
COLOR_SCALE = [GREEN, "#f59e0b", "#ef4444"]   # 綠→黃→紅
LINE_COLORS = {
    "WestTrunkLine":  BLUE,
    "SeaLine":        "#f59e0b",
    "EastTrunkLine":  GREEN,
    "NorthLink":      "#ef4444",
    "SouthLink":      "#a78bfa",
    "PingTungLine":   "#22d3ee",
    "TaiDongLine":    "#56d364",
}


def render(df, filtered_df, date_label, processor=None, **kwargs):
    page_header("◉", "站點熱力圖", "全台車站誤點空間分布 · GIS Visualization")
    st.caption(f"目前顯示範圍：{date_label}")

    with st.expander("📊 地圖模式說明"):
        st.markdown("""
        | 模式 | 說明 | 適合用途 |
        |------|------|----------|
        | **🔥 密度熱力圖** | 以 `DelayTime` 為權重的地理密度 | 找出誤點熱點區域 |
        | **🔵 氣泡誤點圖** | 各站聚合成氣泡 | 比較各站誤點差異 |
        | **📍 車站位置** | 純地理分布 | 確認資料涵蓋範圍 |
        """)

    _work_df = filtered_df.copy() if not filtered_df.empty else pd.DataFrame()

    # 合併座標
    if not _work_df.empty and processor:
        _stations_coords = processor.get_stations_data()
        if not _stations_coords.empty:
            _work_df["StationID"] = _work_df["StationID"].astype(str).str.strip().str.zfill(4)
            _stations_coords = _stations_coords.copy()
            _stations_coords["StationID"] = _stations_coords["StationID"].astype(str).str.strip().str.zfill(4)
            _drop = [c for c in ["StationName", "Lat", "Lon"] if c not in _work_df.columns or _work_df[c].isna().all()]
            _work_df = _work_df.drop(columns=_drop, errors="ignore")
            _coords_cols = ["StationID"] + [c for c in ["StationName", "Lat", "Lon"] if c in _stations_coords.columns]
            _work_df = _work_df.merge(_stations_coords[_coords_cols], on="StationID", how="left")

    if _work_df.empty or "Lat" not in _work_df.columns or _work_df["Lat"].isna().all():
        st.warning("座標資料載入失敗，無法顯示地圖。")
        return

    # ── Filters ───────────────────────────────────────────────
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 2])

    with f_col1:
        all_types = sorted(_work_df["TrainType"].dropna().unique().tolist())
        sel_types = st.multiselect("車種", all_types, default=all_types, key="map_types")

    with f_col2:
        if "Period" in _work_df.columns:
            all_periods = sorted(_work_df["Period"].dropna().unique().tolist())
            sel_periods = st.multiselect("時段", all_periods, default=all_periods, key="map_periods")
        else:
            sel_periods = None

    with f_col3:
        map_mode = st.radio("地圖模式", ["🔥 密度熱力圖", "🔵 氣泡誤點圖", "📍 車站位置"],
                            index=0, key="map_mode", horizontal=True)

    with f_col4:
        view_metric = st.radio("顯示指標", ["平均誤點（分）", "誤點率（%）"],
                               index=0, key="map_metric", horizontal=True)

    # ── Apply Filters ─────────────────────────────────────────
    map_df = _work_df.dropna(subset=["Lat", "Lon"]).copy()
    if sel_types:
        map_df = map_df[map_df["TrainType"].isin(sel_types)]
    if sel_periods and "Period" in map_df.columns:
        map_df = map_df[map_df["Period"].isin(sel_periods)]

    if map_df.empty:
        st.warning("篩選後無資料，請調整篩選條件。")
        return

    # ── Aggregate by station ──────────────────────────────────
    map_df = map_df.dropna(subset=["StationName"])
    if map_df.empty:
        st.warning("篩選後無有效車站名稱資料。")
        return

    station_map = (
        map_df.groupby(["StationName", "Lat", "Lon"])
        .agg(平均誤點=("DelayTime", "mean"), 筆數=("DelayTime", "count"), 誤點率=("IsDelayed", "mean"))
        .reset_index()
    )
    station_map["平均誤點"] = station_map["平均誤點"].round(2)
    station_map["誤點率_pct"] = (station_map["誤點率"] * 100).round(1)

    color_col = "平均誤點" if "平均誤點" in view_metric else "誤點率_pct"
    hover_label = "平均誤點（分）" if "平均誤點" in view_metric else "誤點率（%）"

    # ── Map rendering ─────────────────────────────────────────
    if map_mode == "🔥 密度熱力圖":
        fig = px.density_map(
            map_df, lat="Lat", lon="Lon", z="DelayTime",
            radius=28, center=MAP_CENTER, zoom=MAP_ZOOM,
            map_style=MAP_STYLE, color_continuous_scale=COLOR_SCALE,
            range_color=[0, map_df["DelayTime"].quantile(0.95)],
            labels={"z": "誤點分鐘"},
        )
        fig.add_trace(go.Scattermap(
            lat=station_map["Lat"], lon=station_map["Lon"],
            mode="markers+text",
            marker=dict(size=5, color="rgba(240,246,252,0.4)"),
            text=station_map["StationName"],
            textfont=dict(size=9, color="rgba(240,246,252,0.5)"),
            textposition="top right",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "平均誤點：%{customdata[0]} 分<br>"
                "誤點率：%{customdata[1]}%<br>"
                "觀測筆數：%{customdata[2]}<extra></extra>"
            ),
            customdata=station_map[["平均誤點", "誤點率_pct", "筆數"]].values,
            showlegend=False,
        ))

    elif map_mode == "🔵 氣泡誤點圖":
        fig = px.scatter_map(
            station_map, lat="Lat", lon="Lon",
            hover_name="StationName", color=color_col, size=color_col,
            size_max=22, color_continuous_scale=COLOR_SCALE,
            zoom=MAP_ZOOM, center=MAP_CENTER, map_style=MAP_STYLE,
            labels={color_col: hover_label},
            custom_data=["StationName", "平均誤點", "誤點率_pct", "筆數"],
        )
        fig.update_traces(hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "平均誤點：%{customdata[1]} 分<br>"
            "誤點率：%{customdata[2]}%<br>"
            "觀測筆數：%{customdata[3]}<extra></extra>"
        ))

    else:  # 📍 車站位置
        fig = go.Figure()
        fig.add_trace(go.Scattermap(
            lat=station_map["Lat"], lon=station_map["Lon"],
            mode="markers+text",
            marker=dict(
                size=10, color=station_map[color_col],
                colorscale=COLOR_SCALE,
                colorbar=dict(
                    title=dict(text=hover_label, font=dict(color=TEXT_SECONDARY)),
                    tickfont=dict(color=TEXT_SECONDARY),
                    bgcolor="rgba(0,0,0,0)",
                ),
                showscale=True,
            ),
            text=station_map["StationName"],
            textfont=dict(size=9, color="#f0f6fc"),
            textposition="top right",
            hovertemplate=(
                "<b>%{text}</b><br>"
                f"{hover_label}：%{{customdata[0]}}<br>"
                "觀測筆數：%{customdata[1]}<extra></extra>"
            ),
            customdata=station_map[[color_col, "筆數"]].values,
        ))
        fig.update_layout(map=dict(style=MAP_STYLE, center=MAP_CENTER, zoom=MAP_ZOOM))

    # Layout
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        font=dict(color=TEXT_SECONDARY, family="Inter, Noto Sans TC"),
        coloraxis_colorbar=dict(
            title=dict(text=hover_label, font=dict(color=TEXT_SECONDARY)),
            tickfont=dict(color=TEXT_SECONDARY),
        ),
    )

    # ── Rail lines ────────────────────────────────────────────
    if processor:
        shapes = processor.get_shape()
        if shapes:
            for line_id, shape_data in shapes.items():
                color_key = line_id.replace("TRA_", "")
                line_color = LINE_COLORS.get(color_key, "#484f58")
                fig.add_trace(go.Scattermap(
                    lon=shape_data["lons"], lat=shape_data["lats"],
                    mode="lines",
                    line=dict(width=2.5, color=line_color),
                    name=shape_data["name"], hoverinfo="name", showlegend=True,
                ))

    st.plotly_chart(fig, use_container_width=True)

    # ── Stats Panel ───────────────────────────────────────────
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        kpi_card("車站總數", f"{len(station_map)} 站", "blue")
    with m2:
        kpi_card("觀測筆數", f"{int(station_map['筆數'].sum()):,}")
    with m3:
        kpi_card("全體平均誤點", f"{station_map['平均誤點'].mean():.2f} 分", "yellow")
    with m4:
        kpi_card("全體誤點率", f"{(map_df['IsDelayed'].mean()*100):.1f}%",
                 "green" if map_df['IsDelayed'].mean() < 0.15 else "yellow")

    # ── Top 10 ────────────────────────────────────────────────
    st.markdown("---")
    section_title("🔴 誤點前 10 名車站")
    top10 = (
        station_map.nlargest(10, "平均誤點")
        [["StationName", "平均誤點", "誤點率_pct", "筆數"]]
        .reset_index(drop=True)
    )
    top10.index = top10.index + 1
    top10.columns = ["車站", "平均誤點（分）", "誤點率（%）", "觀測筆數"]

    col_tbl, col_bar = st.columns([1, 1], gap="large")
    with col_tbl:
        st.dataframe(
            top10.style
            .background_gradient(cmap="RdYlGn_r", subset=["平均誤點（分）", "誤點率（%）"])
            .format({"平均誤點（分）": "{:.2f}", "誤點率（%）": "{:.1f}%", "觀測筆數": "{:,}"}),
            use_container_width=True,
        )

    with col_bar:
        fig_bar = go.Figure(go.Bar(
            x=top10["平均誤點（分）"], y=top10["車站"],
            orientation="h",
            marker=dict(color=top10["平均誤點（分）"], colorscale=COLOR_SCALE, showscale=False, line=dict(width=0)),
            text=top10["平均誤點（分）"].apply(lambda v: f"{v:.2f} 分"),
            textposition="outside", textfont=dict(size=11, color=TEXT_SECONDARY),
        ))
        fig_bar.update_layout(**PLOTLY_THEME, height=360,
                              yaxis=dict(**AXIS_STYLE, autorange="reversed"),
                              xaxis=dict(**AXIS_STYLE, title="平均誤點（分）"))
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Distribution ──────────────────────────────────────────
    st.markdown("---")
    section_title("📊 各車站平均誤點分布")
    fig_hist = go.Figure(go.Histogram(
        x=station_map["平均誤點"], nbinsx=25,
        marker=dict(color=BLUE, line=dict(width=0)), opacity=0.85,
    ))
    fig_hist.update_layout(**PLOTLY_THEME, height=220,
                           xaxis=dict(**AXIS_STYLE, title="平均誤點（分）"),
                           yaxis=dict(**AXIS_STYLE, title="車站數"))
    st.plotly_chart(fig_hist, use_container_width=True)
