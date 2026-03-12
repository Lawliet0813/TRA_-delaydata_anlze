"""
Design System — TRA Delay Research Dashboard
============================================
Rail Operations Board · Research-first visual language
"""

# ── Color Palette ──────────────────────────────────────────────
BG_PRIMARY    = "#07111a"
BG_SECONDARY  = "#0c1722"
BG_TERTIARY   = "#142231"
BORDER        = "rgba(173, 194, 214, 0.12)"
BORDER_HOVER  = "rgba(75,163,255,0.42)"

BLUE          = "#4ba3ff"
BLUE_GLOW     = "rgba(75,163,255,0.22)"
GREEN         = "#35c48b"
YELLOW        = "#f1b84b"
RED           = "#f26b5e"
PURPLE        = "#8ca8ff"
CYAN          = "#3cc9d6"

TEXT_PRIMARY   = "#eef5fb"
TEXT_SECONDARY = "#9eb0c4"
TEXT_MUTED     = "#5d7187"

COLORS = [BLUE, GREEN, YELLOW, RED, PURPLE, CYAN]

# ── Plotly Theme ───────────────────────────────────────────────
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(12,23,34,0.72)",
    font=dict(color=TEXT_SECONDARY, family="IBM Plex Sans TC, Noto Sans TC, sans-serif", size=12),
    margin=dict(l=16, r=16, t=40, b=16),
)

AXIS_STYLE = dict(
    gridcolor="rgba(255,255,255,0.04)",
    linecolor="rgba(255,255,255,0.06)",
    tickcolor=TEXT_MUTED,
    zeroline=False,
)

# ── CSS Stylesheet ─────────────────────────────────────────────
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+TC:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ===== Global ===== */
.stApp {{
    background: {BG_PRIMARY};
    background-image:
        radial-gradient(circle at top left, rgba(75,163,255,0.14), transparent 32%),
        radial-gradient(circle at bottom right, rgba(53,196,139,0.09), transparent 28%),
        linear-gradient(180deg, #07111a 0%, #091521 36%, #07111a 100%);
    color: {TEXT_PRIMARY};
}}

html, body, .stApp, .stMarkdown, p {{
    font-family: 'IBM Plex Sans TC', 'Noto Sans TC', sans-serif !important;
}}

.block-container {{
    padding-top: calc(3.35rem + env(safe-area-inset-top, 0px)) !important;
    padding-bottom: 2rem !important;
}}

/* Preserve Streamlit/Material icon glyphs; broad span/div font overrides break them. */
[class*="material-symbols"] {{
    font-family: "Material Symbols Rounded", "Material Symbols Outlined" !important;
}}

[class*="material-icons"] {{
    font-family: "Material Icons" !important;
}}

h1, h2, h3, h4 {{
    font-family: 'IBM Plex Sans TC', 'Noto Sans TC', sans-serif !important;
    font-weight: 700 !important;
    color: {TEXT_PRIMARY} !important;
    letter-spacing: -0.03em;
}}

h1 {{ font-size: 1.9rem !important; }}
h2 {{ font-size: 1.12rem !important; color: {TEXT_SECONDARY} !important; }}

code {{
    font-family: 'JetBrains Mono', monospace !important;
    color: {BLUE} !important;
    background: rgba(59,130,246,0.1) !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
}}

/* ===== Sidebar ===== */
section[data-testid="stSidebar"] {{
    background: {BG_SECONDARY} !important;
    border-right: 1px solid {BORDER} !important;
}}

section[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    color: {TEXT_SECONDARY} !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    text-align: left !important;
    padding: 10px 14px !important;
    margin-bottom: 2px !important;
}}

section[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(59,130,246,0.08) !important;
    border-color: rgba(59,130,246,0.15) !important;
    color: {TEXT_PRIMARY} !important;
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: rgba(75,163,255,0.12) !important;
    border-color: rgba(75,163,255,0.25) !important;
    color: {BLUE} !important;
    font-weight: 600 !important;
    box-shadow: 0 0 20px rgba(75,163,255,0.1) !important;
}}

/* ===== Metric Cards ===== */
[data-testid="metric-container"] {{
    background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.02));
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 18px 22px !important;
    transition: all 0.3s ease;
}}

