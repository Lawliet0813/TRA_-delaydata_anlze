"""
車次追蹤頁面 — 指定日期 × 車次，查看單班次旅程中的延誤累積。

資料來源：
- 歷史日期 → StationLiveBoard + DailyTrainTimetable 重建後資料
- 當天     → TDX TrainLiveBoard API（即時呼叫）
"""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from views.components import kpi_card, note_card, page_header, section_title, story_card
from views.theme import AXIS_STYLE, BLUE, GREEN, PLOTLY_THEME, TEXT_SECONDARY, YELLOW

RED = "#f85149"
AMBER = "#f59e0b"
BG_COLOR = "#07111a"


def _lookup_schedule_meta(schedule_df: pd.DataFrame, train_no: str) -> dict:
    if schedule_df is None or schedule_df.empty or "TrainNo" not in schedule_df.columns:
        return {}
    matched = schedule_df[schedule_df["TrainNo"].astype(str) == str(train_no)]
    if matched.empty:
        return {}
    row = matched.iloc[0]
    return {
        "TrainType": row.get("TrainTypeSimple", ""),
        "FromStation": row.get("FromStation", ""),
        "ToStation": row.get("ToStation", ""),
        "FirstDep": row.get("FirstDep", ""),
        "LastArr": row.get("LastArr", ""),
    }


def _resolve_route_text(meta: dict, fallback_from: str = "", fallback_to: str = "") -> str:
    from_station = str(meta.get("FromStation") or fallback_from or "").strip()
    to_station = str(meta.get("ToStation") or fallback_to or "").strip()
    if from_station and to_station:
        return f"{from_station} → {to_station}"
    if from_station:
        return from_station
    if to_station:
        return to_station
    return "-"


def _build_station_name_map(processor) -> dict:
    if processor is None or not hasattr(processor, "get_stations_data"):
        return {}
    stations = processor.get_stations_data()
    if stations is None or stations.empty or "StationID" not in stations.columns or "StationName" not in stations.columns:
        return {}
    station_df = stations[["StationID", "StationName"]].dropna(subset=["StationID"]).copy()
    station_df["StationID"] = station_df["StationID"].astype(str).str.strip().str.zfill(4)
    station_df["StationName"] = station_df["StationName"].astype(str).str.strip()
    station_df = station_df[station_df["StationName"] != ""]
    return dict(zip(station_df["StationID"], station_df["StationName"]))


def _enrich_station_names(sub: pd.DataFrame, processor=None) -> pd.DataFrame:
    if sub.empty:
        return sub
    enriched = sub.copy()
    if "StationID" not in enriched.columns:
        return enriched
    enriched["StationID"] = enriched["StationID"].astype(str).str.strip().str.zfill(4)
    if "StationName" not in enriched.columns:
        enriched["StationName"] = pd.NA
    station_map = _build_station_name_map(processor)
    cleaned_name = enriched["StationName"].astype("string").str.strip()
    invalid_name = cleaned_name.isna() | (cleaned_name == "") | (cleaned_name == enriched["StationID"])
    if station_map:
        enriched.loc[invalid_name, "StationName"] = enriched.loc[invalid_name, "StationID"].map(station_map)
    enriched["StationName"] = (
        enriched["StationName"]
        .astype("string")
        .str.strip()
        .fillna(enriched["StationID"])
    )
    return enriched


