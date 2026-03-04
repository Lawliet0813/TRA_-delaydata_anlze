"""
數據總覽 (Data Overview) — KPIs + Charts + Trends
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from views.theme import PLOTLY_THEME, AXIS_STYLE, COLORS, BLUE, GREEN, TEXT_SECONDARY
from views.components import page_header, kpi_card, section_title


def render(df, filtered_df, date_label, **kwargs):
    page_header("◈", "數據總覽", "全台列車誤點基礎統計 · Descriptive Statistics")

    _ddf = filtered_df
    st.caption(f"目前顯示範圍：{date_label}　共 {len(_ddf):,} 筆觀測")

    if _ddf.empty:
        st.warning("此日期無資料，請重新選擇。")
        return

    # ── KPI Row ───────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("觀測筆數", f"{len(_ddf):,}", "blue")
    with c2:
        kpi_card("準點率", f"{round((1-_ddf['IsDelayed'].mean())*100,1)}%", "green")
    with c3:
        avg_d = round(_ddf["DelayTime"].mean(), 2)
        kpi_card("平均誤點", f"{avg_d} min", "yellow" if avg_d > 1 else "green")
    with c4:
        kpi_card("最大誤點", f"{int(_ddf['DelayTime'].max())} min", "red")
    with c5:
        kpi_card("資料天數", f"{_ddf['Date'].nunique()} 天")

    with st.expander("📊 指標說明"):
        st.markdown("""
        | 指標 | 計算方式 | 備註 |
        |------|----------|------|
        | **觀測筆數** | 一班次在一個車站的到站紀錄 | TDX `StationLiveBoard` 每 10 分鐘抓取 |
        | **準點率** | `(1 − IsDelayed.mean()) × 100%` | `IsDelayed = 1` 當 `DelayTime ≥ 2分鐘` |
        | **平均誤點** | `DelayTime` 算術平均（含 0 分鐘） | 單位：分鐘 |
        | **最大誤點** | `DelayTime` 最大值 | 單位：分鐘 |
        | **資料天數** | `Date` 不重複日期數 | |
        """)

    st.markdown("---")

    # ── 2×2 Chart Grid ────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        section_title("各車種平均誤點")
        type_d = _ddf.groupby("TrainType")["DelayTime"].mean().sort_values(ascending=True).reset_index()
        fig = go.Figure(go.Bar(
            x=type_d["DelayTime"], y=type_d["TrainType"],
            orientation="h",
            marker=dict(
                color=type_d["DelayTime"],
                colorscale=[[0, GREEN], [0.5, "#f59e0b"], [1, "#ef4444"]],
                showscale=False,
                line=dict(width=0),
            ),
            text=type_d["DelayTime"].round(2).astype(str) + " min",
            textposition="outside",
            textfont=dict(size=11, color=TEXT_SECONDARY),
        ))
        fig.update_layout(**PLOTLY_THEME, height=260,
                          xaxis=dict(**AXIS_STYLE, title="平均誤點（分鐘）"),
                          yaxis=dict(**AXIS_STYLE))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 說明", key="exp_traintype"):
            st.markdown("""
            依 `TrainType` 分組取 `DelayTime` 算術平均。
            顏色漸層：🟢 低誤點 → 🟡 中 → 🔴 高。
            停靠站越多的車種累積誤點機會較高。
            """)

    with col_b:
        section_title("各時段準點率")
        if "Period" in _ddf.columns:
            period_d = _ddf.groupby("Period")["IsDelayed"].apply(
                lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率")
            order = ["深夜", "離峰", "尖峰"]
            period_d["Period"] = pd.Categorical(period_d["Period"], categories=order, ordered=True)
            period_d = period_d.sort_values("Period")
            fig = go.Figure(go.Bar(
                x=period_d["Period"], y=period_d["準點率"],
                marker=dict(
                    color=[GREEN, BLUE, "#f59e0b"],
                    line=dict(width=0),
                ),
                text=period_d["準點率"].astype(str) + "%",
                textposition="outside",
                textfont=dict(size=12, color=TEXT_SECONDARY),
            ))
            fig.update_layout(**PLOTLY_THEME, height=260,
                              yaxis=dict(**AXIS_STYLE, range=[85, 100], title="準點率 (%)"),
                              xaxis=dict(**AXIS_STYLE))
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📊 說明", key="exp_period"):
                st.markdown("""
                **時段分類**（依 `ScheduledArr`）：
                - **尖峰**：06:00–09:00 及 17:00–20:00
                - **深夜**：00:00–06:00
                - **離峰**：其餘時段
                """)

    st.markdown("---")
    col_c, col_d = st.columns(2, gap="large")

    with col_c:
        section_title("誤點分鐘數分布")
        delay_clip = _ddf[_ddf["DelayTime"] <= 30]["DelayTime"]
        fig = go.Figure(go.Histogram(
            x=delay_clip, nbinsx=30,
            marker=dict(color=BLUE, line=dict(width=0)),
            opacity=0.85,
        ))
        fig.update_layout(**PLOTLY_THEME, height=240,
                          xaxis=dict(**AXIS_STYLE, title="誤點分鐘（截至30分）"),
                          yaxis=dict(**AXIS_STYLE, title="筆數"))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 說明", key="exp_histogram"):
            st.markdown("""
            為避免極端值壓縮圖形，截斷顯示 ≤ 30 分鐘。
            分布高度右偏為台鐵誤點資料的典型型態。
            """)

    with col_d:
        section_title("假日 vs 平日")
        if "HolidayType" in _ddf.columns:
            hol_d = _ddf.groupby("HolidayType").agg(
                準點率=("IsDelayed", lambda x: round((1-x.mean())*100, 1)),
                平均誤點=("DelayTime", lambda x: round(x.mean(), 2)),
                筆數=("IsDelayed", "count")
            ).reset_index()
            st.dataframe(
                hol_d.style.format({"準點率": "{:.1f}%", "平均誤點": "{:.2f} min", "筆數": "{:,}"}),
                use_container_width=True, hide_index=True
            )
            with st.expander("📊 說明", key="exp_holiday"):
                st.markdown("""
                `HolidayType` 細分：**平日** / **週末** / **國定假日**。
                連假旅運量增加可能延長站停時間。
                """)

    # ── Daily Trend（固定顯示全量，並標示目前選取日期） ────────
    st.markdown("---")
    section_title("逐日準點率趨勢　　⚠ 此圖固定顯示全部日期")
    daily = df.groupby("Date")["IsDelayed"].apply(
        lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["Date"], y=daily["準點率"],
        mode="lines+markers",
        line=dict(color=BLUE, width=2.5),
        marker=dict(size=6, color=BLUE),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.06)",
        name="全部日期",
    ))
    # 若有篩選日期，在該日加入標記
    sel_daily = _ddf.groupby("Date")["IsDelayed"].apply(
        lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率")
    if len(sel_daily) < len(daily):
        fig.add_trace(go.Scatter(
            x=sel_daily["Date"], y=sel_daily["準點率"],
            mode="markers",
            marker=dict(size=11, color="#f59e0b", symbol="diamond",
                        line=dict(width=2, color="#0a0e14")),
            name=f"篩選中：{date_label}",
        ))
    fig.update_layout(**PLOTLY_THEME, height=220,
                      yaxis=dict(**AXIS_STYLE, range=[85, 100], title="準點率 (%)"),
                      xaxis=dict(**AXIS_STYLE),
                      legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("※ 折線固定顯示全部日期趨勢；若已選取特定日期，黃色菱形標示該日位置。")