[data-testid="metric-container"]:hover {{
    border-color: {BORDER_HOVER};
    box-shadow: 0 14px 34px rgba(0,0,0,0.18);
    transform: translateY(-1px);
}}

[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px;
    font-weight: 500 !important;
}}

[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.85rem !important;
    font-weight: 600 !important;
}}

[data-testid="stMetricDelta"] {{
    font-size: 0.72rem !important;
}}

/* ===== Buttons ===== */
.stButton > button {{
    background: transparent !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_SECONDARY} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    transition: all 0.25s ease !important;
    padding: 8px 16px !important;
}}

.stButton > button:hover {{
    border-color: {BLUE} !important;
    color: {BLUE} !important;
    box-shadow: 0 0 20px rgba(59,130,246,0.1) !important;
}}

.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {BLUE}, #3577ff) !important;
    border-color: transparent !important;
    color: #03101a !important;
    font-weight: 600 !important;
    box-shadow: 0 6px 18px rgba(75,163,255,0.28) !important;
}}

.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 24px rgba(59,130,246,0.4) !important;
    transform: translateY(-1px);
}}

/* ===== Dividers ===== */
hr {{ border-color: rgba(255,255,255,0.05) !important; }}

/* ===== DataFrames ===== */
.stDataFrame {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    overflow: hidden;
}}

/* ===== Expander ===== */
.streamlit-expanderHeader {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT_SECONDARY} !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
}}

.streamlit-expanderHeader:hover {{
    border-color: {BORDER_HOVER} !important;
    color: {TEXT_PRIMARY} !important;
}}

/* ===== Info / Warning / Error / Success ===== */
.stAlert > div {{
    border-radius: 8px !important;
}}

div[data-testid="stAlert"] {{
    border-radius: 8px !important;
}}

/* ===== Select Boxes ===== */
.stSelectbox > div > div {{
    background: rgba(255,255,255,0.03) !important;
    border-color: {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT_PRIMARY} !important;
}}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0px;
    background: rgba(255,255,255,0.02);
    border-radius: 10px;
    padding: 4px;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    color: {TEXT_SECONDARY};
    font-weight: 500;
    font-size: 0.85rem;
    padding: 8px 16px;
}}

.stTabs [aria-selected="true"] {{
    background: rgba(75,163,255,0.12) !important;
    color: {BLUE} !important;
}}

/* ===== Custom Classes ===== */

/* Glass Card */
.glass-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.018));
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 24px;
    transition: all 0.3s ease;
}}

.glass-card:hover {{
    border-color: rgba(59,130,246,0.2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}}

/* Status Badge */
.badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.3px;
}}
.badge-blue   {{ background: rgba(59,130,246,0.12); color: {BLUE};   border: 1px solid rgba(59,130,246,0.25); }}
.badge-green  {{ background: rgba(16,185,129,0.12); color: {GREEN};  border: 1px solid rgba(16,185,129,0.25); }}
.badge-yellow {{ background: rgba(245,158,11,0.12); color: {YELLOW}; border: 1px solid rgba(245,158,11,0.25); }}
.badge-red    {{ background: rgba(239,68,68,0.12);  color: {RED};    border: 1px solid rgba(239,68,68,0.25); }}

/* Page Header */
.page-header {{
    padding: 8px 0 18px 0;
    margin-bottom: 24px;
    border-bottom: 1px solid {BORDER};
}}
.page-header h1 {{
    background: linear-gradient(135deg, {TEXT_PRIMARY} 0%, {TEXT_SECONDARY} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px !important;
    line-height: 1.18 !important;
    padding-top: 2px;
}}
.page-header .subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 0.85rem;
    font-weight: 400;
    margin-top: 4px;
}}

/* KPI Card (enhanced) */
.kpi-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.02));
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 18px 20px;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}}

.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg, {BLUE}, {CYAN});
    opacity: 0;
    transition: opacity 0.3s;
}}

.kpi-card:hover {{
    border-color: rgba(59,130,246,0.2);
    box-shadow: 0 14px 34px rgba(0,0,0,0.18);
    transform: translateY(-2px);
}}

.kpi-card:hover::before {{ opacity: 1; }}

