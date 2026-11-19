"""⑥ 服务价值小结 + 规则模板月度报告生成、预览、复制、下载与保存。"""

from datetime import datetime

import streamlit as st

import ui
from db.analysis import (
    analyze_window_contents,
    fetch_window_contents,
    month_analysis_window,
)
from db.database import PLATFORM_LABELS, fetch_accounts, init_db
from db.metrics import fetch_account_performance, fetch_available_months, fetch_core_metrics
from db.reports import (
    fetch_latest_analysis_report,
    generate_monthly_report,
    save_analysis_report,
)

st.set_page_config(page_title="服务价值与月度报告", page_icon="🗂️", layout="wide")
ui.inject_css()
init_db()

current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
session_month = st.session_state.get("report_month", current_month)
if session_month not in months:
    months.insert(0, session_month)

ui.page_header(
    "服务价值小结 · 月度报告",
    "本月运营带来的品牌与转化价值",
    f"{session_month[:4]} 年 {session_month[5:7]} 月",
    "真实上传数据",
)

selected_month = st.selectbox(
    "报告月份",
    options=months,
    index=months.index(session_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
    key="report_month",
    label_visibility="collapsed",
)

core = fetch_core_metrics(selected_month)
if core["content_count"] == 0:
    st.info("本月暂无数据，无法生成报告")
    st.stop()

# ---------------------------------------------------------------------------
# ⑥ 服务价值小结
# ---------------------------------------------------------------------------
account_rows = fetch_account_performance(selected_month)
total_interactions = core["likes"] + core["comments"] + core["shares"] + core["favorites"]

start_time, end_time = month_analysis_window(selected_month)
window_contents = fetch_window_contents(start_time, end_time)
accounts = fetch_accounts()
hits, _ = analyze_window_contents(window_contents, accounts, 2.0)

platform_parts = []
for platform, label in PLATFORM_LABELS.items():
    platform_views = sum(row["views"] for row in account_rows if row["platform"] == platform)
    platform_counts = sum(row["content_count"] for row in account_rows if row["platform"] == platform)
    platform_parts.append(f"{label}{platform_views:,}（{platform_counts} 条）")

ui.section("06", "服务价值小结", "本月运营带来的品牌与转化价值")
ui.value_grid(
    [
        {
            "label": "本月总曝光",
            "value": ui.fmt_int(core["views"]),
            "detail": " + ".join(
                f"{label}{sum(row['views'] for row in account_rows if row['platform'] == platform):,}"
                for platform, label in PLATFORM_LABELS.items()
            ),
        },
        {
            "label": "本月总互动",
            "value": ui.fmt_int(total_interactions),
            "detail": f"点赞 {core['likes']:,} + 评论 {core['comments']:,} + 分享 {core['shares']:,} + 收藏 {core['favorites']:,}",
        },
        {
            "label": "内容产出",
            "value": f"{core['content_count']} 条",
            "detail": f"覆盖 {core['account_count']} 个账号",
        },
        {
            "label": "识别爆款",
            "value": f"{len(hits)} 条",
            "detail": "互动量超过账号均值 2 倍",
        },
    ]
)

active_rows = [row for row in account_rows if row["content_count"] > 0]
top_platform_label, top_platform_views = max(
    ((label, sum(row["views"] for row in account_rows if row["platform"] == platform)) for platform, label in PLATFORM_LABELS.items()),
    key=lambda pair: pair[1],
)
best_account = max(active_rows, key=lambda row: (row["total_interactions"], row["views"]))
weakest_account = min(active_rows, key=lambda row: (row["total_interactions"], row["views"]))
top_share = top_platform_views / core["views"] if core["views"] else 0

ui.text_card(
    [
        f"<b>统计周期：</b>{selected_month[:4]} 年 {selected_month[5:7]} 月　<b>数据来源：</b>手动上传的平台导出文件",
        f"本月矩阵共发布 <b>{core['content_count']}</b> 条内容，覆盖 <b>{core['account_count']}</b> 个账号，"
        f"获得总曝光 <b>{core['views']:,}</b> 次、总互动 <b>{total_interactions:,}</b> 次，"
        f"按默认规则识别爆款 <b>{len(hits)}</b> 条。",
        f"{top_platform_label}是本月主要传播阵地，曝光占比 <b>{top_share:.1%}</b>；"
        f"「{ui.esc(best_account['account_name'])}」互动表现领先（{best_account['total_interactions']:,} 次），"
        f"「{ui.esc(weakest_account['account_name'])}」本月互动 {weakest_account['total_interactions']:,} 次，仍有提升空间。",
        f"各平台曝光结构：" + "；".join(platform_parts) + "。",
        "建议下月复用高互动选题与爆款表达，加强低效账号更新与跨平台协同，"
        "持续跟踪数据变化，提升校园品牌传播、招生宣传和家校沟通的实际成效。",
    ]
)

st.divider()

# ---------------------------------------------------------------------------
# 月度报告
# ---------------------------------------------------------------------------
ui.section("附", "月度报告", "规则模板生成 · 不调用外部 AI API")

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
