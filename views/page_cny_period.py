"""
春節節點比較 — 六個節點（除夕前 / 除夕前夕 / 除夕 / 初一~三 / 初四~六 / 初七+）
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cny_processor import CNY_PERIOD_ORDER
from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED, COLORS
from views.components import kpi_card, note_card, section_title


def render(ctx: dict) -> None:
    perceived = ctx["perceived"]

    if perceived is None or perceived.empty:
        st.info("目前篩選條件下沒有資料。")
        return

    summary = (
        perceived.groupby("春節節點", observed=True)["延誤分鐘"]
        .agg(["mean", "median", "size"])
        .rename(columns={"mean": "平均", "median": "中位數", "size": "樣本數"})
        .reset_index()
    )
    summary["春節節點"] = pd.Categorical(summary["春節節點"], categories=CNY_PERIOD_ORDER, ordered=True)
    summary = summary.sort_values("春節節點").reset_index(drop=True)

    section_title("六節點平均誤點")
    fig = px.bar(
        summary,
        x="春節節點",
        y="平均",
        color="春節節點",
        text="平均",
        color_discrete_sequence=COLORS,
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(**PLOTLY_THEME, height=440, showlegend=False, yaxis_title="平均誤點（分鐘）")
    fig.update_xaxes(**AXIS_STYLE, categoryorder="array", categoryarray=CNY_PERIOD_ORDER)
    fig.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    # KPI
    peak = summary.loc[summary["平均"].idxmax()]
    low = summary.loc[summary["平均"].idxmin()]
    cols = st.columns(3)
    with cols[0]:
        kpi_card("最尖峰節點", str(peak["春節節點"]), color="red", sub=f"{peak['平均']:.2f} 分鐘")
    with cols[1]:
        kpi_card("最平穩節點", str(low["春節節點"]), color="green", sub=f"{low['平均']:.2f} 分鐘")
    with cols[2]:
        kpi_card("尖峰－平穩差距", f"{peak['平均'] - low['平均']:.2f} 分鐘")

    # Boxplot（用抽樣避免太慢）
    section_title("誤點分布（抽樣 5 萬筆）")
    sample = perceived.sample(n=min(50000, len(perceived)), random_state=42)
    fig2 = px.box(
        sample,
        x="春節節點",
        y="延誤分鐘",
        color="春節節點",
        color_discrete_sequence=COLORS,
        points=False,
    )
    fig2.update_layout(**PLOTLY_THEME, height=420, showlegend=False, yaxis_title="誤點（分鐘）")
    fig2.update_xaxes(**AXIS_STYLE, categoryorder="array", categoryarray=CNY_PERIOD_ORDER)
    fig2.update_yaxes(**AXIS_STYLE, range=[-5, 25])
    st.plotly_chart(fig2, use_container_width=True)

    # 交叉：年 × 節點
    section_title("年 × 節點 平均誤點熱表")
    heat = (
        perceived.groupby(["年", "春節節點"], observed=True)["延誤分鐘"]
        .mean()
        .reset_index()
    )
    heat_pivot = heat.pivot(index="年", columns="春節節點", values="延誤分鐘")
    heat_pivot = heat_pivot.reindex(columns=CNY_PERIOD_ORDER)
    fig3 = go.Figure(
        data=go.Heatmap(
            z=heat_pivot.values,
            x=heat_pivot.columns,
            y=heat_pivot.index.astype(str),
            colorscale=[[0, GREEN], [0.5, YELLOW], [1, RED]],
            colorbar=dict(title="平均分"),
            text=[[f"{v:.2f}" if pd.notna(v) else "" for v in row] for row in heat_pivot.values],
            texttemplate="%{text}",
        )
    )
    fig3.update_layout(**PLOTLY_THEME, height=400)
    fig3.update_xaxes(**AXIS_STYLE)
    fig3.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig3, use_container_width=True)

    section_title("明細表")
    display = summary.copy()
    display["平均"] = display["平均"].round(3)
    display["中位數"] = display["中位數"].round(3)
    st.dataframe(display, use_container_width=True, hide_index=True)

    note_card(
        "觀察",
        "除夕前夕（除夕前 1–2 天）為五年一致的最尖峰節點。Tukey HSD 事後檢定顯示該節點與其餘五節點的兩兩差異皆達 p<.001。",
    )
