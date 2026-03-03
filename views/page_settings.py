"""
系統設定 (Settings) — API Keys, Data Management, Directory Status
"""
import streamlit as st
import os
import glob
from datetime import datetime
from views.theme import BLUE, GREEN, YELLOW, RED, TEXT_SECONDARY, TEXT_MUTED, BORDER
from views.components import page_header, section_title, status_badge
from processor import CLOUD_MODE


def render(df, research_df, processor, DATA_DIR, CLIENT_ID, CLIENT_SECRET,
           crawl_live_board=None, crawl_alerts=None, crawl_timetable=None,
           crawl_stations=None, **kwargs):
    page_header("⚙", "系統設定中心", "API 金鑰管理 · 資料蒐集控制 · 匯出工具 · 目錄監控")

    col_l, col_r = st.columns(2, gap="large")

    # ── Left: API Keys & Static Data ──────────────────────────
    with col_l:
        section_title("API 金鑰設定")
        cid  = st.text_input("TDX Client ID",     value=CLIENT_ID,     type="password")
        csec = st.text_input("TDX Client Secret", value=CLIENT_SECRET, type="password")
        if st.button("💾 儲存 API 設定", use_container_width=True):
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            with open(env_path, "w") as f:
                f.write(f'TDX_CLIENT_ID="{cid}"\nTDX_CLIENT_SECRET="{csec}"\n')
            st.success("API 設定已儲存")

        st.markdown("---")
        section_title("靜態資料更新")
        if CLOUD_MODE:
            st.info("雲端模式：靜態資料由 GitHub Actions 每日 06:00 自動更新。")
        else:
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
                    badge_color = "green" if age_hrs < 24 else "yellow" if age_hrs < 168 else "red"
                    st.markdown(
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.75rem;'
                        f'margin-bottom:4px;">'
                        f'{status_badge(label, badge_color)} '
                        f'<span style="color:{TEXT_SECONDARY};margin-left:8px;">'
                        f'{mtime.strftime("%m/%d %H:%M")} · {size_kb:.1f} KB</span>'
                        f'</div>', unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.75rem;'
                        f'margin-bottom:4px;">'
                        f'{status_badge(label, "red")} '
                        f'<span style="color:{TEXT_SECONDARY};margin-left:8px;">尚未下載</span>'
                        f'</div>', unsafe_allow_html=True)

            st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1:
                if st.button("↺ 車站座標", use_container_width=True):
                    if crawl_stations:
                        with st.spinner("抓取中..."):
                            crawl_stations()
                        st.success("車站座標已更新")
            with c_s2:
                if st.button("↺ 時刻表", use_container_width=True):
                    if crawl_timetable:
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

    # ── Right: Manual Crawl & Export ──────────────────────────
    with col_r:
        section_title("手動資料抓取")
        if CLOUD_MODE:
            st.info("雲端模式：資料由 GitHub Actions 推送至 GitHub，此處無法手動抓取。")
        else:
            st.markdown(
                f'<div style="font-size:0.8rem;color:{TEXT_SECONDARY};margin-bottom:12px;">'
                '⚠ 自動抓取由排程負責，此處僅供手動補抓。</div>',
                unsafe_allow_html=True)
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                if st.button("▶ 即時板 + 通報", use_container_width=True, type="primary"):
                    if crawl_live_board and crawl_alerts:
                        with st.spinner("抓取中..."):
                            crawl_live_board()
                            crawl_alerts()
                        st.success("抓取完成")
            with c_m2:
                if st.button("▶ 時刻表（今日）", use_container_width=True):
                    if crawl_timetable:
                        with st.spinner("抓取時刻表..."):
                            crawl_timetable()
                        st.success("時刻表抓取完成")

        st.markdown("---")
        section_title("資料匯出")
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

    # ── Directory Status ──────────────────────────────────────
    st.markdown("---")
    section_title("資料目錄狀況")

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
                f'<div class="dir-card">'
                f'<div class="header">{cfg["icon"]} {cfg["key"]}</div>'
                f'<div class="label">{cfg["label"]}</div>',
                unsafe_allow_html=True)

            if not os.path.isdir(base):
                st.markdown(f'{status_badge("目錄不存在", "red")}</div>', unsafe_allow_html=True)
                continue

            if cfg["pattern_daily"]:
                date_dirs = sorted(glob.glob(os.path.join(base, "????-??-??")))
                if not date_dirs:
                    st.markdown(f'{status_badge("無資料", "red")}</div>', unsafe_allow_html=True)
                else:
                    total_files = sum(len(glob.glob(os.path.join(d, "*.json"))) for d in date_dirs)
                    today_dir = os.path.join(base, datetime.now().strftime("%Y-%m-%d"))
                    today_n = len(glob.glob(os.path.join(today_dir, "*.json"))) if os.path.isdir(today_dir) else 0
                    badge_color = "green" if today_n > 0 else "red"

                    st.markdown(
                        f'{status_badge(f"今日 {today_n} 筆", badge_color)}'
                        f'<span style="font-family:JetBrains Mono,monospace;font-size:0.72rem;'
                        f'color:{TEXT_SECONDARY};margin-left:6px;">累計 {total_files:,}</span>',
                        unsafe_allow_html=True)

                    rows_html = ""
                    for d_path in date_dirs[-5:]:
                        d_name = os.path.basename(d_path)
                        n = len(glob.glob(os.path.join(d_path, "*.json")))
                        dir_size_kb = sum(os.path.getsize(f) for f in glob.glob(os.path.join(d_path, "*.json"))) / 1024
                        is_today = d_name == datetime.now().strftime("%Y-%m-%d")
                        today_class = " today" if is_today else ""
                        rows_html += (
                            f'<div class="row{today_class}">'
                            f'<span class="name">{d_name}</span>'
                            f'<span class="val">{n} 筆 / {dir_size_kb:.0f}KB</span>'
                            f'</div>')
                    st.markdown(rows_html + '</div>', unsafe_allow_html=True)
            else:
                json_files = sorted(glob.glob(os.path.join(base, "*.json")))
                if not json_files:
                    st.markdown(f'{status_badge("無資料", "red")}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'{status_badge(f"{len(json_files)} 個檔案", "green")}',
                        unsafe_allow_html=True)

                    rows_html = ""
                    for fpath in json_files[-6:]:
                        fname = os.path.basename(fpath)
                        size_kb = os.path.getsize(fpath) / 1024
                        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                        age_hrs = (datetime.now() - mtime).total_seconds() / 3600
                        dot_color = GREEN if age_hrs < 24 else YELLOW if age_hrs < 168 else RED
                        rows_html += (
                            f'<div class="row">'
                            f'<span class="name"><span style="color:{dot_color};">●</span> {fname}</span>'
                            f'<span class="val">{mtime.strftime("%m/%d %H:%M")}</span>'
                            f'</div>')
                    st.markdown(rows_html + '</div>', unsafe_allow_html=True)

    # ── Storage Summary ───────────────────────────────────────
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

    st.markdown(f"""
    <div class="storage-bar">
        <div class="item">
            <span class="dot" style="background:{BLUE};"></span>
            JSON <span class="val">{total_json:,}</span> 個 · <span class="val">{total_size_mb:.1f} MB</span>
        </div>
        <div class="item">
            <span class="dot" style="background:{GREEN};"></span>
            CSV <span class="val">{len(csv_files)}</span> 個 · <span class="val">{csv_size_mb:.1f} MB</span>
        </div>
        <div class="item">
            合計 <span class="val">{(total_size_mb + csv_size_mb):.1f} MB</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