.kpi-label {{
    color: {TEXT_SECONDARY};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 500;
    margin-bottom: 8px;
}}

.kpi-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    line-height: 1.2;
}}

.kpi-value.blue  {{ color: {BLUE}; }}
.kpi-value.green {{ color: {GREEN}; }}
.kpi-value.yellow {{ color: {YELLOW}; }}
.kpi-value.red   {{ color: {RED}; }}

.kpi-sub {{
    color: {TEXT_MUTED};
    font-size: 0.72rem;
    margin-top: 6px;
}}

/* Hero */
.hero {{
    padding: 24px 0 22px 0;
    position: relative;
}}

.hero h1 {{
    font-size: 2.35rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, {TEXT_PRIMARY} 10%, {BLUE} 75%, #8fd0ff 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    margin-bottom: 8px !important;
    line-height: 1.12 !important;
    padding-top: 2px;
}}

.hero .subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 0.95rem;
    font-weight: 400;
}}

.hero .institution {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-top: 16px;
    padding: 6px 16px;
    border-radius: 20px;
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.15);
    color: {BLUE};
    font-size: 0.78rem;
    font-weight: 500;
}}

.hero .kicker {{
    font-family: 'JetBrains Mono', monospace;
    color: {YELLOW};
    font-size: 0.72rem;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    margin-bottom: 12px;
}}

/* Live Pulse */
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
}}

.live-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {GREEN};
    margin-right: 6px;
    animation: pulse 2s ease-in-out infinite;
    box-shadow: 0 0 8px rgba(16,185,129,0.5);
}}

.live-dot.stale {{
    background: {YELLOW};
    box-shadow: 0 0 8px rgba(245,158,11,0.5);
}}

.live-dot.dead {{
    background: {RED};
    animation: none;
    box-shadow: 0 0 8px rgba(239,68,68,0.5);
}}

/* Section Title */
.section-title {{
    font-size: 0.72rem;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid {BORDER};
}}

/* Variable Tag */
.var-tag {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid {BORDER};
    margin: 3px;
    font-size: 0.8rem;
    transition: all 0.2s;
}}

.var-tag:hover {{
    border-color: rgba(59,130,246,0.3);
    background: rgba(59,130,246,0.05);
}}

.var-tag .code {{
    font-family: 'JetBrains Mono', monospace;
    color: {BLUE};
    font-size: 0.75rem;
}}

.var-tag .label {{
    color: {TEXT_SECONDARY};
    font-size: 0.75rem;
}}

/* Sidebar Logo */
.sidebar-brand {{
    padding: 20px 0 24px 0;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 20px;
}}

.sidebar-brand .mono {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: {BLUE};
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
}}

.sidebar-brand .title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    line-height: 1.4;
}}

/* Sidebar Stats */
.sidebar-stats {{
    font-size: 0.75rem;
    color: {TEXT_SECONDARY};
    line-height: 2;
}}

.sidebar-stats .val {{
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
}}

.toolbar-shell {{
    background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.018));
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 18px 22px 12px 22px;
    margin-top: 0.2rem;
    margin-bottom: 24px;
}}

.toolbar-title {{
    font-family: 'JetBrains Mono', monospace;
    color: {TEXT_MUTED};
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    margin-bottom: 6px;
}}

.toolbar-heading {{
    color: {TEXT_PRIMARY};
    font-size: 1.18rem;
    font-weight: 600;
    margin-bottom: 4px;
    line-height: 1.2;
}}

.toolbar-copy {{
    color: {TEXT_SECONDARY};
    font-size: 0.82rem;
    line-height: 1.7;
}}

.toolbar-stat {{
    background: rgba(255,255,255,0.03);
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 14px 16px;
    min-height: 94px;
}}

.toolbar-stat .label {{
    font-family: 'JetBrains Mono', monospace;
    color: {TEXT_MUTED};
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
}}

.toolbar-stat .value {{
    color: {TEXT_PRIMARY};
    font-size: 1.05rem;
    font-weight: 600;
}}

.toolbar-stat .meta {{
    color: {TEXT_SECONDARY};
    font-size: 0.76rem;
    margin-top: 6px;
    line-height: 1.5;
}}

.story-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.02));
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 18px 20px;
    min-height: 132px;
}}

