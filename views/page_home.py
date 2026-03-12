"""
首頁 (Home) — Research dashboard landing page
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from views.theme import (
    PLOTLY_THEME,
    AXIS_STYLE,
    BLUE,
    GREEN,
    YELLOW,
    RED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from views.components import kpi_card, note_card, section_title, story_card, method_step
from views.navigation import goto_page


def _safe_current_df(df: pd.DataFrame, filtered_df: pd.DataFrame | None) -> pd.DataFrame:
    if filtered_df is not None and not filtered_df.empty:
        return filtered_df.copy()
    return df.copy()


def _delay_color(delay_value: float) -> str:
    if delay_value >= 4:
        return RED
    if delay_value >= 2:
        return YELLOW
    return GREEN


def _build_daily_trend_chart(full_df: pd.DataFrame, selected_date: str | None = None) -> go.Figure | None:
    if full_df.empty or "Date" not in full_df.columns:
        return None

    daily = (
        full_df.groupby("Date")
        .agg(
            準點率=("IsDelayed", lambda x: round((1 - x.mean()) * 100, 1)),
            平均誤點=("DelayTime", lambda x: round(x.mean(), 2)),
            觀測筆數=("DelayTime", "count"),
        )
        .reset_index()
        .sort_values("Date")
    )
    if daily.empty:
        return None

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=daily["Date"],
            y=daily["平均誤點"],
            name="平均誤點",
            marker=dict(color="rgba(75,163,255,0.18)", line=dict(width=0)),
            hovertemplate="日期 %{x}<br>平均誤點 %{y:.2f} 分<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["準點率"],
            name="準點率",
            mode="lines+markers",
            line=dict(color=BLUE, width=2.8),
            marker=dict(size=7, color=BLUE),
            hovertemplate="日期 %{x}<br>準點率 %{y:.1f}%<extra></extra>",
        ),
        secondary_y=False,
    )
    if selected_date and selected_date != "全部日期" and selected_date in set(daily["Date"]):
        highlight = daily[daily["Date"] == selected_date]
        fig.add_trace(
            go.Scatter(
                x=highlight["Date"],
                y=highlight["準點率"],
                name="目前範圍",
                mode="markers",
                marker=dict(size=14, color=YELLOW, symbol="diamond", line=dict(width=2, color=BG_COLOR())),
                hovertemplate="目前範圍 %{x}<br>準點率 %{y:.1f}%<extra></extra>",
            ),
            secondary_y=False,
        )

    fig.update_layout(
        **PLOTLY_THEME,
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        bargap=0.28,
    )
    fig.update_yaxes(title_text="準點率 (%)", range=[75, 100], secondary_y=False, **AXIS_STYLE)
    fig.update_yaxes(title_text="平均誤點（分）", rangemode="tozero", secondary_y=True, **AXIS_STYLE)
    fig.update_xaxes(**AXIS_STYLE, title=None)
    return fig


def BG_COLOR() -> str:
    return "#07111a"


def _build_train_type_lollipop(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "TrainType" not in df.columns:
        return None
    type_summary = (
        df.groupby("TrainType")
        .agg(平均誤點=("DelayTime", "mean"), 準點率=("IsDelayed", lambda x: (1 - x.mean()) * 100))
        .reset_index()
        .sort_values("平均誤點")
    )
    if type_summary.empty:
        return None

    colors = [_delay_color(v) for v in type_summary["平均誤點"]]
    fig = go.Figure()
    for _, row in type_summary.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[0, row["平均誤點"]],
                y=[row["TrainType"], row["TrainType"]],
                mode="lines",
                line=dict(color="rgba(158,176,196,0.26)", width=4),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=type_summary["平均誤點"],
            y=type_summary["TrainType"],
            mode="markers+text",
            marker=dict(size=14, color=colors, line=dict(width=2, color=BG_COLOR())),
            text=type_summary["平均誤點"].round(2).astype(str) + " 分",
            textposition="middle right",
            textfont=dict(size=11, color=TEXT_SECONDARY),
            customdata=type_summary["準點率"].round(1),
            hovertemplate="<b>%{y}</b><br>平均誤點 %{x:.2f} 分<br>準點率 %{customdata:.1f}%<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=16, r=48, t=18, b=16)},
        height=300,
    )
    fig.update_xaxes(**AXIS_STYLE, title="平均誤點（分）", rangemode="tozero")
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _build_period_profile(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "Period" not in df.columns:
        return None
    period_summary = (
        df.groupby("Period")
        .agg(準點率=("IsDelayed", lambda x: round((1 - x.mean()) * 100, 1)), 平均誤點=("DelayTime", "mean"))
        .reset_index()
    )
    if period_summary.empty:
        return None

    order = ["深夜", "離峰", "尖峰"]
    period_summary["Period"] = pd.Categorical(period_summary["Period"], categories=order, ordered=True)
    period_summary = period_summary.sort_values("Period")
    fig = go.Figure(
        go.Bar(
            x=period_summary["Period"],
            y=period_summary["準點率"],
            marker=dict(
                color=[GREEN if v >= 95 else BLUE if v >= 90 else YELLOW for v in period_summary["準點率"]],
                line=dict(width=0),
            ),
            text=period_summary["準點率"].astype(str) + "%",
            textposition="outside",
            customdata=period_summary["平均誤點"].round(2),
            hovertemplate="<b>%{x}</b><br>準點率 %{y:.1f}%<br>平均誤點 %{customdata:.2f} 分<extra></extra>",
        )
    )
    fig.update_layout(**PLOTLY_THEME, height=300)
    fig.update_yaxes(**AXIS_STYLE, title="準點率 (%)", range=[80, 100])
    fig.update_xaxes(**AXIS_STYLE, title=None)
    return fig


def render(df, filtered_df=None, date_label="📅 全部日期", **kwargs):
    current_df = _safe_current_df(df, filtered_df)

    st.markdown(
        """
        <div class="hero">
            <div class="kicker">Rail Operations Research Board</div>
            <h1>台鐵列車誤點影響因素之量化分析</h1>
            <div class="subtitle">把全台列車停靠紀錄轉成可讀的營運趨勢、站點差異與研究線索</div>
            <div class="institution">政治大學 MEPA · 社會科學研究方法（一）期末報告</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if current_df.empty:
        st.warning("目前篩選範圍沒有資料。")
        return

    total = len(current_df)
    punctuality = round((1 - current_df["IsDelayed"].mean()) * 100, 1)
    avg_delay = round(current_df["DelayTime"].mean(), 2)
    max_delay = int(current_df["DelayTime"].max())
    days = int(current_df["Date"].nunique()) if "Date" in current_df.columns else 0

    st.caption(f"目前顯示範圍：{date_label}　共 {total:,} 筆觀測")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("觀測筆數", f"{total:,}", "blue", "班次 × 車站停靠紀錄")
    with c2:
        kpi_card("研究準點率", f"{punctuality}%", "green", "2 分鐘門檻")
    with c3:
        kpi_card("平均誤點", f"{avg_delay} 分", "yellow" if avg_delay >= 2 else "green")
    with c4:
        kpi_card("最大誤點", f"{max_delay} 分", "red", f"涵蓋 {days} 天")

    trend_col, insight_col = st.columns([1.7, 1.0], gap="large")
    with trend_col:
        section_title("全期間趨勢")
        trend_fig = _build_daily_trend_chart(
            df,
            selected_date=None if date_label == "📅 全部日期" else date_label.replace("📅 ", ""),
        )
        if trend_fig is not None:
            st.plotly_chart(trend_fig, use_container_width=True)
        st.caption("折線讀準點率，柱狀讀平均誤點。若目前鎖定單日，會在趨勢中標出位置。")

    worst_type = "—"
    worst_type_delay = 0.0
    if "TrainType" in current_df.columns:
        by_type = current_df.groupby("TrainType")["DelayTime"].mean().sort_values(ascending=False)
        if not by_type.empty:
            worst_type = str(by_type.index[0])
            worst_type_delay = float(by_type.iloc[0])

    weakest_period = "—"
    weakest_period_pct = 0.0
    if "Period" in current_df.columns:
        by_period = current_df.groupby("Period")["IsDelayed"].apply(lambda x: (1 - x.mean()) * 100).sort_values()
        if not by_period.empty:
            weakest_period = str(by_period.index[0])
            weakest_period_pct = float(by_period.iloc[0])

    focus_train_no = ""
    focus_train_date = ""
    focus_train_delay = 0.0
    if {"TrainNo", "DelayTime"}.issubset(current_df.columns):
        focus_row = current_df.sort_values("DelayTime", ascending=False).iloc[0]
        focus_train_no = str(focus_row.get("TrainNo") or "").strip()
        focus_train_date = str(focus_row.get("Date") or "").strip()
        focus_train_delay = float(focus_row.get("DelayTime") or 0)

    with insight_col:
        section_title("本次觀察")
        story_card(
            "目前範圍",
            f"{days} 天 / {total:,} 筆",
            "這組篩選代表目前所有圖表與排名的比較基準。",
            tone="blue",
        )
        story_card(
            "高風險車種",
            worst_type,
            f"在目前範圍內，平均誤點最高約 {worst_type_delay:.2f} 分。",
            tone="red" if worst_type_delay >= 4 else "yellow",
        )
        story_card(
            "最弱時段",
            weakest_period,
            f"該時段準點率約 {weakest_period_pct:.1f}%，值得優先交叉檢查路段與車種。",
            tone="yellow" if weakest_period_pct < 90 else "green",
        )
        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button("看高風險車種", key="home_go_type", use_container_width=True):
                goto_page(
                    "準點率分析",
                    filters={"train_type": worst_type} if worst_type != "—" else None,
                )
        with action_cols[1]:
            if st.button("看最弱時段", key="home_go_period", use_container_width=True):
                goto_page(
                    "準點率分析",
                    filters={"period": weakest_period} if weakest_period != "—" else None,
                )
        if focus_train_no and st.button(
            f"追最大延誤班次 {focus_train_no}",
            key="home_go_tracker",
            use_container_width=True,
            type="primary",
        ):
            goto_page(
                "車次追蹤",
                tracker_date=focus_train_date,
                tracker_train_no=focus_train_no,
            )
        st.caption(
            f"目前最大單筆延誤為 {focus_train_delay:.1f} 分，點上方可直接切去班次追蹤。"
            if focus_train_no else
            "目前範圍缺少可直接追蹤的班次資訊。"
        )

    chart_col, side_col = st.columns([1.25, 1.0], gap="large")
    with chart_col:
        section_title("車種平均誤點")
        fig = _build_train_type_lollipop(current_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        if st.button("在準點率分析中延伸檢查", key="home_go_punctuality", use_container_width=True):
            goto_page("準點率分析")
    with side_col:
        section_title("時段表現")
        fig = _build_period_profile(current_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        note_card(
            "讀圖方式",
            "首頁只保留最先要回答的問題：最近整體是否變差、哪個車種最不穩、哪個時段最容易出現延誤。",
        )
        if st.button("改看站點空間分布", key="home_go_heatmap", use_container_width=True):
            goto_page("站點熱力圖")

    lower_left, lower_right = st.columns([1.15, 0.85], gap="large")
    with lower_left:
        section_title("研究設計摘要")
        st.markdown(
            """
            <div class="compact-list">
                <div class="compact-item">
                    <div class="term">Y1</div>
                    <div class="desc">DelayTime：每班車在每個停靠站的實際誤點分鐘數。</div>
                </div>
                <div class="compact-item">
                    <div class="term">Y2</div>
                    <div class="desc">IsDelayed：依研究定義，超過 2 分鐘即視為誤點。</div>
                </div>
                <div class="compact-item">
                    <div class="term">X</div>
                    <div class="desc">車種、時段、假日、站序、前站誤點、方向、線別與站體規模。</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with lower_right:
        section_title("分析模組")
        st.markdown(
            method_step("01", "描述統計", "先看趨勢、比較與分布，確認延誤的基本輪廓。")
            + method_step("02", "空間檢視", "用站點熱力與路網圖找出誤點集中區。")
            + method_step("03", "模型解釋", "把延誤風險與嚴重度拆開估計，避免混讀。"),
            unsafe_allow_html=True,
        )
        module_cols = st.columns(3)
        with module_cols[0]:
            if st.button("看總覽", key="home_go_overview", use_container_width=True):
                goto_page("數據總覽")
        with module_cols[1]:
            if st.button("看熱力圖", key="home_go_heatmap2", use_container_width=True):
                goto_page("站點熱力圖")
        with module_cols[2]:
            if st.button("跑模型", key="home_go_reg", use_container_width=True):
                goto_page("OLS 迴歸")
