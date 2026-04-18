"""
ANOVA 與卡方：年份 × 誤點 / 準點
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED
from views.components import kpi_card, note_card, section_title


def _fmt_p(p):
    if p is None:
        return "—"
    if p < 1e-6:
        return f"<1e-6"
    return f"{p:.2e}"


def render(ctx: dict) -> None:
    inf = ctx["inferential"]

    st.markdown(
        '<div class="note-card"><div class="title">注意</div>'
        '<div class="body">本頁數值為五年全體推論結果，不受全域篩選影響。</div></div>',
        unsafe_allow_html=True,
    )

    # ── ANOVA：年份 × 延誤分鐘 ─────────────────────
    section_title("ANOVA：年份對平均誤點（官方 / 感知）")
    anova_a = inf.get("anova_year_delay_official", {})
    anova_b = inf.get("anova_year_delay_perceived", {})

    cols = st.columns(2)
    with cols[0]:
        kpi_card(
            "A 官方 proxy",
            f"F={anova_a.get('F', 0):.2f}",
            color="blue",
            sub=f"p = {_fmt_p(anova_a.get('p'))}",
        )
    with cols[1]:
        kpi_card(
            "B 旅客感知",
            f"F={anova_b.get('F', 0):.2f}",
            color="green",
            sub=f"p = {_fmt_p(anova_b.get('p'))}",
        )

    def _means_fig(means: dict, title: str, color: str):
        if not means:
            return None
        s = pd.Series(means).sort_index()
        fig = go.Figure(
            go.Bar(
                x=s.index.astype(str), y=s.values, text=[f"{v:.2f}" for v in s.values],
                marker_color=color,
            )
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**PLOTLY_THEME, height=340, title=title, yaxis_title="平均誤點（分鐘）")
        fig.update_xaxes(**AXIS_STYLE, type="category")
        fig.update_yaxes(**AXIS_STYLE)
        return fig

    left, right = st.columns(2)
    with left:
        fig_a = _means_fig(anova_a.get("各年平均", {}), "A 官方 — 各年平均誤點", BLUE)
        if fig_a:
            st.plotly_chart(fig_a, use_container_width=True)
    with right:
        fig_b = _means_fig(anova_b.get("各年平均", {}), "B 感知 — 各年平均誤點", GREEN)
        if fig_b:
            st.plotly_chart(fig_b, use_container_width=True)

    note_card(
        "ANOVA 判讀",
        "兩指標 F 值皆顯著（p<.001），代表五年平均誤點存在差異；視覺化均指向 2025 為異常峰值。",
    )

    # ── 卡方：年份 × 準點 ─────────────────────────
    section_title("卡方：年份 × 準點是否")
    chi_official = inf.get("chi2_year_ontime_official", {})
    chi_b5 = inf.get("chi2_year_ontime_perceived_5", {})
    chi_b3 = inf.get("chi2_year_ontime_perceived_3", {})

    rows = st.columns(3)
    with rows[0]:
        kpi_card(
            "A 官方 5 分",
            f"χ²={chi_official.get('chi2', 0):.1f}",
            color="blue",
            sub=f"df={chi_official.get('dof', 0)}, p={_fmt_p(chi_official.get('p'))}",
        )
    with rows[1]:
        kpi_card(
            "B 感知 5 分",
            f"χ²={chi_b5.get('chi2', 0):.1f}",
            color="green",
            sub=f"df={chi_b5.get('dof', 0)}, p={_fmt_p(chi_b5.get('p'))}",
        )
    with rows[2]:
        kpi_card(
            "B 感知 3 分",
            f"χ²={chi_b3.get('chi2', 0):.1f}",
            color="",
            sub=f"df={chi_b3.get('dof', 0)}, p={_fmt_p(chi_b3.get('p'))}",
        )

    # 交叉表
    def _table_df(chi: dict, label: str):
        tbl = chi.get("table", {})
        if not tbl:
            return None
        rows_dict = {}
        for outcome, years_dict in tbl.items():
            for y, cnt in years_dict.items():
                rows_dict.setdefault(str(y), {})[str(outcome)] = cnt
        df = pd.DataFrame(rows_dict).T.reset_index().rename(columns={"index": "年"})
        df.columns = ["年", "準點" if "True" in df.columns else df.columns[1], "誤點" if "False" in df.columns else df.columns[2]]
        return df

    tab1, tab2, tab3 = st.tabs(["A 官方 5 分", "B 感知 5 分", "B 感知 3 分"])
    for tab, chi, label in [
        (tab1, chi_official, "A 官方 5 分"),
        (tab2, chi_b5, "B 感知 5 分"),
        (tab3, chi_b3, "B 感知 3 分"),
    ]:
        with tab:
            tbl = chi.get("table", {})
            if not tbl:
                st.write("無資料")
                continue
            rows_list = []
            for outcome, years_dict in tbl.items():
                label_name = "準點" if outcome == "True" else "誤點"
                for y, cnt in years_dict.items():
                    rows_list.append({"年": int(y), "狀態": label_name, "筆數": cnt})
            df = pd.DataFrame(rows_list)
            pivot = df.pivot_table(index="年", columns="狀態", values="筆數", fill_value=0)
            pivot["準點率"] = pivot["準點"] / (pivot["準點"] + pivot["誤點"])
            st.dataframe(
                pivot.reset_index().style.format({"準點率": "{:.2%}", "準點": "{:,}", "誤點": "{:,}"}),
                use_container_width=True,
                hide_index=True,
            )
