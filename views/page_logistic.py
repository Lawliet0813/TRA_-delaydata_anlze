"""
Logistic 迴歸 — 年 × 春節節點 × 車種 × 路線 對準點的獨立效果
"""
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, RED, TEXT_MUTED
from views.components import kpi_card, note_card, section_title


def render(ctx: dict) -> None:
    inf = ctx["inferential"]
    logistic = inf.get("logistic_official", {})

    st.markdown(
        '<div class="note-card"><div class="title">注意</div>'
        '<div class="body">模型以五年全體 A 官方 proxy 資料訓練，不受全域篩選影響。</div></div>',
        unsafe_allow_html=True,
    )

    if not logistic:
        st.info("找不到 Logistic 結果。")
        return

    section_title("模型指標")
    cols = st.columns(3)
    with cols[0]:
        kpi_card("樣本數", f"{logistic.get('樣本數', 0):,}")
    with cols[1]:
        kpi_card("Pseudo R²", f"{logistic.get('pseudo_R2', 0):.4f}", color="blue")
    with cols[2]:
        kpi_card("Log-Likelihood", f"{logistic.get('LL', 0):,.1f}")

    # 整理係數表
    coefs = logistic.get("coefs", [])
    if not coefs:
        st.info("無係數資料。")
        return

    df = pd.DataFrame(coefs)
    df = df[df["變項"] != "Intercept"].copy()

    # 分類：類型前綴
    def classify(name: str) -> str:
        if name.startswith("C(年)"):
            return "年份"
        if name.startswith("C(春節節點)"):
            return "春節節點"
        if name.startswith("C(車種)"):
            return "車種"
        if name.startswith("C(路線)"):
            return "路線"
        return "其他"

    df["類別"] = df["變項"].map(classify)
    df["乾淨名稱"] = df["變項"].str.replace(r"^C\([^)]+\)\[T\.|\]$", "", regex=True)

    section_title("Odds Ratio 森林圖（95% CI）")
    df_ok = df.dropna(subset=["OR", "p"]).copy()
    df_ok["log_OR"] = df_ok["OR"].apply(math.log)
    df_ok["lower_log"] = df_ok["CI95_下"].apply(lambda v: math.log(v) if pd.notna(v) and v > 0 else None)
    df_ok["upper_log"] = df_ok["CI95_上"].apply(lambda v: math.log(v) if pd.notna(v) and v > 0 else None)
    df_ok = df_ok.sort_values(["類別", "OR"])

    colors = [RED if row["OR"] < 1 and row["p"] < 0.05 else GREEN if row["OR"] > 1 and row["p"] < 0.05 else TEXT_MUTED for _, row in df_ok.iterrows()]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_ok["OR"],
            y=df_ok["乾淨名稱"] + "（" + df_ok["類別"] + "）",
            mode="markers",
            marker=dict(color=colors, size=11, line=dict(color="white", width=1)),
            error_x=dict(
                type="data",
                symmetric=False,
                array=df_ok["CI95_上"] - df_ok["OR"],
                arrayminus=df_ok["OR"] - df_ok["CI95_下"],
                color=TEXT_MUTED,
            ),
            text=[
                f"OR={o:.3f}, p={p:.3g}" for o, p in zip(df_ok["OR"], df_ok["p"])
            ],
            hovertemplate="%{y}<br>%{text}<extra></extra>",
        )
    )
    fig.add_vline(x=1, line_dash="dash", line_color=TEXT_MUTED)
    fig.update_layout(
        **PLOTLY_THEME,
        height=max(600, len(df_ok) * 26),
        xaxis_title="Odds Ratio（對比參考組）",
        xaxis_type="log",
    )
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    section_title("係數明細")
    display = df[["類別", "乾淨名稱", "coef", "OR", "CI95_下", "CI95_上", "p"]].copy()
    display.columns = ["類別", "變項", "β", "OR", "CI95 下", "CI95 上", "p"]
    for col in ["β", "OR", "CI95 下", "CI95 上"]:
        display[col] = pd.to_numeric(display[col], errors="coerce").round(4)
    display["p"] = display["p"].apply(lambda p: "—" if pd.isna(p) else ("<1e-6" if p < 1e-6 else f"{p:.3g}"))
    st.dataframe(display, use_container_width=True, hide_index=True)

    note_card(
        "解讀",
        "OR > 1 且 p<.05：相較參考組，該類別的準點機率較高（綠點）；"
        "OR < 1 且 p<.05：準點機率較低（紅點）。"
        "在控制其他變項後，2025 年（OR=0.65）與除夕前夕（OR=0.52）兩者對準點有顯著負向效果，"
        "而 2023、2024、2026 三年相對 2022 基準年皆有較佳表現。",
    )
    note_card(
        "關於「貨物列車」係數",
        "貨物列車（7 字頭）最高速 60 km/h，車種效應的 OR 高低不應直接與旅客列車並列比較；"
        "高 OR 未必代表運營表現佳，而可能反映其低速但班次少、衝突機率低。"
        "若要單看旅客列車，可於全域篩選器排除「貨物列車」。",
    )
