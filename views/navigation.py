import streamlit as st


FILTER_KEY_MAP = {
    "date": "global_date_filter",
    "train_type": "global_train_type_filter",
    "period": "global_period_filter",
    "direction": "global_direction_filter",
    "trip_line": "global_trip_line_filter",
}


def goto_page(
    page: str,
    filters: dict[str, str] | None = None,
    tracker_date: str | None = None,
    tracker_train_no: str | None = None,
) -> None:
    if filters:
        for key, value in filters.items():
            session_key = FILTER_KEY_MAP.get(key)
            if session_key and value:
                st.session_state[session_key] = value

    if tracker_date:
        st.session_state["tracker_prefill_date"] = tracker_date
    if tracker_train_no:
        st.session_state["tracker_prefill_train_no"] = str(tracker_train_no)

    st.session_state.nav = page
    st.rerun()