def _build_stop_detail(sub: pd.DataFrame, processor, train_no: str) -> pd.DataFrame:
    observed = sub.copy()
    if observed.empty:
        return observed
    observed["_obs_order"] = range(1, len(observed) + 1)

    keep_cols = [
        c for c in [
            "StopSeq",
            "StationID",
            "StationName",
            "DelayTime",
            "ActualDep",
            "IsDelayed",
            "PrevDelay",
            "ScheduledArr",
            "ScheduledDep",
            "Direction",
            "_obs_order",
        ]
        if c in observed.columns
    ]
    observed = observed[keep_cols].copy()

    if "StopSeq" in observed.columns:
        observed = observed.drop_duplicates(subset=["StopSeq"], keep="last")
    elif "StationID" in observed.columns:
        observed = observed.drop_duplicates(subset=["StationID"], keep="last")

    if processor is None or not hasattr(processor, "get_train_timetable"):
        return observed.sort_values("_obs_order").reset_index(drop=True)

    full_stops = processor.get_train_timetable(train_no)
    if full_stops.empty:
        return observed.sort_values("_obs_order").reset_index(drop=True)

    base_cols = [c for c in ["StopSeq", "StationID", "StationName", "ScheduledArr", "ScheduledDep"] if c in full_stops.columns]
    detail = full_stops[base_cols].drop_duplicates(subset=["StopSeq"], keep="last")
    if "StopSeq" in observed.columns:
        detail = detail.merge(
            observed.drop(columns=["StationID", "StationName", "ScheduledArr", "ScheduledDep"], errors="ignore"),
            on="StopSeq",
            how="left",
        )
    else:
        detail = detail.merge(
            observed.drop(columns=["StationName", "ScheduledArr", "ScheduledDep"], errors="ignore"),
            on="StationID",
            how="left",
        )
    if "StationName" in detail.columns:
        detail["StationName"] = detail["StationName"].fillna(detail.get("StationID"))
    return detail.sort_values("StopSeq").reset_index(drop=True)


def _fetch_train_live(train_no: str) -> pd.DataFrame:
    try:
        from auth import auth_header
        from config import BASE_URL

        url = f"{BASE_URL}/TrainLiveBoard/TrainNo/{train_no}"
        resp = requests.get(url, headers=auth_header(), params={"$format": "JSON"}, timeout=8)
        resp.raise_for_status()
        boards = resp.json().get("TrainLiveBoards", [])
        if not boards:
            return pd.DataFrame()
        records = []
        for item in boards:
            records.append(
                {
                    "StationID": item.get("StationID", ""),
                    "StationName": item.get("StationName", {}).get("Zh_tw", ""),
                    "DelayTime": item.get("DelayTime", 0),
                    "TrainType": item.get("TrainTypeName", {}).get("Zh_tw", ""),
                    "Direction": item.get("Direction", ""),
                    "EndingStationID": item.get("EndingStationID", ""),
                    "UpdateTime": item.get("UpdateTime", ""),
                }
            )
        return pd.DataFrame(records)
    except Exception as exc:
        st.error(f"API 呼叫失敗：{exc}")
        return pd.DataFrame()


def _get_history(df: pd.DataFrame, train_no: str, sel_date: str) -> pd.DataFrame:
    sub = df[
        (df["TrainNo"].astype(str) == str(train_no))
        & (df["Date"].astype(str) == sel_date)
    ].copy()
    if sub.empty:
        return sub
    if "StopSeq" in sub.columns:
        return sub.sort_values("StopSeq").reset_index(drop=True)
    if "ScheduledArr" in sub.columns:
        return sub.sort_values("ScheduledArr").reset_index(drop=True)
    return sub.reset_index(drop=True)


def _delay_status(delay_value: float | int | None) -> str:
    if pd.isna(delay_value):
        return "無資料"
    if delay_value >= 5:
        return "官方誤點"
    if delay_value >= 2:
        return "研究誤點"
    if delay_value >= 1:
        return "輕微延誤"
    return "準點"


def _delay_color(delay_value: float | int | None) -> str:
    if pd.isna(delay_value):
        return TEXT_SECONDARY
    if delay_value >= 5:
        return RED
    if delay_value >= 2:
        return YELLOW
    if delay_value >= 1:
        return AMBER
    return GREEN


