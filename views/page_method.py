"""
方法論 — 變項定義、春節節點切分規則、資料清理流程
"""
import streamlit as st

from views.components import method_step, section_title, note_card, var_tag


def render(ctx: dict) -> None:
    section_title("變項定義")
    cols = st.columns(2)
    with cols[0]:
        st.markdown(var_tag("Y<sub>1</sub>", "延誤分鐘（連續）"), unsafe_allow_html=True)
        st.markdown(var_tag("Y<sub>2A</sub>", "準點（官方 5 分）"), unsafe_allow_html=True)
        st.markdown(var_tag("Y<sub>2B</sub>", "準點（感知 3 / 5 分）"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(var_tag("X<sub>1</sub>", "年（2022–2026）"), unsafe_allow_html=True)
        st.markdown(var_tag("X<sub>2</sub>", "春節節點（6 類）"), unsafe_allow_html=True)
        st.markdown(var_tag("X<sub>3</sub>", "車種（自強 / 莒光 / 區間…）"), unsafe_allow_html=True)
        st.markdown(var_tag("X<sub>4</sub>", "路線區段（7 類）"), unsafe_allow_html=True)

    section_title("春節節點切分規則")
    st.markdown(
        """
        <div class="glass-card">
          <p>以農曆除夕當日為原點（<code>offset=0</code>），依日期與該年除夕相對天數分類：</p>
          <ul>
            <li><b>春節前（除夕前 3 天以上）</b>：offset &lt; -2</li>
            <li><b>除夕前夕（除夕前 1–2 天）</b>：-2 ≤ offset ≤ -1</li>
            <li><b>除夕</b>：offset = 0</li>
            <li><b>春節期間（初一至初三）</b>：1 ≤ offset ≤ 3</li>
            <li><b>收假日（初四至初六）</b>：4 ≤ offset ≤ 6</li>
            <li><b>春節後（初七以上）</b>：offset ≥ 7</li>
          </ul>
          <p>五年除夕對照：2022-01-31、2023-01-21、2024-02-09、2025-01-28、2026-02-16。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_title("資料清理流程")
    st.markdown(
        f"""
        <div class="glass-card">
            {method_step("1", "讀取五年原始 CSV", "交通部公開『臺鐵列車即時延誤時間歷史資料』，逐日 CSV 共 2022–2026 春節期間。")}
            {method_step("2", "時區與型別整理", "SrcUpdateTime / UpdateTime 轉為 Asia/Taipei，取日期作為日索引。")}
            {method_step("3", "去重", "以 (日期, TrainNo, StationID) 為鍵，保留 SrcUpdateTime 最晚的一筆，反映車站離站前最後觀測。")}
            {method_step("4", "衍生變項", "依 TrainNo 首碼判定車種、依 StationID 首碼歸納路線區段、以相對除夕日產生春節節點。")}
            {method_step("5", "雙指標建構", "A 官方 proxy：每 (日期, 車次) 取最晚觀測站延誤；B 感知：每 (日期, 車次, 車站) 皆列入。")}
            {method_step("6", "推論統計", "ANOVA、卡方、Tukey HSD、配對 t、Logistic 迴歸，並輸出 inferential_results.json。")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_title("指標選擇說明")
    note_card(
        "為何 A 是 proxy 而非真正『終點站』",
        "臺鐵即時延誤 API 在列車進入終點站後停止更新，最晚觀測通常為倒數 1–2 站。"
        "倒數 1–2 站至終點站車程多為 5–10 分鐘，列車已無顯著加減速空間，延誤狀態大致等同終點到站延誤，"
        "因此以『最後觀測站延誤』作為官方口徑 proxy。",
    )
    note_card(
        "為何採雙指標",
        "官方以終點站為基準易低估沿線累積壓力；感知指標以全程各站為基準，更能反映旅客實際體驗差異。"
        "兩者並呈可凸顯統計口徑選擇對結論的影響。",
    )

    section_title("參考資料")
    st.markdown(
        """
        <div class="glass-card">
          <ul>
            <li>交通部統計處《臺鐵旅客列車營運概況》20611-01-01。</li>
            <li>交通部 TDX 開放資料平臺：臺鐵列車即時延誤時間歷史資料。</li>
            <li>分析腳本：<code>RAWdata/analysis/scripts/01_clean.py</code> ~ <code>04_inferential.py</code>。</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
