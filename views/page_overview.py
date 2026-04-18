"""
資料總覽 — 五年樣本結構
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, COLORS
from views.components import kpi_card, section_title


def render(ctx: dict) -> None:
    perceived = ctx["perceived"]
    official = ctx["official"]

    if perceived is None or perceived.empty:
        st.info("目前篩選條件下沒有資料，請調整全域篩選。")
        return

    section_title("各年觀測數")
    cols = st.columns(4)
    with cols[0]:
        kpi_card("B 感知觀測", f"{len(perceived):,}", color="green")
    with cols[1]:
        kpi_card("A 官方車次", f"{len(official):,}", color="blue")
    with cols[2]:
        kpi_card("獨立車次", f"{perceived['TrainNo'].nunique():,}")
    with cols[3]:
        kpi_card("涵蓋車站", f"{perceived['StationID'].nunique():,}")

    by_year = (
        perceived.groupby("年", observed=True)
        .size()
        .reset_index(name="觀測數")
        .sort_values("年")
    )
    fig = px.bar(
        by_year,
        x="年",
        y="觀測數",
        text="觀測數",
        color_discrete_sequence=[BLUE],
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(title="各年 B 感知觀測數", **PLOTLY_THEME)
    fig.update_xaxes(**AXIS_STYLE, type="category")
    fig.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    section_title("春節節點 × 年 分布")
    cross = (
        perceived.groupby(["年", "春節節點"], observed=True)
        .size()
        .reset_index(name="觀測數")
    )
    fig2 = px.bar(
        cross,
        x="年",
        y="觀測數",
        color="春節節點",
        barmode="stack",
        color_discrete_sequence=COLORS,
    )
    fig2.update_layout(**PLOTLY_THEME, legend=dict(orientation="h", y=-0.2))
    fig2.update_xaxes(**AXIS_STYLE, type="category")
    fig2.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig2, use_container_width=True)

    left, right = st.columns(2)
    with left:
        section_title("車種分布")
        tt = perceived["車種"].value_counts().reset_index()
        tt.columns = ["車種", "觀測數"]
        fig3 = px.bar(tt, x="觀測數", y="車種", orientation="h", color_discrete_sequence=[GREEN])
        fig3.update_layout(**PLOTLY_THEME, height=360)
        fig3.update_xaxes(**AXIS_STYLE)
        fig3.update_yaxes(**AXIS_STYLE, categoryorder="total ascending")
        st.plotly_chart(fig3, use_container_width=True)

    with right:
        section_title("路線區段分布")
        rr = perceived["路線區段"].value_counts().reset_index()
        rr.columns = ["路線區段", "觀測數"]
        fig4 = px.bar(rr, x="觀測數", y="路線區段", orientation="h", color_discrete_sequence=[BLUE])
        fig4.update_layout(**PLOTLY_THEME, height=360)
        fig4.update_xaxes(**AXIS_STYLE)
        fig4.update_yaxes(**AXIS_STYLE, categoryorder="total ascending")
        st.plotly_chart(fig4, use_container_width=True)

    section_title("樣本交叉表（年 × 春節節點）")
    pivot = (
        perceived.pivot_table(
            index="年", columns="春節節點", values="TrainNo", aggfunc="count", fill_value=0
        )
        .reset_index()
    )
    st.dataframe(pivot, use_container_width=True, hide_index=True)
