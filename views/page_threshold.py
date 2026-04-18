"""
閾值敏感度 — 1/3/5/10 分鐘下 A / B 準點率差異
"""
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED
from views.components import note_card, section_title


def render(ctx: dict) -> None:
    df = ctx["threshold"]
    if df is None or df.empty:
        st.info("找不到 threshold_sensitivity.csv。")
        return

    section_title("A 官方 vs B 感知（各閾值）")
    # 先單獨畫合併列
    combined = df[df["年"].astype(str) == "合併"]
    per_year = df[df["年"].astype(str) != "合併"].copy()
    per_year["年"] = per_year["年"].astype(int)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=combined["閾值分鐘"], y=combined["A_官方proxy"],
            name="A 官方（合併）", mode="lines+markers",
            line=dict(color=BLUE, width=3), marker=dict(size=10),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=combined["閾值分鐘"], y=combined["B_感知"],
            name="B 感知（合併）", mode="lines+markers",
            line=dict(color=GREEN, width=3), marker=dict(size=10),
        )
    )
    fig.update_layout(
        **PLOTLY_THEME, height=420,
        xaxis_title="閾值（分鐘）", yaxis_title="準點率",
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_xaxes(**AXIS_STYLE, dtick=1)
    fig.update_yaxes(**AXIS_STYLE, tickformat=".1%")
    st.plotly_chart(fig, use_container_width=True)

    section_title("A - B 差異（逐年）")
    fig2 = go.Figure()
    for year in sorted(per_year["年"].unique()):
        sub = per_year[per_year["年"] == year]
        fig2.add_trace(
            go.Scatter(
                x=sub["閾值分鐘"], y=sub["A-B差"],
                mode="lines+markers", name=str(year),
            )
        )
    fig2.add_hline(y=0, line_dash="dash", line_color=YELLOW)
    fig2.update_layout(
        **PLOTLY_THEME, height=400,
        xaxis_title="閾值（分鐘）", yaxis_title="A − B（正 = A 較高）",
        legend=dict(orientation="h", y=-0.2),
    )
    fig2.update_xaxes(**AXIS_STYLE, dtick=1)
    fig2.update_yaxes(**AXIS_STYLE, tickformat=".3f")
    st.plotly_chart(fig2, use_container_width=True)

    section_title("逐列明細")
    st.dataframe(df, use_container_width=True, hide_index=True)

    note_card(
        "閱讀方式",
        "正號代表官方指標（終點站）顯示的準點率較高；負號代表旅客感知（全程平均）較寬鬆。"
        "差異絕對值普遍在 1% 以內，顯示兩指標在準點率整體水準上相當接近，但在誤點分鐘的分布上仍有顯著不同（詳見「配對 t 檢定」頁）。",
    )
