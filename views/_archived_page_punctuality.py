"""
準點率分析 (Punctuality) — Official vs research comparison board
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, YELLOW, RED, TEXT_SECONDARY
from views.components import kpi_card, note_card, page_header, section_title, story_card


def _official_delay_col(terminal_df: pd.DataFrame) -> str:
    return "IsDelayed_Official" if "IsDelayed_Official" in terminal_df.columns else "IsDelayed"


def _rate_from_binary(series: pd.Series) -> float:
    return round((1 - series.mean()) * 100, 1)


def _build_type_gap_df(full_df: pd.DataFrame, terminal_df: pd.DataFrame) -> pd.DataFrame:
    if full_df.empty or terminal_df.empty or "TrainType" not in full_df.columns:
        return pd.DataFrame()
    official_col = _official_delay_col(terminal_df)
    official = (
        terminal_df.groupby("TrainType")[official_col]
        .apply(_rate_from_binary)
        .reset_index(name="官方準點率")
    )
    research = (
        full_df.groupby("TrainType")["IsDelayed"]
        .apply(_rate_from_binary)
        .reset_index(name="研究準點率")
    )
    compare = official.merge(research, on="TrainType", how="inner")
    if compare.empty:
        return compare
    compare["差距"] = (compare["官方準點率"] - compare["研究準點率"]).round(1)
    return compare.sort_values("差距", ascending=False)


def _build_type_dumbbell(compare: pd.DataFrame) -> go.Figure | None:
    if compare.empty:
        return None
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
            name="研究判定標準",
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
            name="官方判定標準",
            hovertemplate="<b>%{y}</b><br>官方準點率 %{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=16, r=48, t=20, b=16)},
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(**AXIS_STYLE, title="準點率 (%)", range=[70, 100])
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _build_period_profile(full_df: pd.DataFrame, terminal_df: pd.DataFrame) -> go.Figure | None:
    if full_df.empty or "Period" not in full_df.columns:
        return None
    order = ["深夜", "離峰", "尖峰"]
    research = (
        full_df.groupby("Period")["IsDelayed"]
        .apply(_rate_from_binary)
        .reset_index(name="研究準點率")
    )
    research["Period"] = pd.Categorical(research["Period"], categories=order, ordered=True)
    research = research.sort_values("Period")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=research["Period"],
            y=research["研究準點率"],
            name="研究判定標準",
            marker=dict(color="rgba(75,163,255,0.35)", line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>研究準點率 %{y:.1f}%<extra></extra>",
        )
    )
    if not terminal_df.empty and "Period" in terminal_df.columns:
        official_col = _official_delay_col(terminal_df)
        official = (
            terminal_df.groupby("Period")[official_col]
            .apply(_rate_from_binary)
            .reset_index(name="官方準點率")
        )
        official["Period"] = pd.Categorical(official["Period"], categories=order, ordered=True)
        official = official.sort_values("Period")
        fig.add_trace(
            go.Scatter(
                x=official["Period"],
                y=official["官方準點率"],
                name="官方判定標準",
                mode="lines+markers+text",
                line=dict(color=GREEN, width=2.6),
                marker=dict(size=9, color=GREEN),
                text=official["官方準點率"].astype(str) + "%",
                textposition="top center",
                hovertemplate="<b>%{x}</b><br>官方準點率 %{y:.1f}%<extra></extra>",
            )
        )
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=16, t=20, b=16)}, height=320)
    fig.update_yaxes(**AXIS_STYLE, title="準點率 (%)", range=[75, 100])
    fig.update_xaxes(**AXIS_STYLE, title=None)
    return fig


def _build_cross_heatmap(full_df: pd.DataFrame) -> go.Figure | None:
    if full_df.empty or "Period" not in full_df.columns or "TrainType" not in full_df.columns:
        return None
    cross = (
        full_df.groupby(["Period", "TrainType"])["IsDelayed"]
        .apply(_rate_from_binary)
        .reset_index(name="準點率")
    )
    if cross.empty:
        return None
    order = ["深夜", "離峰", "尖峰"]
    pivot = (
        cross.assign(Period=pd.Categorical(cross["Period"], categories=order, ordered=True))
        .pivot(index="TrainType", columns="Period", values="準點率")
        .reindex(columns=order)
    )
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale=[
                [0.0, RED],
                [0.45, YELLOW],
                [1.0, GREEN],
            ],
            zmin=70,
            zmax=100,
            text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=11),
            colorbar=dict(
                title=dict(text="研究準點率 (%)", font=dict(color=TEXT_SECONDARY)),
                tickfont=dict(color=TEXT_SECONDARY),
                bgcolor="rgba(0,0,0,0)",
            ),
            hovertemplate="<b>%{y}</b><br>%{x}<br>研究準點率 %{z:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=16, t=20, b=16)}, height=360)
    fig.update_xaxes(**AXIS_STYLE, title=None)
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _build_holiday_compare(full_df: pd.DataFrame) -> go.Figure | None:
    if full_df.empty or "HolidayType" not in full_df.columns:
        return None
    summary = (
        full_df.groupby("HolidayType")
        .agg(
            準點率=("IsDelayed", _rate_from_binary),
            平均誤點=("DelayTime", "mean"),
        )
        .reset_index()
    )
    if summary.empty:
        return None
    fig = go.Figure(
        go.Scatter(
            x=summary["準點率"],
            y=summary["HolidayType"],
            mode="markers+text",
            marker=dict(
                size=(summary["平均誤點"].clip(lower=0.5) * 10).tolist(),
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
    fig.update_layout(**{**PLOTLY_THEME, "margin": dict(l=16, r=36, t=20, b=16)}, height=260)
    fig.update_xaxes(**AXIS_STYLE, title="研究準點率 (%)", range=[75, 100])
    fig.update_yaxes(**AXIS_STYLE, title=None)
    return fig


def _render_schedule_lookup(schedule_df: pd.DataFrame) -> None:
    section_title("班次首末班時間查詢")
    if schedule_df.empty:
        st.info("首末班時間表尚未產生，請先確認本機 hourly 匯出是否完成，或檢查 `train_schedule.csv`。")
        return

    sc1, sc2, sc3 = st.columns([2, 2, 1])
    with sc1:
        all_types = ["全部車種"] + sorted(schedule_df["TrainTypeSimple"].dropna().unique().tolist())
        selected_type = st.selectbox("車種篩選", all_types, key="sched_type_v2")
    with sc2:
        search_no = st.text_input("車次號碼查詢", placeholder="例：101", key="sched_no_v2")
    with sc3:
        direction = st.selectbox("行駛方向", ["全部", "順行（基→高）", "逆行（高→基）"], key="sched_dir_v2")

    sdf = schedule_df.copy()
    if selected_type != "全部車種":
        sdf = sdf[sdf["TrainTypeSimple"] == selected_type]
    if search_no.strip():
        sdf = sdf[sdf["TrainNo"].astype(str).str.contains(search_no.strip(), na=False)]
    if direction == "順行（基→高）":
        sdf = sdf[sdf["Direction"] == 0]
    elif direction == "逆行（高→基）":
        sdf = sdf[sdf["Direction"] == 1]

    show_cols = ["TrainNo", "TrainTypeSimple", "FromStation", "FirstDep", "ToStation", "LastArr", "Direction"]
    labels = {
        "TrainNo": "車次",
        "TrainTypeSimple": "車種",
        "FromStation": "始發站",
        "FirstDep": "始發時間",
        "ToStation": "終點站",
        "LastArr": "終到時間",
        "Direction": "方向",
    }
    disp = sdf[[c for c in show_cols if c in sdf.columns]].rename(columns=labels)
    if "方向" in disp.columns:
        disp["方向"] = disp["方向"].map({0: "順行", 1: "逆行"})
    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=min(380, 35 + len(disp) * 35),
    )
    st.caption(
        f"共 {len(disp):,} 班次｜首班 {sdf['FirstDep'].min() if not sdf.empty else '—'}｜末班 {sdf['LastArr'].max() if not sdf.empty else '—'}"
    )


def render(df, filtered_df, date_label, schedule_df=None, **kwargs):
    page_header("◎", "準點率分析", "把官方判定標準與研究判定標準拆開比較，直接看到差距出在哪裡")

    scope_df = filtered_df.copy()
    st.caption(f"目前顯示範圍：{date_label}　共 {len(scope_df):,} 筆觀測")
    if scope_df.empty:
        st.warning("此日期無資料，請重新選擇。")
        return

    terminal_df = scope_df[scope_df["IsTerminal"] == 1].copy() if "IsTerminal" in scope_df.columns else pd.DataFrame()
    research_pct = round((1 - scope_df["IsDelayed"].mean()) * 100, 2)
    official_pct = None
    if not terminal_df.empty:
        official_pct = round((1 - terminal_df[_official_delay_col(terminal_df)].mean()) * 100, 2)
    gap_pct = round(official_pct - research_pct, 2) if official_pct is not None else None

    type_gap_df = _build_type_gap_df(scope_df, terminal_df)
    max_gap_train = "—"
    max_gap_value = 0.0
    if not type_gap_df.empty:
        max_gap_train = str(type_gap_df.iloc[0]["TrainType"])
        max_gap_value = float(type_gap_df.iloc[0]["差距"])

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card(
            "官方準點率",
            f"{official_pct:.2f}%" if official_pct is not None else "—",
            "green" if official_pct is not None and official_pct >= 90 else "yellow",
            "終點站，5 分鐘門檻",
        )
    with c2:
        kpi_card(
            "研究準點率",
            f"{research_pct:.2f}%",
            "green" if research_pct >= 90 else "yellow",
            "全停靠站，2 分鐘門檻",
        )
    with c3:
        kpi_card(
            "標準差距",
            f"{gap_pct:+.2f}pt" if gap_pct is not None else "—",
            "blue" if gap_pct is not None else "",
            "正值代表官方判定標準較寬鬆",
        )

    top_left, top_right = st.columns([1.45, 1.0], gap="large")
    with top_left:
        section_title("車種差距")
        fig = _build_type_dumbbell(type_gap_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("目前終點站樣本不足，無法比較各車種的官方與研究判定標準差距。")
    with top_right:
        section_title("本次觀察")
        story_card(
            "最大標準差距",
            max_gap_train,
            f"該車種官方與研究準點率相差約 {max_gap_value:+.1f} 個百分點。" if type_gap_df.shape[0] else "目前樣本不足，無法穩定估計各車種差距。",
            tone="yellow" if max_gap_value < 5 else "red",
        )
        story_card(
            "整體判讀",
            "終點站較寬鬆" if gap_pct is not None and gap_pct > 0 else "兩種標準接近",
            "官方判定標準只看終點站，研究判定標準則把途中停靠的旅客體感延誤也算進來。",
            tone="blue",
        )
        story_card(
            "研究用途",
            "差距可解釋",
            "這頁不是要證明誰對誰錯，而是把不同統計定義造成的視角差異講清楚。",
            tone="green",
        )

    lower_left, lower_right = st.columns([1.2, 1.0], gap="large")
    with lower_left:
        section_title("時段輪廓")
        period_fig = _build_period_profile(scope_df, terminal_df)
        if period_fig is not None:
            st.plotly_chart(period_fig, use_container_width=True)
    with lower_right:
        section_title("假日輪廓")
        holiday_fig = _build_holiday_compare(scope_df)
        if holiday_fig is not None:
            st.plotly_chart(holiday_fig, use_container_width=True)
        else:
            st.info("目前缺少 `HolidayType` 欄位資料。")
        note_card(
            "判讀建議",
            "先看哪些時段或日別本來就比較不穩，再回頭對照車種差距，會比較容易拆出延誤來源。",
        )

    section_title("時段 × 車種交叉熱圖")
    heatmap_fig = _build_cross_heatmap(scope_df)
    if heatmap_fig is not None:
        st.plotly_chart(heatmap_fig, use_container_width=True)
        st.caption("這張圖固定看研究判定標準，適合找出哪種車種在特定時段特別脆弱。")
    else:
        st.info("目前資料不足，無法建立交叉熱圖。")

    st.markdown("---")
    _render_schedule_lookup(schedule_df if schedule_df is not None else pd.DataFrame())
