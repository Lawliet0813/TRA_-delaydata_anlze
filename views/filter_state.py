"""
春節研究版全域篩選器：年份 / 春節節點 / 車種 / 路線區段。
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from cny_processor import CNY_PERIOD_ORDER


DEFAULTS = {
    "cny_years": [],
    "cny_periods": [],
    "cny_train_types": [],
    "cny_regions": [],
}

TRAIN_TYPE_ORDER = [
    "自強號 (含EMU3000)",
    "莒光號",
    "復興號/區間快",
    "區間快車",
    "區間車",
    "對號列車(7字頭)",
    "春節加班車",
    "其他對號",
    "未知",
]

REGION_ORDER = [
    "縱貫線北段",
    "縱貫線中段",
    "縱貫線南段",
    "南迴/屏東線",
    "台東線",
    "宜蘭/北迴線",
    "其他",
    "未知",
]


def ensure_filter_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = list(value)


def _ordered_unique(frame: pd.DataFrame, column: str, order: list[str] | None) -> list:
    if frame is None or frame.empty or column not in frame.columns:
        return []
    values = [v for v in frame[column].dropna().unique().tolist()]
    if order:
        ranked = {name: idx for idx, name in enumerate(order)}
        values = sorted(values, key=lambda item: (ranked.get(str(item), len(ranked)), str(item)))
    else:
        values = sorted(values)
    return values


def render_global_filters(df: pd.DataFrame) -> dict:
    """在頁面頂端渲染春節四維篩選器，並回傳當前狀態字典。"""
    ensure_filter_state()

    years = _ordered_unique(df, "年", None)
    periods = _ordered_unique(df, "春節節點", CNY_PERIOD_ORDER)
    train_types = _ordered_unique(df, "車種", TRAIN_TYPE_ORDER)
    regions = _ordered_unique(df, "路線區段", REGION_ORDER)

    cols = st.columns([1.1, 1.6, 1.4, 1.4, 0.6], gap="large")
    with cols[0]:
        st.multiselect(
            "年份",
            years,
            default=st.session_state["cny_years"],
            key="cny_years",
            placeholder="全部年份",
        )
    with cols[1]:
        st.multiselect(
            "春節節點",
            periods,
            default=st.session_state["cny_periods"],
            key="cny_periods",
            placeholder="全部節點",
        )
    with cols[2]:
        st.multiselect(
            "車種",
            train_types,
            default=st.session_state["cny_train_types"],
            key="cny_train_types",
            placeholder="全部車種",
        )
    with cols[3]:
        st.multiselect(
            "路線區段",
            regions,
            default=st.session_state["cny_regions"],
            key="cny_regions",
            placeholder="全部路線",
        )
    with cols[4]:
        st.markdown("<div style='height: 1.6rem;'></div>", unsafe_allow_html=True)
        if st.button("重置", use_container_width=True):
            for key, value in DEFAULTS.items():
                st.session_state[key] = list(value)
            st.rerun()

    return {
        "years": st.session_state["cny_years"],
        "periods": st.session_state["cny_periods"],
        "train_types": st.session_state["cny_train_types"],
        "regions": st.session_state["cny_regions"],
    }


def apply_global_filters(
    df_perceived: pd.DataFrame,
    df_official: pd.DataFrame,
    state: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """對感知（B）與官方（A）兩張表同時套用篩選。"""
    from cny_processor import apply_cny_filters

    perceived = apply_cny_filters(
        df_perceived,
        years=state.get("years") or None,
        periods=state.get("periods") or None,
        train_types=state.get("train_types") or None,
        regions=state.get("regions") or None,
    )
    # 官方表以「路線區段_資料推導終點」作為路線欄位，需要轉欄名處理
    if df_official is not None and not df_official.empty:
        tmp = df_official.copy()
        if "路線區段_資料推導終點" in tmp.columns and "路線區段" not in tmp.columns:
            tmp["路線區段"] = tmp["路線區段_資料推導終點"]
        official = apply_cny_filters(
            tmp,
            years=state.get("years") or None,
            periods=state.get("periods") or None,
            train_types=state.get("train_types") or None,
            regions=state.get("regions") or None,
        )
    else:
        official = df_official
    return perceived, official


def build_scope_label(state: dict) -> str:
    if state.get("years"):
        return "📅 " + "、".join(str(y) for y in state["years"])
    return "📅 2022–2026 合併"


def render_scope_summary(state: dict, filtered_df: pd.DataFrame) -> None:
    pills = []
    if state.get("years"):
        pills.append(f'<span class="scope-pill">年份：{"、".join(str(y) for y in state["years"])}</span>')
    if state.get("periods"):
        for p in state["periods"]:
            pills.append(f'<span class="scope-pill">{p}</span>')
    if state.get("train_types"):
        for t in state["train_types"]:
            pills.append(f'<span class="scope-pill">{t}</span>')
    if state.get("regions"):
        for r in state["regions"]:
            pills.append(f'<span class="scope-pill">{r}</span>')
    if not pills:
        pills.append('<span class="scope-pill">五年全樣本</span>')

    count = len(filtered_df) if filtered_df is not None else 0
    st.markdown(
        f"""
        <div class="scope-strip">
            <div>
                <div class="eyebrow">目前分析範圍</div>
                <div class="headline">目前條件下共有 {count:,} 筆觀測值</div>
            </div>
            <div class="pills">{''.join(pills)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
