import pandas as pd
import streamlit as st


DEFAULTS = {
    "global_date_filter": "全部日期",
    "global_train_type_filter": "全部車種",
    "global_period_filter": "全部時段",
    "global_direction_filter": "全部方向",
    "global_trip_line_filter": "全部線別",
}

PERIOD_ORDER = ["尖峰", "離峰", "深夜", "未知"]
DIRECTION_LABELS = {
    0: "順行（基→高）",
    1: "逆行（高→基）",
}
TRIP_LINE_LABELS = {
    0: "山線",
    1: "海線",
    2: "成追線",
}


def ensure_filter_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _sync_option(key: str, options: list[str]) -> None:
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]


def _sorted_unique(frame: pd.DataFrame, column: str, order: list[str] | None = None) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    values = [str(v).strip() for v in frame[column].dropna().tolist() if str(v).strip()]
    unique_values = sorted(set(values))
    if order:
        ranked = {name: idx for idx, name in enumerate(order)}
        unique_values = sorted(unique_values, key=lambda item: (ranked.get(item, len(ranked)), item))
    return unique_values


def _normalize_numeric(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _direction_options(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "Direction" not in frame.columns:
        return []
    options = []
    for value in sorted({_normalize_numeric(v) for v in frame["Direction"].dropna().tolist()}):
        if value is None:
            continue
        options.append(DIRECTION_LABELS.get(value, f"方向 {value}"))
    return options


def _trip_line_options(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "TripLine" not in frame.columns:
        return []
    options = []
    for value in sorted({_normalize_numeric(v) for v in frame["TripLine"].dropna().tolist()}):
        if value is None:
            continue
        options.append(TRIP_LINE_LABELS.get(value, f"線別 {value}"))
    return options


def render_global_filters(df: pd.DataFrame) -> dict[str, str]:
    ensure_filter_state()

    date_options = ["全部日期"] + _sorted_unique(df, "Date")[::-1]
    train_type_options = ["全部車種"] + _sorted_unique(df, "TrainType")
    period_options = ["全部時段"] + _sorted_unique(df, "Period", PERIOD_ORDER)
    direction_options = ["全部方向"] + _direction_options(df)
    trip_line_options = ["全部線別"] + _trip_line_options(df)

    _sync_option("global_date_filter", date_options)
    _sync_option("global_train_type_filter", train_type_options)
    _sync_option("global_period_filter", period_options)
    _sync_option("global_direction_filter", direction_options)
    _sync_option("global_trip_line_filter", trip_line_options)

    cols = st.columns([1.35, 1.0, 1.0, 1.0, 1.0, 0.7], gap="large")
    with cols[0]:
        st.selectbox("日期", date_options, key="global_date_filter")
    with cols[1]:
        st.selectbox("車種", train_type_options, key="global_train_type_filter")
    with cols[2]:
        st.selectbox("時段", period_options, key="global_period_filter")
    with cols[3]:
        st.selectbox("方向", direction_options, key="global_direction_filter")
    with cols[4]:
        st.selectbox("線別", trip_line_options, key="global_trip_line_filter")
    with cols[5]:
        st.markdown("<div style='height: 1.6rem;'></div>", unsafe_allow_html=True)
        if st.button("重置", use_container_width=True):
            for key, value in DEFAULTS.items():
                st.session_state[key] = value
            st.rerun()

    return {
        "date": st.session_state["global_date_filter"],
        "train_type": st.session_state["global_train_type_filter"],
        "period": st.session_state["global_period_filter"],
        "direction": st.session_state["global_direction_filter"],
        "trip_line": st.session_state["global_trip_line_filter"],
    }


def _filter_frame(frame: pd.DataFrame, state: dict[str, str]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    filtered = frame.copy()
    if state["date"] != "全部日期" and "Date" in filtered.columns:
        filtered = filtered[filtered["Date"].astype(str) == state["date"]]
    if state["train_type"] != "全部車種" and "TrainType" in filtered.columns:
        filtered = filtered[filtered["TrainType"].astype(str) == state["train_type"]]
    if state["period"] != "全部時段" and "Period" in filtered.columns:
        filtered = filtered[filtered["Period"].astype(str) == state["period"]]
    if state["direction"] != "全部方向" and "Direction" in filtered.columns:
        direction_value = next(
            (key for key, label in DIRECTION_LABELS.items() if label == state["direction"]),
            None,
        )
        if direction_value is not None:
            filtered = filtered[pd.to_numeric(filtered["Direction"], errors="coerce") == direction_value]
    if state["trip_line"] != "全部線別" and "TripLine" in filtered.columns:
        trip_line_value = next(
            (key for key, label in TRIP_LINE_LABELS.items() if label == state["trip_line"]),
            None,
        )
        if trip_line_value is not None:
            filtered = filtered[pd.to_numeric(filtered["TripLine"], errors="coerce") == trip_line_value]
    return filtered.copy()


def apply_global_filters(
    df: pd.DataFrame,
    research_df: pd.DataFrame,
    state: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _filter_frame(df, state), _filter_frame(research_df, state)


def build_scope_label(state: dict[str, str]) -> str:
    if state["date"] == "全部日期":
        return "📅 全部日期"
    return f"📅 {state['date']}"


def render_scope_summary(state: dict[str, str], filtered_df: pd.DataFrame) -> None:
    pills = []
    for value in state.values():
        if value.startswith("全部"):
            continue
        pills.append(f'<span class="scope-pill">{value}</span>')
    if not pills:
        pills.append('<span class="scope-pill">全樣本</span>')

    st.markdown(
        f"""
        <div class="scope-strip">
            <div>
                <div class="eyebrow">Current Scope</div>
                <div class="headline">{len(filtered_df):,} 筆觀測落在目前條件內</div>
            </div>
            <div class="pills">{''.join(pills)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
