"""
首頁 (Home) — Hero + Research Overview + Live KPIs
"""
import streamlit as st
import plotly.graph_objects as go
from views.theme import PLOTLY_THEME, AXIS_STYLE, COLORS, BLUE, GREEN, TEXT_SECONDARY, TEXT_MUTED, BORDER
from views.components import page_header, kpi_card, section_title, method_step


def render(df, filtered_df=None, date_label="📅 全部日期", **kwargs):
    # ── Hero ──────────────────────────────────────────────────
    st.markdown("""
    <div class="hero">
        <h1>台鐵列車誤點影響因素之量化分析</h1>
        <div class="subtitle">Taiwan Railways Delay Analysis · Research Command Center</div>
        <div class="institution">🎓 國立政治大學 MEPA · 社會科學研究方法（一）期末報告</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Live KPIs（依日期篩選器同步） ─────────────────────────
    _kdf = filtered_df if (filtered_df is not None and not filtered_df.empty) else df
    if not _kdf.empty:
        total = len(_kdf)
        pct_rate = round((1 - _kdf["IsDelayed"].mean()) * 100, 1)
        avg_delay = round(_kdf["DelayTime"].mean(), 2)
        days = _kdf["Date"].nunique()
        date_range = f'{_kdf["Date"].min()} ~ {_kdf["Date"].max()}'

        st.caption(f"目前顯示範圍：{date_label}　共 {total:,} 筆觀測")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("觀測筆數", f"{total:,}", "blue", "班次 × 車站紀錄")
        with c2:
            kpi_card("準點率", f"{pct_rate}%", "green", "τ = 2 分鐘")
        with c3:
            kpi_card("平均誤點", f"{avg_delay} min", "yellow" if avg_delay > 1 else "green")
        with c4:
            kpi_card("資料天數", f"{days} 天", sub=date_range)
    else:
        st.warning("尚無資料")

    st.markdown("---")

    # ── Research Design ───────────────────────────────────────
    col_l, col_r = st.columns([3, 2], gap="large")

    with col_l:
        section_title("研究摘要")
        st.markdown(f"""
        <div style="color:{TEXT_SECONDARY}; line-height:2; font-size:0.88rem; margin-bottom:24px;">
        本研究以 TDX 即時動態 API 自行蒐集全台臺鐵列車誤點資料，結合時刻表結構特徵，
        建構「班次 × 車站」層級的面板資料集，透過 OLS 線性迴歸模型，系統性探討影響
        列車誤點分鐘數的結構性因素。
        </div>
        """, unsafe_allow_html=True)

        section_title("研究設計")
        design_items = [
            ("Y₁", "DelayTime", "各站實際誤點分鐘數（連續）"),
            ("Y₂", "IsDelayed", "是否誤點 ≥ 2 分鐘（二元）"),
            ("X₁", "TrainType", "車種（自強 / 區間快 / 區間 / 莒光 / 傾斜式）"),
            ("X₃", "Period", "時段（尖峰 / 離峰 / 深夜）"),
            ("X₄", "IsHoliday", "假日旗標"),
            ("X₆", "StationGrade", "站等級"),
            ("X₇", "SideTrackCount", "側線數"),
            ("X₈", "IsDouble", "單複線別"),
            ("X₉", "PrevDelay", "前站誤點（累積效應）"),
            ("X₁₀", "Direction", "行駛方向"),
            ("X₁₁", "TripLine", "路線別（山海線）"),
        ]
        rows_html = ""
        for label, var, desc in design_items:
            rows_html += f"""
            <tr>
                <td style="color:{TEXT_MUTED};font-size:0.78rem;padding:7px 12px 7px 0;white-space:nowrap;font-weight:500;">{label}</td>
                <td style="font-family:JetBrains Mono,monospace;color:{BLUE};font-size:0.78rem;padding:7px 12px;">{var}</td>
                <td style="color:{TEXT_SECONDARY};font-size:0.78rem;padding:7px 0;">{desc}</td>
            </tr>"""
        st.markdown(f"""
        <table class="research-table">
            <thead><tr>
                <th>代號</th>
                <th>欄位</th>
                <th>說明</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    with col_r:
        # ── Train Type Distribution ───────────────────────────
        if not df.empty:
            section_title("車種分布")
            tc = df["TrainType"].value_counts().reset_index()
            tc.columns = ["車種", "筆數"]
            fig = go.Figure(go.Bar(
                x=tc["筆數"], y=tc["車種"],
                orientation="h",
                marker=dict(
                    color=COLORS[:len(tc)],
                    line=dict(width=0),
                ),
                text=tc["筆數"].apply(lambda x: f"{x:,}"),
                textposition="outside",
                textfont=dict(size=11, color=TEXT_SECONDARY),
            ))
            fig.update_layout(
                **PLOTLY_THEME, height=220,
                xaxis=dict(**AXIS_STYLE, title=None),
                yaxis=dict(**AXIS_STYLE, title=None),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # ── Methods ───────────────────────────────────────────
        section_title("方法論")
        methods_html = (
            method_step("01", "OLS 線性迴歸", "DelayTime ~ X₁ ~ X₁₁ + PrevDelay")
            + method_step("02", "Logit 迴歸", "IsDelayed ~ 同上（二元分類）")
            + method_step("03", "GIS 空間分析", "各站誤點空間分布地圖")
        )
        st.markdown(methods_html, unsafe_allow_html=True)