.story-card + .story-card {{
    margin-top: 12px;
}}

.story-card .eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    color: {TEXT_MUTED};
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 10px;
}}

.story-card .value {{
    color: {TEXT_PRIMARY};
    font-size: 1.42rem;
    font-weight: 700;
    line-height: 1.25;
}}

.story-card .body {{
    color: {TEXT_SECONDARY};
    font-size: 0.8rem;
    line-height: 1.7;
    margin-top: 8px;
}}

.story-card.blue .value {{ color: {BLUE}; }}
.story-card.green .value {{ color: {GREEN}; }}
.story-card.yellow .value {{ color: {YELLOW}; }}
.story-card.red .value {{ color: {RED}; }}

.note-card {{
    background: rgba(75,163,255,0.08);
    border: 1px solid rgba(75,163,255,0.18);
    border-radius: 16px;
    padding: 16px 18px;
}}

.note-card .title {{
    color: {TEXT_PRIMARY};
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 6px;
}}

.note-card .body {{
    color: {TEXT_SECONDARY};
    font-size: 0.8rem;
    line-height: 1.75;
}}

.compact-list {{
    display: grid;
    gap: 10px;
}}

.compact-item {{
    display: grid;
    grid-template-columns: 84px 1fr;
    gap: 10px;
    align-items: start;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}}

.compact-item .term {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: {BLUE};
}}

.compact-item .desc {{
    font-size: 0.8rem;
    color: {TEXT_SECONDARY};
    line-height: 1.65;
}}

/* Table Styles */
.research-table {{
    width: 100%;
    border-collapse: collapse;
}}

.research-table th {{
    color: {TEXT_MUTED};
    font-size: 0.7rem;
    text-align: left;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 8px 12px 8px 0;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}

.research-table td {{
    padding: 8px 12px 8px 0;
    font-size: 0.8rem;
    border-bottom: 1px solid rgba(255,255,255,0.02);
}}

.research-table tr:hover td {{
    background: rgba(59,130,246,0.03);
}}

/* Method Step */
.method-step {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 12px 16px;
    border-radius: 10px;
    background: rgba(255,255,255,0.02);
    border: 1px solid {BORDER};
    margin-bottom: 8px;
    transition: all 0.2s;
}}

.method-step:hover {{
    border-color: rgba(59,130,246,0.2);
}}

.method-step .num {{
    min-width: 28px; height: 28px;
    border-radius: 8px;
    background: rgba(59,130,246,0.12);
    color: {BLUE};
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.method-step .name {{
    color: {TEXT_PRIMARY};
    font-size: 0.85rem;
    font-weight: 600;
}}

.method-step .desc {{
    color: {TEXT_SECONDARY};
    font-size: 0.75rem;
    margin-top: 2px;
}}

/* Filter Section */
.filter-label {{
    font-size: 0.7rem;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 8px;
}}

/* Directory Status Card */
.dir-card {{
    background: rgba(255,255,255,0.02);
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
}}

.dir-card .header {{
    font-size: 0.7rem;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}}

.dir-card .label {{
    font-size: 0.82rem;
    color: {TEXT_PRIMARY};
    font-weight: 600;
    margin-bottom: 10px;
}}

.dir-card .row {{
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-size: 0.72rem;
}}

.dir-card .row .name {{ color: {TEXT_SECONDARY}; }}
.dir-card .row .val  {{ color: {TEXT_PRIMARY}; }}
.dir-card .row.today .name {{ color: {BLUE}; }}

/* Storage Bar */
.storage-bar {{
    background: rgba(255,255,255,0.03);
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: {TEXT_SECONDARY};
    display: flex;
    gap: 24px;
    align-items: center;
}}

.storage-bar .item {{
    display: flex;
    align-items: center;
    gap: 8px;
}}

.storage-bar .dot {{
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
}}

.storage-bar .val {{
    color: {TEXT_PRIMARY};
    font-weight: 500;
}}

@media (max-width: 900px) {{
    .block-container {{
        padding-top: calc(4.25rem + env(safe-area-inset-top, 0px)) !important;
    }}

    .toolbar-shell {{
        padding: 16px 16px 12px 16px;
    }}
}}

</style>
"""
