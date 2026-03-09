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


def render(df, filtered_research_df, date_label, **kwargs):
    page_header("≋", "OLS 線性迴歸", "誤點分鐘數影響因素估計 · Ordinary Least Squares")

    _rdf = filtered_research_df
    st.caption(f"目前顯示範圍：{date_label}　共 {len(_rdf):,} 筆觀測")

    with st.expander("📊 模型設計說明"):
        st.markdown("""
        **分析單位**  
        本頁以「車次 × 車站」為一筆觀測值，並套用目前頁面的日期篩選。只有同時具備
        `DelayTime`、`StopSeq`、`PrevDelay`、`Period`、`TrainType`、`IsHoliday`
        的資料會納入估計。

        **模型目的**  
        這一頁用兩種模型看同一組結構因素：
        - **OLS**：估計哪些因素會讓誤點分鐘數增加或減少
        - **Logit**：估計哪些因素會提高「是否誤點」的機率

        **應變數（Y）**  
        - **OLS**：`DelayTime`，連續變數，單位是分鐘
        - **Logit**：`IsDelayed`，二元變數，這頁目前採用程式中的官方口徑：`DelayTime >= 5`

        **模型形式**  
        - **OLS**：`DelayTime = β0 + β1X1 + ... + βkXk + ε`
        - **Logit**：`logit(P(IsDelayed=1)) = β0 + β1X1 + ... + βkXk`

        **自變數編碼方式**

        | 類型 | 欄位 / 轉換 | 說明 |
        |------|-------------|------|
        | 車種 (X1) | `IsZiQiang`、`IsQuJianKuai`、`IsTilt`、`IsJuGuang` | 虛擬變數；基準組為 `區間` |
        | 停靠順序 (X2) | `StopSeq` | 數值變數；站序越後段，越能反映累積誤點 |
        | 時段 (X3) | `IsPeak`、`IsNight` | 虛擬變數；基準組為 `離峰` |
        | 假日 (X4) | `IsHoliday` | 0 = 平日，1 = 非平日（週末或國定假日） |
        | 前站誤點 (X9) | `PrevDelay` | 數值變數；衡量誤點在相鄰站間的傳遞 |

        **如何解讀係數**
        - **OLS β 係數**：在其他變數固定下，該因素平均會讓 `DelayTime` 增減多少分鐘
        - **Logit β 係數**：在其他變數固定下，該因素會讓誤點的對數勝算增加或減少
        - 正值代表誤點風險或誤點程度上升，負值代表下降

        **顯著性標記**  
        `*** p<0.001`、`** p<0.01`、`* p<0.05`、`† p<0.1`

        **注意事項**
        - 本頁是關聯分析，不直接代表因果效果
        - 類別變數都需要相對於基準組解讀
        - Logit 的係數不是「機率增加幾 %」，若要更直觀解讀，需再轉成邊際效果或勝算比
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
        應變數：<code>DelayTime</code>（誤點分鐘數，連續）<br>
        自變數：車種虛擬變數（基準：區間）、停靠順序、時段（基準：離峰）、假日、前站誤點<br>
        樣本處理：僅使用關鍵欄位完整的觀測值，避免缺漏值直接進入模型
        </div>
        """, unsafe_allow_html=True)
    with col_run:
        run_ols = st.button("▶  執行 OLS 迴歸", type="primary", use_container_width=True)
        run_logit = st.button("▶  執行 Logit 迴歸", use_container_width=True)

    st.markdown("---")

    if run_ols or run_logit:
        reg_df = _rdf.dropna(
            subset=["DelayTime", "StopSeq", "PrevDelay", "Period", "TrainType", "IsHoliday"]
        ).copy()
        reg_df["IsZiQiang"]    = (reg_df["TrainType"] == "自強").astype(int)
        reg_df["IsQuJianKuai"] = (reg_df["TrainType"] == "區間快").astype(int)
        reg_df["IsTilt"]       = (reg_df["TrainType"] == "傾斜式自強").astype(int)
        reg_df["IsJuGuang"]    = (reg_df["TrainType"] == "莒光").astype(int)
        reg_df["IsPeak"]       = (reg_df["Period"] == "尖峰").astype(int)
        reg_df["IsNight"]      = (reg_df["Period"] == "深夜").astype(int)

        xvars = ["IsZiQiang", "IsQuJianKuai", "IsTilt", "IsJuGuang",
                 "StopSeq", "IsPeak", "IsNight", "IsHoliday", "PrevDelay"]
        var_labels = {
            "const": "截距",
            "IsZiQiang": "自強（vs 區間）",
            "IsQuJianKuai": "區間快（vs 區間）",
            "IsTilt": "傾斜式自強（vs 區間）",
            "IsJuGuang": "莒光（vs 區間）",
            "StopSeq": "停靠順序",
            "IsPeak": "尖峰時段",
            "IsNight": "深夜時段",
            "IsHoliday": "假日",
            "PrevDelay": "前站誤點（分）",
        }

        X = sm.add_constant(reg_df[xvars].astype(float))
        y_cont = reg_df["DelayTime"]
        y_bin  = reg_df["IsDelayed"]

        if run_ols:
            model = sm.OLS(y_cont, X).fit()
            model_name = "OLS 線性迴歸"
            r2_label = "R²"
            r2_val = f"{model.rsquared:.4f}"
            adj_r2 = f"{model.rsquared_adj:.4f}"
        else:
            model = sm.Logit(y_bin, X).fit(disp=0)
            model_name = "Logit 迴歸"
            r2_label = "Pseudo R²"
            r2_val = f"{model.prsquared:.4f}"
            adj_r2 = "—"

        section_title(f"{model_name} 結果")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            kpi_card(r2_label, r2_val, "blue")
        with m2:
            kpi_card("Adj. R²", adj_r2)
        with m3:
            kpi_card("樣本數 N", f"{int(model.nobs):,}", "green")
        with m4:
            kpi_card("AIC", f"{model.aic:.1f}")

        result_df = pd.DataFrame({
            "變數": [var_labels.get(v, v) for v in model.params.index],
            "β 係數": model.params.values.round(4),
            "標準誤": model.bse.values.round(4),
            "t / z": model.tvalues.values.round(3),
            "p 值": model.pvalues.values.round(4),
            "顯著性": ["***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else "†" if p<0.1 else "" for p in model.pvalues.values],
        })

        st.dataframe(
            result_df.style.format({"β 係數": "{:.4f}", "標準誤": "{:.4f}", "t / z": "{:.3f}", "p 值": "{:.4f}"}),
            use_container_width=True, hide_index=True
        )
        st.caption("*** p<0.001  ** p<0.01  * p<0.05  † p<0.1")

        # ── Lollipop Chart ────────────────────────────────────
        coef = result_df[result_df["變數"] != "截距"].copy()
        fig = go.Figure()

        for _, row in coef.iterrows():
            color = BLUE if row["β 係數"] > 0 else "#ef4444"
            # Horizontal line (stick)
            fig.add_trace(go.Scatter(
                x=[0, row["β 係數"]], y=[row["變數"], row["變數"]],
                mode="lines",
                line=dict(color=color, width=2),
                showlegend=False,
            ))
            # End point (lollipop head)
            fig.add_trace(go.Scatter(
                x=[row["β 係數"]], y=[row["變數"]],
                mode="markers",
                marker=dict(size=10, color=color,
                            line=dict(width=2, color="rgba(255,255,255,0.2)")),
                showlegend=False,
                hovertemplate=f"<b>{row['變數']}</b><br>β = {row['β 係數']:.4f}<br>p = {row['p 值']:.4f}<extra></extra>",
            ))
            # CI whiskers
            fig.add_trace(go.Scatter(
                x=[row["β 係數"] - row["標準誤"]*1.96,
                   row["β 係數"] + row["標準誤"]*1.96],
                y=[row["變數"], row["變數"]],
                mode="lines",
                line=dict(color=color, width=1, dash="dot"),
                showlegend=False,
            ))

        fig.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.1)", line_width=1)
        fig.update_layout(**PLOTLY_THEME, height=340,
                          xaxis=dict(**AXIS_STYLE, title="係數估計值（95% CI）"),
                          yaxis=dict(**AXIS_STYLE))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📄 完整 statsmodels Summary"):
            st.text(model.summary().as_text())
