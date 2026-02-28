import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
import os
from config import CLIENT_ID, CLIENT_SECRET, DATA_DIR
from processor import DataProcessor, CLOUD_MODE

if not CLOUD_MODE:
    from crawlers.live_board import crawl_live_board
    from crawlers.alert import crawl_alerts
    from crawlers.timetable import crawl_timetable
    from crawlers.station import crawl_stations
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm

# ══════════════════════════════════════════════════════════════
#  頁面設定 & 主題
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="TRA 誤點研究指揮中心",
    layout="wide",
    page_icon="🚆",
    initial_sidebar_state="expanded"
)

# 全域 CSS：深色工業風 + 台鐵綠
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+TC:wght@300;400;700&display=swap');

/* 全域背景 */
.stApp { background-color: #0d1117; color: #e6edf3; }
section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }

/* 字型 */
html, body, .stApp, .stMarkdown, p, span, div { font-family: 'Noto Sans TC', sans-serif !important; font-size: 15px !important; }
code, .stCode { font-family: 'IBM Plex Mono', monospace !important; }

/* 標題樣式 */
h1 { font-size: 1.9rem !important; font-weight: 700 !important; color: #e6edf3 !important; letter-spacing: -0.5px; }
h2 { font-size: 1.4rem !important; font-weight: 700 !important; color: #e6edf3 !important; border-left: 3px solid #2ea043; padding-left: 10px; }
h3 { font-size: 1.15rem !important; font-weight: 400 !important; color: #8b949e !important; }

/* Metric 卡片 */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 20px !important;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover { border-color: #2ea043; }
[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.82rem !important; text-transform: uppercase; letter-spacing: 0.8px; }
[data-testid="stMetricValue"] { color: #2ea043 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 2.1rem !important; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* 按鈕 */
.stButton > button {
    background: transparent;
    border: 1px solid #2ea043;
    color: #2ea043;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    transition: all 0.2s;
}
.stButton > button:hover { background: #2ea043; color: #0d1117; }
.stButton > button[kind="primary"] { background: #2ea043; color: #0d1117; }

/* Radio 導覽 */
.stRadio > label { display: none; }
.stRadio > div { gap: 2px !important; }
.stRadio > div > label {
    padding: 8px 12px !important;
    border-radius: 6px !important;
    color: #8b949e !important;
    font-size: 0.95rem !important;
    transition: all 0.15s;
    cursor: pointer;
}
.stRadio > div > label:hover { background: #21262d !important; color: #e6edf3 !important; }
.stRadio > div [data-checked="true"] > div:first-child + div { color: #e6edf3 !important; background: #21262d !important; border-radius: 6px; }

/* 分隔線 */
hr { border-color: #21262d !important; }

/* Dataframe */
.stDataFrame { border: 1px solid #21262d !important; border-radius: 8px !important; }

/* Expander */
.streamlit-expanderHeader { background: #161b22 !important; border: 1px solid #21262d !important; border-radius: 6px !important; color: #8b949e !important; }

/* Info / Warning / Success */
.stInfo { background: rgba(46,160,67,0.1) !important; border-left: 3px solid #2ea043 !important; }
.stWarning { background: rgba(210,153,34,0.1) !important; border-left: 3px solid #d29922 !important; }
.stError { background: rgba(248,81,73,0.1) !important; border-left: 3px solid #f85149 !important; }
.stSuccess { background: rgba(46,160,67,0.1) !important; border-left: 3px solid #2ea043 !important; }

/* 狀態徽章 */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.5px;
}
.badge-green { background: rgba(46,160,67,0.15); color: #2ea043; border: 1px solid rgba(46,160,67,0.3); }
.badge-yellow { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
.badge-red { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }

/* 頁面標題列 */
.page-header {
    padding: 20px 0 16px 0;
    margin-bottom: 24px;
    border-bottom: 1px solid #21262d;
}
.page-header .subtitle { color: #8b949e; font-size: 0.85rem; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# Plotly 統一主題
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#161b22",
    font=dict(color="#8b949e", family="Noto Sans TC", size=12),
    margin=dict(l=0, r=0, t=36, b=0),
)
AXIS_STYLE = dict(gridcolor="#21262d", linecolor="#21262d", tickcolor="#21262d")
GREEN = "#2ea043"
COLORS = ["#2ea043", "#388bfd", "#d29922", "#f85149", "#bc8cff", "#79c0ff"]

# ══════════════════════════════════════════════════════════════
#  資料載入
# ══════════════════════════════════════════════════════════════
processor = DataProcessor(DATA_DIR)

@st.cache_data(ttl=180)
def load_data():
    df = processor.parse_live_board()
    rd = processor.build_research_dataset()
    return df, rd

df, research_df = load_data()

# ══════════════════════════════════════════════════════════════
#  側邊欄
# ══════════════════════════════════════════════════════════════
PAGES = [
    "首頁",
    "數據總覽",
    "準點率分析",
    "站點熱力圖",
    "OLS 迴歸",
    "異常通報",
    "系統設定",
]
PAGE_ICONS = ["⬡", "◈", "◎", "◉", "≋", "⚠", "⚙"]

with st.sidebar:
    st.markdown("""
    <div style="padding: 16px 0 20px 0; border-bottom: 1px solid #21262d; margin-bottom: 16px;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.65rem; color:#2ea043; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;">RESEARCH DASHBOARD</div>
        <div style="font-size:1.1rem; font-weight:700; color:#e6edf3; line-height:1.3;">台鐵誤點<br>研究指揮中心</div>
    </div>
    """, unsafe_allow_html=True)

    if "nav" not in st.session_state:
        st.session_state.nav = "首頁"

    for icon, name in zip(PAGE_ICONS, PAGES):
        label = f"{icon}  {name}"
        is_active = st.session_state.nav == name
        if st.button(
            label,
            key=f"nav_{name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.nav = name
            st.cache_data.clear()
            df, research_df = load_data()
            st.rerun()

    st.markdown("<div style='margin-top:24px; border-top:1px solid #21262d; padding-top:16px;'></div>", unsafe_allow_html=True)

    # 抓取狀態
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(DATA_DIR, "live_board", today)
    files_today = sorted(glob.glob(os.path.join(today_dir, "*.json"))) if os.path.exists(today_dir) else []

    if files_today:
        last_file = files_today[-1]
        t_str = os.path.basename(last_file).replace(".json", "")
        try:
            last_dt = datetime.strptime(f"{today} {t_str[:2]}:{t_str[2:4]}:{t_str[4:6]}", "%Y-%m-%d %H:%M:%S")
            mins = int((datetime.now() - last_dt).total_seconds() / 60)
            if mins <= 5:
                badge_cls, status_txt = "badge-green", f"LIVE · {mins}min ago"
            elif mins <= 15:
                badge_cls, status_txt = "badge-yellow", f"SLOW · {mins}min ago"
            else:
                badge_cls, status_txt = "badge-red", f"DEAD · {mins}min"
            st.markdown(f'<span class="badge {badge_cls}">{status_txt}</span>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:#8b949e;margin-top:6px;">最後更新 {last_dt.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
        except:
            st.markdown('<span class="badge badge-yellow">UNKNOWN</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-red">NO DATA</span>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-size:0.75rem; color:#8b949e; margin-top:12px; line-height:1.8;">
        今日抓取　<span style="color:#e6edf3; font-family:IBM Plex Mono,monospace;">{len(files_today)}</span> 次<br>
        累積筆數　<span style="color:#e6edf3; font-family:IBM Plex Mono,monospace;">{len(df):,}</span> 筆<br>
        資料範圍　<span style="color:#e6edf3; font-family:IBM Plex Mono,monospace;">{df['Date'].min() if not df.empty else '—'}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("↺  重新整理", use_container_width=True):
        st.cache_data.clear()
        df, research_df = load_data()
        st.rerun()

page = st.session_state.nav

# ══════════════════════════════════════════════════════════════
#  ⬡  首頁
# ══════════════════════════════════════════════════════════════
if page == "首頁":
    st.markdown("""
    <div class="page-header">
        <h1>⬡ 台鐵列車誤點影響因素之量化分析</h1>
        <div class="subtitle">Taiwan Railways Delay Analysis · 碩士課程期末報告 · 國立政治大學行政管理碩士學程</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([3, 2], gap="large")

    with col_l:
        st.markdown("## 研究摘要")
        st.markdown("""
        <div style="color:#8b949e; line-height:1.9; font-size:0.9rem;">
        本研究以 TDX 即時動態 API 自行蒐集全台臺鐵列車誤點資料，結合時刻表結構特徵，
        建構「班次 × 車站」層級的面板資料集，透過 OLS 線性迴歸模型，系統性探討影響
        列車誤點分鐘數的結構性因素。
        </div>
        """, unsafe_allow_html=True)

        st.markdown("## 研究設計")

        design_items = [
            ("應變數 Y₁", "DelayTime", "各站實際誤點分鐘數（連續）"),
            ("應變數 Y₂", "IsDelayed", "是否誤點 ≥5 分鐘（二元）"),
            ("X₂ 車種", "TrainType", "自強 / 區間快 / 區間 / 莒光 / 傾斜式"),
            ("X₃ 時段", "Period", "尖峰 / 離峰 / 深夜"),
            ("X₄ 星期", "Weekday", "0–6"),
            ("X₅ 月份", "Month", "1–12"),
            ("X₆ 站等級", "StationGrade", "特等至招呼站"),
            ("X₇ 側線數", "SideTrackCount", "待填（廠站略圖）"),
            ("X₈ 單複線", "IsDouble", "待填（廠站略圖）"),
            ("X₉ 混合度", "MixIndex", "同站同小時車種數"),
            ("X₁₀ 速差", "SpeedDiff", "同站同小時最快最慢差"),
            ("PrevDelay", "前站誤點", "誤點累積效應"),
        ]
        rows_html = ""
        for label, var, desc in design_items:
            rows_html += f"""
            <tr>
                <td style="color:#8b949e;font-size:0.75rem;padding:5px 12px 5px 0;white-space:nowrap;">{label}</td>
                <td style="color:#2ea043;font-family:IBM Plex Mono,monospace;font-size:0.75rem;padding:5px 12px;">{var}</td>
                <td style="color:#8b949e;font-size:0.75rem;padding:5px 0;">{desc}</td>
            </tr>"""
        st.markdown(f"""
        <table style="width:100%; border-collapse:collapse; margin-top:8px;">
            <thead><tr>
                <th style="color:#e6edf3;font-size:0.72rem;text-align:left;padding:0 12px 8px 0;border-bottom:1px solid #21262d;">變數</th>
                <th style="color:#e6edf3;font-size:0.72rem;text-align:left;padding:0 12px 8px;border-bottom:1px solid #21262d;">欄位</th>
                <th style="color:#e6edf3;font-size:0.72rem;text-align:left;padding:0 0 8px;border-bottom:1px solid #21262d;">說明</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown("## 資料現況")

        if not df.empty:
            total = len(df)
            pct_rate = round((1 - df["IsDelayed"].mean()) * 100, 1)
            avg_delay = round(df["ArrivalDelay"].mean(), 2)
            date_range = f"{df['Date'].min()} ～ {df['Date'].max()}"
            days = df["Date"].nunique()

            st.metric("累積觀測筆數", f"{total:,} 筆")
            st.metric("整體準點率", f"{pct_rate} %")
            st.metric("平均誤點分鐘", f"{avg_delay} min")
            st.metric("資料天數", f"{days} 天")
            st.markdown(f'<div style="font-size:0.75rem;color:#8b949e;margin-top:8px;">資料期間：{date_range}</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("## 車種分布")
            tc = df["TrainType"].value_counts().reset_index()
            tc.columns = ["車種", "筆數"]
            fig = go.Figure(go.Bar(
                x=tc["筆數"], y=tc["車種"],
                orientation="h",
                marker_color=COLORS[:len(tc)],
                text=tc["筆數"].apply(lambda x: f"{x:,}"),
                textposition="outside",
                textfont=dict(size=11, color="#8b949e"),
            ))
            fig.update_layout(**PLOTLY_THEME, height=200,
                              xaxis_title=None, yaxis_title=None,
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("尚無資料")

        st.markdown("---")
        st.markdown("## 方法論")
        methods = [
            ("主要", "OLS 線性迴歸", "DelayTime ~ X₂～X₁₀ + PrevDelay"),
            ("輔助", "Logit 迴歸", "IsDelayed ~ 同上"),
            ("補充", "GIS 空間分析", "各站誤點空間分布"),
        ]
        for badge, method, note in methods:
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">
                <span class="badge badge-green" style="margin-top:2px;min-width:32px;text-align:center;">{badge}</span>
                <div>
                    <div style="color:#e6edf3;font-size:0.85rem;font-weight:600;">{method}</div>
                    <div style="color:#8b949e;font-size:0.75rem;">{note}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  ◈  數據總覽
# ══════════════════════════════════════════════════════════════
elif page == "數據總覽":
    st.markdown("""
    <div class="page-header">
        <h1>◈ 數據總覽</h1>
        <div class="subtitle">全台列車誤點基礎統計 · Descriptive Statistics</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("尚無資料，請確認資料蒐集排程正常運作。")
    else:
        # KPI 列
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("觀測筆數", f"{len(df):,}")
        c2.metric("準點率", f"{round((1-df['IsDelayed'].mean())*100,1)} %")
        c3.metric("平均誤點", f"{round(df['ArrivalDelay'].mean(),2)} min")
        c4.metric("最大誤點", f"{int(df['ArrivalDelay'].max())} min")
        c5.metric("資料天數", f"{df['Date'].nunique()} 天")

        st.markdown("---")
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("## 各車種平均誤點")
            type_d = df.groupby("TrainType")["ArrivalDelay"].mean().sort_values(ascending=True).reset_index()
            fig = go.Figure(go.Bar(
                x=type_d["ArrivalDelay"], y=type_d["TrainType"],
                orientation="h",
                marker=dict(color=COLORS[:len(type_d)]),
                text=type_d["ArrivalDelay"].round(2).astype(str) + " min",
                textposition="outside",
            ))
            fig.update_layout(**PLOTLY_THEME, height=260, xaxis_title="平均誤點（分鐘）")
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("## 各時段準點率")
            if "Period" in df.columns:
                period_d = df.groupby("Period")["IsDelayed"].apply(
                    lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率")
                order = ["深夜", "離峰", "尖峰"]
                period_d["Period"] = pd.Categorical(period_d["Period"], categories=order, ordered=True)
                period_d = period_d.sort_values("Period")
                fig = go.Figure(go.Bar(
                    x=period_d["Period"], y=period_d["準點率"],
                    marker_color=GREEN,
                    text=period_d["準點率"].astype(str) + "%",
                    textposition="outside",
                ))
                fig.update_layout(**PLOTLY_THEME, height=260,
                                  yaxis=dict(**AXIS_STYLE, range=[85, 100]),
                                  yaxis_title="準點率 (%)")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2, gap="large")

        with col_c:
            st.markdown("## 誤點分鐘數分布")
            delay_clip = df[df["ArrivalDelay"] <= 30]["ArrivalDelay"]
            fig = go.Figure(go.Histogram(
                x=delay_clip, nbinsx=30,
                marker_color=GREEN, opacity=0.8,
            ))
            fig.update_layout(**PLOTLY_THEME, height=240,
                              xaxis_title="誤點分鐘（截至30分）", yaxis_title="筆數")
            st.plotly_chart(fig, use_container_width=True)

        with col_d:
            st.markdown("## 假日 vs 平日")
            if "HolidayType" in df.columns:
                hol_d = df.groupby("HolidayType").agg(
                    準點率=("IsDelayed", lambda x: round((1-x.mean())*100,1)),
                    平均誤點=("ArrivalDelay", lambda x: round(x.mean(),2)),
                    筆數=("IsDelayed", "count")
                ).reset_index()
                st.dataframe(
                    hol_d.style.format({"準點率": "{:.1f}%", "平均誤點": "{:.2f} min", "筆數": "{:,}"}),
                    use_container_width=True, hide_index=True
                )

        st.markdown("---")
        st.markdown("## 逐日準點率趨勢")
        daily = df.groupby("Date")["IsDelayed"].apply(
            lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily["Date"], y=daily["準點率"],
            mode="lines+markers",
            line=dict(color=GREEN, width=2),
            marker=dict(size=6, color=GREEN),
            fill="tozeroy",
            fillcolor="rgba(46,160,67,0.08)",
        ))
        fig.update_layout(**PLOTLY_THEME, height=220,
                          yaxis=dict(**AXIS_STYLE, range=[85, 100]),
                          yaxis_title="準點率 (%)")
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
#  ◎  準點率分析
# ══════════════════════════════════════════════════════════════
elif page == "準點率分析":
    st.markdown("""
    <div class="page-header">
        <h1>◎ 準點率分析</h1>
        <div class="subtitle">雙維度準點率比較：台鐵官方終點代理 vs 路網全站指標</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("尚無資料")
    else:
        terminal_df = df[df["IsLastRecord"] == 1] if "IsLastRecord" in df.columns else pd.DataFrame()
        inter_pct = round((1 - df["IsDelayed"].mean()) * 100, 2)
        off_pct = round((1 - terminal_df["IsDelayed"].mean()) * 100, 2) if not terminal_df.empty else None
        diff = round(off_pct - inter_pct, 2) if off_pct else None

        c1, c2, c3 = st.columns(3)
        c1.metric("路網站間準點率", f"{inter_pct} %", help="全部班次在所有停靠站的準點率")
        if off_pct:
            c2.metric("終點代理準點率", f"{off_pct} %", help="每班次最後一筆紀錄的準點率")
            c3.metric("兩者差距", f"{diff:+.2f} %",
                      delta=f"{'列車接近終點誤點增加' if diff < 0 else '列車趕回誤點'}")

        with st.expander("⚠ API 限制與指標定義說明", expanded=False):
            st.markdown("""
            TDX `TrainLiveBoard` 的特性是列車抵達**終點站後即從即時板消失**，
            因此本研究改以每班次當天**最後一筆抓取紀錄**作為終點代理值。

            | 指標 | 定義 | 備註 |
            |------|------|------|
            | 路網站間準點率 | 所有班次 × 所有停靠站 | 本研究自定義 |
            | 終點代理準點率 | 每班次最後一筆紀錄 | 代理台鐵月報口徑 |
            """)

        st.markdown("---")
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("## 各車種：路網站間準點率")
            d = df.groupby("TrainType")["IsDelayed"].apply(
                lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率").sort_values("準點率")
            fig = go.Figure(go.Bar(
                x=d["準點率"], y=d["TrainType"], orientation="h",
                marker_color=COLORS[:len(d)],
                text=d["準點率"].astype(str)+"%", textposition="outside",
            ))
            fig.update_layout(**PLOTLY_THEME, height=240,
                              xaxis=dict(**AXIS_STYLE, range=[80, 100]))
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("## 各車種：終點代理準點率")
            if terminal_df.empty:
                st.info("尚無終點代理資料")
            else:
                d2 = terminal_df.groupby("TrainType")["IsDelayed"].apply(
                    lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率").sort_values("準點率")
                fig2 = go.Figure(go.Bar(
                    x=d2["準點率"], y=d2["TrainType"], orientation="h",
                    marker_color=COLORS[:len(d2)],
                    text=d2["準點率"].astype(str)+"%", textposition="outside",
                ))
                fig2.update_layout(**PLOTLY_THEME, height=240,
                                   xaxis=dict(**AXIS_STYLE, range=[80, 100]))
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.markdown("## 各時段 × 車種準點率交叉比較")
        if "Period" in df.columns:
            cross = df.groupby(["Period", "TrainType"])["IsDelayed"].apply(
                lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率")
            fig3 = px.bar(
                cross, x="Period", y="準點率", color="TrainType",
                barmode="group",
                color_discrete_sequence=COLORS,
                category_orders={"Period": ["深夜", "離峰", "尖峰"]},
            )
            fig3.update_layout(**PLOTLY_THEME, height=280,
                               yaxis=dict(**AXIS_STYLE, range=[75, 100]),
                               legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b949e")))
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")
        st.markdown("## 假日效應")
        if "HolidayType" in df.columns:
            hol = df.groupby(["HolidayType", "TrainType"])["IsDelayed"].apply(
                lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率")
            fig4 = px.bar(hol, x="HolidayType", y="準點率", color="TrainType",
                          barmode="group", color_discrete_sequence=COLORS)
            fig4.update_layout(**PLOTLY_THEME, height=260,
                               yaxis=dict(**AXIS_STYLE, range=[75, 100]),
                               legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b949e")))
            st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════
#  ◉  站點熱力圖
# ══════════════════════════════════════════════════════════════
elif page == "站點熱力圖":
    st.markdown("""
    <div class="page-header">
        <h1>◉ 站點熱力圖</h1>
        <div class="subtitle">全台車站誤點空間分布 · GIS Visualization</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty or "Lat" not in df.columns or df["Lat"].isna().all():
        st.warning("座標資料尚未載入，請至「系統設定」更新車站座標。")
    else:
        map_df = df.dropna(subset=["Lat", "Lon"])
        station_map = map_df.groupby(["StationName", "Lat", "Lon"]).agg(
            平均誤點=("ArrivalDelay", "mean"),
            筆數=("ArrivalDelay", "count"),
            誤點率=("IsDelayed", "mean"),
        ).reset_index()
        station_map["平均誤點"] = station_map["平均誤點"].round(2)
        station_map["誤點率_pct"] = (station_map["誤點率"] * 100).round(1)

        c1, c2 = st.columns([3, 1])
        with c2:
            view_mode = st.radio("顯示指標", ["平均誤點（分）", "誤點率（%）"], index=0)

        color_col = "平均誤點" if "平均誤點" in view_mode else "誤點率_pct"
        hover_label = "平均誤點（分）" if "平均誤點" in view_mode else "誤點率（%）"

        fig = px.scatter_mapbox(
            station_map,
            lat="Lat", lon="Lon",
            hover_name="StationName",
            color=color_col,
            size=color_col,
            size_max=18,
            color_continuous_scale=["#2ea043", "#d29922", "#f85149"],
            zoom=6.5,
            center={"lat": 23.8, "lon": 121.0},
            mapbox_style="carto-darkmatter",
            labels={color_col: hover_label},
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            height=560,
            coloraxis_colorbar=dict(
                title=dict(text=hover_label, font=dict(color="#8b949e")),
                tickfont=dict(color="#8b949e"),
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("## 誤點前 10 名車站")
        top10 = station_map.nlargest(10, "平均誤點")[["StationName", "平均誤點", "誤點率_pct", "筆數"]]
        top10.columns = ["車站", "平均誤點（分）", "誤點率（%）", "觀測筆數"]
        st.dataframe(
            top10.style.format({"平均誤點（分）": "{:.2f}", "誤點率（%）": "{:.1f}", "觀測筆數": "{:,}"}),
            use_container_width=True, hide_index=True
        )

# ══════════════════════════════════════════════════════════════
#  ≋  OLS 迴歸
# ══════════════════════════════════════════════════════════════
elif page == "OLS 迴歸":
    st.markdown("""
    <div class="page-header">
        <h1>≋ OLS 線性迴歸</h1>
        <div class="subtitle">誤點分鐘數影響因素估計 · Ordinary Least Squares</div>
    </div>
    """, unsafe_allow_html=True)

    if research_df.empty or len(research_df) < 30:
        st.warning(f"資料量不足（目前 {len(research_df):,} 筆），建議累積至少 1,000 筆後執行迴歸。")
    else:
        col_info, col_run = st.columns([2, 1])
        with col_info:
            st.markdown("## 變數設定")
            st.markdown("""
            <div style="font-size:0.85rem; color:#8b949e; line-height:1.8;">
            應變數：<code style="color:#2ea043;">DelayTime</code>（誤點分鐘數，連續）<br>
            自變數：車種虛擬變數（基準：區間）、停靠順序、時段（基準：離峰）、
            假日、前站誤點分鐘數
            </div>
            """, unsafe_allow_html=True)
        with col_run:
            run_ols = st.button("▶  執行 OLS 迴歸", type="primary", use_container_width=True)
            run_logit = st.button("▶  執行 Logit 迴歸", use_container_width=True)

        st.markdown("---")

        if run_ols or run_logit:
            reg_df = research_df.dropna(
                subset=["DelayTime","StopSeq","PrevDelay","Period","TrainType","IsHoliday"]
            ).copy()
            reg_df["IsZiQiang"]    = (reg_df["TrainType"] == "自強").astype(int)
            reg_df["IsQuJianKuai"] = (reg_df["TrainType"] == "區間快").astype(int)
            reg_df["IsTilt"]       = (reg_df["TrainType"] == "傾斜式自強").astype(int)
            reg_df["IsJuGuang"]    = (reg_df["TrainType"] == "莒光").astype(int)
            reg_df["IsPeak"]       = (reg_df["Period"] == "尖峰").astype(int)
            reg_df["IsNight"]      = (reg_df["Period"] == "深夜").astype(int)

            xvars = ["IsZiQiang","IsQuJianKuai","IsTilt","IsJuGuang",
                     "StopSeq","IsPeak","IsNight","IsHoliday","PrevDelay"]
            var_labels = {
                "const":"截距",
                "IsZiQiang":"自強（vs 區間）",
                "IsQuJianKuai":"區間快（vs 區間）",
                "IsTilt":"傾斜式自強（vs 區間）",
                "IsJuGuang":"莒光（vs 區間）",
                "StopSeq":"停靠順序",
                "IsPeak":"尖峰時段",
                "IsNight":"深夜時段",
                "IsHoliday":"假日",
                "PrevDelay":"前站誤點（分）",
            }

            X = sm.add_constant(reg_df[xvars].astype(float))
            y_cont = reg_df["DelayTime"]
            y_bin  = reg_df["IsDelayed"]

            if run_ols:
                model = sm.OLS(y_cont, X).fit()
                model_name = "OLS 線性迴歸"
                r2_label = "R²"
                r2_val = f"{model.rsquared:.4f}"
                adj_r2 = f"{model.rsquared_adj:.4f}"
            else:
                model = sm.Logit(y_bin, X).fit(disp=0)
                model_name = "Logit 迴歸"
                r2_label = "Pseudo R²"
                r2_val = f"{model.prsquared:.4f}"
                adj_r2 = "—"

            st.markdown(f"## {model_name} 結果")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(r2_label, r2_val)
            m2.metric("Adj. R²", adj_r2)
            m3.metric("樣本數 N", f"{int(model.nobs):,}")
            m4.metric("AIC", f"{model.aic:.1f}")

            result_df = pd.DataFrame({
                "變數": [var_labels.get(v, v) for v in model.params.index],
                "β 係數": model.params.values.round(4),
                "標準誤": model.bse.values.round(4),
                "t / z": model.tvalues.values.round(3),
                "p 值": model.pvalues.values.round(4),
                "顯著性": ["***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else "†" if p<0.1 else "" for p in model.pvalues.values],
            })

            st.dataframe(
                result_df.style.format({"β 係數":"{:.4f}","標準誤":"{:.4f}","t / z":"{:.3f}","p 值":"{:.4f}"}),
                use_container_width=True, hide_index=True
            )
            st.caption("*** p<0.001  ** p<0.01  * p<0.05  † p<0.1")

            # 係數圖
            coef = result_df[result_df["變數"] != "截距"].copy()
            fig = go.Figure()
            for _, row in coef.iterrows():
                color = GREEN if row["β 係數"] > 0 else "#f85149"
                fig.add_trace(go.Scatter(
                    x=[row["β 係數"]], y=[row["變數"]],
                    mode="markers",
                    marker=dict(size=10, color=color),
                    error_x=dict(type="data", array=[row["標準誤"]*1.96], color=color, thickness=1.5),
                    showlegend=False,
                ))
            fig.add_vline(x=0, line_dash="dash", line_color="#21262d", line_width=1)
            fig.update_layout(**PLOTLY_THEME, height=300, xaxis_title="係數估計值（95% CI）")
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📄 完整 statsmodels Summary"):
                st.text(model.summary().as_text())


# ══════════════════════════════════════════════════════════════
#  ⚠  異常通報
# ══════════════════════════════════════════════════════════════
elif page == "異常通報":
    st.markdown("""
    <div class="page-header">
        <h1>⚠ 異常通報分析</h1>
        <div class="subtitle">誤點原因分類統計 · Alert Analysis</div>
    </div>
    """, unsafe_allow_html=True)

    alerts_df = processor.parse_alerts()

    if alerts_df.empty:
        st.info("尚無異常通報資料。")
    else:
        c1, c2 = st.columns([1, 2], gap="large")

        with c1:
            st.markdown("## 原因分類佔比")
            cat_count = alerts_df["Category"].value_counts().reset_index()
            cat_count.columns = ["原因", "件數"]
            fig = go.Figure(go.Pie(
                labels=cat_count["原因"],
                values=cat_count["件數"],
                marker_colors=COLORS[:len(cat_count)],
                hole=0.5,
                textinfo="percent",
                textfont=dict(size=11, color="#e6edf3"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8b949e"),
                margin=dict(l=0, r=0, t=0, b=0),
                height=280,
                showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b949e", size=11)),
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("## 各類原因定義")
            defs = processor.reason_definitions
            for cat, desc in defs.items():
                st.markdown(f"""
                <div style="display:flex;gap:10px;margin-bottom:8px;align-items:flex-start;">
                    <span class="badge badge-green" style="min-width:60px;text-align:center;white-space:nowrap;">{cat[:4]}</span>
                    <div style="color:#8b949e;font-size:0.8rem;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 最新通報紀錄")
        st.dataframe(
            alerts_df.sort_values("PublishTime", ascending=False).head(50),
            use_container_width=True, hide_index=True
        )

# ══════════════════════════════════════════════════════════════
#  ⚙  系統設定
# ══════════════════════════════════════════════════════════════
elif page == "系統設定":
    st.markdown("""
    <div class="page-header">
        <h1>⚙ 系統設定中心</h1>
        <div class="subtitle">API 金鑰管理 · 資料蒐集控制 · 匯出工具</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        st.markdown("## API 金鑰設定")
        cid  = st.text_input("TDX Client ID",     value=CLIENT_ID,     type="password")
        csec = st.text_input("TDX Client Secret", value=CLIENT_SECRET, type="password")
        if st.button("💾 儲存 API 設定", use_container_width=True):
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            with open(env_path, "w") as f:
                f.write(f'TDX_CLIENT_ID="{cid}"\nTDX_CLIENT_SECRET="{csec}"\n')
            st.success("API 設定已儲存")

        st.markdown("---")
        st.markdown("## 靜態資料更新")
        if st.button("↺ 更新車站座標", use_container_width=True):
            with st.spinner("抓取中..."):
                crawl_stations()
            st.success("車站座標已更新")
        if st.button("↺ 更新時刻表", use_container_width=True):
            with st.spinner("抓取中..."):
                crawl_timetable()
            st.success("時刻表已更新")

    with col_r:
        st.markdown("## 手動資料抓取")
        if CLOUD_MODE:
            st.info("雲端模式：資料由 Mac mini 定期推送至 GitHub，此處無法手動抓取。")
        else:
            st.markdown('<div style="font-size:0.8rem;color:#8b949e;margin-bottom:12px;">⚠ 自動抓取由 launchd 排程負責（每3分鐘），此處僅供手動補抓。</div>', unsafe_allow_html=True)
            if st.button("▶ 手動抓取一次（即時板 + 通報）", use_container_width=True):
                with st.spinner("抓取中..."):
                    crawl_live_board()
                    crawl_alerts()
                st.success("抓取完成")

        st.markdown("---")
        st.markdown("## 資料匯出")
        if st.button("📥 匯出全台原始資料 CSV", use_container_width=True):
            out = os.path.join(DATA_DIR, "processed_data.csv")
            df.to_csv(out, index=False, encoding="utf-8-sig")
            st.success(f"已匯出 processed_data.csv（{len(df):,} 筆）")

        if st.button("🔬 匯出研究資料集 CSV", use_container_width=True):
            out = processor.export_research_csv()
            if out:
                st.success(f"已匯出 research_dataset.csv（{len(research_df):,} 筆）")

        st.markdown("---")
        st.markdown("## 資料目錄狀況")
        dates = sorted(glob.glob(os.path.join(DATA_DIR, "live_board", "*")))
        for d_path in dates[-5:]:
            d_name = os.path.basename(d_path)
            n = len(glob.glob(os.path.join(d_path, "*.json")))
            st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.78rem;color:#8b949e;padding:3px 0;">{d_name} <span style="color:#2ea043;">{n}</span> 筆</div>', unsafe_allow_html=True)
