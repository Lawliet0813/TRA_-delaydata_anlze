"""
準點率分析 (Punctuality) — Dual Definition Comparison
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from views.theme import PLOTLY_THEME, AXIS_STYLE, COLORS, BLUE, GREEN, YELLOW, RED, TEXT_SECONDARY, TEXT_MUTED
from views.components import page_header, kpi_card, section_title


def render(df, filtered_df, date_label, schedule_df=None, **kwargs):
    page_header("◎", "準點率分析", "台鐵官方準點率 vs 本研究全站準點率 · 雙定義比較")

    _pdf = filtered_df
    st.caption(f"目前顯示範圍：{date_label}　共 {len(_pdf):,} 筆觀測")

    if _pdf.empty:
        st.warning("此日期無資料，請重新選擇。")
        return

    # ── Dual Punctuality KPIs ─────────────────────────────────
    terminal_df = _pdf[_pdf["IsTerminal"] == 1] if "IsTerminal" in _pdf.columns else pd.DataFrame()
    research_pct = round((1 - _pdf["IsDelayed"].mean()) * 100, 2)

    if not terminal_df.empty and "IsDelayed_Official" in terminal_df.columns:
        official_pct = round((1 - terminal_df["IsDelayed_Official"].mean()) * 100, 2)
    elif not terminal_df.empty:
        official_pct = round((1 - terminal_df["IsDelayed"].mean()) * 100, 2)
    else:
        official_pct = None
    diff = round(official_pct - research_pct, 2) if official_pct is not None else None

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card(
            "台鐵官方準點率",
            f"{official_pct}%" if official_pct is not None else "—",
            "green" if official_pct and official_pct > 90 else "yellow",
            "終點站 · τ = 5 分鐘"
        )
    with c2:
        kpi_card(
            "本研究全站準點率",
            f"{research_pct}%",
            "green" if research_pct > 85 else "yellow",
            "所有停靠站 · τ = 2 分鐘"
        )
    with c3:
        if diff is not None:
            kpi_card("兩者差距", f"{diff:+.2f}%", "blue",
                     "官方標準較寬鬆" if diff > 0 else "兩者相近")
        else:
            kpi_card("兩者差距", "—", sub="終點站資料不足")

    with st.expander("📊 兩種準點率計算方式說明"):
        st.markdown("""
        | 計算方式 | 判定方式 | 門檻 | 依據 |
        |----------|----------|------|----|
        | **台鐵官方** | 列車抵達**終點站**，超過 5 分鐘算誤點 | τ = 5 min | 台鐵月報 |
        | **本研究全站** | **每個停靠站**到站，超過 2 分鐘算誤點 | τ = 2 min | 日英標準 |

        > 台鐵官方只看終點站，列車中途大誤點後追回就不算——本研究採全站統計更能反映旅客實際感受。
        """)

    st.markdown("---")

    # ── Schedule Query ────────────────────────────────────────
    if schedule_df is None:
        schedule_df = pd.DataFrame()

    section_title("班次首末班時間查詢")
    if schedule_df.empty:
        st.info("首末班時間表尚未產生，請等待 GitHub Actions 重新匯出資料。")
    else:
        sc1, sc2, sc3 = st.columns([2, 2, 1])
        with sc1:
            all_types_s = ["全部車種"] + sorted(schedule_df["TrainTypeSimple"].dropna().unique().tolist())
            sel_type = st.selectbox("車種篩選", all_types_s, key="sched_type")
        with sc2:
            search_no = st.text_input("車次號碼查詢", placeholder="例：101", key="sched_no")
        with sc3:
            dir_opt = st.selectbox("行駛方向", ["全部", "順行（基→高）", "逆行（高→基）"], key="sched_dir")

        sdf = schedule_df.copy()
        if sel_type != "全部車種":
            sdf = sdf[sdf["TrainTypeSimple"] == sel_type]
        if search_no.strip():
            sdf = sdf[sdf["TrainNo"].str.contains(search_no.strip())]
        if dir_opt == "順行（基→高）":
            sdf = sdf[sdf["Direction"] == 0]
        elif dir_opt == "逆行（高→基）":
            sdf = sdf[sdf["Direction"] == 1]

        show_cols = ["TrainNo", "TrainTypeSimple", "FromStation", "FirstDep",
                     "ToStation", "LastArr", "Direction"]
        col_labels = {"TrainNo": "車次", "TrainTypeSimple": "車種",
                      "FromStation": "始發站", "FirstDep": "始發時間",
                      "ToStation": "終點站", "LastArr": "終到時間",
                      "Direction": "方向"}
        disp = sdf[[c for c in show_cols if c in sdf.columns]].rename(columns=col_labels)
        if "方向" in disp.columns:
            disp["方向"] = disp["方向"].map({0: "順行", 1: "逆行"})
        st.dataframe(disp, use_container_width=True, hide_index=True,
                     height=min(400, 35 + len(disp) * 35))
        st.caption(f"共 {len(disp):,} 班次　｜　首班：{sdf['FirstDep'].min() if not sdf.empty else '—'}　末班：{sdf['LastArr'].max() if not sdf.empty else '—'}")

    st.markdown("---")

    # ── Per-TrainType Punctuality ──────────────────────────────
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        section_title("各車種：台鐵官方準點率")
        if not terminal_df.empty:
            col_name = "IsDelayed_Official" if "IsDelayed_Official" in terminal_df.columns else "IsDelayed"
            d = terminal_df.groupby("TrainType")[col_name].apply(
                lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率").sort_values("準點率")
            fig = go.Figure(go.Bar(
                x=d["準點率"], y=d["TrainType"], orientation="h",
                marker=dict(color=COLORS[:len(d)], line=dict(width=0)),
                text=d["準點率"].astype(str)+"%", textposition="outside",
                textfont=dict(size=11, color=TEXT_SECONDARY),
            ))
            fig.update_layout(**PLOTLY_THEME, height=240,
                              xaxis=dict(**AXIS_STYLE, range=[75, 100]),
                              yaxis=dict(**AXIS_STYLE))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("終點站紀錄不足，請累積更多資料。")

    with col_b:
        section_title("各車種：本研究全站準點率")
        d2 = _pdf.groupby("TrainType")["IsDelayed"].apply(
            lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率").sort_values("準點率")
        fig2 = go.Figure(go.Bar(
            x=d2["準點率"], y=d2["TrainType"], orientation="h",
            marker=dict(color=COLORS[:len(d2)], line=dict(width=0)),
            text=d2["準點率"].astype(str)+"%", textposition="outside",
            textfont=dict(size=11, color=TEXT_SECONDARY),
        ))
        fig2.update_layout(**PLOTLY_THEME, height=240,
                           xaxis=dict(**AXIS_STYLE, range=[75, 100]),
                           yaxis=dict(**AXIS_STYLE))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Cross Analysis ────────────────────────────────────────
    st.markdown("---")
    section_title("各時段 × 車種準點率交叉比較")
    if "Period" in _pdf.columns:
        cross = _pdf.groupby(["Period", "TrainType"])["IsDelayed"].apply(
            lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率")
        fig3 = px.bar(
            cross, x="Period", y="準點率", color="TrainType",
            barmode="group",
            color_discrete_sequence=COLORS,
            category_orders={"Period": ["深夜", "離峰", "尖峰"]},
        )
        fig3.update_layout(**PLOTLY_THEME, height=280,
                           yaxis=dict(**AXIS_STYLE, range=[70, 100]),
                           xaxis=dict(**AXIS_STYLE),
                           legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)))
        st.plotly_chart(fig3, use_container_width=True)

    # ── Holiday Effect ────────────────────────────────────────
    st.markdown("---")
    section_title("假日效應")
    if "HolidayType" in _pdf.columns:
        hol = _pdf.groupby(["HolidayType", "TrainType"])["IsDelayed"].apply(
            lambda x: round((1-x.mean())*100, 1)).reset_index(name="準點率")
        fig4 = px.bar(hol, x="HolidayType", y="準點率", color="TrainType",
                      barmode="group", color_discrete_sequence=COLORS)
        fig4.update_layout(**PLOTLY_THEME, height=260,
                           yaxis=dict(**AXIS_STYLE, range=[70, 100]),
                           xaxis=dict(**AXIS_STYLE),
                           legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)))
        st.plotly_chart(fig4, use_container_width=True)
