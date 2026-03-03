"""
Reusable UI Components — TRA Delay Research Dashboard
=====================================================
"""
import streamlit as st
from views.theme import (
    BLUE, GREEN, YELLOW, RED, CYAN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER,
)


def page_header(icon: str, title: str, subtitle: str):
    """Premium page header with gradient title."""
    st.markdown(f"""
    <div class="page-header">
        <h1>{icon}  {title}</h1>
        <div class="subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, value: str, color: str = "", sub: str = ""):
    """Glassmorphism KPI card."""
    color_class = f" {color}" if color else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value{color_class}">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def section_title(text: str):
    """Uppercase monospace section divider."""
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def status_badge(text: str, color: str = "blue"):
    """Inline status badge."""
    return f'<span class="badge badge-{color}">{text}</span>'


def live_status_badge(status: str, label: str):
    """Live status with animated dot."""
    dot_class = ""
    if status == "stale":
        dot_class = "stale"
    elif status == "dead":
        dot_class = "dead"
    return f'<span class="live-dot {dot_class}"></span>{label}'


def glass_container(content_html: str):
    """Wrap content in a glass card."""
    st.markdown(f'<div class="glass-card">{content_html}</div>', unsafe_allow_html=True)


def method_step(num: str, name: str, desc: str):
    """Numbered method step card."""
    return f"""
    <div class="method-step">
        <div class="num">{num}</div>
        <div>
            <div class="name">{name}</div>
            <div class="desc">{desc}</div>
        </div>
    </div>
    """


def var_tag(code: str, label: str):
    """Variable tag for research design."""
    return f"""
    <div class="var-tag">
        <span class="code">{code}</span>
        <span class="label">{label}</span>
    </div>
    """


def sidebar_brand():
    """Sidebar brand / title block."""
    st.markdown("""
    <div class="sidebar-brand">
        <div class="mono">TRA DELAY RESEARCH</div>
        <div class="title">台鐵誤點<br>研究指揮中心</div>
    </div>
    """, unsafe_allow_html=True)


def sidebar_stats(data_source: str, total_count: int, date_range_start: str):
    """Sidebar metadata stats."""
    st.markdown(f"""
    <div class="sidebar-stats">
        資料來源　<span class="val">{data_source}</span><br>
        累積筆數　<span class="val">{total_count:,}</span> 筆<br>
        起始日期　<span class="val">{date_range_start}</span>
    </div>
    """, unsafe_allow_html=True)
