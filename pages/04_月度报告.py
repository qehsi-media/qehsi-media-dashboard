"""规则模板月度报告生成、预览、复制、下载与保存。"""

from datetime import datetime

import streamlit as st

from db.database import init_db
from db.metrics import fetch_available_months, fetch_core_metrics
from db.reports import (
    fetch_latest_analysis_report,
    generate_monthly_report,
    save_analysis_report,
)

st.set_page_config(page_title="月度报告", page_icon="🗂️", layout="wide")
st.title("月度报告")
st.caption("报告由规则模板和 SQLite 数据生成，不调用外部 AI API。")

init_db()
current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
selected_month = st.selectbox(
    "报告月份",
    options=months,
    index=months.index(current_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
)

if fetch_core_metrics(selected_month)["content_count"] == 0:
    st.info("本月暂无数据，无法生成报告")
    st.stop()

latest_report = fetch_latest_analysis_report(selected_month)
session_report = st.session_state.get("current_monthly_report")
if not session_report or session_report["report_month"] != selected_month:
    session_report = latest_report

button_columns = st.columns(2)
generate_clicked = button_columns[0].button("生成本月报告", type="primary")
regenerate_clicked = button_columns[1].button(
    "重新生成", disabled=session_report is None
)

if generate_clicked or regenerate_clicked:
    report_content = generate_monthly_report(selected_month)
    if report_content is None:
        st.info("本月暂无数据，无法生成报告")
        st.stop()
    report_id = save_analysis_report(selected_month, report_content)
    session_report = fetch_latest_analysis_report(selected_month)
    st.session_state["current_monthly_report"] = session_report
    st.success(f"报告已生成并保存到 analysis_reports，记录 ID：{report_id}")

if session_report is None:
    st.info("请点击“生成本月报告”。")
    st.stop()

report_content = session_report["report_content"]
st.caption(
    f"当前报告：{selected_month}｜保存时间：{session_report['created_at']}｜"
    f"记录 ID：{session_report['id']}"
)
st.download_button(
    "下载 Markdown 报告（.md）",
    data=report_content.encode("utf-8"),
    file_name=f"新媒体月度报告_{selected_month}.md",
    mime="text/markdown",
)

preview_tab, copy_tab = st.tabs(["报告预览", "复制 Markdown"])
with preview_tab:
    st.markdown(report_content)
with copy_tab:
    st.caption("代码框右上角提供复制按钮，可复制完整 Markdown 原文。")
    st.code(report_content, language="markdown", wrap_lines=True)