def _journey_summary(detail_df: pd.DataFrame) -> dict:
    valid_delay = detail_df["DelayTime"].fillna(0)
    delayed_research = int((valid_delay >= 2).sum())
    delayed_official = int((valid_delay >= 5).sum())
    first_delay_station = "—"
    delayed_rows = detail_df[valid_delay >= 2]
    if not delayed_rows.empty:
        first_delay_station = str(delayed_rows.iloc[0].get("StationName") or delayed_rows.iloc[0].get("StationID") or "—")
    peak_row = detail_df.loc[valid_delay.idxmax()] if not detail_df.empty else None
    peak_station = "—"
    peak_delay = 0.0
    if peak_row is not None:
        peak_station = str(peak_row.get("StationName") or peak_row.get("StationID") or "—")
        peak_delay = float(peak_row.get("DelayTime") or 0)
    end_delay = float(valid_delay.iloc[-1]) if not detail_df.empty else 0.0
    coverage_rate = float(detail_df["CoverageRate"].dropna().iloc[0]) if "CoverageRate" in detail_df.columns and detail_df["CoverageRate"].notna().any() else 0.0
    observed_stop_count = int(detail_df["ObservedStopCount"].dropna().iloc[0]) if "ObservedStopCount" in detail_df.columns and detail_df["ObservedStopCount"].notna().any() else 0
    scheduled_stop_count = int(detail_df["ScheduledStopCount"].dropna().iloc[0]) if "ScheduledStopCount" in detail_df.columns and detail_df["ScheduledStopCount"].notna().any() else int(len(detail_df))
    return {
        "stop_count": int(len(detail_df)),
        "avg_delay": round(float(valid_delay.mean()), 2),
        "max_delay": round(float(valid_delay.max()), 1),
        "research_delay_count": delayed_research,
        "official_delay_count": delayed_official,
        "first_delay_station": first_delay_station,
        "peak_station": peak_station,
        "peak_delay": peak_delay,
        "end_delay": end_delay,
        "coverage_rate": coverage_rate,
        "observed_stop_count": observed_stop_count,
        "scheduled_stop_count": scheduled_stop_count,
    }


def _build_delay_profile_chart(detail_df: pd.DataFrame, title: str) -> go.Figure:
    chart_df = detail_df.copy()
    if "StopSeq" not in chart_df.columns:
        chart_df["StopSeq"] = range(1, len(chart_df) + 1)
    chart_df["StopSeq"] = pd.to_numeric(chart_df["StopSeq"], errors="coerce")
    chart_df = chart_df.dropna(subset=["StopSeq"])
    chart_df["DelayTime"] = pd.to_numeric(chart_df["DelayTime"], errors="coerce").fillna(0)
    chart_df["StationLabel"] = chart_df.apply(
        lambda r: f"{int(r['StopSeq'])}｜{r['StationName']}"
        if pd.notna(r.get("StationName")) else f"{int(r['StopSeq'])}",
        axis=1,
    )

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=2, fillcolor="rgba(53,196,139,0.06)", line_width=0)
    fig.add_hrect(y0=2, y1=5, fillcolor="rgba(241,184,75,0.08)", line_width=0)
    fig.add_hrect(y0=5, y1=max(chart_df["DelayTime"].max() + 1, 6), fillcolor="rgba(242,107,94,0.08)", line_width=0)
    fig.add_trace(
        go.Scatter(
            x=chart_df["StopSeq"],
            y=chart_df["DelayTime"],
            mode="lines+markers",
            line=dict(color=BLUE, width=2.5),
            marker=dict(
                size=10,
                color=chart_df["DelayTime"].apply(_delay_color),
                line=dict(width=1.6, color=BG_COLOR),
            ),
            customdata=chart_df[["StationLabel", "DelayTime"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>延誤 %{customdata[1]} 分<extra></extra>",
            showlegend=False,
        )
    )
    fig.add_hline(y=2, line_dash="dot", line_color=YELLOW, annotation_text="研究門檻 2 分", annotation_position="top left")
    fig.add_hline(y=5, line_dash="dot", line_color=RED, annotation_text="官方門檻 5 分", annotation_position="top right")
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=16, r=16, t=42, b=16)},
        title=dict(text=title, font=dict(size=14, color="#e6edf3")),
        height=360,
    )
    fig.update_xaxes(
        **AXIS_STYLE,
        title="停靠序",
        tickmode="array",
        tickvals=chart_df["StopSeq"],
        ticktext=chart_df["StationLabel"],
        tickangle=-40,
        tickfont=dict(size=10),
    )
    fig.update_yaxes(**AXIS_STYLE, title="延誤（分）", rangemode="tozero")
    return fig


