import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from config import CLIENT_ID, CLIENT_SECRET, DATA_DIR
from processor import DataProcessor, CLOUD_MODE

if not CLOUD_MODE:
    from crawlers.station_live import crawl_station_live
    from crawlers.alert import crawl_alerts
    from crawlers.daily_timetable import crawl_daily_timetable
    from crawlers.station import crawl_stations

from views.theme import CSS, TEXT_MUTED
from views.components import sidebar_brand, sidebar_stats
from views.filter_state import (
    apply_global_filters,
    build_scope_label,
    render_global_filters,
    render_scope_summary,
)

import views.page_home as page_home
import views.page_overview as page_overview
import views.page_punctuality as page_punctuality
import views.page_heatmap as page_heatmap
import views.page_regression as page_regression
import views.page_train_tracker as page_train_tracker
import views.page_system_status as page_system_status

# ══════════════════════════════════════════════════════════════
#  頁面設定 & 主題
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="TRA 誤點研究指揮中心",
    layout="wide",
    page_icon="🚆",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  資料載入
# ══════════════════════════════════════════════════════════════
processor = DataProcessor(DATA_DIR)


@st.cache_data(ttl=180)
def load_data():
    df = processor.parse_station_live()
    rd = processor.build_research_dataset()
    return df, rd


@st.cache_data(ttl=3600)
def load_train_schedule():
    """載入首末班車時間表（train_schedule.csv）"""
    if CLOUD_MODE:
        from datetime import datetime as _dt
        _base = os.environ.get(
            "GITHUB_RAW_BASE",
            "https://raw.githubusercontent.com/Lawliet0813/TRA_-delaydata_anlze/main/data",
        )
        url = f"{_base}/train_schedule.csv?v={int(_dt.now().timestamp())}"
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
#  側邊欄 / 導覽架構
# ══════════════════════════════════════════════════════════════
NAV_GROUPS = [
    {
        "label": "總覽",
        "pages": [
            ("首頁", "⬡"),
            ("資料總覽", "◈"),
        ],
    },
    {
        "label": "診斷",
        "pages": [
            ("準點率分析", "◎"),
            ("車站熱力圖", "◉"),
            ("車次追蹤", "◷"),
            ("OLS 迴歸", "≋"),
        ],
    },
    {
        "label": "維運",
        "pages": [
            ("系統與資料狀態", "⚙"),
        ],
    },
]
PAGE_COPY = {
    "首頁": "研究主畫面，先看整體趨勢、目前樣態與最值得追的異常。",
    "資料總覽": "用描述統計拆解誤點的趨勢、比較與分布。",
    "準點率分析": "比較官方口徑與研究口徑，檢查準點率落差出在哪裡。",
    "車站熱力圖": "從車站與路網空間分布理解誤點集中的區段。",
    "車次追蹤": "追單一車次的全程表現，確認延誤如何沿線累積。",
    "OLS 迴歸": "用可解釋的營運變數拆出風險與嚴重度的主要因素。",
    "系統與資料狀態": "把資料中心、異常通報與爬蟲監控整合在同一個維運入口。",
}

today = datetime.now().strftime("%Y-%m-%d")
status_badge_cls = "badge-red"
status_txt = "NO DATA"
last_update_txt = ""
data_source = "—"
files_today = []

if CLOUD_MODE:
    if not df.empty:
        last_date = str(df["Date"].max())
        status_badge_cls = "badge-green" if last_date == today else "badge-yellow"
        status_txt = f"雲端 · {last_date}"
        last_update_txt = f"最後資料日期 {last_date}"
    data_source = "GitHub Actions 雲端排程"
else:
    today_dir = os.path.join(DATA_DIR, "station_live", today)
    files_today = (
        sorted(glob.glob(os.path.join(today_dir, "*.json")))
        if os.path.isdir(today_dir) else []
    )
    if files_today:
        t_str = os.path.basename(files_today[-1]).replace(".json", "")
        try:
            last_dt = datetime.strptime(
                f"{today} {t_str[:2]}:{t_str[2:4]}:{t_str[4:6]}",
                "%Y-%m-%d %H:%M:%S",
            )
            mins = int((datetime.now() - last_dt).total_seconds() / 60)
            if mins <= 5:
                status_badge_cls, status_txt = "badge-green", f"即時 · {mins} 分鐘前"
            elif mins <= 15:
                status_badge_cls, status_txt = "badge-yellow", f"延遲 · {mins} 分鐘前"
            else:
                status_badge_cls, status_txt = "badge-red", f"中斷 · {mins} 分鐘"
            last_update_txt = f"最後更新 {last_dt.strftime('%H:%M:%S')}"
        except Exception:
            status_badge_cls, status_txt = "badge-yellow", "狀態不明"
    data_source = f"{len(files_today)} 次"

