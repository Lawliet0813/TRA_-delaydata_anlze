"""
Tukey HSD — 春節節點兩兩比較森林圖
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, GREEN, RED, TEXT_MUTED
from views.components import kpi_card, note_card, section_title


def render(ctx: dict) -> None:
    inf = ctx["inferential"]
    tukey = inf.get("tukey_period_delay", {})
    pairs = tukey.get("pairs", [])

    st.markdown(
        '<div class="note-card"><div class="title">注意</div>'
        f'<div class="body">Tukey HSD 以抽樣 {tukey.get("樣本數", 0):,} 筆進行，為五年合併結果，不受全域篩選影響。</div></div>',
        unsafe_allow_html=True,
    )

    if not pairs:
        st.info("無 Tukey 結果。")
        return

    section_title("兩兩比較森林圖")
    df = pd.DataFrame(pairs)
    df["pair"] = df["group1"] + "  vs  " + df["group2"]
    df = df.sort_values("meandiff")

    colors = [RED if bool(r) else TEXT_MUTED for r in df["reject"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["meandiff"],
            y=df["pair"],
            mode="markers",
            marker=dict(color=colors, size=12, line=dict(color="white", width=1)),
            error_x=dict(
                type="data",
                symmetric=False,
                array=df["upper"] - df["meandiff"],
                arrayminus=df["meandiff"] - df["lower"],
                color=TEXT_MUTED,
            ),
            text=[
                f"Δ={m:.3f}, p={p:.3g}" for m, p in zip(df["meandiff"], df["p_adj"])
            ],
            hovertemplate="%{y}<br>%{text}<extra></extra>",
            name="meandiff",
        )
    )
    fig.add_vline(x=0, line_dash="dash", line_color=TEXT_MUTED)
    fig.update_layout(
        **PLOTLY_THEME,
        height=max(500, len(df) * 28),
        xaxis_title="平均誤點差（分鐘，group2 − group1）",
    )
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    sig = df[df["reject"]]
    cols = st.columns(3)
    with cols[0]:
        kpi_card("兩兩比較總數", f"{len(df)} 組")
    with cols[1]:
        kpi_card("達顯著差異", f"{len(sig)} 組", color="red", sub="p<.05")
    with cols[2]:
        kpi_card("不顯著", f"{len(df) - len(sig)} 組", color="")

    section_title("明細表")
    display = df[["pair", "meandiff", "lower", "upper", "p_adj", "reject"]].copy()
    display.columns = ["比較組", "平均差", "CI 下", "CI 上", "校正 p", "拒絕 H0"]
    display["平均差"] = display["平均差"].round(3)
    display["CI 下"] = display["CI 下"].round(3)
    display["CI 上"] = display["CI 上"].round(3)
    display["校正 p"] = display["校正 p"].apply(lambda p: f"{p:.3g}")
    st.dataframe(display, use_container_width=True, hide_index=True)

    note_card(
        "解讀",
        "紅點為顯著差異（p<.05）。除夕前夕（-2 ~ -1 天）相對其他五節點皆顯著升高 1.1–1.9 分鐘。"
        "除夕與收假日、春節後三者之間則無顯著差異。",
    )