def _build_journey_timeline_chart(detail_df: pd.DataFrame) -> go.Figure | None:
    chart_df = detail_df.copy()
    if "StopSeq" not in chart_df.columns:
        chart_df["StopSeq"] = range(1, len(chart_df) + 1)
    time_col = "ScheduledDep" if "ScheduledDep" in chart_df.columns else "ScheduledArr"
    if time_col not in chart_df.columns:
        return None
    chart_df[time_col] = pd.to_datetime(chart_df[time_col], format="%H:%M", errors="coerce")
    chart_df = chart_df.dropna(subset=[time_col])
    if chart_df.empty:
        return None

    chart_df["DelayTime"] = pd.to_numeric(chart_df["DelayTime"], errors="coerce").fillna(0)
    chart_df["ActualTime"] = chart_df[time_col] + pd.to_timedelta(chart_df["DelayTime"], unit="m")
    chart_df["StationLabel"] = chart_df.apply(
        lambda r: f"{int(r['StopSeq'])}｜{r['StationName']}" if pd.notna(r.get("StopSeq")) else str(r.get("StationName", "")),
        axis=1,
    )
    chart_df["Status"] = chart_df["DelayTime"].apply(_delay_status)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df[time_col],
            y=chart_df["StationLabel"],
            mode="lines+markers",
            name="表定",
            line=dict(color="rgba(158,176,196,0.42)", width=2),
            marker=dict(size=8, color="rgba(158,176,196,0.72)"),
            hovertemplate="<b>%{y}</b><br>表定 %{x|%H:%M}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["ActualTime"],
            y=chart_df["StationLabel"],
            mode="lines+markers",
            name="實際",
            line=dict(color=BLUE, width=2.6),
            marker=dict(
                size=10,
                color=chart_df["DelayTime"].apply(_delay_color),
                line=dict(width=1.3, color=BG_COLOR),
            ),
            customdata=chart_df[["DelayTime", "Status"]].values,
            hovertemplate="<b>%{y}</b><br>實際 %{x|%H:%M}<br>延誤 %{customdata[0]} 分<br>%{customdata[1]}<extra></extra>",
        )
    )
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=16, r=16, t=20, b=16)},
        height=max(320, 36 * len(chart_df)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(**AXIS_STYLE, title="時間")
    fig.update_yaxes(**AXIS_STYLE, title=None, autorange="reversed")
    return fig


def _render_live_view(train_no: str, today_str: str, schedule_df: pd.DataFrame | None) -> None:
    section_title(f"即時動態｜{train_no} 次｜{today_str}")
    st.caption("資料來源：TDX TrainLiveBoard API。即時模式僅顯示列車當前位置，並非全程停靠紀錄。")
    with st.spinner("呼叫 TDX API 中…"):
        live_df = _fetch_train_live(train_no)

    if live_df.empty:
        st.warning(f"查無 {train_no} 次的即時資料。可能尚未出發、已到終點，或車次號碼有誤。")
        return

    row = live_df.iloc[0]
    update_time = str(row.get("UpdateTime", ""))[:19].replace("T", " ")
    meta = _lookup_schedule_meta(schedule_df, train_no)
    route_text = _resolve_route_text(meta)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("車種", str(meta.get("TrainType") or row.get("TrainType") or "-"), "blue")
    with c2:
        kpi_card("目前位置", str(row.get("StationName") or row.get("StationID") or "-"), "green")
    with c3:
        live_delay = float(row.get("DelayTime", 0) or 0)
        kpi_card("即時延誤", f"{live_delay:.0f} 分", "red" if live_delay >= 5 else "yellow" if live_delay >= 2 else "green")
    with c4:
        kpi_card("行駛區間", route_text, "blue", update_time if update_time else "—")

    note_card(
        "即時模式限制",
        "今天的查詢只會回傳列車目前所在車站。如果你要看完整沿線延誤累積，請改查歷史日期。",
    )


def _render_history_view(
    df: pd.DataFrame,
    train_no: str,
    sel_date: str,
    schedule_df: pd.DataFrame | None,
    processor,
) -> None:
    section_title(f"旅程視圖｜{train_no} 次｜{sel_date}")
    sub = _get_history(df, train_no, str(sel_date))
    if sub.empty:
        st.warning(f"查無 {sel_date} 日 {train_no} 次的資料，可能該日未行駛或爬蟲未覆蓋。")
        return

    sub = _enrich_station_names(sub, processor)
    detail_df = _build_stop_detail(sub, processor, train_no)
    detail_df = _enrich_station_names(detail_df, processor)
    detail_df["DelayTime"] = pd.to_numeric(detail_df.get("DelayTime"), errors="coerce")

    meta = _lookup_schedule_meta(schedule_df, train_no)
    fallback_from = str(detail_df["StationName"].iloc[0]) if not detail_df.empty else ""
    fallback_to = str(detail_df["StationName"].iloc[-1]) if not detail_df.empty else ""
    route_text = _resolve_route_text(meta, fallback_from, fallback_to)
    train_type = meta.get("TrainType") or (sub["TrainType"].iloc[0] if "TrainType" in sub.columns and not sub.empty else "-")
    first_dep = meta.get("FirstDep") or (detail_df["ScheduledDep"].dropna().iloc[0] if "ScheduledDep" in detail_df.columns and detail_df["ScheduledDep"].notna().any() else "-")
    last_arr = meta.get("LastArr") or (detail_df["ScheduledArr"].dropna().iloc[-1] if "ScheduledArr" in detail_df.columns and detail_df["ScheduledArr"].notna().any() else "-")

    meta_cols = st.columns(5)
    with meta_cols[0]:
        kpi_card("車種", str(train_type), "blue")
    with meta_cols[1]:
        kpi_card("始發站", str(meta.get("FromStation") or fallback_from or "-"), "blue")
    with meta_cols[2]:
        kpi_card("終點站", str(meta.get("ToStation") or fallback_to or "-"), "blue")
    with meta_cols[3]:
        kpi_card("始發時間", str(first_dep), "green")
    with meta_cols[4]:
        kpi_card("終到時間", str(last_arr), "green")
    st.caption(f"行駛區間：{route_text}")

    summary = _journey_summary(detail_df)
    insight_col, stats_col = st.columns([1.0, 1.3], gap="large")
    with insight_col:
        story_card(
            "最早出現研究誤點",
            summary["first_delay_station"],
            f"從這一站開始延誤達 2 分鐘以上，後續車站就要觀察是否持續累積。",
            tone="yellow" if summary["research_delay_count"] else "green",
        )
        story_card(
            "延誤峰值",
            f"{summary['peak_station']} · {summary['peak_delay']:.0f} 分",
            "這是整段旅程中延誤最嚴重的車站，可回頭對照路段或前站傳遞效應。",
            tone="red" if summary["peak_delay"] >= 5 else "yellow",
        )
        story_card(
            "終點狀態",
            f"{summary['end_delay']:.0f} 分",
            "終點延誤低，不代表中途旅客沒有感受到延誤；這正是這頁要看的重點。",
            tone="blue",
        )
    with stats_col:
        s1, s2, s3, s4, s5 = st.columns(5)
        with s1:
            kpi_card("停靠站數", f"{summary['stop_count']}", "blue")
        with s2:
            kpi_card("平均延誤", f"{summary['avg_delay']:.2f} 分", "yellow" if summary["avg_delay"] >= 2 else "green")
        with s3:
            kpi_card("研究誤點站", f"{summary['research_delay_count']} 站", "yellow", "≥ 2 分")
        with s4:
            kpi_card("官方誤點站", f"{summary['official_delay_count']} 站", "red", "≥ 5 分")
        with s5:
            kpi_card("觀測覆蓋率", f"{summary['coverage_rate'] * 100:.1f}%", "blue", f"{summary['observed_stop_count']}/{summary['scheduled_stop_count']} 站")
        note_card(
            "判讀順序",
            "先看觀測覆蓋率，再看延誤強度圖與時間軸。`DelaySource=observed` 是實際觀測，其他類型是依 timetable 骨架補值。",
        )

    chart_left, chart_right = st.columns([1.2, 1.0], gap="large")
    with chart_left:
        section_title("延誤強度")
        st.plotly_chart(
            _build_delay_profile_chart(detail_df, f"{train_no} 次 {sel_date} 各站延誤強度"),
            use_container_width=True,
        )
    with chart_right:
        section_title("旅程時間軸")
        timeline_fig = _build_journey_timeline_chart(detail_df)
        if timeline_fig is not None:
            st.plotly_chart(timeline_fig, use_container_width=True)
        else:
            st.info("目前缺少足夠的表定時間欄位，暫時無法建立旅程時間軸。")

    with st.expander("停靠明細"):
        show_df = detail_df.copy()
        if "DelayTime" in show_df.columns:
            show_df["狀態"] = show_df["DelayTime"].apply(_delay_status)
        show_cols = [
            c for c in [
                "StopSeq",
                "StationName",
                "ScheduledArr",
                "ScheduledDep",
                "ActualDep",
                "DelayTime",
                "ObservedDelayTime",
                "DelaySource",
                "狀態",
                "PrevDelay",
            ]
            if c in show_df.columns
        ]
        renamed = show_df[show_cols].rename(
            columns={
                "StopSeq": "停靠序",
                "StationName": "車站",
                "ScheduledArr": "表定到站",
                "ScheduledDep": "表定開車",
                "ActualDep": "實際開車",
                "DelayTime": "延誤(分)",
                "ObservedDelayTime": "原始觀測延誤",
                "DelaySource": "資料來源",
                "PrevDelay": "前站延誤",
            }
        )
        st.dataframe(renamed, use_container_width=True, hide_index=True)

    with st.expander("指標說明"):
        st.markdown(
            """
            | 指標 | 說明 |
            |------|------|
            | **研究誤點站** | `DelayTime >= 2` 分鐘 |
            | **官方誤點站** | `DelayTime >= 5` 分鐘 |
            | **資料來源** | `observed` 為實際觀測；其餘為依 timetable 骨架重建 |
            | **觀測覆蓋率** | 該班次實際觀測到的站數 / timetable 全部停靠站數 |
            | **延誤強度圖** | 看哪一站開始累積、哪一站達到峰值 |
            | **旅程時間軸** | 比較表定與實際通過時刻，觀察整趟旅程是否追回時間 |
            """
        )


def render(df: pd.DataFrame, **kwargs):
    page_header("◗", "車次追蹤", "把單班次沿線停靠紀錄轉成可讀的旅程延誤視圖")
    schedule_df = kwargs.get("schedule_df")
    processor = kwargs.get("processor")

    today_str = date.today().strftime("%Y-%m-%d")
    available_dates = sorted(df["Date"].astype(str).unique(), reverse=True) if not df.empty else []
    if today_str not in available_dates:
        available_dates = [today_str] + available_dates
    if not available_dates:
        st.warning("目前篩選範圍沒有可追蹤的車次資料。")
        return

    prefill_date = st.session_state.get("tracker_prefill_date")
    if "tracker_date_v2" not in st.session_state:
        if prefill_date in available_dates:
            st.session_state["tracker_date_v2"] = prefill_date
        elif available_dates:
            st.session_state["tracker_date_v2"] = available_dates[0]
    elif st.session_state["tracker_date_v2"] not in available_dates and available_dates:
        st.session_state["tracker_date_v2"] = available_dates[0]

    if "tracker_train_txt_v2" not in st.session_state and st.session_state.get("tracker_prefill_train_no"):
        st.session_state["tracker_train_txt_v2"] = st.session_state["tracker_prefill_train_no"]

    col_a, col_b, col_c = st.columns([1.5, 1.6, 0.6], gap="large")
    with col_a:
        sel_date = st.selectbox("選擇日期", available_dates, key="tracker_date_v2")
    with col_b:
        is_today = str(sel_date) == today_str
        if not is_today and not df.empty:
            day_trains = sorted(df[df["Date"].astype(str) == str(sel_date)]["TrainNo"].astype(str).unique())
            prefill_train = st.session_state.get("tracker_prefill_train_no")
            if day_trains:
                if "tracker_train_sel_v2" not in st.session_state:
                    st.session_state["tracker_train_sel_v2"] = (
                        prefill_train if prefill_train in day_trains else day_trains[0]
                    )
                elif st.session_state["tracker_train_sel_v2"] not in day_trains:
                    st.session_state["tracker_train_sel_v2"] = (
                        prefill_train if prefill_train in day_trains else day_trains[0]
                    )
            train_input = st.selectbox("選擇車次", day_trains, key="tracker_train_sel_v2")
        else:
            train_input = st.text_input("輸入車次號碼", placeholder="例如：131", key="tracker_train_txt_v2")
    with col_c:
        st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
        search = st.button("查詢", use_container_width=True, type="primary")

    if not search:
        note_card("使用方式", "先選日期，再選車次。歷史日期會顯示完整旅程，即時日期只會顯示目前所在位置。")
        return

    train_no = str(train_input).strip()
    if not train_no:
        st.warning("請輸入車次號碼。")
        return

    if is_today:
        _render_live_view(train_no, today_str, schedule_df)
    else:
        _render_history_view(df, train_no, str(sel_date), schedule_df, processor)
