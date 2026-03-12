"""
系統設定 — 系統與資料維運頁
"""
import glob
import os
from datetime import datetime

import streamlit as st

from processor import CLOUD_MODE
from views.components import kpi_card, note_card, page_header, section_title, status_badge, story_card
from views.theme import BLUE, GREEN, RED, TEXT_MUTED, TEXT_SECONDARY, YELLOW


def _collect_storage_stats(data_dir: str) -> dict:
    total_json = 0
    total_json_mb = 0.0
    for root, _, files in os.walk(data_dir):
        for fname in files:
            if fname.endswith(".json"):
                full_path = os.path.join(root, fname)
                total_json += 1
                total_json_mb += os.path.getsize(full_path) / (1024 * 1024)
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    csv_size_mb = sum(os.path.getsize(path) for path in csv_files) / (1024 * 1024)
    return {
        "json_count": total_json,
        "json_mb": total_json_mb,
        "csv_count": len(csv_files),
        "csv_mb": csv_size_mb,
        "total_mb": total_json_mb + csv_size_mb,
    }


def _dir_card_html(title: str, lines: list[str]) -> str:
    body = "".join(lines)
    return f"""
    <div class="dir-card">
        <div class="header">{title}</div>
        {body}
    </div>
    """


def _render_static_assets(data_dir: str) -> None:
    section_title("靜態資料資產")
    static_files = {
        "stations.json": "車站座標",
        "train_types.json": "車種定義",
        "line_network.json": "路線網路",
        "shape.json": "路網形狀",
    }
    rows = []
    for fname, label in static_files.items():
        path = os.path.join(data_dir, "static", fname)
        if os.path.exists(path):
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            badge_color = "green" if age_hours < 24 else "yellow" if age_hours < 168 else "red"
            rows.append(
                f"""
                <div class="compact-item">
                    <div class="term">{label}</div>
                    <div class="desc">{status_badge(mtime.strftime("%m/%d %H:%M"), badge_color)}
                    <span style="margin-left:8px;color:{TEXT_SECONDARY};">{os.path.getsize(path) / 1024:.1f} KB</span></div>
                </div>
                """
            )
        else:
            rows.append(
                f"""
                <div class="compact-item">
                    <div class="term">{label}</div>
                    <div class="desc">{status_badge("尚未建立", "red")}</div>
                </div>
                """
            )
    st.markdown(f'<div class="compact-list">{"".join(rows)}</div>', unsafe_allow_html=True)


def _render_manual_actions(
    df,
    research_df,
    processor,
    data_dir,
    crawl_live_board=None,
    crawl_alerts=None,
    crawl_timetable=None,
    crawl_stations=None,
) -> None:
    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        section_title("手動補抓")
        if CLOUD_MODE:
            note_card(
                "雲端模式",
                "目前資料由 GitHub Actions 自動更新。雲端部署環境僅供展示，不在此執行爬蟲或寫入憑證。",
            )
        else:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("補抓即時板與通報", use_container_width=True, type="primary"):
                    if crawl_live_board and crawl_alerts:
                        with st.spinner("抓取中..."):
                            crawl_live_board()
                            crawl_alerts()
                        st.success("已完成即時板與通報補抓")
                if st.button("更新車站資料", use_container_width=True):
                    if crawl_stations:
                        with st.spinner("抓取車站資料..."):
                            crawl_stations()
                        st.success("車站資料已更新")
            with c2:
                if st.button("更新今日時刻表", use_container_width=True):
                    if crawl_timetable:
                        with st.spinner("抓取時刻表..."):
                            crawl_timetable()
                        st.success("今日時刻表已更新")
                if st.button("更新路網與車種", use_container_width=True):
                    with st.spinner("抓取路網資料..."):
                        try:
                            from crawlers.line_network import crawl_line_network
                            from crawlers.shape import crawl_shape
                            from crawlers.train_type import crawl_train_types

                            crawl_train_types()
                            crawl_line_network()
                            crawl_shape()
                            st.success("路網與車種資料已更新")
                        except Exception as exc:
                            st.error(f"抓取失敗：{exc}")
            note_card(
                "使用原則",
                "這裡只保留資料補採與匯出操作，不處理 API 金鑰。金鑰應由環境變數或部署平台憑證機制統一管理。",
            )

    with right:
        section_title("資料匯出")
        e1, e2 = st.columns(2)
        with e1:
            if st.button("匯出原始 CSV", use_container_width=True):
                out = os.path.join(data_dir, "processed_data.csv")
                df.to_csv(out, index=False, encoding="utf-8-sig")
                st.success(f"已匯出原始資料（{len(df):,} 筆）")
        with e2:
            if st.button("匯出研究資料集", use_container_width=True):
                out = processor.export_research_csv()
                if out:
                    st.success(f"已匯出研究資料（{len(research_df):,} 筆）")
        note_card(
            "輸出用途",
            "原始 CSV 適合做資料備份與檢查，研究資料集則是後續回歸與報告圖表的主要輸入。",
        )


