"""
車站熱力圖 — 空間風險分析頁
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from views.theme import (
    PLOTLY_THEME,
    AXIS_STYLE,
    BLUE,
    GREEN,
    YELLOW,
    RED,
    TEXT_SECONDARY,
)
from views.components import kpi_card, note_card, page_header, section_title, story_card


MAP_CENTER = {"lat": 23.8, "lon": 121.0}
MAP_ZOOM = 6.5
MAP_STYLE = "carto-darkmatter"
COLOR_SCALE = [GREEN, YELLOW, RED]
LINE_COLORS = {
    "WL": BLUE,
    "WL-C": YELLOW,
    "WL-M": "#eab308",
    "TL": BLUE,
    "TL-C": YELLOW,
    "TL-M": "#eab308",
    "TL-N": "#60a5fa",
    "TL-S": "#3b82f6",
    "EL": GREEN,
    "YL": "#34d399",
    "NL": RED,
    "PL": "#22d3ee",
    "TT": "#56d364",
    "SL": "#a78bfa",
    "CZ": "#94a3b8",
    "JJ": "#fb7185",
    "LJ": "#c084fc",
    "NW": "#f97316",
    "PX": "#f43f5e",
    "SA": "#06b6d4",
}
BG_COLOR = "#07111a"


def _attach_station_coords(work_df: pd.DataFrame, processor) -> pd.DataFrame:
    if work_df.empty or processor is None:
        return work_df
    stations = processor.get_stations_data()
    if stations is None or stations.empty:
        return work_df

    enriched = work_df.copy()
    enriched["StationID"] = enriched["StationID"].astype(str).str.strip().str.zfill(4)
    stations = stations.copy()
    stations["StationID"] = stations["StationID"].astype(str).str.strip().str.zfill(4)
    for col in ["StationName", "Lat", "Lon"]:
        if col not in enriched.columns:
            enriched[col] = pd.NA
    lookup_cols = ["StationID"] + [c for c in ["StationName", "Lat", "Lon"] if c in stations.columns]
    lookup = stations[lookup_cols].drop_duplicates(subset=["StationID"])
    enriched = enriched.merge(lookup, on="StationID", how="left", suffixes=("", "_coord"))
    for col in ["StationName", "Lat", "Lon"]:
        coord_col = f"{col}_coord"
        if coord_col in enriched.columns:
            enriched[col] = enriched[col].fillna(enriched[coord_col])
            enriched = enriched.drop(columns=[coord_col])
    for col in ["Lat", "Lon"]:
        enriched[col] = pd.to_numeric(enriched[col], errors="coerce")
    return enriched


def _aggregate_station_metrics(map_df: pd.DataFrame) -> pd.DataFrame:
    station_map = (
        map_df.groupby(["StationID", "StationName", "Lat", "Lon"], dropna=False)
        .agg(
            平均誤點=("DelayTime", "mean"),
            觀測筆數=("DelayTime", "count"),
            誤點率=("IsDelayed", "mean"),
            最大誤點=("DelayTime", "max"),
        )
        .reset_index()
    )
    station_map["平均誤點"] = station_map["平均誤點"].round(2)
    station_map["誤點率_pct"] = (station_map["誤點率"] * 100).round(1)
    station_map["最大誤點"] = station_map["最大誤點"].round(0).astype(int)
    station_map["風險指數"] = (
        station_map["平均誤點"] * 0.65
        + station_map["誤點率_pct"] * 0.35 / 10
    ).round(2)
    return station_map.sort_values("風險指數", ascending=False)


def _metric_spec(metric_name: str) -> tuple[str, str]:
    if metric_name == "誤點率（%）":
        return "誤點率_pct", "誤點率（%）"
    if metric_name == "最大誤點（分）":
        return "最大誤點", "最大誤點（分）"
    return "平均誤點", "平均誤點（分）"


def _add_rail_lines(fig: go.Figure, processor) -> None:
    if processor is None:
        return
    shapes = processor.get_shape()
    if not shapes:
        return
    for line_id, shape_data in shapes.items():
        fig.add_trace(
            go.Scattermap(
                lon=shape_data["lons"],
                lat=shape_data["lats"],
                mode="lines",
                line=dict(width=2.2, color=LINE_COLORS.get(line_id, "rgba(158,176,196,0.55)")),
                name=shape_data["name"],
                hoverinfo="name",
                showlegend=False,
            )
        )


def _build_map(
    raw_df: pd.DataFrame,
    station_map: pd.DataFrame,
    mode: str,
    metric_col: str,
    metric_label: str,
    processor,
) -> go.Figure:
    if mode == "熱區密度":
        upper_bound = float(raw_df["DelayTime"].quantile(0.95))
        upper_bound = upper_bound if upper_bound > 0 else max(float(raw_df["DelayTime"].max()), 1.0)
        fig = px.density_map(
            raw_df,
            lat="Lat",
            lon="Lon",
            z="DelayTime",
            radius=28,
            center=MAP_CENTER,
            zoom=MAP_ZOOM,
            map_style=MAP_STYLE,
            color_continuous_scale=COLOR_SCALE,
            range_color=[0, upper_bound],
            labels={"z": "誤點分鐘"},
        )
        fig.add_trace(
            go.Scattermap(
                lat=station_map["Lat"],
                lon=station_map["Lon"],
                mode="markers",
                marker=dict(size=7, color="rgba(238,245,251,0.45)"),
                customdata=station_map[["StationName", "平均誤點", "誤點率_pct", "觀測筆數"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "平均誤點 %{customdata[1]} 分<br>"
                    "誤點率 %{customdata[2]}%<br>"
                    "觀測筆數 %{customdata[3]}<extra></extra>"
                ),
                showlegend=False,
            )
        )
    else:
        marker_sizes = (
            station_map["觀測筆數"]
            .rank(pct=True)
            .mul(22)
            .clip(lower=8, upper=28)
            .round(1)
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scattermap(
                lat=station_map["Lat"],
                lon=station_map["Lon"],
                mode="markers+text" if mode == "車站標記" else "markers",
                text=station_map["StationName"] if mode == "車站標記" else None,
                textposition="top right",
                textfont=dict(size=9, color="rgba(238,245,251,0.72)"),
                marker=dict(
                    size=marker_sizes if mode == "氣泡分布" else 10,
                    color=station_map[metric_col],
                    colorscale=COLOR_SCALE,
                    opacity=0.88,
                    colorbar=dict(
                        title=dict(text=metric_label, font=dict(color=TEXT_SECONDARY)),
                        tickfont=dict(color=TEXT_SECONDARY),
                        bgcolor="rgba(0,0,0,0)",
                    ),
                    showscale=True,
                ),
                customdata=station_map[["StationName", metric_col, "平均誤點", "誤點率_pct", "觀測筆數"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{metric_label} %{{customdata[1]}}<br>"
                    "平均誤點 %{customdata[2]} 分<br>"
                    "誤點率 %{customdata[3]}%<br>"
                    "觀測筆數 %{customdata[4]}<extra></extra>"
                ),
                showlegend=False,
            )
        )
        fig.update_layout(map=dict(style=MAP_STYLE, center=MAP_CENTER, zoom=MAP_ZOOM))

    _add_rail_lines(fig, processor)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=680,
        font=dict(color=TEXT_SECONDARY, family="IBM Plex Sans TC, Noto Sans TC"),
        coloraxis_colorbar=dict(
            title=dict(text=metric_label, font=dict(color=TEXT_SECONDARY)),
            tickfont=dict(color=TEXT_SECONDARY),
        ),
    )
    return fig


def _build_top_station_bar(station_map: pd.DataFrame, metric_col: str, metric_label: str) -> go.Figure:
    topn = station_map.nlargest(12, metric_col).sort_values(metric_col)
    fig = go.Figure(
        go.Bar(
            x=topn[metric_col],
            y=topn["StationName"],
            orientation="h",
            marker=dict(color=topn[metric_col], colorscale=COLOR_SCALE, line=dict(width=0)),
            text=topn[metric_col].astype(str),
            textposition="outside",
            customdata=topn[["平均誤點", "誤點率_pct", "觀測筆數"]].values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{metric_label} %{{x}}<br>"
                "平均誤點 %{customdata[0]} 分<br>"
                "誤點率 %{customdata[1]}%<br>"
                "觀測筆數 %{customdata[2]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=32, t=16, b=16)}, height=420)
    fig.update_xaxes(**AXIS_STYLE, title=metric_label, rangemode="tozero")
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _build_station_distribution(station_map: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Histogram(
            x=station_map["平均誤點"],
            nbinsx=24,
            marker=dict(color="rgba(75,163,255,0.58)", line=dict(width=0)),
            hovertemplate="平均誤點 %{x:.2f} 分<br>車站數 %{y}<extra></extra>",
        )
    )
    for value, label, color in [
        (float(station_map["平均誤點"].median()), "中位數", GREEN),
        (float(station_map["平均誤點"].quantile(0.9)), "P90", YELLOW),
    ]:
        fig.add_vline(x=value, line_color=color, line_dash="dot", line_width=2)
        fig.add_annotation(x=value, y=1, yref="paper", text=f"{label} {value:.1f}", showarrow=False, font=dict(size=10, color=color))
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=16, t=20, b=16)}, height=290)
    fig.update_xaxes(**AXIS_STYLE, title="各車站平均誤點（分）")
    fig.update_yaxes(**AXIS_STYLE, title="車站數")
    return fig


def _build_corridor_chart(map_df: pd.DataFrame) -> go.Figure | None:
    group_fields = []
    if "TripLine" in map_df.columns:
        group_fields.append("TripLine")
    if "Direction" in map_df.columns:
        group_fields.append("Direction")
    if not group_fields:
        return None

    summary = (
        map_df.groupby(group_fields)
        .agg(平均誤點=("DelayTime", "mean"), 誤點率=("IsDelayed", "mean"), 觀測筆數=("DelayTime", "count"))
        .reset_index()
    )
    if summary.empty:
        return None

    if "TripLine" in summary.columns:
        line_map = {0: "山線", 1: "海線", 2: "其他線"}
        summary["TripLine"] = summary["TripLine"].map(line_map).fillna(summary["TripLine"].astype(str))
    if "Direction" in summary.columns:
        dir_map = {0: "順行", 1: "逆行"}
        summary["Direction"] = summary["Direction"].map(dir_map).fillna(summary["Direction"].astype(str))

    label_cols = [c for c in ["TripLine", "Direction"] if c in summary.columns]
    summary["群組"] = summary[label_cols].astype(str).agg(" / ".join, axis=1)
    summary["誤點率_pct"] = (summary["誤點率"] * 100).round(1)
    summary = summary.sort_values("平均誤點", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=summary["平均誤點"],
            y=summary["群組"],
            orientation="h",
            marker=dict(color=BLUE, line=dict(width=0)),
            name="平均誤點",
            hovertemplate="<b>%{y}</b><br>平均誤點 %{x:.2f} 分<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=summary["誤點率_pct"],
            y=summary["群組"],
            mode="markers+text",
            marker=dict(size=11, color=YELLOW, line=dict(width=1.5, color=BG_COLOR)),
            text=summary["誤點率_pct"].astype(str) + "%",
            textposition="middle right",
            name="誤點率",
            hovertemplate="<b>%{y}</b><br>誤點率 %{x:.1f}%<extra></extra>",
            xaxis="x2",
        )
    )
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=16, r=40, t=20, b=16)},
        height=290,
        xaxis=dict(**AXIS_STYLE, title="平均誤點（分）", domain=[0, 0.72]),
        xaxis2=dict(
            **AXIS_STYLE,
            title="誤點率 (%)",
            overlaying="x",
            side="top",
            range=[0, max(100, float(summary["誤點率_pct"].max()) + 5)],
            domain=[0, 0.72],
        ),
        yaxis=dict(**AXIS_STYLE, title=None),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    )
    return fig


def render(df, filtered_df, date_label, processor=None, **kwargs):
    page_header("◉", "車站熱力圖", "把車站誤點資料轉成可讀的空間風險地圖與車站排行")
    st.caption(f"目前顯示範圍：{date_label}")

    work_df = filtered_df.copy() if not filtered_df.empty else pd.DataFrame()
    work_df = _attach_station_coords(work_df, processor)
    if work_df.empty or "Lat" not in work_df.columns or work_df["Lat"].isna().all():
        st.warning("座標資料載入失敗，無法顯示地圖。")
        return

    control_cols = st.columns([1.5, 1.4, 1.1, 1.2], gap="large")
    with control_cols[0]:
        all_types = sorted(work_df["TrainType"].dropna().unique().tolist())
        selected_types = st.multiselect("車種", all_types, default=all_types, key="map_types_v2")
    with control_cols[1]:
        if "Period" in work_df.columns:
            all_periods = sorted(work_df["Period"].dropna().unique().tolist())
            selected_periods = st.multiselect("時段", all_periods, default=all_periods, key="map_periods_v2")
        else:
            selected_periods = []
    with control_cols[2]:
        map_mode = st.selectbox("地圖模式", ["氣泡分布", "熱區密度", "車站標記"], index=0, key="map_mode_v2")
    with control_cols[3]:
        view_metric = st.selectbox("著色指標", ["平均誤點（分）", "誤點率（%）", "最大誤點（分）"], index=0, key="map_metric_v2")

    map_df = work_df.dropna(subset=["Lat", "Lon", "StationName"]).copy()
    map_df = map_df[map_df["DelayTime"].notna()].copy()
    if selected_types:
        map_df = map_df[map_df["TrainType"].isin(selected_types)]
    if selected_periods and "Period" in map_df.columns:
        map_df = map_df[map_df["Period"].isin(selected_periods)]
    if map_df.empty:
        st.warning("篩選後沒有可用的車站資料。")
        return

    station_map = _aggregate_station_metrics(map_df)
    metric_col, metric_label = _metric_spec(view_metric)

    worst_station = station_map.iloc[0]
    median_station = station_map.sort_values("平均誤點").iloc[len(station_map) // 2]
    stable_station = station_map.sort_values("風險指數", ascending=True).iloc[0]

    map_col, side_col = st.columns([1.75, 1.0], gap="large")
    with map_col:
        section_title("全台分布")
        st.plotly_chart(
            _build_map(map_df, station_map, map_mode, metric_col, metric_label, processor),
            use_container_width=True,
        )
        st.caption("優先看空間集中區，再用右側排行榜鎖定最值得追的車站。")
    with side_col:
        section_title("空間研判")
        story_card(
            "最高風險站",
            str(worst_station["StationName"]),
            f"{metric_label} 最高，平均誤點 {worst_station['平均誤點']} 分，誤點率 {worst_station['誤點率_pct']}%。",
            tone="red",
        )
        story_card(
            "中位數車站",
            str(median_station["StationName"]),
            f"這類車站更接近全體常態，平均誤點約 {median_station['平均誤點']} 分。",
            tone="blue",
        )
        story_card(
            "最穩定站",
            str(stable_station["StationName"]),
            f"風險指數最低，平均誤點 {stable_station['平均誤點']} 分，誤點率 {stable_station['誤點率_pct']}%。",
            tone="green",
        )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        kpi_card("車站總數", f"{len(station_map)} 站", "blue")
    with m2:
        kpi_card("觀測筆數", f"{int(station_map['觀測筆數'].sum()):,}", "blue")
    with m3:
        kpi_card("全體平均誤點", f"{station_map['平均誤點'].mean():.2f} 分", "yellow")
    with m4:
        overall_rate = float(map_df["IsDelayed"].mean() * 100)
        kpi_card("全體誤點率", f"{overall_rate:.1f}%", "green" if overall_rate < 15 else "yellow")

    lower_left, lower_right = st.columns([1.2, 1.0], gap="large")
    with lower_left:
        section_title(f"高風險車站排行：{metric_label}")
        st.plotly_chart(_build_top_station_bar(station_map, metric_col, metric_label), use_container_width=True)
        top_table = (
            station_map.nlargest(12, metric_col)[["StationName", "平均誤點", "誤點率_pct", "最大誤點", "觀測筆數"]]
            .rename(columns={
                "StationName": "車站",
                "平均誤點": "平均誤點（分）",
                "誤點率_pct": "誤點率（%）",
                "最大誤點": "最大誤點（分）",
                "觀測筆數": "觀測筆數",
            })
        )
        st.dataframe(
            top_table.style.format({
                "平均誤點（分）": "{:.2f}",
                "誤點率（%）": "{:.1f}%",
                "最大誤點（分）": "{:.0f}",
                "觀測筆數": "{:,}",
            }),
            use_container_width=True,
            hide_index=True,
        )
    with lower_right:
        section_title("車站分布")
        st.plotly_chart(_build_station_distribution(station_map), use_container_width=True)
        corridor_fig = _build_corridor_chart(map_df)
        if corridor_fig is not None:
            section_title("路線摘要")
            st.plotly_chart(corridor_fig, use_container_width=True)
        note_card(
            "讀圖方式",
            "地圖用來找空間聚集，排行用來找具體車站，路線摘要則協助判斷問題是否集中在特定線別或行車方向。",
        )
