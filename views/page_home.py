"""
首頁 — 研究動機、資料規模與關鍵發現
"""
import streamlit as st

from views.components import kpi_card, note_card, section_title, story_card


def render(ctx: dict) -> None:
    perceived = ctx["perceived_all"]
    official = ctx["official_all"]
    inferential = ctx["inferential"]
    meta = inferential.get("meta", {})

    section_title("研究定位")
    st.markdown(
        """
        <div class="glass-card">
          <p style='font-size:1.02rem; line-height:1.75;'>
            春節為臺鐵年度最高運量壓力測試。本研究以 <b>2022–2026 年春節期間</b>
            交通部公開的「臺鐵列車即時延誤時間歷史資料」為基礎，比較
            <b>官方準點口徑（指標 A，終點站 ≤ 5 分）</b> 與
            <b>旅客感知口徑（指標 B，全程各站 ≤ 3/5 分）</b> 的誤點樣貌，
            並以 ANOVA、Tukey HSD、配對 t、Logistic 迴歸檢定年份與春節節點的差異。
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_title("樣本規模")
    cols = st.columns(4)
    with cols[0]:
        kpi_card("觀測年份", f"{len(meta.get('年份', []))} 年", sub="2022–2026")
    with cols[1]:
        kpi_card("B 感知觀測", f"{meta.get('B筆數', len(perceived)):,}", color="green", sub="站點級")
    with cols[2]:
        kpi_card("A 官方車次", f"{meta.get('A筆數', len(official)):,}", color="blue", sub="每日每車次")
    with cols[3]:
        kpi_card("春節節點", "6 類", sub="除夕前至春節後")

    section_title("關鍵發現")
    anova_b = inferential.get("anova_year_delay_perceived", {})
    yearly = anova_b.get("各年平均", {})
    peak_year = max(yearly, key=lambda k: yearly[k]) if yearly else None

    tukey_pairs = inferential.get("tukey_period_delay", {}).get("pairs", [])
    pre_eve_effect = next(
        (p for p in tukey_pairs if "除夕前夕" in str(p.get("group2", "")) and "收假日" in str(p.get("group1", ""))),
        None,
    )

    paired = inferential.get("paired_AB", {})
    logistic = inferential.get("logistic_official", {})

    rows = st.columns(2)
    with rows[0]:
        if peak_year:
            story_card(
                "年度異常",
                f"{peak_year} 年感知平均誤點 {yearly[peak_year]:.2f} 分鐘",
                f"明顯高於其他四年（約 1.3–1.9 分鐘區間），ANOVA F={anova_b.get('F', 0):.1f}，"
                "p < .001，差異達統計顯著。",
                tone="red",
            )
        story_card(
            "A vs B 落差",
            f"指標 A 比 B 高出 {paired.get('差_均值', 0):.2f} 分鐘",
            f"配對 t={paired.get('t', 0):.2f}，p < .001，樣本 {paired.get('配對數', 0):,} 組。"
            "說明末站延誤（官方口徑）系統性高於全程平均。",
            tone="yellow",
        )
    with rows[1]:
        if pre_eve_effect:
            story_card(
                "節點高峰",
                f"除夕前夕誤點 +{pre_eve_effect.get('meandiff', 0):.2f} 分鐘",
                "相較收假日，除夕前 1–2 天誤點明顯升高（Tukey p < .001），為五年一致的尖峰節點。",
                tone="red",
            )
        story_card(
            "模型解釋力",
            f"Logistic Pseudo R² = {logistic.get('pseudo_R2', 0):.3f}",
            f"在控制車種、路線、年份後，春節節點與年份對準點仍有獨立顯著效果，"
            f"樣本 {logistic.get('樣本數', 0):,} 車次。",
            tone="blue",
        )

    section_title("資料與指標")
    note_card(
        "資料來源",
        "交通部「臺鐵列車即時延誤時間歷史資料」2022–2026 年春節期間；經去重（同日同車次同站取 SrcUpdateTime 最晚），"
        "補上春節節點、車種、路線區段三個衍生變項。",
    )
    note_card(
        "指標 A（官方準點率 proxy）",
        "每 (日期, 車次) 一筆，取該車次當日最晚觀測站的延誤，閾值 5 分鐘；用以逼近臺鐵官方「終點站 ≤ 5 分」口徑。",
    )
    note_card(
        "指標 B（旅客感知準點率）",
        "每 (日期, 車次, 車站) 一筆，以全程各站觀測的延誤平均，提供閾值 3 / 5 分鐘雙版本。",
    )
