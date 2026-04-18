import streamlit as st

import views.page_alerts as page_alerts
import views.page_crawler_monitor as page_crawler_monitor
import views.page_settings as page_settings


def render(
    df,
    research_df,
    processor,
    DATA_DIR,
    CLIENT_ID,
    CLIENT_SECRET,
    **kwargs,
):
    tabs = st.tabs(["資料中心", "異常通報", "爬蟲監控"])

    with tabs[0]:
        page_settings.render(
            df=df,
            research_df=research_df,
            processor=processor,
            DATA_DIR=DATA_DIR,
            CLIENT_ID=CLIENT_ID,
            CLIENT_SECRET=CLIENT_SECRET,
            **kwargs,
        )

    with tabs[1]:
        page_alerts.render(processor=processor)

    with tabs[2]:
        page_crawler_monitor.render(data_dir=DATA_DIR)
