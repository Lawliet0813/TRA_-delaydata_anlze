"""
異常通報 (Alerts) — Timeline + Categorized Analysis
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from views.theme import PLOTLY_THEME, COLORS, GREEN, BLUE, TEXT_SECONDARY, TEXT_MUTED, BORDER
from views.components import page_header, section_title


def render(processor, **kwargs):
    page_header("⚠", "異常通報分析", "誤點原因分類統計 · Alert Analysis")

    alerts_df = processor.parse_alerts()

    if alerts_df.empty:
        st.info("尚無異常通報資料。")
        return

    c1, c2 = st.columns([1, 2], gap="large")

    with c1:
        section_title("原因分類佔比")
        cat_count = alerts_df["Category"].value_counts().reset_index()
        cat_count.columns = ["原因", "件數"]

        fig = go.Figure(go.Pie(
            labels=cat_count["原因"],
            values=cat_count["件數"],
            marker=dict(colors=COLORS[:len(cat_count)], line=dict(width=2, color="#0a0e14")),
            hole=0.6,
            textinfo="percent",
            textfont=dict(size=11, color="#f0f6fc"),
            hovertemplate="<b>%{label}</b><br>%{value} 件 (%{percent})<extra></extra>",
        ))
        # Center label
        fig.add_annotation(
            text=f"<b>{cat_count['件數'].sum()}</b><br><span style='font-size:11px;color:{TEXT_SECONDARY}'>件</span>",
            font=dict(size=24, color="#f0f6fc", family="JetBrains Mono"),
            showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY),
            margin=dict(l=0, r=0, t=0, b=0),
            height=300,
            showlegend=True,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY, size=11)),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        section_title("各類原因定義")
        defs = processor.reason_definitions
        for cat, desc in defs.items():
            st.markdown(f"""
            <div style="display:flex;gap:12px;margin-bottom:10px;align-items:center;
                        padding:10px 14px;border-radius:8px;
                        background:rgba(255,255,255,0.02);border:1px solid {BORDER};
                        transition:all 0.2s;">
                <span class="badge badge-blue" style="min-width:60px;text-align:center;white-space:nowrap;">{cat[:4]}</span>
                <div style="color:{TEXT_SECONDARY};font-size:0.82rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    section_title("最新通報紀錄")
    st.dataframe(
        alerts_df.sort_values("PublishTime", ascending=False).head(50),
        use_container_width=True, hide_index=True
    )