with st.sidebar:
    sidebar_brand()

    if "nav" not in st.session_state:
        st.session_state.nav = "首頁"

    for group in NAV_GROUPS:
        st.markdown(
            f'<div class="sidebar-group-label">{group["label"]}</div>',
            unsafe_allow_html=True,
        )
        for name, icon in group["pages"]:
            is_active = st.session_state.nav == name
            if st.button(
                f"{icon}  {name}",
                key=f"nav_{name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.nav = name
                st.rerun()

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.06);margin:16px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<span class="badge {status_badge_cls}">{status_txt}</span>',
        unsafe_allow_html=True,
    )
    if last_update_txt:
        st.markdown(
            f'<div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:4px;">'
            f"{last_update_txt}</div>",
            unsafe_allow_html=True,
        )

    sidebar_stats(
        data_source=data_source,
        total_count=len(df),
        date_range_start=str(df["Date"].min()) if not df.empty else "—",
    )

page = st.session_state.nav
page_group = next(
    (group["label"] for group in NAV_GROUPS if any(name == page for name, _ in group["pages"])),
    "總覽",
)

st.markdown(
    f"""
    <div class="toolbar-shell">
        <div class="toolbar-title">{page_group}</div>
        <div class="toolbar-heading">{page}</div>
        <div class="toolbar-copy">{PAGE_COPY.get(page, '')}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

global_filter_state = render_global_filters(df)
filtered_df, filtered_research_df = apply_global_filters(df, research_df, global_filter_state)
_date_label = build_scope_label(global_filter_state)

toolbar_cols = st.columns([1.0, 1.0, 0.7], gap="large")
with toolbar_cols[0]:
    st.markdown(
        f"""
        <div class="toolbar-stat">
            <div class="label">資料狀態</div>
            <div class="value">{status_txt}</div>
            <div class="meta">{last_update_txt or '等待新資料'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with toolbar_cols[1]:
    st.markdown(
        f"""
        <div class="toolbar-stat">
            <div class="label">目前樣本</div>
            <div class="value">{len(filtered_df):,} 筆</div>
            <div class="meta">全資料共 {len(df):,} 筆</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with toolbar_cols[2]:
    st.markdown("<div style='height: 1.6rem;'></div>", unsafe_allow_html=True)
    if st.button("↺ 重新整理", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

render_scope_summary(global_filter_state, filtered_df)

# ══════════════════════════════════════════════════════════════
#  頁面路由
# ══════════════════════════════════════════════════════════════
_crawl_kwargs: dict = {}
if not CLOUD_MODE:
    _crawl_kwargs = dict(
        crawl_live_board=crawl_station_live,
        crawl_alerts=crawl_alerts,
        crawl_timetable=crawl_daily_timetable,
        crawl_stations=crawl_stations,
    )

if page == "首頁":
    page_home.render(df, filtered_df=filtered_df, date_label=_date_label)
elif page == "資料總覽":
    page_overview.render(df, filtered_df=filtered_df, date_label=_date_label)
elif page == "準點率分析":
    page_punctuality.render(
        df, filtered_df=filtered_df,
        date_label=_date_label, schedule_df=schedule_df,
    )
elif page == "車站熱力圖":
    page_heatmap.render(
        df, filtered_df=filtered_df,
        date_label=_date_label, processor=processor,
    )
elif page == "車次追蹤":
    page_train_tracker.render(filtered_df, schedule_df=schedule_df, processor=processor)
elif page == "OLS 迴歸":
    page_regression.render(
        df, filtered_research_df=filtered_research_df, date_label=_date_label,
    )
elif page == "系統與資料狀態":
    page_system_status.render(
        df=df, research_df=research_df, processor=processor,
        DATA_DIR=DATA_DIR, CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET,
        **_crawl_kwargs,
    )
