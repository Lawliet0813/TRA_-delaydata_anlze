"""
爬蟲監控儀表板 — 本機 launchd 狀態、採集統計、執行日誌與模式比較
"""
import streamlit as st
import os
import glob
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import plotly.graph_objects as go

from views.theme import (
    BLUE, GREEN, YELLOW, RED, CYAN, PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER,
    BG_SECONDARY, PLOTLY_THEME, AXIS_STYLE,
)
from views.components import page_header, kpi_card, section_title, status_badge, glass_container
from processor import CLOUD_MODE

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, "Library", "Logs")

AGENTS = [
    {
        "label": "com.lawliet.tra.live",
        "name": "即時板",
        "icon": "◉",
        "log": os.path.join(LOG_DIR, "tra_live_local.log"),
        "schedule": "每 10 分鐘",
        "color": BLUE,
    },
    {
        "label": "com.lawliet.tra.alert",
        "name": "整點通報與 CSV",
        "icon": "◈",
        "log": os.path.join(LOG_DIR, "tra_hourly_local.log"),
        "schedule": "每小時整點",
        "color": GREEN,
    },
    {
        "label": "com.lawliet.tra.timetable",
        "name": "時刻表",
        "icon": "◷",
        "log": os.path.join(LOG_DIR, "tra_timetable_local.log"),
        "schedule": "每日 06:05",
        "color": CYAN,
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────

def get_launchd_status() -> dict:
    """呼叫 launchctl list，回傳各 label 的 {pid, exit_code, running} dict。"""
    result = {}
    try:
        out = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, timeout=5
        ).stdout
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                pid_str, exit_str, label = parts
                for agent in AGENTS:
                    if agent["label"] == label.strip():
                        running = pid_str.strip() != "-"
                        result[label.strip()] = {
                            "pid": pid_str.strip(),
                            "exit_code": int(exit_str.strip()),
                            "running": running,
                            "loaded": True,
                        }
    except Exception:
        pass
    for agent in AGENTS:
        if agent["label"] not in result:
            result[agent["label"]] = {"pid": "-", "exit_code": -1, "running": False, "loaded": False}
    return result


def read_log_tail(path: str, n: int = 25) -> list[str]:
    """讀取 log 檔最後 n 行。"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-n:]]
    except Exception:
        return []


def parse_last_run(path: str) -> str | None:
    """從 log 的 [DONE] 或 [SKIP] 行解析最後執行時間。"""
    lines = read_log_tail(path, 50)
    for line in reversed(lines):
        for tag in ("[DONE]", "[SKIP]", "[PUSHED]", "[ERROR]"):
            if tag in line:
                try:
                    return line.split(" ")[0] + " " + line.split(" ")[1]
                except Exception:
                    return None
    return None


def parse_last_record_count(path: str) -> str:
    """從 hourly log 解析最後匯出的筆數。"""
    lines = read_log_tail(path, 30)
    for line in reversed(lines):
        if "匯出完成" in line and "筆" in line:
            try:
                return line.split("（")[1].split("筆")[0].strip() + " 筆"
            except Exception:
                pass
    return "—"


def count_today_files(data_dir: str, subdir: str) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    d = os.path.join(data_dir, subdir, today)
    if not os.path.isdir(d):
        return 0
    return len(glob.glob(os.path.join(d, "*.json")))


def hourly_collection_chart(data_dir: str) -> go.Figure:
    """繪製今日各小時 station_live 採集筆數。"""
    today = datetime.now().strftime("%Y-%m-%d")
    d = os.path.join(data_dir, "station_live", today)
    hour_counts = defaultdict(int)
    if os.path.isdir(d):
        for f in glob.glob(os.path.join(d, "*.json")):
            fname = os.path.basename(f)
            try:
                hour = int(fname[:2])
                hour_counts[hour] += 1
            except Exception:
                pass
    hours = list(range(6, 24))
    counts = [hour_counts.get(h, 0) for h in hours]
    labels = [f"{h:02d}:00" for h in hours]
    fig = go.Figure(go.Bar(
        x=labels, y=counts,
        marker=dict(
            color=[BLUE if c > 0 else "rgba(255,255,255,0.04)" for c in counts],
            line=dict(color="rgba(0,0,0,0)", width=0),
        ),
        hovertemplate="%{x}：%{y} 次<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        height=200,
        title=dict(text="今日各小時採集次數（station_live）", font_size=12, x=0, y=0.98),
        xaxis=dict(**AXIS_STYLE, tickfont_size=10),
        yaxis=dict(**AXIS_STYLE, tickfont_size=10, title="次數"),
        bargap=0.3,
    )
    return fig


# ── Render ─────────────────────────────────────────────────────────────────

def render(data_dir: str):
    page_header("◆", "爬蟲監控儀表板", "launchd 排程狀態、採集統計、執行日誌與模式比較")

    if CLOUD_MODE:
        st.info("雲端模式下此頁面不可用。資料由 GitHub Actions 負責採集，"
                "請至 GitHub 儲存庫的 Actions 頁面查看執行紀錄。")
        return

    # ══ 自動重新整理 ════════════════════════════════════════════════════════
    col_title, col_refresh = st.columns([6, 1])
    with col_refresh:
        if st.button("↺ 重新整理", use_container_width=True):
            st.rerun()

    # ══ Section 1：launchd Agent 狀態 ══════════════════════════════════════
    section_title("LAUNCHD AGENT 狀態")
    statuses = get_launchd_status()
    agent_cols = st.columns(3)

    for col, agent in zip(agent_cols, AGENTS):
        s = statuses[agent["label"]]
        last_run = parse_last_run(agent["log"])

        if not s["loaded"]:
            badge_text, badge_color = "未載入", "red"
            dot_color = RED
        elif s["running"]:
            badge_text, badge_color = f"執行中 PID {s['pid']}", "blue"
            dot_color = BLUE
        elif s["exit_code"] == 0:
            badge_text, badge_color = "閒置", "green"
            dot_color = GREEN
        else:
            badge_text, badge_color = f"錯誤 exit={s['exit_code']}", "red"
            dot_color = RED

        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                    <span style="font-size:1.1rem;color:{agent['color']};">{agent['icon']}</span>
                    <span style="font-size:0.82rem;font-weight:600;color:{TEXT_PRIMARY};">{agent['name']}</span>
                </div>
                <div style="display:inline-flex;align-items:center;gap:6px;
                    padding:4px 10px;border-radius:12px;margin-bottom:10px;
                    background:rgba(255,255,255,0.04);border:1px solid {BORDER};">
                    <span style="width:7px;height:7px;border-radius:50%;background:{dot_color};
                        display:inline-block;box-shadow:0 0 6px {dot_color};"></span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                        color:{TEXT_PRIMARY};">{badge_text}</span>
                </div>
                <div style="font-size:0.73rem;color:{TEXT_MUTED};font-family:'JetBrains Mono',monospace;">
                    排程　{agent['schedule']}<br>
                    最後執行　{last_run or '尚無記錄'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ══ Section 2：今日採集統計 ════════════════════════════════════════════
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    section_title("今日採集統計")

    live_today = count_today_files(data_dir, "station_live")
    alert_today = count_today_files(data_dir, "alerts")

    # 計算 station_live 今日資料大小
    today = datetime.now().strftime("%Y-%m-%d")
    sl_dir = os.path.join(data_dir, "station_live", today)
    size_mb = 0.0
    if os.path.isdir(sl_dir):
        size_mb = sum(
            os.path.getsize(f)
            for f in glob.glob(os.path.join(sl_dir, "*.json"))
        ) / (1024 * 1024)

    # 最後一次 CSV 推送時間
    last_push = parse_last_run(AGENTS[1]["log"])
    last_record = parse_last_record_count(AGENTS[1]["log"])

    stat_cols = st.columns(4)
    with stat_cols[0]:
        color = "green" if live_today > 0 else "red"
        kpi_card("即時板 JSON 今日", str(live_today), color, "station_live 檔案數")
    with stat_cols[1]:
        color = "green" if alert_today > 0 else "yellow"
        kpi_card("通報資料今日", str(alert_today), color, "alerts 檔案數")
    with stat_cols[2]:
        kpi_card("今日資料量", f"{size_mb:.1f} MB", "blue", "station_live JSON")
    with stat_cols[3]:
        kpi_card("最後 CSV 推送", last_push.split(" ")[1][:5] if last_push else "—", "",
                 f"{last_record}")

    # 採集分佈圖
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(
        hourly_collection_chart(data_dir),
        use_container_width=True,
    )

    # ══ Section 3：Log 查閱 ════════════════════════════════════════════════
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    section_title("最新執行日誌")

    tab_live, tab_hourly, tab_timetable = st.tabs([
        "◉  即時板", "◈  整點通報與 CSV", "◷  時刻表"
    ])

    for tab, agent in zip([tab_live, tab_hourly, tab_timetable], AGENTS):
        with tab:
            lines = read_log_tail(agent["log"], 30)
            if not lines:
                st.caption(f"尚無記錄 · {agent['log']}")
            else:
                # 對不同狀態的行上色
                colored = []
                for line in lines:
                    if "[ERROR]" in line:
                        c = RED
                    elif "[WARN]" in line:
                        c = YELLOW
                    elif "[DONE]" in line or "[PUSHED]" in line:
                        c = GREEN
                    elif "[START]" in line:
                        c = BLUE
                    elif "[SKIP]" in line:
                        c = TEXT_MUTED
                    else:
                        c = TEXT_SECONDARY
                    safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    colored.append(f'<span style="color:{c};">{safe}</span>')

                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border:1px solid {BORDER};
                    border-radius:10px;padding:16px;font-family:'JetBrains Mono',monospace;
                    font-size:0.72rem;line-height:1.8;overflow-x:auto;">
                    {"<br>".join(colored)}
                </div>
                <div style="font-size:0.7rem;color:{TEXT_MUTED};margin-top:6px;">
                    {agent['log']}
                </div>
                """, unsafe_allow_html=True)

    # ══ Section 4：GitHub Actions vs 本地比較 ══════════════════════════════
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    section_title("GitHub Actions 與本機 launchd 比較")

    rows = [
        ("排程方式",        "GitHub 伺服器排程（cron）",  "launchd StartInterval / StartCalendarInterval"),
        ("可用性",          "全天候執行（不需開機）",      "需 Mac 開機且不可休眠"),
        ("憑證管理",        "GitHub Secrets（加密）",    ".env 明文（存本機）"),
        ("Python 版本",    "3.11（Ubuntu）",             "3.14（本機 venv）"),
        ("Raw JSON 推送",  "✅ Force push（占用儲存庫空間）", "❌ 保留本機，節省空間"),
        ("CSV 推送機制",   "同一儲存庫直接 commit",        "複製到 ~/tra_git_push 後再 push"),
        ("並發衝突處理",   "concurrency group 保護",     "單一 process，無衝突"),
        ("執行日誌",       "GitHub Actions 介面（90 天）",  "~/Library/Logs/tra_*.log"),
        ("失敗通知",       "電子郵件自動通知",              "需手動查看日誌"),
        ("執行成本",       "消耗 Actions 免費額度",       "本機電力"),
        ("當前狀態",       "⏸ 已暫停（workflow_dispatch）", "▶ 運行中（launchd loaded）"),
    ]

    header_style = (
        f"font-size:0.7rem;color:{TEXT_MUTED};text-transform:uppercase;"
        f"letter-spacing:0.8px;font-weight:600;padding:8px 14px;"
        f"border-bottom:1px solid {BORDER};"
    )
    row_style_base = (
        f"font-size:0.8rem;padding:8px 14px;border-bottom:1px solid rgba(255,255,255,0.02);"
    )

    rows_html = ""
    for i, (dim, gh, local) in enumerate(rows):
        bg = "background:rgba(255,255,255,0.015);" if i % 2 == 0 else ""
        rows_html += f"""
        <tr style="{bg}">
            <td style="{row_style_base}color:{TEXT_SECONDARY};font-weight:500;">{dim}</td>
            <td style="{row_style_base}color:{TEXT_PRIMARY};">{gh}</td>
            <td style="{row_style_base}color:{TEXT_PRIMARY};">{local}</td>
        </tr>"""

    st.markdown(f"""
    <div style="border:1px solid {BORDER};border-radius:12px;overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="{header_style}width:22%;">面向</th>
                    <th style="{header_style}width:39%;color:{YELLOW};">GitHub Actions</th>
                    <th style="{header_style}width:39%;color:{GREEN};">本地 launchd</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # 手動啟動按鈕
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    section_title("手動觸發")
    btn_c1, btn_c2, btn_c3, _ = st.columns([1, 1, 1, 2])
    with btn_c1:
        if st.button("▶ 立即抓取即時板", use_container_width=True):
            with st.spinner("執行中..."):
                r = subprocess.run(
                    ["/bin/zsh", os.path.join(data_dir, "..", "scripts", "tra_live.sh")],
                    capture_output=True, text=True, timeout=30
                )
            if r.returncode == 0:
                st.success("抓取完成，請重新整理")
            else:
                st.error(f"失敗：{r.stderr[:200]}")
    with btn_c2:
        if st.button("▶ 立即執行整點流程", use_container_width=True):
            with st.spinner("執行中（約 10 秒）..."):
                r = subprocess.run(
                    ["/bin/zsh", os.path.join(data_dir, "..", "scripts", "tra_hourly.sh")],
                    capture_output=True, text=True, timeout=120
                )
            if r.returncode == 0:
                st.success("匯出並推送完成，請重新整理")
            else:
                st.error(f"失敗：{r.stderr[:300]}")
    with btn_c3:
        if st.button("▶ 抓取時刻表", use_container_width=True):
            with st.spinner("執行中..."):
                r = subprocess.run(
                    ["/bin/zsh", os.path.join(data_dir, "..", "scripts", "tra_timetable.sh")],
                    capture_output=True, text=True, timeout=60
                )
            if r.returncode == 0:
                st.success("時刻表抓取完成")
            else:
                st.error(f"失敗：{r.stderr[:200]}")
