"""本月核心数据与各账号表现。"""

from datetime import datetime

import pandas as pd
import streamlit as st

from db.database import PLATFORM_LABELS, init_db
from db.metrics import (
    fetch_account_performance,
    fetch_available_months,
    fetch_core_metrics,
)

st.set_page_config(page_title="数据看板", page_icon="📈", layout="wide")
st.title("数据看板")
st.caption("按 publish_time 所在月份统计；总互动 = 点赞 + 评论 + 分享 + 收藏。")

init_db()
current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
selected_month = st.selectbox(
    "统计月份",
    options=months,
    index=months.index(current_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
)

core = fetch_core_metrics(selected_month)
if core["content_count"] == 0:
    st.info("本月暂无数据，请先上传")
    st.stop()

st.subheader("本月核心数据")
first_row = st.columns(4)
first_row[0].metric("总播放/阅读量", f"{core['views']:,}")
first_row[1].metric("总点赞", f"{core['likes']:,}")
first_row[2].metric("总评论", f"{core['comments']:,}")
first_row[3].metric("总分享", f"{core['shares']:,}")
second_row = st.columns(3)
second_row[0].metric("总收藏", f"{core['favorites']:,}")
second_row[1].metric("内容总数", f"{core['content_count']:,}")
second_row[2].metric("覆盖账号数", f"{core['account_count']:,}")

st.divider()
account_rows = fetch_account_performance(selected_month)

st.subheader("各账号表现")
account_table = pd.DataFrame(
    [
        {
            "账号名称": row["account_name"],
            "平台": PLATFORM_LABELS.get(row["platform"], row["platform"]),
            "内容数": row["content_count"],
            "总播放/阅读": row["views"],
            "总互动": row["total_interactions"],
            "平均互动": round(
                row["total_interactions"] / row["content_count"], 2
            )
            if row["content_count"]
            else 0.0,
            "互动率": f"{row['total_interactions'] / row['views']:.2%}"
            if row["views"]
            else "—",
        }
        for row in account_rows
    ]
)
st.dataframe(account_table, width="stretch", hide_index=True)
st.caption("平均互动 = 总互动 ÷ 内容数；互动率 = 总互动 ÷ 总播放/阅读，播放/阅读为 0 时显示“—”。")

st.subheader("各账号互动量排名")
chart_rows = [row for row in account_rows if row["content_count"] > 0]
chart_df = pd.DataFrame(
    [
        {
            "账号": f"{row['account_name']}（{PLATFORM_LABELS.get(row['platform'], row['platform'])}）",
            "总互动": row["total_interactions"],
        }
        for row in sorted(chart_rows, key=lambda item: item["total_interactions"])
    ]
)
if chart_df.empty:
    st.info("暂无可排名的账号数据")
else:
    st.bar_chart(chart_df, x="账号", y="总互动", horizontal=True)

st.divider()
st.subheader("平台维度汇总")
platform_table = pd.DataFrame(
    [
        {
            "平台": label,
            "内容数": sum(
                row["content_count"]
                for row in account_rows
                if row["platform"] == platform
            ),
            "总曝光": sum(
                row["views"] for row in account_rows if row["platform"] == platform
            ),
            "总互动": sum(
                row["total_interactions"]
                for row in account_rows
                if row["platform"] == platform
            ),
            "占比": (
                f"{sum(row['views'] for row in account_rows if row['platform'] == platform) / core['views']:.2%}"
                if core["views"]
                else "0.00%"
            ),
        }
        for platform, label in PLATFORM_LABELS.items()
    ]
)
st.dataframe(platform_table, width="stretch", hide_index=True)
st.caption("总曝光为播放量/阅读量之和；占比 = 该平台总曝光 ÷ 全平台总曝光。")