def _render_directory_health(data_dir: str) -> None:
    section_title("資料目錄健康度")
    dir_specs = [
        ("station_live", "站板資料", True),
        ("alerts", "異常通報", True),
        ("timetable", "時刻表", False),
        ("static", "靜態資料", False),
    ]
    cols = st.columns(len(dir_specs))
    today_str = datetime.now().strftime("%Y-%m-%d")

    for col, (folder, label, daily_pattern) in zip(cols, dir_specs):
        base = os.path.join(data_dir, folder)
        with col:
            if not os.path.isdir(base):
                st.markdown(
                    _dir_card_html(
                        label,
                        [f'<div class="label">{status_badge("目錄不存在", "red")}</div>'],
                    ),
                    unsafe_allow_html=True,
                )
                continue

            if daily_pattern:
                date_dirs = sorted(glob.glob(os.path.join(base, "????-??-??")))
                total_files = sum(len(glob.glob(os.path.join(path, "*.json"))) for path in date_dirs)
                today_dir = os.path.join(base, today_str)
                today_count = len(glob.glob(os.path.join(today_dir, "*.json"))) if os.path.isdir(today_dir) else 0
                color = "green" if today_count > 0 else "red"
                recent_lines = [
                    f'<div class="label">{status_badge(f"今日 {today_count} 筆", color)}</div>',
                    f'<div class="row"><span class="name">累計檔案</span><span class="val">{total_files:,}</span></div>',
                ]
                for path in date_dirs[-3:]:
                    dname = os.path.basename(path)
                    count = len(glob.glob(os.path.join(path, "*.json")))
                    recent_lines.append(
                        f'<div class="row"><span class="name">{dname}</span><span class="val">{count}</span></div>'
                    )
                st.markdown(_dir_card_html(label, recent_lines), unsafe_allow_html=True)
            else:
                json_files = sorted(glob.glob(os.path.join(base, "*.json")))
                color = "green" if json_files else "red"
                lines = [f'<div class="label">{status_badge(f"{len(json_files)} 個檔案", color)}</div>']
                for path in json_files[-4:]:
                    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%m/%d %H:%M")
                    lines.append(
                        f'<div class="row"><span class="name">{os.path.basename(path)}</span><span class="val">{mtime}</span></div>'
                    )
                st.markdown(_dir_card_html(label, lines), unsafe_allow_html=True)


def render(
    df,
    research_df,
    processor,
    DATA_DIR,
    CLIENT_ID,
    CLIENT_SECRET,
    crawl_live_board=None,
    crawl_alerts=None,
    crawl_timetable=None,
    crawl_stations=None,
    **kwargs,
):
    page_header("⚙", "系統與資料中心", "環境狀態、資料資產、補抓工具與輸出管理")

    environment_name = "雲端 / GitHub Raw" if CLOUD_MODE else "本機 / launchd"
    secret_status = "由部署環境管理" if CLOUD_MODE else "由本機 .env 管理"
    storage = _collect_storage_stats(DATA_DIR)

    top_left, top_right = st.columns([1.15, 1.0], gap="large")
    with top_left:
        section_title("系統狀態")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi_card("執行模式", environment_name, "blue")
        with k2:
            kpi_card("原始資料", f"{len(df):,} 筆", "green")
        with k3:
            kpi_card("研究資料", f"{len(research_df):,} 筆", "yellow")
        with k4:
            kpi_card("總儲存量", f"{storage['total_mb']:.1f} MB", "blue")

        note_card(
            "憑證處理",
            f"TDX API 金鑰不再於介面中顯示或編輯，統一改由 {secret_status}，避免展示頁面承擔憑證管理責任。",
        )

    with top_right:
        section_title("本頁用途")
        story_card(
            "資料維運",
            "補抓與匯出",
            "保留爬蟲補採、CSV 匯出與目錄檢查，方便整理研究資料流程。",
            tone="blue",
        )
        story_card(
            "安全性",
            "不顯示金鑰",
            "將介面與憑證管理分離，避免在本機或雲端展示時暴露機敏資訊。",
            tone="green",
        )
        story_card(
            "研究導向",
            "資料先於設定",
            "這頁現在優先回答資料是否健康、檔案是否完整、是否需要補抓。",
            tone="yellow",
        )

    st.markdown("---")
    left, right = st.columns([1.0, 1.0], gap="large")
    with left:
        _render_static_assets(DATA_DIR)
    with right:
        section_title("儲存摘要")
        st.markdown(
            f"""
            <div class="compact-list">
                <div class="compact-item">
                    <div class="term">JSON</div>
                    <div class="desc">{storage['json_count']:,} 個檔案，約 {storage['json_mb']:.1f} MB</div>
                </div>
                <div class="compact-item">
                    <div class="term">CSV</div>
                    <div class="desc">{storage['csv_count']} 個檔案，約 {storage['csv_mb']:.1f} MB</div>
                </div>
                <div class="compact-item">
                    <div class="term">資料目錄</div>
                    <div class="desc" style="word-break:break-all;">{DATA_DIR}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        note_card(
            "建議",
            "如果這頁主要用於展示，維持資訊型呈現即可；真正的憑證與部署調整應留在環境變數、GitHub Secrets 或雲端平台後台。",
        )

    st.markdown("---")
    _render_manual_actions(
        df=df,
        research_df=research_df,
        processor=processor,
        data_dir=DATA_DIR,
        crawl_live_board=crawl_live_board,
        crawl_alerts=crawl_alerts,
        crawl_timetable=crawl_timetable,
        crawl_stations=crawl_stations,
    )

    st.markdown("---")
    _render_directory_health(DATA_DIR)
