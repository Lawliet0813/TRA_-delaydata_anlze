import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
import os
from config import CLIENT_ID, CLIENT_SECRET, DATA_DIR
from processor import DataProcessor, CLOUD_MODE, GITHUB_RAW_BASE

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

@st.cache_data(ttl=3600)
def load_train_schedule():
    """載入首末班車時間表（train_schedule.csv）"""
    if CLOUD_MODE:
        from datetime import datetime as _dt
        url = f"{GITHUB_RAW_BASE}/train_schedule.csv?v={int(_dt.now().timestamp())}"
        try:
            return pd.read_csv(url, dtype={"TrainNo": str})
        except Exception:
            return pd.DataFrame()
    local = os.path.join(DATA_DIR, "train_schedule.csv")
    if os.path.exists(local):
        return pd.read_csv(local, dtype={"TrainNo": str})
    return pd.DataFrame()

df, research_df = load_data()
schedule_df = load_train_schedule()

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

    if CLOUD_MODE:
        # 雲端模式：改用已載入的 df 判斷資料新鮮度，不依賴本機資料夾
        if not df.empty:
            last_date = df["Date"].max()
            if last_date == today:
                badge_cls, status_txt = "badge-green", f"CLOUD · {last_date}"
            else:
                badge_cls, status_txt = "badge-yellow", f"STALE · {last_date}"
        else:
            badge_cls, status_txt = "badge-red", "NO DATA"
        st.markdown(f'<span class="badge {badge_cls}">{status_txt}</span>', unsafe_allow_html=True)
        st.markdown(f"""
    <div style="font-size:0.75rem; color:#8b949e; margin-top:12px; line-height:1.8;">
        今日抓取　<span style="color:#e6edf3; font-family:IBM Plex Mono,monospace;">GitHub Actions</span><br>
        累積筆數　<span style="color:#e6edf3; font-family:IBM Plex Mono,monospace;">{len(df):,}</span> 筆<br>
        資料範圍　<span style="color:#e6edf3; font-family:IBM Plex Mono,monospace;">{df['Date'].min() if not df.empty else '—'}</span>
    </div>
    """, unsafe_allow_html=True)
    else:
        # 本機模式：原有邏輯不動
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

    # ── 日期篩選器 ────────────────────────────────────────────
    st.markdown("<div style='margin-top:20px; border-top:1px solid #21262d; padding-top:16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem; color:#8b949e; letter-spacing:1px; text-transform:uppercase; margin-bottom:8px;">DATE FILTER</div>', unsafe_allow_html=True)

    if not df.empty and "Date" in df.columns:
        _available_dates = sorted(df["Date"].dropna().unique().tolist(), reverse=True)
        _date_options = ["全部日期"] + _available_dates
        selected_date = st.selectbox(
            "選擇日期",
            options=_date_options,
            index=0,
            label_visibility="collapsed",
            key="date_filter",
        )
    else:
        selected_date = "全部日期"
        st.markdown('<div style="font-size:0.75rem; color:#8b949e;">尚無資料</div>', unsafe_allow_html=True)

page = st.session_state.nav

# ── 依日期篩選全域 DataFrame ──────────────────────────────────
if not df.empty and "Date" in df.columns and selected_date != "全部日期":
    filtered_df = df[df["Date"] == selected_date].copy()
    filtered_research_df = research_df[research_df["Date"] == selected_date].copy() if not research_df.empty and "Date" in research_df.columns else research_df.copy()
    _date_label = f"📅 {selected_date}"
else:
    filtered_df = df.copy()
    filtered_research_df = research_df.copy()
    _date_label = "📅 全部日期"

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
            ("應變數 Y₂", "IsDelayed", "是否誤點 ≥2 分鐘（二元，本研究全站定義）"),
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
            avg_delay = round(df["DelayTime"].mean(), 2)
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
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **計算方式**：統計各車種在資料集中出現的筆數（每筆 = 一班次在一車站的到站紀錄）。

                **資料來源**：交通部 TDX 平台 `StationLiveBoard` API，每 10 分鐘自動抓取一次，
                由 `processor.parse_live_board()` 解析並彙整，`TrainType` 欄位經 `_simplify_type()` 函式統一分類。
                """)
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

    _ddf = filtered_df  # 使用日期篩選後的資料
    st.caption(f"目前顯示範圍：{_date_label}　共 {len(_ddf):,} 筆觀測")

    if _ddf.empty:
        st.warning("此日期無資料，請重新選擇。")
    else:
        # KPI 列
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("觀測筆數", f"{len(_ddf):,}")
        c2.metric("準點率", f"{round((1-_ddf['IsDelayed'].mean())*100,1)} %")
        c3.metric("平均誤點", f"{round(_ddf['DelayTime'].mean(),2)} min")
        c4.metric("最大誤點", f"{int(_ddf['DelayTime'].max())} min")
        c5.metric("資料天數", f"{_ddf['Date'].nunique()} 天")

        with st.expander("📊 指標說明", expanded=False):
            st.markdown("""
            | 指標 | 計算方式 | 備註 |
            |------|----------|------|
            | **觀測筆數** | 每筆 = 一班次在一個車站的到站紀錄 | 由 TDX `StationLiveBoard` 每 10 分鐘抓取彙整 |
            | **準點率** | `(1 − IsDelayed.mean()) × 100%` | `IsDelayed = 1` 當 `DelayTime ≥ 2分鐘`（本研究門檻，參考日英標準） |
            | **平均誤點** | `DelayTime` 欄位算術平均（含 0 分鐘正常班次） | 單位：分鐘 |
            | **最大誤點** | `DelayTime` 欄位最大值 | 單位：分鐘 |
            | **資料天數** | `Date` 欄位不重複日期數 | YYYY-MM-DD 格式 |
            """)

        st.markdown("---")
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("## 各車種平均誤點")
            type_d = _ddf.groupby("TrainType")["DelayTime"].mean().sort_values(ascending=True).reset_index()
            fig = go.Figure(go.Bar(
                x=type_d["DelayTime"], y=type_d["TrainType"],
                orientation="h",
                marker=dict(color=COLORS[:len(type_d)]),
                text=type_d["DelayTime"].round(2).astype(str) + " min",
                textposition="outside",
            ))
            fig.update_layout(**PLOTLY_THEME, height=260, xaxis_title="平均誤點（分鐘）")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **計算方式**：依 `TrainType`（車種）分組，對所有停靠站紀錄的 `DelayTime` 取算術平均。

                車種分類邏輯（`_simplify_type()`）：
                - 太魯閣 / 普悠瑪 → **傾斜式自強**
                - 自強（其他）→ **自強**
                - 區間快 → **區間快**
                - 區間 → **區間**
                - 莒光 → **莒光**

                > 停靠站越多的車種（如區間車）誤點累積機會較高，直接比較時需留意路徑長度差異。

                **資料來源**：交通部 TDX 平台 `StationLiveBoard` API，每 10 分鐘抓取一次；
                `DelayTime` 欄位為 TDX 直接回傳之誤點分鐘數（與表定時間比較），由 `processor.parse_live_board()` 彙整。
                """)

        with col_b:
            st.markdown("## 各時段準點率")
            if "Period" in _ddf.columns:
                period_d = _ddf.groupby("Period")["IsDelayed"].apply(
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
                with st.expander("📊 說明", expanded=False):
                    st.markdown("""
                    **時段分類**（依表定到站時間 `ScheduleArrivalTime` 衍生）：
                    - **尖峰**：06:00–09:00 及 17:00–20:00
                    - **深夜**：00:00–06:00
                    - **離峰**：其餘時段

                    **準點率計算**：`(1 − IsDelayed.mean()) × 100%`，門檻 τ = 2 分鐘

                    **資料來源**：交通部 TDX `StationLiveBoard` API；`Period` 欄位由 `processor.build_research_dataset()` 依 `ScheduleArrivalTime` 衍生；準點率門檻 τ = 2 分鐘參考日本 JR 及英國 Network Rail 統計標準。
                    """)

        st.markdown("---")
        col_c, col_d = st.columns(2, gap="large")

        with col_c:
            st.markdown("## 誤點分鐘數分布")
            delay_clip = _ddf[_ddf["DelayTime"] <= 30]["DelayTime"]
            fig = go.Figure(go.Histogram(
                x=delay_clip, nbinsx=30,
                marker_color=GREEN, opacity=0.8,
            ))
            fig.update_layout(**PLOTLY_THEME, height=240,
                              xaxis_title="誤點分鐘（截至30分）", yaxis_title="筆數")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **資料來源**：交通部 TDX 平台 `StationLiveBoard` API，`DelayTime` 欄位為 TDX 直接回傳之誤點分鐘數（整數，與表定到站時間比較），由 `processor.parse_live_board()` 彙整。

                為避免極端值壓縮圖形，**截斷顯示 ≤ 30 分鐘**的觀測值，
                超過 30 分鐘的異常誤點仍納入 KPI 計算，僅此圖不呈現。

                > 分布高度右偏（大量 0 分鐘記錄）為台鐵誤點資料的典型型態，
                  適合使用負二項迴歸或零膨脹模型處理。
                """)

        with col_d:
            st.markdown("## 假日 vs 平日")
            if "HolidayType" in _ddf.columns:
                hol_d = _ddf.groupby("HolidayType").agg(
                    準點率=("IsDelayed", lambda x: round((1-x.mean())*100,1)),
                    平均誤點=("DelayTime", lambda x: round(x.mean(),2)),
                    筆數=("IsDelayed", "count")
                ).reset_index()
                st.dataframe(
                    hol_d.style.format({"準點率": "{:.1f}%", "平均誤點": "{:.2f} min", "筆數": "{:,}"}),
                    use_container_width=True, hide_index=True
                )
                with st.expander("📊 說明", expanded=False):
                    st.markdown("""
                    **假日判定**（`IsHoliday` 欄位，`_is_holiday()` 函式）：
                    依台灣政府公告國定假日日期及週六/日判定。

                    `HolidayType` 細分為：
                    - **平日**：週一至週五非國定假日
                    - **週末**：週六/週日
                    - **國定假日**：行政院公告補班補課日除外

                    **資料來源**：交通部 TDX `StationLiveBoard` API 彙整資料；假日判定依行政院人事行政總處公告之國定假日日期，由 `_is_holiday()` 函式處理。
                    """)

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
        st.caption("※ 逐日趨勢圖固定顯示全部日期，不受上方日期篩選影響，以保留完整時間序列視圖。")
        with st.expander("📊 說明", expanded=False):
            st.markdown("""
            **計算方式**：依每天（`Date`）分組，計算當日所有停靠站記錄的準點率。

            Y 軸範圍固定為 85%–100% 以放大差異。若某日準點率低於 85% 將截斷於底部，
            可透過游標懸停查看精確數值。

            > 此圖不受側邊欄日期篩選影響，固定呈現累積資料期間的完整趨勢。

            **資料來源**：交通部 TDX `StationLiveBoard` API，自研究開始日期起每日持續累積，本圖固定顯示所有已蒐集日期的完整趨勢（不受日期篩選影響）。
            """)


# ══════════════════════════════════════════════════════════════
#  ◎  準點率分析
# ══════════════════════════════════════════════════════════════
elif page == "準點率分析":
    st.markdown("""
    <div class="page-header">
        <h1>◎ 準點率分析</h1>
        <div class="subtitle">台鐵官方準點率 vs 本研究全站準點率 · 雙定義比較</div>
    </div>
    """, unsafe_allow_html=True)

    _pdf = filtered_df  # 使用日期篩選後的資料
    st.caption(f"目前顯示範圍：{_date_label}　共 {len(_pdf):,} 筆觀測")

    if _pdf.empty:
        st.warning("此日期無資料，請重新選擇。")
    else:
        # ── 官方準點率：終點站 + τ=5分 ──────────────────────────
        terminal_df = _pdf[_pdf["IsTerminal"] == 1] if "IsTerminal" in _pdf.columns else pd.DataFrame()
        research_pct = round((1 - _pdf["IsDelayed"].mean()) * 100, 2)      # 全站統計 τ=2分
        if not terminal_df.empty and "IsDelayed_Official" in terminal_df.columns:
            official_pct = round((1 - terminal_df["IsDelayed_Official"].mean()) * 100, 2)
        elif not terminal_df.empty:
            official_pct = round((1 - terminal_df["IsDelayed"].mean()) * 100, 2)
        else:
            official_pct = None
        diff = round(official_pct - research_pct, 2) if official_pct is not None else None

        c1, c2, c3 = st.columns(3)
        c1.metric("台鐵官方準點率",
                  f"{official_pct} %" if official_pct is not None else "—",
                  help="終點站到達，誤點門檻 5 分鐘（對齊台鐵月報定義）")
        c2.metric("本研究全站準點率",
                  f"{research_pct} %",
                  help="所有停靠站記錄，誤點門檻 2 分鐘")
        if diff is not None:
            c3.metric("兩者差距", f"{diff:+.2f} %",
                      delta="官方標準較寬鬆" if diff > 0 else "兩者相近")

        with st.expander("📊 兩種準點率計算方式說明", expanded=False):
            st.markdown("""
            | 計算方式 | 判定方式 | 門檻 | 資料來源依據 |
            |----------|----------|------|--------------|
            | **台鐵官方統計** | 列車抵達**終點站**，超過 5 分鐘才算誤點 | τ = 5 分鐘 | 對齊台鐵每月公告之準點率統計數字 |
            | **本研究全站統計** | 列車在**每個停靠站**到站，超過 2 分鐘即算誤點 | τ = 2 分鐘 | 參考日本 JR 及英國 Network Rail 的統計標準 |

            > **為什麼要並列兩種計算方式？**
            > 台鐵官方統計只看終點站，列車就算中途大誤點、後來追回來，就不列入誤點計算。
            > 本研究改採全站統計，可以抓到中途各站的累積延誤狀況，更能反映旅客的實際搭乘感受。
            > 兩種計算方式並列呈現，方便與台鐵官方數字直接對照，也讓研究結果更具說服力。
            """)

        st.markdown("---")

        # ── 首末班車查詢 ─────────────────────────────────────
        st.markdown("## 班次首末班時間查詢")
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
            disp["方向"] = disp["方向"].map({0: "順行", 1: "逆行"}) if "方向" in disp.columns else disp.get("方向","")
            st.dataframe(disp, use_container_width=True, hide_index=True,
                         height=min(400, 35 + len(disp) * 35))
            st.caption(f"共 {len(disp):,} 班次　｜　首班：{sdf['FirstDep'].min() if not sdf.empty else '—'}　末班：{sdf['LastArr'].max() if not sdf.empty else '—'}")

        st.markdown("---")
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("## 各車種：台鐵官方準點率")
            if not terminal_df.empty:
                d = terminal_df.groupby("TrainType")["IsDelayed_Official" if "IsDelayed_Official" in terminal_df.columns else "IsDelayed"].apply(
                    lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率").sort_values("準點率")
                fig = go.Figure(go.Bar(
                    x=d["準點率"], y=d["TrainType"], orientation="h",
                    marker_color=COLORS[:len(d)],
                    text=d["準點率"].astype(str)+"%", textposition="outside",
                ))
                fig.update_layout(**PLOTLY_THEME, height=240,
                                  xaxis=dict(**AXIS_STYLE, range=[80, 100]))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("終點站紀錄不足，請累積更多資料後再查看。")
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **台鐵官方統計方式**：只統計在終點站（`IsTerminal=1`）的到站紀錄，`DelayTime ≥ 5 分鐘`才算誤點，與台鐵每月公告的準點率計算方式相同。

                **資料來源**：交通部 TDX `StationLiveBoard` API；`IsTerminal` 欄位由 `processor` 對照 TDX 時刻表（`/Rail/TRA/GeneralTimetable`）比對終點站判定；官方準點率定義參考臺鐵每月營運統計月報。
                """)

        with col_b:
            st.markdown("## 各車種：本研究全站準點率")
            d2 = _pdf.groupby("TrainType")["IsDelayed"].apply(
                lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率").sort_values("準點率")
            fig2 = go.Figure(go.Bar(
                x=d2["準點率"], y=d2["TrainType"], orientation="h",
                marker_color=COLORS[:len(d2)],
                text=d2["準點率"].astype(str)+"%", textposition="outside",
            ))
            fig2.update_layout(**PLOTLY_THEME, height=240,
                               xaxis=dict(**AXIS_STYLE, range=[80, 100]))
            st.plotly_chart(fig2, use_container_width=True)
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **本研究全站統計方式**：涵蓋所有停靠站（含中途各站）的到站紀錄，`DelayTime ≥ 2 分鐘`即算誤點，比台鐵官方統計更能反映旅客在中途站的實際等候情形。

                **資料來源**：交通部 TDX `StationLiveBoard` API，每 10 分鐘抓取一次；準點率門檻 τ = 2 分鐘參考日本 JR 東日本及英國 Network Rail 的統計標準。
                """)

        st.markdown("---")
        st.markdown("## 各時段 × 車種準點率交叉比較")
        if "Period" in _pdf.columns:
            cross = _pdf.groupby(["Period", "TrainType"])["IsDelayed"].apply(
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
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                採用**本研究全站統計方式**（τ = 2 分鐘）。橫軸為時段、縱軸為準點率，各色長條代表不同車種。

                尖峰時段班距短、列車密度高，一旦某班車延誤，後面的班次很容易跟著卡住；
                長程車種（自強、莒光）停靠站多，中途累積誤點的機會也比較高。
                這張圖同時呈現時段（X3）與車種（X1）的交叉效應，對應本研究的核心研究假設。

                **資料來源**：交通部 TDX `StationLiveBoard` API；`Period`（時段）欄位由 `ScheduleArrivalTime` 衍生，`TrainType`（車種）欄位經 `_simplify_type()` 統一分類。
                """)

        st.markdown("---")
        st.markdown("## 假日效應")
        if "HolidayType" in _pdf.columns:
            hol = _pdf.groupby(["HolidayType", "TrainType"])["IsDelayed"].apply(
                lambda x: round((1-x.mean())*100,1)).reset_index(name="準點率")
            fig4 = px.bar(hol, x="HolidayType", y="準點率", color="TrainType",
                          barmode="group", color_discrete_sequence=COLORS)
            fig4.update_layout(**PLOTLY_THEME, height=260,
                               yaxis=dict(**AXIS_STYLE, range=[75, 100]),
                               legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b949e")))
            st.plotly_chart(fig4, use_container_width=True)
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                採用**本研究全站統計方式**（τ = 2 分鐘）。比較平日、週末、國定假日三種情境下，各車種的準點率差異。

                連假或連續假期旅運量明顯增加，但台鐵的班次數不一定同步加開，
                旅客上下車時間拉長、站停時間超秒，就容易讓誤點一站一站往後傳。
                此圖對應研究設計中假日變數（X4）的單變數視覺化。

                **資料來源**：交通部 TDX `StationLiveBoard` API；`HolidayType` 欄位由 `_is_holiday()` 函式依行政院人事行政總處公告假日判定。
                """)


# ══════════════════════════════════════════════════════════════
#  ◉  站點熱力圖  ── 強化版
# ══════════════════════════════════════════════════════════════
elif page == "站點熱力圖":
    st.markdown("""
    <div class="page-header">
        <h1>◉ 站點熱力圖</h1>
        <div class="subtitle">全台車站誤點空間分布 · GIS Visualization</div>
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"目前顯示範圍：{_date_label}")
    with st.expander("📊 地圖模式說明", expanded=False):
        st.markdown("""
        | 模式 | 說明 | 適合用途 |
        |------|------|----------|
        | **🔥 密度熱力圖** | 以每筆原始紀錄的 `DelayTime` 為權重，顯示誤點能量的地理密度 | 找出全台誤點熱點區域 |
        | **🔵 氣泡誤點圖** | 每個車站聚合成一個氣泡，顏色深淺和大小代表平均誤點或誤點率 | 比較各站間的誤點差異 |
        | **📍 車站位置** | 純地理分布，不含誤點資訊 | 確認資料涵蓋的車站範圍 |

        **聚合方式（氣泡圖）**：依 `StationName + Lat + Lon` 分組，計算：
        - 平均誤點 = `DelayTime.mean()`
        - 誤點率 = `IsDelayed.mean() × 100%`（門檻 τ = 2 分鐘）
        - 顏色梯度：🟢 綠（低）→ 🟡 黃（中）→ 🔴 紅（高）
        """)
    _work_df = filtered_df.copy() if not filtered_df.empty else pd.DataFrame()

    # ── 補充座標欄位（無條件重新 merge，防止 Lat_x/Lon_x 殘留欄位干擾）──
    if not _work_df.empty:
        _stations_coords = processor.get_stations_data()
        if not _stations_coords.empty:
            # 統一 StationID 格式：str + strip + 4 位補零
            _work_df["StationID"] = _work_df["StationID"].astype(str).str.strip().str.zfill(4)
            _stations_coords = _stations_coords.copy()
            _stations_coords["StationID"] = _stations_coords["StationID"].astype(str).str.strip().str.zfill(4)

            # ★ 修正：無條件清除舊座標與站名欄位（含 _x/_y 殘留）
            _work_df = _work_df.drop(
                columns=[c for c in [
                    "Lat", "Lon", "Lat_x", "Lon_x", "Lat_y", "Lon_y",
                    "StationName", "StationName_x", "StationName_y"
                ] if c in _work_df.columns],
                errors="ignore"
            )

            # 從 stations_coords 合併最新座標與站名
            _merge_cols = [c for c in ["StationID", "StationName", "Lat", "Lon"]
                           if c in _stations_coords.columns]
            _work_df = _work_df.merge(
                _stations_coords[_merge_cols],
                on="StationID", how="left"
            )

    if _work_df.empty or "Lat" not in _work_df.columns or _work_df["Lat"].isna().all():
        _stations_diag = processor.get_stations_data()
        # 細部診斷
        _lat_exists = "Lat" in _work_df.columns
        _lat_null = _work_df["Lat"].isna().all() if _lat_exists else "N/A"
        _sname_exists = "StationName" in _work_df.columns
        _sname_null = _work_df["StationName"].isna().all() if _sname_exists else "N/A"
        _sid_sample = str(_work_df["StationID"].iloc[0]) if not _work_df.empty else "N/A"
        _coords_sid_sample = str(_stations_diag["StationID"].iloc[0]) if not _stations_diag.empty else "N/A"
        st.warning("座標資料載入失敗，無法顯示地圖。")
        st.caption(f"_work_df columns: {list(_work_df.columns)}")
        st.caption(
            f"診斷：stations_coords={len(_stations_diag)}筆 | CLOUD_MODE={CLOUD_MODE} | "
            f"_work_df={len(_work_df)}筆 | "
            f"Lat欄位={_lat_exists}/全NaN={_lat_null} | "
            f"StationName={_sname_exists}/全NaN={_sname_null} | "
            f"StationID樣本（df）={_sid_sample} / （coords）={_coords_sid_sample}"
        )
    else:
        # ── 篩選器 ──────────────────────────────────────────
        with st.expander("🔍 篩選條件", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)

            with f_col1:
                all_types = sorted(_work_df["TrainType"].dropna().unique().tolist())
                sel_types = st.multiselect(
                    "車種", all_types, default=all_types,
                    help="選擇要納入分析的車種"
                )

            with f_col2:
                if "Period" in _work_df.columns:
                    all_periods = sorted(_work_df["Period"].dropna().unique().tolist())
                    sel_periods = st.multiselect(
                        "時段", all_periods, default=all_periods,
                        help="尖峰 / 離峰 / 深夜"
                    )
                else:
                    sel_periods = None

            with f_col3:
                map_mode = st.radio(
                    "地圖模式",
                    ["🔥 密度熱力圖", "🔵 氣泡誤點圖", "📍 車站位置"],
                    index=0,
                )

            with f_col4:
                view_metric = st.radio(
                    "顯示指標",
                    ["平均誤點（分）", "誤點率（%）"],
                    index=0,
                )

        # ── 套用篩選 ─────────────────────────────────────────
        map_df = _work_df.dropna(subset=["Lat", "Lon"]).copy()
        if sel_types:
            map_df = map_df[map_df["TrainType"].isin(sel_types)]
        if sel_periods and "Period" in map_df.columns:
            map_df = map_df[map_df["Period"].isin(sel_periods)]

        if map_df.empty:
            st.warning("篩選後無資料，請調整篩選條件。")
        else:
            # ── 聚合：以車站為單位 ───────────────────────────
            # ★ 修正：過濾掉 StationName 為空的列，避免 groupby KeyError
            map_df = map_df.dropna(subset=["StationName"])
            if map_df.empty:
                st.warning("篩選後無有效車站名稱資料，請確認 stations.json 已包含完整站名。")
            else:
                station_map = (
                    map_df.groupby(["StationName", "Lat", "Lon"])
                    .agg(
                        平均誤點=("DelayTime", "mean"),
                        筆數=("DelayTime", "count"),
                        誤點率=("IsDelayed", "mean"),
                    )
                    .reset_index()
                )
                station_map["平均誤點"] = station_map["平均誤點"].round(2)
                station_map["誤點率_pct"] = (station_map["誤點率"] * 100).round(1)

                color_col   = "平均誤點" if "平均誤點" in view_metric else "誤點率_pct"
                hover_label = "平均誤點（分）" if "平均誤點" in view_metric else "誤點率（%）"

                MAP_CENTER  = {"lat": 23.8, "lon": 121.0}
                MAP_ZOOM    = 6.5
                MAP_STYLE   = "carto-darkmatter"
                COLOR_SCALE = ["#2ea043", "#d29922", "#f85149"]   # 綠→黃→紅

                # ── 地圖繪製 ─────────────────────────────────────
                if map_mode == "🔥 密度熱力圖":
                    # 以每筆原始紀錄（含重複加權）繪製密度
                    fig = px.density_map(
                        map_df,
                        lat="Lat",
                        lon="Lon",
                        z="DelayTime",          # 權重 = 誤點分鐘
                        radius=28,
                        center=MAP_CENTER,
                        zoom=MAP_ZOOM,
                        map_style=MAP_STYLE,
                        color_continuous_scale=COLOR_SCALE,
                        range_color=[0, map_df["DelayTime"].quantile(0.95)],
                        labels={"z": "誤點分鐘（加權）"},
                        title="全台車站誤點密度熱力圖",
                    )
                    # 疊加車站位置點（半透明）
                    fig.add_trace(
                        go.Scattermap(
                            lat=station_map["Lat"],
                            lon=station_map["Lon"],
                            mode="markers+text",
                            marker=dict(size=5, color="rgba(230,237,243,0.5)"),
                            text=station_map["StationName"],
                            textfont=dict(size=9, color="rgba(230,237,243,0.6)"),
                            textposition="top right",
                            hovertemplate=(
                                "<b>%{text}</b><br>"
                                "平均誤點：%{customdata[0]} 分<br>"
                                "誤點率：%{customdata[1]}%<br>"
                                "觀測筆數：%{customdata[2]}<extra></extra>"
                            ),
                            customdata=station_map[["平均誤點", "誤點率_pct", "筆數"]].values,
                            name="車站位置",
                            showlegend=False,
                        )
                    )

                elif map_mode == "🔵 氣泡誤點圖":
                    fig = px.scatter_map(
                        station_map,
                        lat="Lat",
                        lon="Lon",
                        hover_name="StationName",
                        color=color_col,
                        size=color_col,
                        size_max=22,
                        color_continuous_scale=COLOR_SCALE,
                        zoom=MAP_ZOOM,
                        center=MAP_CENTER,
                        map_style=MAP_STYLE,
                        labels={color_col: hover_label},
                        custom_data=["StationName", "平均誤點", "誤點率_pct", "筆數"],
                    )
                    fig.update_traces(
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "平均誤點：%{customdata[1]} 分<br>"
                            "誤點率：%{customdata[2]}%<br>"
                            "觀測筆數：%{customdata[3]}<extra></extra>"
                        )
                    )

                else:  # 📍 車站位置
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scattermap(
                            lat=station_map["Lat"],
                            lon=station_map["Lon"],
                            mode="markers+text",
                            marker=dict(
                                size=10,
                                color=station_map[color_col],
                                colorscale=COLOR_SCALE,
                                colorbar=dict(
                                    title=dict(text=hover_label, font=dict(color="#8b949e")),
                                    tickfont=dict(color="#8b949e"),
                                    bgcolor="rgba(0,0,0,0)",
                                ),
                                showscale=True,
                            ),
                            text=station_map["StationName"],
                            textfont=dict(size=9, color="#e6edf3"),
                            textposition="top right",
                            hovertemplate=(
                                "<b>%{text}</b><br>"
                                f"{hover_label}：%{{customdata[0]}}<br>"
                                "觀測筆數：%{customdata[1]}<extra></extra>"
                            ),
                            customdata=station_map[[color_col, "筆數"]].values,
                            name="車站",
                        )
                    )
                    fig.update_layout(
                        map=dict(
                            style=MAP_STYLE,
                            center=MAP_CENTER,
                            zoom=MAP_ZOOM,
                        )
                    )

                # ── 統一 layout ──────────────────────────────────
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=36, b=0),
                    height=580,
                    font=dict(color="#8b949e", family="Noto Sans TC"),
                    coloraxis_colorbar=dict(
                        title=dict(text=hover_label, font=dict(color="#8b949e")),
                        tickfont=dict(color="#8b949e"),
                    ),
                )

                # ── 疊加台鐵路線幾何軌跡 ─────────────────────────────
                shapes = processor.get_shape()
                LINE_COLORS = {
                    "WestTrunkLine":  "#388bfd",
                    "SeaLine":        "#d29922",
                    "EastTrunkLine":  "#2ea043",
                    "NorthLink":      "#f85149",
                    "SouthLink":      "#bc8cff",
                    "PingTungLine":   "#79c0ff",
                    "TaiDongLine":    "#56d364",
                }
                if shapes:
                    for line_id, shape_data in shapes.items():
                        color_key = line_id.replace("TRA_", "")
                        line_color = LINE_COLORS.get(color_key, "#484f58")
                        fig.add_trace(
                            go.Scattermap(
                                lon=shape_data["lons"],
                                lat=shape_data["lats"],
                                mode="lines",
                                line=dict(width=2.5, color=line_color),
                                name=shape_data["name"],
                                hoverinfo="name",
                                showlegend=True,
                            )
                        )

                st.plotly_chart(fig, use_container_width=True)
                with st.expander("📊 資料來源說明", expanded=False):
                    st.markdown("""
                    **誤點資料**：交通部 TDX `StationLiveBoard` API，每 10 分鐘自動抓取一次，`DelayTime` 為 TDX 回傳之誤點分鐘數。

                    **車站座標**：交通部 TDX `Station` API（`/Rail/TRA/Station`），存於 `static/stations.json`，由 `processor.get_stations_data()` 載入，以 `StationID`（4 位補零）對照合併。

                    **路線軌跡**：交通部 TDX `Shape` API（`/Rail/TRA/Shape`），存於 `static/shape.json`，由 `processor.get_shape()` 載入，疊加於地圖上顯示台鐵各線路線走向。
                    """)

                # ── 下方統計面板 ─────────────────────────────────
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("車站總數", f"{len(station_map)} 站")
                m2.metric("觀測筆數", f"{int(station_map['筆數'].sum()):,}")
                m3.metric("全體平均誤點", f"{station_map['平均誤點'].mean():.2f} 分")
                m4.metric("全體誤點率",
                          f"{(map_df['IsDelayed'].mean()*100):.1f}%")

                # ── 誤點前 10 名 ─────────────────────────────────
                st.markdown("## 🔴 誤點前 10 名車站")
                top10 = (
                    station_map
                    .nlargest(10, "平均誤點")
                    [["StationName", "平均誤點", "誤點率_pct", "筆數"]]
                    .reset_index(drop=True)
                )
                top10.index = top10.index + 1   # 從 1 開始排名
                top10.columns = ["車站", "平均誤點（分）", "誤點率（%）", "觀測筆數"]

                col_tbl, col_bar = st.columns([1, 1], gap="large")
                with col_tbl:
                    st.dataframe(
                        top10.style
                        .background_gradient(
                            cmap="RdYlGn_r",
                            subset=["平均誤點（分）", "誤點率（%）"],
                        )
                        .format({
                            "平均誤點（分）": "{:.2f}",
                            "誤點率（%）": "{:.1f}%",
                            "觀測筆數": "{:,}",
                        }),
                        use_container_width=True,
                    )

                with col_bar:
                    fig_bar = go.Figure(
                        go.Bar(
                            x=top10["平均誤點（分）"],
                            y=top10["車站"],
                            orientation="h",
                            marker=dict(
                                color=top10["平均誤點（分）"],
                                colorscale=COLOR_SCALE,
                                showscale=False,
                            ),
                            text=top10["平均誤點（分）"].apply(lambda v: f"{v:.2f} 分"),
                            textposition="outside",
                            textfont=dict(size=11, color="#8b949e"),
                        )
                    )
                    fig_bar.update_layout(
                        **PLOTLY_THEME,
                        height=360,
                        yaxis=dict(**AXIS_STYLE, autorange="reversed"),
                        xaxis=dict(**AXIS_STYLE, title="平均誤點（分）"),
                        title="Top 10 高誤點車站",
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                    with st.expander("📊 說明", expanded=False):
                        st.markdown("""
                        **計算方式**：依 `StationName` 聚合，取各站 `DelayTime` 算術平均，選取前 10 名。

                        **資料來源**：交通部 TDX `StationLiveBoard` API；車站座標來自 TDX `Station` API（`static/stations.json`）。
                        """)

                # ── 車站誤點分布（直方圖）────────────────────────
                st.markdown("---")
                st.markdown("## 📊 各車站平均誤點分布")
                fig_hist = go.Figure(
                    go.Histogram(
                        x=station_map["平均誤點"],
                        nbinsx=25,
                        marker_color=GREEN,
                        opacity=0.85,
                    )
                )
                fig_hist.update_layout(
                    **PLOTLY_THEME,
                    height=220,
                    xaxis=dict(**AXIS_STYLE, title="平均誤點（分）"),
                    yaxis=dict(**AXIS_STYLE, title="車站數"),
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                with st.expander("📊 說明", expanded=False):
                    st.markdown("""
                    **計算方式**：先對每個車站的 `DelayTime` 取算術平均，再將各站平均誤點值繪製成直方圖，橫軸為平均誤點分鐘數，縱軸為車站數量。

                    **資料來源**：交通部 TDX `StationLiveBoard` API；車站座標來自 TDX `Station` API（`static/stations.json`）。
                    """)

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

    _rdf = filtered_research_df  # 使用日期篩選後的研究資料集
    st.caption(f"目前顯示範圍：{_date_label}　共 {len(_rdf):,} 筆觀測")

    with st.expander("📊 模型設計說明", expanded=False):
        st.markdown("""
        **應變數（Y）**：
        - **OLS**：`DelayTime`（連續，誤點分鐘數）
        - **Logit**：`IsDelayed`（二元，τ = 2 分鐘）

        **自變數（X）與對應研究假設**：

        | 變數 | 欄位 | 說明 |
        |------|------|------|
        | 車種（X1） | `IsZiQiang` 等虛擬變數 | 基準組 = 區間；傾斜式自強為最高速車種 |
        | 停靠順序（X2） | `StopSeq` | 停靠越後面累積誤點越多 |
        | 尖峰時段（X3） | `IsPeak` | 尖峰班距緊，誤點傳遞效應強 |
        | 假日（X4） | `IsHoliday` | 旅運量增加，停靠時間延長 |
        | 前站誤點（X9） | `PrevDelay` | 誤點傳遞，最強預測因子 |

        **顯著性判定**：`*** p<0.001`、`** p<0.01`、`* p<0.05`、`† p<0.1`

        **係數圖解讀**：橫條中心點 = β 估計值，橫條長度 = 95% 信賴區間（±1.96 × SE）。
        跨越 0 的橫條表示該變數在統計上不顯著影響誤點。
        """)

    if _rdf.empty or len(_rdf) < 30:
        st.warning(f"資料量不足（目前 {len(_rdf):,} 筆），建議累積至少 1,000 筆後執行迴歸。")
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
            reg_df = _rdf.dropna(
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
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **圖形說明**：每個點代表一個自變數的 OLS/Logit 估計係數（β），橫條為 95% 信賴區間（±1.96 × 標準誤）。
                🟢 綠色點 = 正向效果（誤點增加）、🔴 紅色點 = 負向效果（誤點減少）。
                橫條跨越 0 虛線者表示該變數在統計上不顯著。

                **資料來源**：交通部 TDX `StationLiveBoard` API 彙整後的研究資料集（`research_dataset.csv`），
                由 `processor.build_research_dataset()` 建構，包含各班次 × 車站層級的面板資料。
                迴歸分析使用 Python `statsmodels` 套件執行。
                """)

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
            with st.expander("📊 說明", expanded=False):
                st.markdown("""
                **計算方式**：依 `Category`（原因類別）欄位計算各類別件數佔比。

                **資料來源**：交通部 TDX `Alert` API（`/Rail/TRA/Alert`），存於 `data/alerts/` 目錄，
                由 `processor.parse_alerts()` 解析；`Category` 欄位為本研究依通報內文關鍵字自動分類。
                """)
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
        <div class="subtitle">API 金鑰管理 · 資料蒐集控制 · 匯出工具 · 目錄監控</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="large")

    # ── 左欄：API 金鑰 & 靜態資料 ─────────────────────────────
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
        if CLOUD_MODE:
            st.info("雲端模式：靜態資料由 GitHub Actions 每日 06:00 自動更新。")
        else:
            # 顯示各靜態檔案的現有狀態
            static_files = {
                "stations.json": "車站座標",
                "train_types.json": "車種定義",
                "line_network.json": "路線網路",
            }
            for fname, label in static_files.items():
                fpath = os.path.join(DATA_DIR, "static", fname)
                if os.path.exists(fpath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    size_kb = os.path.getsize(fpath) / 1024
                    age_hrs = (datetime.now() - mtime).total_seconds() / 3600
                    badge = "badge-green" if age_hrs < 24 else "badge-yellow" if age_hrs < 168 else "badge-red"
                    st.markdown(
                        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;'
                        f'margin-bottom:4px;">'
                        f'<span class="badge {badge}" style="margin-right:8px;">{label}</span>'
                        f'<span style="color:#8b949e;">{mtime.strftime("%m/%d %H:%M")} · {size_kb:.1f} KB</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;'
                        f'margin-bottom:4px;">'
                        f'<span class="badge badge-red" style="margin-right:8px;">{label}</span>'
                        f'<span style="color:#8b949e;">尚未下載</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1:
                if st.button("↺ 車站座標", use_container_width=True):
                    with st.spinner("抓取中..."):
                        crawl_stations()
                    st.success("車站座標已更新")
            with c_s2:
                if st.button("↺ 時刻表", use_container_width=True):
                    with st.spinner("抓取中..."):
                        crawl_timetable()
                    st.success("時刻表已更新")
            with c_s3:
                if st.button("↺ 車種/路線", use_container_width=True):
                    with st.spinner("抓取中..."):
                        try:
                            from crawlers.train_type import crawl_train_types
                            from crawlers.line_network import crawl_line_network
                            from crawlers.shape import crawl_shape
                            crawl_train_types()
                            crawl_line_network()
                            crawl_shape()
                            st.success("車種與路線資料已更新")
                        except Exception as e:
                            st.error(f"抓取失敗：{e}")

    # ── 右欄：手動抓取 & 匯出 ─────────────────────────────────
    with col_r:
        st.markdown("## 手動資料抓取")
        if CLOUD_MODE:
            st.info("雲端模式：資料由 Mac mini 定期推送至 GitHub，此處無法手動抓取。")
        else:
            st.markdown(
                '<div style="font-size:0.8rem;color:#8b949e;margin-bottom:12px;">'
                '⚠ 自動抓取由 launchd 排程負責（每3分鐘），此處僅供手動補抓。'
                '</div>',
                unsafe_allow_html=True
            )
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                if st.button("▶ 即時板 + 通報", use_container_width=True, type="primary"):
                    with st.spinner("抓取中..."):
                        crawl_live_board()
                        crawl_alerts()
                    st.success("抓取完成")
            with c_m2:
                if st.button("▶ 時刻表（今日）", use_container_width=True):
                    with st.spinner("抓取時刻表..."):
                        crawl_timetable()
                    st.success("時刻表抓取完成")

        st.markdown("---")
        st.markdown("## 資料匯出")
        c_e1, c_e2 = st.columns(2)
        with c_e1:
            if st.button("📥 匯出原始 CSV", use_container_width=True):
                out = os.path.join(DATA_DIR, "processed_data.csv")
                df.to_csv(out, index=False, encoding="utf-8-sig")
                st.success(f"已匯出（{len(df):,} 筆）")
        with c_e2:
            if st.button("🔬 匯出研究資料集", use_container_width=True):
                out = processor.export_research_csv()
                if out:
                    st.success(f"已匯出（{len(research_df):,} 筆）")

    # ── 資料目錄狀況（全寬） ──────────────────────────────────
    st.markdown("---")
    st.markdown("## 資料目錄狀況")

    DIR_CONFIG = [
        {"key": "live_board",   "label": "即時板 TrainLiveBoard",   "icon": "🚂", "pattern_daily": True},
        {"key": "station_live", "label": "站板 StationLiveBoard",   "icon": "🏟", "pattern_daily": True},
        {"key": "alerts",       "label": "異常通報 Alerts",          "icon": "⚠",  "pattern_daily": True},
        {"key": "timetable",    "label": "時刻表 Timetable",         "icon": "📅", "pattern_daily": False},
        {"key": "static",       "label": "靜態資料 Static",          "icon": "📌", "pattern_daily": False},
    ]

    dir_cols = st.columns(len(DIR_CONFIG))

    for col, cfg in zip(dir_cols, DIR_CONFIG):
        base = os.path.join(DATA_DIR, cfg["key"])
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;color:#8b949e;font-family:IBM Plex Mono,monospace;'
                f'text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">'
                f'{cfg["icon"]} {cfg["key"]}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div style="font-size:0.8rem;color:#e6edf3;margin-bottom:8px;font-weight:600;">'
                f'{cfg["label"]}</div>',
                unsafe_allow_html=True
            )

            if not os.path.isdir(base):
                st.markdown('<span class="badge badge-red">目錄不存在</span>', unsafe_allow_html=True)
                continue

            if cfg["pattern_daily"]:
                date_dirs = sorted(glob.glob(os.path.join(base, "????-??-??")))
                if not date_dirs:
                    st.markdown('<span class="badge badge-red">無資料</span>', unsafe_allow_html=True)
                else:
                    total_files = sum(
                        len(glob.glob(os.path.join(d, "*.json"))) for d in date_dirs
                    )
                    today_dir = os.path.join(base, datetime.now().strftime("%Y-%m-%d"))
                    today_n = len(glob.glob(os.path.join(today_dir, "*.json"))) if os.path.isdir(today_dir) else 0
                    badge_cls = "badge-green" if today_n > 0 else "badge-red"
                    st.markdown(
                        f'<span class="badge {badge_cls}">今日 {today_n} 筆</span>'
                        f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;'
                        f'color:#8b949e;margin-left:6px;">累計 {total_files:,}</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown('<div style="margin-top:6px;"></div>', unsafe_allow_html=True)
                    for d_path in date_dirs[-5:]:
                        d_name = os.path.basename(d_path)
                        d_jsons = glob.glob(os.path.join(d_path, "*.json"))
                        n = len(d_jsons)
                        dir_size_kb = sum(os.path.getsize(f) for f in d_jsons) / 1024
                        is_today = d_name == datetime.now().strftime("%Y-%m-%d")
                        name_color = "#2ea043" if is_today else "#8b949e"
                        st.markdown(
                            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;'
                            f'padding:2px 0;border-bottom:1px solid #21262d;display:flex;'
                            f'justify-content:space-between;">'
                            f'<span style="color:{name_color};">{d_name}</span>'
                            f'<span style="color:#e6edf3;">{n} <span style="color:#8b949e;">筆</span>'
                            f' / {dir_size_kb:.0f}<span style="color:#8b949e;">KB</span></span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            else:
                json_files = sorted(glob.glob(os.path.join(base, "*.json")))
                if not json_files:
                    st.markdown('<span class="badge badge-red">無資料</span>', unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<span class="badge badge-green">{len(json_files)} 個檔案</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown('<div style="margin-top:6px;"></div>', unsafe_allow_html=True)
                    for fpath in json_files[-8:]:
                        fname = os.path.basename(fpath)
                        size_kb = os.path.getsize(fpath) / 1024
                        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                        age_hrs = (datetime.now() - mtime).total_seconds() / 3600
                        dot_color = "#2ea043" if age_hrs < 24 else "#d29922" if age_hrs < 168 else "#f85149"
                        st.markdown(
                            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;'
                            f'padding:2px 0;border-bottom:1px solid #21262d;">'
                            f'<span style="color:{dot_color};">●</span> '
                            f'<span style="color:#e6edf3;">{fname}</span><br>'
                            f'<span style="color:#8b949e;padding-left:12px;">'
                            f'{mtime.strftime("%m/%d %H:%M")} · {size_kb:.1f} KB</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

    # ── 整體磁碟用量摘要 ──────────────────────────────────────
    st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
    total_size_mb = 0.0
    total_json = 0
    for root, _, files in os.walk(DATA_DIR):
        for f in files:
            if f.endswith(".json"):
                fp = os.path.join(root, f)
                total_size_mb += os.path.getsize(fp) / (1024 * 1024)
                total_json += 1
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    csv_size_mb = sum(os.path.getsize(f) for f in csv_files) / (1024 * 1024)

    st.markdown(
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#8b949e;'
        f'background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 16px;">'
        f'JSON 檔案　<span style="color:#2ea043;">{total_json:,}</span> 個　'
        f'<span style="color:#e6edf3;">{total_size_mb:.1f} MB</span>'
        f'　　CSV 匯出　<span style="color:#388bfd;">{len(csv_files)}</span> 個　'
        f'<span style="color:#e6edf3;">{csv_size_mb:.1f} MB</span>'
        f'　　合計　<span style="color:#e6edf3;">{(total_size_mb + csv_size_mb):.1f} MB</span>'
        f'</div>',
        unsafe_allow_html=True
    )
