"""
車次追蹤頁面 — 指定日期 × 車次，查看全程誤點折線圖。

資料來源：
- 歷史日期 → data/output/processed_data.csv
- 當天     → TDX TrainLiveBoard API（即時呼叫）
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import date

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, TEXT_SECONDARY
from views.components import page_header, section_title

RED   = "#f85149"
AMBER = "#f59e0b"


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


def _build_stop_detail(sub: pd.DataFrame, processor, train_no: str) -> pd.DataFrame:
    observed = sub.copy()
    if observed.empty:
        return observed

    keep_cols = [c for c in ["StopSeq", "StationID", "StationName", "DelayTime", "IsDelayed", "PrevDelay"] if c in observed.columns]
    observed = observed[keep_cols].drop_duplicates(subset=["StopSeq"], keep="last")

    if processor is None or not hasattr(processor, "get_train_timetable"):
        return observed.sort_values("StopSeq").reset_index(drop=True)

    full_stops = processor.get_train_timetable(train_no)
    if full_stops.empty:
        return observed.sort_values("StopSeq").reset_index(drop=True)

    base_cols = [c for c in ["StopSeq", "StationID", "StationName", "ScheduledArr", "ScheduledDep"] if c in full_stops.columns]
    detail = full_stops[base_cols].drop_duplicates(subset=["StopSeq"], keep="last")
    detail = detail.merge(
        observed.drop(columns=["StationID", "StationName"], errors="ignore"),
        on="StopSeq",
        how="left",
    )
    if "StationName" in detail.columns:
        detail["StationName"] = detail["StationName"].fillna(detail.get("StationID"))
    return detail.sort_values("StopSeq").reset_index(drop=True)


# ══ 即時 API 呼叫 ══════════════════════════════════════════════════════════════

def _fetch_train_live(train_no: str) -> pd.DataFrame:
    """
    呼叫 TDX TrainLiveBoard/{TrainNo}，回傳該車次目前位置。
    注意：此 API 只回傳「列車目前所在車站」單一筆，非全程。
    """
    try:
        from config import BASE_URL
        from auth import auth_header
        url = f"{BASE_URL}/TrainLiveBoard/TrainNo/{train_no}"
        resp = requests.get(url, headers=auth_header(),
                            params={"$format": "JSON"}, timeout=8)
        resp.raise_for_status()
        boards = resp.json().get("TrainLiveBoards", [])
        if not boards:
            return pd.DataFrame()
        records = []
        for r in boards:
            records.append({
                "StationID":       r.get("StationID", ""),
                "StationName":     r.get("StationName", {}).get("Zh_tw", ""),
                "DelayTime":       r.get("DelayTime", 0),
                "TrainType":       r.get("TrainTypeName", {}).get("Zh_tw", ""),
                "Direction":       r.get("Direction", ""),
                "EndingStationID": r.get("EndingStationID", ""),
                "UpdateTime":      r.get("UpdateTime", ""),
            })
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"API 呼叫失敗：{e}")
        return pd.DataFrame()


# ══ 歷史資料查詢 ══════════════════════════════════════════════════════════════

def _get_history(df: pd.DataFrame, train_no: str, sel_date: str) -> pd.DataFrame:
    sub = df[
        (df["TrainNo"].astype(str) == str(train_no)) &
        (df["Date"].astype(str) == sel_date)
    ].copy()
    if sub.empty:
        return sub
    return sub.sort_values("StopSeq").reset_index(drop=True)


# ══ KPI 列 ════════════════════════════════════════════════════════════════════
def _draw_kpi_row(sub: pd.DataFrame):
    total   = len(sub)
    max_d   = int(sub["DelayTime"].max())
    avg_d   = round(sub["DelayTime"].mean(), 1)
    over5   = int((sub["DelayTime"] >= 5).sum())
    on_time = total - int((sub["DelayTime"] >= 1).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("最大誤點", f"{max_d} min")
    c2.metric("平均誤點", f"{avg_d} min")
    c3.metric("超標站數（≥5min）", f"{over5} 站")
    c4.metric("準點站數（0min）", f"{on_time} 站")


# ══ 折線圖 ════════════════════════════════════════════════════════════════
def _draw_delay_chart(sub: pd.DataFrame, title: str):
    name_col = "StationName" if ("StationName" in sub.columns and sub["StationName"].notna().any()) else "StationID"
    sub = sub.copy()
    sub["x_label"] = sub.apply(
        lambda r: f"{int(r['StopSeq'])}｜{r[name_col]}"
        if pd.notna(r.get("StopSeq")) else str(r[name_col]),
        axis=1
    )
    colors = sub["DelayTime"].apply(
        lambda d: RED if d >= 5 else (AMBER if d >= 1 else GREEN)
    )
    fig = go.Figure()
    # 塡充背景
    fig.add_trace(go.Scatter(
        x=sub["x_label"], y=sub["DelayTime"],
        mode="lines", line=dict(color=BLUE, width=0),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.07)",
        showlegend=False, hoverinfo="skip",
    ))
    # 主線 + 點
    fig.add_trace(go.Scatter(
        x=sub["x_label"], y=sub["DelayTime"],
        mode="lines+markers", name="誤點分鐘",
        line=dict(color=BLUE, width=2),
        marker=dict(size=9, color=colors, line=dict(width=1.5, color="#0d1117")),
        hovertemplate="<b>%{x}</b><br>誤點：%{y} 分鐘<extra></extra>",
    ))
    # 5 分鐘基準線
    fig.add_hline(
        y=5, line_dash="dot", line_color=RED,
        annotation_text="官方誤點門檻（5 min）",
        annotation_font_color=RED,
        annotation_position="top right",
    )
    fig.update_layout(
        **PLOTLY_THEME,
        title=dict(text=title, font=dict(size=14, color="#e6edf3")),
        height=400,
        xaxis=dict(**AXIS_STYLE, title="停靠順序｜車站", tickangle=-40, tickfont=dict(size=10)),
        yaxis=dict(**AXIS_STYLE, title="誤點（分鐘）", rangemode="tozero"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
#  主渲染函數
# ══════════════════════════════════════════════════════════════

def render(df: pd.DataFrame, **kwargs):
    page_header("◗", "車次追蹤", "指定日期 × 車次全程誤點分析")
    schedule_df = kwargs.get("schedule_df")
    processor = kwargs.get("processor")

    today_str = date.today().strftime("%Y-%m-%d")

    # ── 輸入區 ─────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([2, 2, 1])

    with col_a:
        available_dates = sorted(df["Date"].unique(), reverse=True) if not df.empty else []
        if today_str not in [str(d) for d in available_dates]:
            available_dates = [today_str] + list(available_dates)
        sel_date = st.selectbox("選擇日期", available_dates, key="tracker_date")

    with col_b:
        is_today = (str(sel_date) == today_str)
        if not is_today and not df.empty:
            day_trains = sorted(
                df[df["Date"].astype(str) == str(sel_date)]["TrainNo"].astype(str).unique()
            )
            train_input = st.selectbox("選擇車次", day_trains, key="tracker_train_sel")
        else:
            train_input = st.text_input("輸入車次號碼", placeholder="例如：131", key="tracker_train_txt")

    with col_c:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        search = st.button("🔍 查詢", use_container_width=True, type="primary")

    if not search:
        st.info("請選擇日期與車次後按下查詢。")
        return

    train_no = str(train_input).strip()
    if not train_no:
        st.warning("請輸入車次號碼。")
        return

    st.markdown("---")

    # ══ 當天：即時 API ═══════════════════════════════════════════════════════
    if is_today:
        section_title(f"🟢 即時動態\u3000{train_no} 次\u3000{today_str}")
        st.caption("資料來源：TDX TrainLiveBoard API（即時）。此 API 只回傳列車目前所在車站，非全程記錄。")

        with st.spinner("呼叫 TDX API 中…"):
            live_df = _fetch_train_live(train_no)

        if live_df.empty:
            st.warning(f"查無 {train_no} 次的即時資料。可能尚未出發、已到終點，或車次號碼有誤。")
            return

        r = live_df.iloc[0]
        update_time = str(r.get("UpdateTime", ""))[:19].replace("T", " ")
        meta = _lookup_schedule_meta(schedule_df, train_no)
        route_text = _resolve_route_text(meta)

        cols = st.columns(4)
        cols[0].metric("車種", meta.get("TrainType") or r.get("TrainType", "-"))
        cols[1].metric("目前位置", r.get("StationName", r.get("StationID", "-")))
        cols[2].metric("即時誤點", f"{r.get('DelayTime', 0)} min")
        cols[3].metric("行駛區間", route_text)
        st.caption(f"資料更新時間：{update_time}")
        st.info("💡 如需查看完整全程誤點折線，請選擇歷史日期（今天的資料會在明天可供查詢）。")

    # ══ 歷史日期：CSV 全程折線 ═══════════════════════════════════════════
    else:
        section_title(f"📈 全程誤點\u3000{train_no} 次\u3000{sel_date}")

        sub = _get_history(df, train_no, str(sel_date))
        if sub.empty:
            st.warning(f"查無 {sel_date} 日 {train_no} 次的資料，可能該日未行駛或爬蟲未覆蓋。")
            return

        meta = _lookup_schedule_meta(schedule_df, train_no)
        fallback_from = sub["StationName"].iloc[0] if "StationName" in sub.columns and not sub.empty else ""
        fallback_to = sub["StationName"].iloc[-1] if "StationName" in sub.columns and not sub.empty else ""
        train_type = meta.get("TrainType") or (sub["TrainType"].iloc[0] if "TrainType" in sub.columns else "-")
        first_arr = meta.get("FirstDep") or (sub["FirstDep"].iloc[0] if "FirstDep" in sub.columns else "-")
        last_arr = meta.get("LastArr") or (sub["LastArr"].iloc[0] if "LastArr" in sub.columns else "-")
        route_text = _resolve_route_text(meta, fallback_from, fallback_to)
        from_station = meta.get("FromStation") or fallback_from or "-"
        to_station = meta.get("ToStation") or fallback_to or "-"

        meta_cols = st.columns(5)
        meta_cols[0].metric("車種", train_type)
        meta_cols[1].metric("始發站", from_station)
        meta_cols[2].metric("終點站", to_station)
        meta_cols[3].metric("始發時間", first_arr)
        meta_cols[4].metric("終到時間", last_arr)
        st.caption(f"行駛區間：{route_text}")

        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
        _draw_kpi_row(sub)

        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
        _draw_delay_chart(sub, f"{train_no} 次 {sel_date} 全程誤點（分鐘）")

        with st.expander("📋 完整停靠明細"):
            detail_df = _build_stop_detail(sub, processor, train_no)
            show_cols = [c for c in [
                "StopSeq", "StationName", "ScheduledArr", "ScheduledDep",
                "DelayTime", "IsDelayed", "PrevDelay"
            ] if c in detail_df.columns]
            st.dataframe(
                detail_df[show_cols].rename(columns={
                    "StopSeq": "停靠序",
                    "StationName": "車站",
                    "ScheduledArr": "表定到站",
                    "ScheduledDep": "表定開車",
                    "DelayTime": "誤點(分)",
                    "IsDelayed": "超標",
                    "PrevDelay": "前站誤點",
                }),
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("📊 指標說明"):
            st.markdown("""
            | 指標 | 說明 |
            |------|------|
            | **誤點分鐘** | TDX `StationLiveBoard` 直接回傳，來自臺鐵 CTC 系統 |
            | **超標站數** | `DelayTime ≥ 5` 分鐘（官方口徑）|
            | **準點站數** | `DelayTime = 0` 分鐘 |
            | **🔴 紅點** | ≥5 分鐘 |
            | **🟡 橘點** | 1–4 分鐘 |
            | **🟢 綠點** | 準點（0 分鐘）|
            """)
