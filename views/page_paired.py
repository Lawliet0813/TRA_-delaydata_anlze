"""
配對 t 檢定 — A 末站延誤 vs B 全程平均延誤
"""
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW
from views.components import kpi_card, note_card, section_title


def render(ctx: dict) -> None:
    inf = ctx["inferential"]
    paired = inf.get("paired_AB", {})

    st.markdown(
        '<div class="note-card"><div class="title">注意</div>'
        '<div class="body">本頁為五年全體配對結果，不受全域篩選影響。</div></div>',
        unsafe_allow_html=True,
    )

    if not paired:
        st.info("無配對 t 結果。")
        return

    section_title("配對 t 檢定結果")
    cols = st.columns(4)
    with cols[0]:
        kpi_card("配對樣本數", f"{paired.get('配對數', 0):,}")
    with cols[1]:
        kpi_card("A 末站均值", f"{paired.get('A_均值', 0):.3f} 分鐘", color="blue")
    with cols[2]:
        kpi_card("B 全程均值", f"{paired.get('B_均值', 0):.3f} 分鐘", color="green")
    with cols[3]:
        kpi_card("A − B 差", f"+{paired.get('差_均值', 0):.3f} 分鐘", color="yellow")

    cols2 = st.columns(3)
    with cols2[0]:
        kpi_card("t 統計量", f"{paired.get('t', 0):.2f}")
    with cols2[1]:
        p = paired.get("p", 1)
        kpi_card("p 值", "<1e-6" if p < 1e-6 else f"{p:.2e}", color="red")
    with cols2[2]:
        kpi_card("差之標準差", f"{paired.get('差_SD', 0):.3f}")

    section_title("兩指標均值對照")
    fig = go.Figure(
        go.Bar(
            x=["A 末站（官方 proxy）", "B 全程平均（感知）"],
            y=[paired.get("A_均值", 0), paired.get("B_均值", 0)],
            text=[f"{paired.get('A_均值', 0):.3f}", f"{paired.get('B_均值', 0):.3f}"],
            marker_color=[BLUE, GREEN],
        )
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**PLOTLY_THEME, height=340, yaxis_title="平均誤點（分鐘）")
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    note_card(
        "解讀",
        paired.get("解讀", "")
        + "　此結果支持『官方終點站口徑會系統性放大誤點感受』的論述：同一車次，末站延誤普遍比全程平均多 0.49 分鐘。",
    )
