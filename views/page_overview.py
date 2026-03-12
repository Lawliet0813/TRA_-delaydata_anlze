"""
資料總覽 — 趨勢、比較與分布
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED, TEXT_SECONDARY
from views.components import kpi_card, note_card, page_header, section_title
from views.navigation import goto_page


def _build_train_type_delay(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "TrainType" not in df.columns:
        return None
    summary = (
        df.groupby("TrainType")
        .agg(平均誤點=("DelayTime", "mean"), 準點率=("IsDelayed", lambda x: (1 - x.mean()) * 100))
        .reset_index()
        .sort_values("平均誤點")
    )
    if summary.empty:
        return None

    bar_colors = [GREEN if v < 1.5 else BLUE if v < 3 else YELLOW if v < 5 else RED for v in summary["平均誤點"]]
    fig = go.Figure(
        go.Bar(
            x=summary["平均誤點"],
            y=summary["TrainType"],
            orientation="h",
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=summary["平均誤點"].round(2).astype(str) + " 分",
            textposition="outside",
            customdata=summary["準點率"].round(1),
            hovertemplate="<b>%{y}</b><br>平均誤點 %{x:.2f} 分<br>準點率 %{customdata:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=36, t=20, b=16)}, height=330)
    fig.update_xaxes(**AXIS_STYLE, title="平均誤點（分）", rangemode="tozero")
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _build_period_rate(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "Period" not in df.columns:
        return None
    summary = (
        df.groupby("Period")
        .agg(準點率=("IsDelayed", lambda x: round((1 - x.mean()) * 100, 1)), 平均誤點=("DelayTime", "mean"))
        .reset_index()
    )
    order = ["深夜", "離峰", "尖峰"]
    summary["Period"] = pd.Categorical(summary["Period"], categories=order, ordered=True)
    summary = summary.sort_values("Period")

    fig = go.Figure(
        go.Scatter(
            x=summary["準點率"],
            y=summary["Period"],
            mode="markers+text",
            marker=dict(
                size=(summary["平均誤點"].fillna(0).clip(lower=0.5) * 9).tolist(),
                color=[GREEN if v >= 95 else BLUE if v >= 90 else YELLOW for v in summary["準點率"]],
                line=dict(width=2, color="#07111a"),
            ),
            text=summary["準點率"].astype(str) + "%",
            textposition="middle right",
            customdata=summary["平均誤點"].round(2),
            hovertemplate="<b>%{y}</b><br>準點率 %{x:.1f}%<br>平均誤點 %{customdata:.2f} 分<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=30, t=20, b=16)}, height=330)
    fig.update_xaxes(**AXIS_STYLE, title="準點率 (%)", range=[80, 100])
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _build_delay_distribution(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "DelayTime" not in df.columns:
        return None
    clipped = df["DelayTime"].clip(upper=30)
    if clipped.empty:
        return None

    p50 = float(clipped.quantile(0.5))
    p90 = float(clipped.quantile(0.9))
    p95 = float(clipped.quantile(0.95))

    fig = go.Figure(
        go.Histogram(
            x=clipped,
            nbinsx=30,
            marker=dict(color="rgba(75,163,255,0.58)", line=dict(width=0)),
            hovertemplate="誤點 %{x} 分<br>筆數 %{y}<extra></extra>",
        )
    )
    for value, label, color in [
        (p50, "P50", GREEN),
        (p90, "P90", YELLOW),
        (p95, "P95", RED),
    ]:
        fig.add_vline(x=value, line_color=color, line_width=2, line_dash="dot")
        fig.add_annotation(
            x=value,
            y=1,
            yref="paper",
            text=f"{label} {value:.1f}",
            showarrow=False,
            font=dict(size=10, color=color),
            xanchor="left",
        )
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=16, t=24, b=16)}, height=300)
    fig.update_xaxes(**AXIS_STYLE, title="誤點分鐘（截斷至 30 分）")
    fig.update_yaxes(**AXIS_STYLE, title="筆數")
    return fig


def _build_punctuality_gap(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "TrainType" not in df.columns or "IsTerminal" not in df.columns:
        return None
    terminal_df = df[df["IsTerminal"] == 1].copy()
    if terminal_df.empty:
        return None

    official_col = "IsDelayed_Official" if "IsDelayed_Official" in terminal_df.columns else "IsDelayed"
    official = (
        terminal_df.groupby("TrainType")[official_col]
        .apply(lambda x: round((1 - x.mean()) * 100, 1))
        .reset_index(name="官方準點率")
    )
    research = (
        df.groupby("TrainType")["IsDelayed"]
        .apply(lambda x: round((1 - x.mean()) * 100, 1))
        .reset_index(name="研究準點率")
    )
    compare = official.merge(research, on="TrainType", how="inner")
    if compare.empty:
        return None
    compare["差距"] = compare["官方準點率"] - compare["研究準點率"]
    compare = compare.sort_values("差距", ascending=False)

    fig = go.Figure()
    for _, row in compare.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["研究準點率"], row["官方準點率"]],
                y=[row["TrainType"], row["TrainType"]],
                mode="lines",
                line=dict(color="rgba(158,176,196,0.28)", width=3),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=compare["研究準點率"],
            y=compare["TrainType"],
            mode="markers",
            marker=dict(size=11, color=BLUE, line=dict(width=1.5, color="#07111a")),
            name="研究",
            hovertemplate="<b>%{y}</b><br>研究準點率 %{x:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=compare["官方準點率"],
            y=compare["TrainType"],
            mode="markers+text",
            marker=dict(size=11, color=GREEN, line=dict(width=1.5, color="#07111a")),
            text=compare["差距"].map(lambda v: f"{v:+.1f}pt"),
            textposition="middle right",
            textfont=dict(size=10, color=TEXT_SECONDARY),
            name="官方",
            hovertemplate="<b>%{y}</b><br>官方準點率 %{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=16, r=50, t=20, b=16)},
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    )
    fig.update_xaxes(**AXIS_STYLE, title="準點率 (%)", range=[75, 100])
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def render(df, filtered_df, date_label, **kwargs):
    page_header("◈", "資料總覽", "把資料拆成趨勢、比較與分布三個閱讀層次")

    if filtered_df.empty:
        st.warning("此日期無資料，請重新選擇。")
        return

    scope_df = filtered_df.copy()
    total = len(scope_df)
    punctuality = round((1 - scope_df["IsDelayed"].mean()) * 100, 1)
    avg_delay = round(scope_df["DelayTime"].mean(), 2)
    p90 = float(scope_df["DelayTime"].quantile(0.9))
    worst_type = ""
    if "TrainType" in scope_df.columns:
        type_rank = scope_df.groupby("TrainType")["DelayTime"].mean().sort_values(ascending=False)
        if not type_rank.empty:
            worst_type = str(type_rank.index[0])

    weakest_period = ""
    if "Period" in scope_df.columns:
        period_rank = scope_df.groupby("Period")["IsDelayed"].apply(lambda x: (1 - x.mean()) * 100).sort_values()
        if not period_rank.empty:
            weakest_period = str(period_rank.index[0])

    st.caption(f"目前顯示範圍：{date_label}　共 {total:,} 筆觀測")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("觀測筆數", f"{total:,}", "blue", "班次 × 車站紀錄")
    with k2:
        kpi_card("研究準點率", f"{punctuality}%", "green")
    with k3:
        kpi_card("平均誤點", f"{avg_delay} 分", "yellow" if avg_delay >= 2 else "green")
    with k4:
        kpi_card("P90 誤點", f"{p90:.1f} 分", "red", "最慢 10% 的延誤門檻")

    top_left, top_right = st.columns(2, gap="large")
    with top_left:
        section_title("比較：各車種平均誤點")
        fig = _build_train_type_delay(scope_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        if st.button("帶著這個車種去準點率分析", key="overview_go_type", use_container_width=True):
            goto_page(
                "準點率分析",
                filters={"train_type": worst_type} if worst_type else None,
            )
    with top_right:
        section_title("比較：各時段準點率")
        fig = _build_period_rate(scope_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        if st.button("帶著這個時段去準點率分析", key="overview_go_period", use_container_width=True):
            goto_page(
                "準點率分析",
                filters={"period": weakest_period} if weakest_period else None,
            )

    bottom_left, bottom_right = st.columns(2, gap="large")
    with bottom_left:
        section_title("分布：誤點分鐘數")
        fig = _build_delay_distribution(scope_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        if st.button("改看車站熱力與空間分布", key="overview_go_heatmap", use_container_width=True):
            goto_page("車站熱力圖")
        note_card(
            "分布判讀",
            "這張圖看的是尾端風險，而不是平均表現。P90、P95 越高，代表少數極端延誤越常把整體拉壞。",
        )
    with bottom_right:
        section_title("判定標準差異：官方 vs 研究")
        fig = _build_punctuality_gap(scope_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
            st.caption("每條線代表同一車種在兩種準點率定義下的差異。右側越遠，表示官方判定標準越寬鬆。")
            if st.button("切到準點率診斷頁細看", key="overview_go_gap", use_container_width=True):
                goto_page("準點率分析")
        else:
            st.info("目前缺少足夠的終點站資料，暫時無法計算官方與研究判定標準的差距。")

    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("追蹤單一車次", key="overview_go_tracker", use_container_width=True):
            goto_page("車次追蹤")
    with action_cols[1]:
        if st.button("看車站熱點", key="overview_go_heatmap_footer", use_container_width=True):
            goto_page("車站熱力圖")
    with action_cols[2]:
        if st.button("跑模型解釋", key="overview_go_reg", use_container_width=True):
            goto_page("OLS 迴歸")
