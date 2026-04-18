"""
春節臺鐵誤點研究 — Streamlit 主程式

資料來源為 2022–2026 年春節期間歷史誤點資料（交通部公開資料），
分析結果來自 `data/cny/` 下的 parquet / csv / json，對應昨天跑完的
`RAWdata/analysis/` 輸出。
"""
import os

import streamlit as st

from cny_processor import CNYDataStore
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
import views.page_cny_trend as page_cny_trend
import views.page_cny_period as page_cny_period
import views.page_threshold as page_threshold
import views.page_heatmap as page_heatmap
import views.page_anova_chi2 as page_anova_chi2
import views.page_tukey as page_tukey
import views.page_paired as page_paired
import views.page_logistic as page_logistic
import views.page_method as page_method
import views.page_raw_preview as page_raw_preview


# ══════════════════════════════════════════════════════════════
#  頁面設定 & 主題
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="春節臺鐵誤點研究",
    layout="wide",
    page_icon="🧧",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CNY_DIR = os.path.join(BASE_DIR, "data", "cny")
STATIONS_COORDS_PATH = os.path.join(BASE_DIR, "data", "stations_coords.csv")

store = CNYDataStore(CNY_DIR)


# ══════════════════════════════════════════════════════════════
#  資料載入（快取）
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def load_perceived():
    return store.load_metric_perceived()


@st.cache_data(ttl=3600)
def load_official():
    return store.load_metric_official()


@st.cache_data(ttl=3600)
def load_threshold():
    return store.load_threshold_sensitivity()


@st.cache_data(ttl=3600)
def load_inferential():
    return store.load_inferential()


@st.cache_data(ttl=3600)
def load_stations_coords():
    import pandas as pd

    if os.path.exists(STATIONS_COORDS_PATH):
        return pd.read_csv(STATIONS_COORDS_PATH, dtype={"StationID": str})
    return pd.DataFrame()


perceived_df = load_perceived()
official_df = load_official()
threshold_df = load_threshold()
inferential = load_inferential()
stations_coords = load_stations_coords()


# ══════════════════════════════════════════════════════════════
#  導覽結構
# ══════════════════════════════════════════════════════════════
NAV_GROUPS = [
    {
        "label": "研究總覽",
        "pages": [
            ("首頁", "⬡"),
            ("資料總覽", "◈"),
        ],
    },
    {
        "label": "描述統計",
        "pages": [
            ("年度誤點趨勢", "≈"),
            ("春節節點比較", "⟡"),
            ("閾值敏感度", "◇"),
            ("車站熱力圖", "◉"),
        ],
    },
    {
        "label": "推論統計",
        "pages": [
            ("ANOVA 與卡方", "χ"),
            ("Tukey 事後比較", "△"),
            ("配對 t 檢定", "⇌"),
            ("Logistic 迴歸", "≋"),
        ],
    },
    {
        "label": "方法與資料",
        "pages": [
            ("方法論", "✎"),
            ("原始資料預覽", "☰"),
        ],
    },
]

PAGE_COPY = {
    "首頁": "春節誤點研究的核心發現、資料來源與指標定義。",
    "資料總覽": "2022–2026 五年春節期間觀測數與結構分布。",
    "年度誤點趨勢": "逐年平均誤點與準點率變化，觀察 2025 異常峰值。",
    "春節節點比較": "除夕前至春節後各節點的誤點分布差異。",
    "閾值敏感度": "改變準點判定閾值（1/3/5/10 分鐘）對 A 官方與 B 感知兩指標的衝擊。",
    "車站熱力圖": "五年春節期間各站平均誤點的空間分布。",
    "ANOVA 與卡方": "年份與誤點 / 準點的差異是否顯著。",
    "Tukey 事後比較": "六個春節節點間的兩兩比較結果。",
    "配對 t 檢定": "指標 A（終點站延誤）與指標 B（全程平均延誤）的系統性落差。",
    "Logistic 迴歸": "在控制車種、路線、節點後，年份與節點對準點的獨立效果。",
    "方法論": "變項定義、春節節點切分規則、資料清理流程。",
    "原始資料預覽": "檢視 2022–2026 逐年原始 CSV 樣本。",
}


# ══════════════════════════════════════════════════════════════
#  側邊欄
# ══════════════════════════════════════════════════════════════
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

    meta = inferential.get("meta", {})
    st.markdown(
        '<span class="badge badge-green">展示鏡像 · 2022–2026</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:4px;">'
        f"A 官方 {meta.get('A筆數', 0):,} 筆 · B 感知 {meta.get('B筆數', 0):,} 筆"
        "</div>",
        unsafe_allow_html=True,
    )

    sidebar_stats(
        data_source="交通部公開資料（2022–2026 春節）",
        total_count=len(perceived_df),
        date_range_start="2022-01-28",
    )


# ══════════════════════════════════════════════════════════════
#  標題列
# ══════════════════════════════════════════════════════════════
page = st.session_state.nav
page_group = next(
    (group["label"] for group in NAV_GROUPS if any(name == page for name, _ in group["pages"])),
    "研究總覽",
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

global_filter_state = render_global_filters(perceived_df)
filtered_perceived, filtered_official = apply_global_filters(
    perceived_df, official_df, global_filter_state
)
_scope_label = build_scope_label(global_filter_state)

toolbar_cols = st.columns([1.0, 1.0, 0.7], gap="large")
with toolbar_cols[0]:
    st.markdown(
        f"""
        <div class="toolbar-stat">
            <div class="label">分析範圍</div>
            <div class="value">{_scope_label}</div>
            <div class="meta">五年春節合併預設</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with toolbar_cols[1]:
    st.markdown(
        f"""
        <div class="toolbar-stat">
            <div class="label">目前樣本（B 感知）</div>
            <div class="value">{len(filtered_perceived):,} 筆</div>
            <div class="meta">全資料共 {len(perceived_df):,} 筆</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with toolbar_cols[2]:
    st.markdown("<div style='height: 1.6rem;'></div>", unsafe_allow_html=True)
    if st.button("↺ 重新整理", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

render_scope_summary(global_filter_state, filtered_perceived)


# ══════════════════════════════════════════════════════════════
#  頁面路由
# ══════════════════════════════════════════════════════════════
context = {
    "perceived": filtered_perceived,
    "official": filtered_official,
    "perceived_all": perceived_df,
    "official_all": official_df,
    "threshold": threshold_df,
    "inferential": inferential,
    "stations_coords": stations_coords,
    "scope_label": _scope_label,
    "filter_state": global_filter_state,
    "store": store,
}

if page == "首頁":
    page_home.render(context)
elif page == "資料總覽":
    page_overview.render(context)
elif page == "年度誤點趨勢":
    page_cny_trend.render(context)
elif page == "春節節點比較":
    page_cny_period.render(context)
elif page == "閾值敏感度":
    page_threshold.render(context)
elif page == "車站熱力圖":
    page_heatmap.render(context)
elif page == "ANOVA 與卡方":
    page_anova_chi2.render(context)
elif page == "Tukey 事後比較":
    page_tukey.render(context)
elif page == "配對 t 檢定":
    page_paired.render(context)
elif page == "Logistic 迴歸":
    page_logistic.render(context)
elif page == "方法論":
    page_method.render(context)
elif page == "原始資料預覽":
    page_raw_preview.render(context)
