"""
年度誤點趨勢 — A 官方 vs B 感知 雙指標五年走勢
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED
from views.components import kpi_card, note_card, section_title


def render(ctx: dict) -> None:
    perceived = ctx["perceived"]
    official = ctx["official"]

    if perceived is None or perceived.empty:
        st.info("目前篩選條件下沒有資料。")
        return

    # 年度平均誤點（A / B）
    b_by_year = perceived.groupby("年", observed=True)["延誤分鐘"].mean().reset_index()
    b_by_year.columns = ["年", "B_感知均值"]
    a_by_year = (
        official.groupby("年", observed=True)["終點站延誤分鐘"].mean().reset_index()
        if official is not None and not official.empty else pd.DataFrame(columns=["年", "A_官方均值"])
    )
    a_by_year.columns = ["年", "A_官方均值"]
    merged = b_by_year.merge(a_by_year, on="年", how="outer").sort_values("年")

    section_title("年度平均誤點（A vs B）")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=merged["年"], y=merged["A_官方均值"], mode="lines+markers",
            name="A 官方 proxy（終點站）", line=dict(color=BLUE, width=3), marker=dict(size=10),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=merged["年"], y=merged["B_感知均值"], mode="lines+markers",
            name="B 旅客感知（全程）", line=dict(color=GREEN, width=3), marker=dict(size=10),
        )
    )
    fig.update_layout(
        **PLOTLY_THEME,
        height=420,
        yaxis_title="平均誤點（分鐘）",
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_xaxes(**AXIS_STYLE, type="category")
    fig.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    # KPI
    peak = merged.loc[merged["B_感知均值"].idxmax()]
    low = merged.loc[merged["B_感知均值"].idxmin()]
    cols = st.columns(3)
    with cols[0]:
        kpi_card("最惡年（B）", f"{int(peak['年'])} 年", color="red", sub=f"{peak['B_感知均值']:.2f} 分鐘")
    with cols[1]:
        kpi_card("最佳年（B）", f"{int(low['年'])} 年", color="green", sub=f"{low['B_感知均值']:.2f} 分鐘")
    with cols[2]:
        kpi_card("五年全體均值（B）", f"{perceived['延誤分鐘'].mean():.2f} 分鐘")

    # 準點率（5 分鐘）
    section_title("年度準點率（5 分鐘閾值）")
    b_rate = perceived.groupby("年", observed=True)["延誤分鐘"].apply(lambda s: (s <= 5).mean()).reset_index()
    b_rate.columns = ["年", "B_準點率_5分"]
    if official is not None and not official.empty:
        a_rate = official.groupby("年", observed=True)["終點站延誤分鐘"].apply(lambda s: (s <= 5).mean()).reset_index()
        a_rate.columns = ["年", "A_準點率_5分"]
        rate_merged = b_rate.merge(a_rate, on="年", how="outer").sort_values("年")
    else:
        rate_merged = b_rate.sort_values("年")
        rate_merged["A_準點率_5分"] = None

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=rate_merged["年"], y=rate_merged["A_準點率_5分"], name="A 官方 5 分", marker_color=BLUE))
    fig2.add_trace(go.Bar(x=rate_merged["年"], y=rate_merged["B_準點率_5分"], name="B 感知 5 分", marker_color=GREEN))
    fig2.update_layout(**PLOTLY_THEME, barmode="group", height=380, yaxis_title="準點率", legend=dict(orientation="h", y=-0.2))
    fig2.update_xaxes(**AXIS_STYLE, type="category")
    fig2.update_yaxes(**AXIS_STYLE, tickformat=".1%")
    st.plotly_chart(fig2, use_container_width=True)

    section_title("明細表")
    display = merged.copy()
    display["A_官方均值"] = display["A_官方均值"].round(3)
    display["B_感知均值"] = display["B_感知均值"].round(3)
    display = display.merge(rate_merged, on="年", how="left")
    st.dataframe(display, use_container_width=True, hide_index=True)

    note_card(
        "觀察重點",
        "2025 年為五年中最嚴重異常（B 感知均值 3.59 分鐘、A 官方 3.71 分鐘）；"
        "其餘四年多落在 1.3–2.1 分鐘區間。對應實際事件，該年適逢 1 月花蓮地震與春節期間運量壓力疊加。",
    )
