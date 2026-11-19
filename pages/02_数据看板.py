"""① 本月核心数据 + ② 各账号表现。"""

from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import ui
from db.database import PLATFORM_LABELS, fetch_accounts, init_db
from db.metrics import (
    fetch_account_performance,
    fetch_available_months,
    fetch_core_metrics,
    shift_month,
)

st.set_page_config(page_title="数据看板", page_icon="📈", layout="wide")
ui.inject_css()
init_db()

current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
session_month = st.session_state.get("dash_month", current_month)
if session_month not in months:
    months.insert(0, session_month)

ui.page_header(
    "青实高国际 · 新媒体矩阵数据看板",
    "青岛实验高中国际部 — 抖音 / 视频号 / 公众号 7 账号矩阵",
    f"{session_month[:4]} 年 {session_month[5:7]} 月",
    "真实上传数据",
)

selected_month = st.selectbox(
    "统计月份",
    options=months,
    index=months.index(session_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
    key="dash_month",
    label_visibility="collapsed",
)

core = fetch_core_metrics(selected_month)
if core["content_count"] == 0:
    st.info("本月暂无数据，请先到「数据上传」页上传平台导出的 CSV/XLSX 文件。")
    st.stop()

previous = fetch_core_metrics(shift_month(selected_month, -1))
total_interactions = core["likes"] + core["comments"] + core["shares"] + core["favorites"]

# ---------------------------------------------------------------------------
# ① 本月核心数据
# ---------------------------------------------------------------------------
ui.section("01", "本月核心数据", f"{selected_month[:4]} 年 {selected_month[5:7]} 月 · 覆盖 {core['account_count']} 个账号")
ui.kpi_grid(
    [
        {
            "label": "总播放 / 阅读",
            "value": ui.fmt_int(core["views"]),
            "delta": ui.delta_html(core["views"], previous["views"]),
        },
        {
            "label": "总互动",
            "value": ui.fmt_int(total_interactions),
            "delta": ui.delta_html(total_interactions, previous["likes"] + previous["comments"] + previous["shares"] + previous["favorites"]),
        },
        {
            "label": "总点赞",
            "value": ui.fmt_int(core["likes"]),
            "delta": ui.delta_html(core["likes"], previous["likes"]),
        },
        {
            "label": "总评论",
            "value": ui.fmt_int(core["comments"]),
            "delta": ui.delta_html(core["comments"], previous["comments"]),
        },
        {
            "label": "总分享",
            "value": ui.fmt_int(core["shares"]),
            "delta": ui.delta_html(core["shares"], previous["shares"]),
        },
        {
            "label": "内容产出",
            "value": f"{ui.fmt_int(core['content_count'])} 条",
            "delta": ui.delta_html(core["content_count"], previous["content_count"]),
        },
    ]
)
st.caption("总互动 = 点赞 + 评论 + 分享 + 收藏；环比对比上一个自然月，上月无数据时显示“新增”。")

# ---------------------------------------------------------------------------
# ② 各账号表现
# ---------------------------------------------------------------------------
ui.section("02", "各账号表现", "7 个账号本月数据一览")

accounts = fetch_accounts()
group_map = {(row["platform"], row["account_name"]): row.get("account_group") for row in accounts}
account_rows = fetch_account_performance(selected_month)
platform_order = {platform: index for index, platform in enumerate(PLATFORM_LABELS)}
account_rows.sort(key=lambda row: (platform_order.get(row["platform"], 9), -row["views"]))

card_rows = []
for row in account_rows:
    views = row["views"]
    card_rows.append(
        {
            "platform": row["platform"],
            "account_name": row["account_name"],
            "role": ui.account_role(row["platform"], group_map.get((row["platform"], row["account_name"]))),
            "content_count": row["content_count"],
            "views": views,
            "interactions": row["total_interactions"],
            "rate": (row["total_interactions"] / views) if views else None,
        }
    )
ui.account_grid(card_rows)

st.write("")
left, right = st.columns([1.35, 1])
with left:
    st.markdown("**各账号本月曝光对比**　<span class='q-hint'>播放量 / 阅读量</span>", unsafe_allow_html=True)
    chart_df = pd.DataFrame(
        [
            {
                "账号": row["account_name"][:14],
                "平台": PLATFORM_LABELS.get(row["platform"], row["platform"]),
                "曝光": row["views"],
                "互动": row["total_interactions"],
            }
            for row in account_rows
        ]
    )
    bars = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusEnd=6, height=16)
        .encode(
            y=alt.Y("账号:N", sort="-x", title=None, axis=alt.Axis(labelLimit=150)),
            x=alt.X("曝光:Q", title=None),
            color=alt.Color(
                "平台:N",
                scale=alt.Scale(
                    domain=list(PLATFORM_LABELS.values()),
                    range=[ui.PLATFORM_COLORS[key] for key in PLATFORM_LABELS],
                ),
                legend=None,
            ),
            tooltip=["账号", "平台", alt.Tooltip("曝光:Q", format=","), alt.Tooltip("互动:Q", format=",")],
        )
        .properties(height=300)
    )
    st.altair_chart(ui.style_chart(bars), use_container_width=True)

with right:
    st.markdown("**各账号互动率对比**　<span class='q-hint'>互动量 ÷ 曝光量</span>", unsafe_allow_html=True)
    rate_df = pd.DataFrame(
        [
            {
                "账号": row["account_name"][:14],
                "平台": PLATFORM_LABELS.get(row["platform"], row["platform"]),
                "互动率": (row["total_interactions"] / row["views"]) if row["views"] else 0.0,
            }
            for row in account_rows
        ]
    )
    rate_chart = (
        alt.Chart(rate_df)
        .mark_bar(cornerRadiusEnd=6, height=16)
        .encode(
            y=alt.Y("账号:N", sort="-x", title=None, axis=alt.Axis(labelLimit=150)),
            x=alt.X("互动率:Q", title=None, axis=alt.Axis(format=".1%")),
            color=alt.Color(
                "平台:N",
                scale=alt.Scale(
                    domain=list(PLATFORM_LABELS.values()),
                    range=[ui.PLATFORM_COLORS[key] for key in PLATFORM_LABELS],
                ),
                legend=None,
            ),
            tooltip=["账号", "平台", alt.Tooltip("互动率:Q", format=".2%")],
        )
        .properties(height=300)
    )
    st.altair_chart(ui.style_chart(rate_chart), use_container_width=True)

st.write("")
platform_rows = []
for platform, label in PLATFORM_LABELS.items():
    rows = [row for row in account_rows if row["platform"] == platform]
    platform_views = sum(row["views"] for row in rows)
    platform_rows.append(
        [
            label,
            f'<span class="cell-sub">{len(rows)} 个账号</span>',
            f'<span class="num">{sum(row["content_count"] for row in rows):,}</span>',
            f'<span class="num">{platform_views:,}</span>',
            f'<span class="num">{sum(row["total_interactions"] for row in rows):,}</span>',
            f'<span class="num">{(platform_views / core["views"]):.1%}</span>' if core["views"] else "—",
        ]
    )
ui.html_table(["平台", "账号", "内容数", "总曝光", "总互动", "曝光占比"], platform_rows)
st.caption("总曝光为播放量 / 阅读量之和；曝光占比 = 该平台总曝光 ÷ 全平台总曝光。")
