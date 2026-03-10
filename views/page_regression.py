"""
OLS 迴歸 (Regression) — Interactive Variable Selector + Results
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from views.theme import PLOTLY_THEME, AXIS_STYLE, BLUE, GREEN, TEXT_SECONDARY, TEXT_MUTED
from views.components import page_header, kpi_card, section_title

try:
    import statsmodels.api as sm
except ImportError:
    sm = None


def _prepare_operational_dataset(df: pd.DataFrame):
    required = [
        "TrainNo", "DelayTime", "IsDelayed", "TrainType", "Period", "IsHoliday",
        "PrevDelay", "StopSeq", "Direction", "TripLine", "StationClass",
        "MixIndex", "SpeedDiff", "IsTerminal",
    ]
    reg_df = df.dropna(subset=required).copy()
    if reg_df.empty:
        return reg_df, [], {}

    reg_df["TrainType"] = reg_df["TrainType"].astype(str)
    reg_df["StationClass"] = reg_df["StationClass"].astype(str).str.strip()
    reg_df["TripLine"] = reg_df["TripLine"].astype(float)
    reg_df["Direction"] = reg_df["Direction"].astype(float)

    reg_df["IsZiQiang"] = (reg_df["TrainType"] == "自強").astype(int)
    reg_df["IsQuJianKuai"] = (reg_df["TrainType"] == "區間快").astype(int)
    reg_df["IsTilt"] = (reg_df["TrainType"] == "傾斜式自強").astype(int)
    reg_df["IsJuGuang"] = (reg_df["TrainType"] == "莒光").astype(int)
    reg_df["IsPeak"] = (reg_df["Period"] == "尖峰").astype(int)
    reg_df["IsNight"] = (reg_df["Period"] == "深夜").astype(int)
    reg_df["IsReverse"] = (reg_df["Direction"] == 1).astype(int)
    reg_df["IsSeaLine"] = (reg_df["TripLine"] == 1).astype(int)
    reg_df["IsOtherLine"] = (reg_df["TripLine"] == 2).astype(int)
    reg_df["IsMajorStation"] = reg_df["StationClass"].isin(["0", "1"]).astype(int)
    reg_df["IsSecondaryStation"] = (reg_df["StationClass"] == "2").astype(int)

    xvars = [
        "IsZiQiang", "IsQuJianKuai", "IsTilt", "IsJuGuang",
        "StopSeq", "IsPeak", "IsNight", "IsHoliday", "PrevDelay",
        "IsReverse", "IsSeaLine", "IsOtherLine",
        "IsMajorStation", "IsSecondaryStation",
        "MixIndex", "SpeedDiff", "IsTerminal",
    ]
    var_labels = {
        "const": "截距",
        "IsZiQiang": "自強（vs 區間）",
        "IsQuJianKuai": "區間快（vs 區間）",
        "IsTilt": "傾斜式自強（vs 區間）",
        "IsJuGuang": "莒光（vs 區間）",
        "StopSeq": "停靠順序",
        "IsPeak": "尖峰時段（vs 離峰）",
        "IsNight": "深夜時段（vs 離峰）",
        "IsHoliday": "假日",
        "PrevDelay": "前站誤點（每 1 分）",
        "IsReverse": "逆行方向（vs 順行）",
        "IsSeaLine": "海線（vs 山線）",
        "IsOtherLine": "其他線別（vs 山線）",
        "IsMajorStation": "大型站（特等/一等）",
        "IsSecondaryStation": "二等站",
        "MixIndex": "同站同小時車種混合度",
        "SpeedDiff": "同站同小時速差（分）",
        "IsTerminal": "終點站停靠",
    }
    return reg_df, xvars, var_labels


def _active_xvars(df: pd.DataFrame, xvars: list[str]) -> list[str]:
    return [x for x in xvars if x in df.columns and df[x].nunique(dropna=False) > 1]


def _build_risk_result_df(model, var_labels: dict) -> pd.DataFrame:
    params = model.params.drop(labels=["const"], errors="ignore")
    bse = model.bse[params.index]
    pvals = model.pvalues[params.index]
    odds_ratio = np.exp(params)
    ci_low = np.exp(params - 1.96 * bse)
    ci_high = np.exp(params + 1.96 * bse)
    return pd.DataFrame({
        "變數": [var_labels.get(v, v) for v in params.index],
        "β 係數": params.values,
        "勝算比 OR": odds_ratio.values,
        "風險變化%": (odds_ratio.values - 1) * 100,
        "95% CI 下界": ci_low.values,
        "95% CI 上界": ci_high.values,
        "p 值": pvals.values,
        "顯著性": [
            "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.1 else ""
            for p in pvals.values
        ],
    }).sort_values("風險變化%", ascending=False)


def _build_severity_result_df(model, var_labels: dict) -> pd.DataFrame:
    params = model.params.drop(labels=["const"], errors="ignore")
    bse = model.bse[params.index]
    pvals = model.pvalues[params.index]
    factor = np.exp(params)
    ci_low = np.exp(params - 1.96 * bse)
    ci_high = np.exp(params + 1.96 * bse)
    return pd.DataFrame({
        "變數": [var_labels.get(v, v) for v in params.index],
        "β 係數": params.values,
        "倍率效果": factor.values,
        "延誤變化%": (factor.values - 1) * 100,
        "95% CI 下界": ci_low.values,
        "95% CI 上界": ci_high.values,
        "p 值": pvals.values,
        "顯著性": [
            "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.1 else ""
            for p in pvals.values
        ],
    }).sort_values("延誤變化%", ascending=False)


def _effect_bar(df: pd.DataFrame, value_col: str, title: str):
    plot_df = df.copy().sort_values(value_col)
    colors = [BLUE if v >= 0 else "#ef4444" for v in plot_df[value_col]]
    fig = go.Figure(go.Bar(
        x=plot_df[value_col],
        y=plot_df["變數"],
        orientation="h",
        marker=dict(color=colors),
        text=[f"{v:+.1f}%" for v in plot_df[value_col]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.12)", line_width=1)
    fig.update_layout(
        **PLOTLY_THEME,
        height=max(340, 36 * len(plot_df)),
        title=title,
        xaxis=dict(**AXIS_STYLE, title="相對影響（%）"),
        yaxis=dict(**AXIS_STYLE, title=None),
        margin=dict(l=16, r=60, t=48, b=16),
    )
    return fig


def render(df, filtered_research_df, date_label, **kwargs):
    page_header("≋", "實務回歸模型", "官方誤點風險 + 已誤點後之嚴重度")

    _rdf = filtered_research_df
    st.caption(f"目前顯示範圍：{date_label}　共 {len(_rdf):,} 筆觀測")

    with st.expander("📊 模型設計說明"):
        st.markdown("""
        **分析單位**  
        本頁以「車次 × 車站」為一筆觀測值，並套用目前頁面的日期篩選。模型只使用當前資料集中欄位完整、
        且在營運上可解釋的變數。

        **模型目的**  
        實務上最關心的是兩件事：
        1. 這班車在本站會不會進入官方定義的誤點
        2. 一旦已經誤點，會惡化到什麼程度

        因此這頁改成兩段式模型，而不是單純用一個 OLS 硬估所有觀測值。

        **應變數（Y）**  
        - **風險模型（Logit）**：`IsDelayed`，官方口徑 `DelayTime >= 5`
        - **嚴重度模型（Gamma GLM, log link）**：`DelayTime`，但只在 `IsDelayed = 1` 的樣本上估計

        **模型形式**  
        - **Logit**：估計某筆停靠紀錄進入官方誤點的機率
        - **Gamma GLM**：適合右偏、非負、長尾的誤點分鐘數，較貼近實務的延誤程度分布

        **為什麼不用單一 OLS**  
        目前資料中大量觀測值是 0 或低分鐘數誤點，直接對全部樣本做 OLS，容易把「是否誤點」
        和「誤點後有多嚴重」混在一起，對營運判讀不夠直觀。

        **自變數編碼方式**

        | 類型 | 欄位 / 轉換 | 說明 |
        |------|-------------|------|
        | 車種 | `IsZiQiang`、`IsQuJianKuai`、`IsTilt`、`IsJuGuang` | 基準組 = `區間` |
        | 站序 | `StopSeq` | 越後段越能反映誤點累積 |
        | 時段 | `IsPeak`、`IsNight` | 基準組 = `離峰` |
        | 日別 | `IsHoliday` | 0 = 平日，1 = 非平日 |
        | 傳遞效應 | `PrevDelay` | 前一站已累積的誤點分鐘數 |
        | 行車方向 | `IsReverse` | 基準組 = 順行 |
        | 線別 | `IsSeaLine`、`IsOtherLine` | 基準組 = 山線 |
        | 站體規模 | `IsMajorStation`、`IsSecondaryStation` | 基準組 = 三等以下站 |
        | 排程複雜度 | `MixIndex`、`SpeedDiff` | 同站同小時混合度與速差 |
        | 終點效果 | `IsTerminal` | 是否為終點站停靠 |

        **如何解讀係數**
        - **Logit** 主要看 `勝算比 OR`：大於 1 表示進入官方誤點的風險上升
        - **Gamma GLM** 主要看 `倍率效果`：大於 1 表示一旦誤點，延誤分鐘數會放大
        - 表格中的 `%` 欄位已轉成實務較好讀的相對變化

        **顯著性標記**  
        `*** p<0.001`、`** p<0.01`、`* p<0.05`、`† p<0.1`

        **注意事項**
        - 本頁是關聯分析，不直接代表因果效果
        - 類別變數都需要相對於基準組解讀
        - 標準誤使用以 `TrainNo` 為單位的聚類穩健估計，較貼近同車次重複觀測的實務情境
        - `SideTrackCount`、`IsDouble` 在目前資料中仍幾乎全缺，因此暫不納入模型
        """)

    if sm is None:
        st.error("statsmodels 未安裝，無法執行迴歸分析。")
        return

    if _rdf.empty or len(_rdf) < 30:
        st.warning(f"資料量不足（目前 {len(_rdf):,} 筆），建議累積至少 1,000 筆後執行迴歸。")
        return

    # ── Variable Setup ────────────────────────────────────────
    col_info, col_run = st.columns([2, 1])
    with col_info:
        section_title("變數設定")
        st.markdown(f"""
        <div style="font-size:0.85rem; color:{TEXT_SECONDARY}; line-height:1.8;">
        風險模型：<code>IsDelayed</code>（官方 5 分鐘口徑）<br>
        嚴重度模型：<code>DelayTime</code>（僅在已誤點樣本上估計）<br>
        自變數：車種、站序、時段、假日、前站誤點、方向、線別、站體規模、混合度、速差、終點站
        </div>
        """, unsafe_allow_html=True)
    with col_run:
        run_models = st.button("▶  執行實務模型", type="primary", use_container_width=True)

    st.markdown("---")

    if run_models:
        reg_df, xvars, var_labels = _prepare_operational_dataset(_rdf)
        if reg_df.empty:
            st.warning("目前可用欄位不足，無法建立實務模型。")
            return

        active_xvars = _active_xvars(reg_df, xvars)
        if len(active_xvars) < 3:
            st.warning("可估計的變數太少，請放寬篩選或累積更多資料。")
            return

        delayed_df = reg_df[reg_df["IsDelayed"] == 1].copy()
        delayed_xvars = _active_xvars(delayed_df, active_xvars)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("風險模型樣本", f"{len(reg_df):,}", "blue")
        with c2:
            kpi_card("已誤點樣本", f"{len(delayed_df):,}", "yellow")
        with c3:
            kpi_card("官方誤點率", f"{reg_df['IsDelayed'].mean()*100:.1f}%", "green")
        with c4:
            kpi_card("聚類數", f"{reg_df['TrainNo'].nunique():,}")

        st.caption(
            "基準組：區間車、離峰、順行、山線、三等以下站。"
            " `SideTrackCount` 與 `IsDouble` 因當前資料缺漏未納入。"
        )

        try:
            risk_groups = pd.factorize(reg_df["TrainNo"].astype(str))[0]
            X_risk = sm.add_constant(reg_df[active_xvars].astype(float))
            y_risk = reg_df["IsDelayed"].astype(int)
            risk_model = sm.Logit(y_risk, X_risk).fit(
                disp=0,
                cov_type="cluster",
                cov_kwds={"groups": risk_groups},
            )
        except Exception as e:
            st.error(f"風險模型估計失敗：{e}")
            return

        if len(delayed_df) < 30:
            st.warning("官方誤點樣本不足，暫時只能顯示風險模型。")
            delayed_model = None
        else:
            try:
                severity_groups = pd.factorize(delayed_df["TrainNo"].astype(str))[0]
                X_sev = sm.add_constant(delayed_df[delayed_xvars].astype(float))
                y_sev = delayed_df["DelayTime"].astype(float)
                delayed_model = sm.GLM(
                    y_sev,
                    X_sev,
                    family=sm.families.Gamma(link=sm.families.links.Log()),
                ).fit(
                    cov_type="cluster",
                    cov_kwds={"groups": severity_groups},
                )
            except Exception as e:
                delayed_model = None
                st.warning(f"嚴重度模型估計失敗，僅顯示風險模型：{e}")

        risk_tab, sev_tab = st.tabs(["官方誤點風險", "已誤點後的嚴重度"])

        with risk_tab:
            section_title("Logit 風險模型")
            r1, r2, r3, r4 = st.columns(4)
            with r1:
                kpi_card("Pseudo R²", f"{risk_model.prsquared:.4f}", "blue")
            with r2:
                kpi_card("AIC", f"{risk_model.aic:.1f}")
            with r3:
                kpi_card("樣本數 N", f"{int(risk_model.nobs):,}", "green")
            with r4:
                kpi_card("平均官方誤點率", f"{reg_df['IsDelayed'].mean()*100:.1f}%")

            risk_df = _build_risk_result_df(risk_model, var_labels)
            st.dataframe(
                risk_df.style.format({
                    "β 係數": "{:.4f}",
                    "勝算比 OR": "{:.3f}",
                    "風險變化%": "{:+.1f}%",
                    "95% CI 下界": "{:.3f}",
                    "95% CI 上界": "{:.3f}",
                    "p 值": "{:.4f}",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("`風險變化%` 以勝算比換算；例如 +25% 代表進入官方誤點的勝算約增加四分之一。")
            st.plotly_chart(_effect_bar(risk_df, "風險變化%", "各因素對官方誤點風險的相對影響"), use_container_width=True)

            with st.expander("📄 風險模型 statsmodels Summary"):
                st.text(risk_model.summary().as_text())

        with sev_tab:
            section_title("Gamma GLM 嚴重度模型")
            if delayed_model is None:
                st.info("目前無法估計嚴重度模型。請累積更多官方誤點樣本後再試。")
            else:
                pseudo_r2 = np.nan
                if getattr(delayed_model, "null_deviance", None):
                    pseudo_r2 = 1 - delayed_model.deviance / delayed_model.null_deviance

                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    kpi_card("Deviance Pseudo R²", f"{pseudo_r2:.4f}" if pd.notna(pseudo_r2) else "—", "blue")
                with s2:
                    kpi_card("AIC", f"{delayed_model.aic:.1f}")
                with s3:
                    kpi_card("樣本數 N", f"{int(delayed_model.nobs):,}", "green")
                with s4:
                    kpi_card("平均延誤", f"{delayed_df['DelayTime'].mean():.2f} 分")

                sev_df = _build_severity_result_df(delayed_model, var_labels)
                st.dataframe(
                    sev_df.style.format({
                        "β 係數": "{:.4f}",
                        "倍率效果": "{:.3f}",
                        "延誤變化%": "{:+.1f}%",
                        "95% CI 下界": "{:.3f}",
                        "95% CI 上界": "{:.3f}",
                        "p 值": "{:.4f}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption("`延誤變化%` 表示在已經官方誤點的前提下，平均誤點分鐘數被放大或縮小的幅度。")
                st.plotly_chart(_effect_bar(sev_df, "延誤變化%", "各因素對已誤點列車延誤程度的相對影響"), use_container_width=True)

                with st.expander("📄 嚴重度模型 statsmodels Summary"):
                    st.text(delayed_model.summary().as_text())
