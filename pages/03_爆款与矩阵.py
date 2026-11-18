"""爆款识别、IP 矩阵与多平台联动分析。"""

from datetime import datetime

import pandas as pd
import streamlit as st

from db.analysis import (
    aggregate_cross_platform,
    analyze_window_contents,
    fetch_month_contents,
    fetch_window_contents,
    month_analysis_window,
)
from db.database import PLATFORM_LABELS, fetch_accounts, init_db
from db.metrics import fetch_available_months



def heat_cells(series: pd.Series) -> list[str]:
    """按列数值生成不依赖额外绘图库的热力底色。"""
    values = pd.to_numeric(series, errors="coerce").fillna(0)
    maximum = values.max()
    if maximum <= 0:
        return [""] * len(series)
    return [
        f"background-color: rgba(255, 112, 67, {0.06 + 0.38 * value / maximum:.3f})"
        for value in values
    ]


st.set_page_config(page_title="爆款与矩阵", page_icon="🔥", layout="wide")
st.title("爆款与矩阵")
init_db()

current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
selected_month = st.selectbox(
    "统计月份",
    options=months,
    index=months.index(current_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
)
threshold = st.number_input(
    "爆款倍数阈值",
    min_value=0.0,
    value=2.0,
    step=0.1,
    help="内容互动量严格大于账号近 30 天平均互动量 × 阈值时，标记为爆款。",
)
start_time, end_time = month_analysis_window(selected_month)
st.caption(
    f"爆款与 IP 矩阵窗口：{start_time[:10]} 至 {end_time[:10]}；"
    f"多平台联动按 {selected_month} 自然月统计。"
)

accounts = fetch_accounts()
window_contents = fetch_window_contents(start_time, end_time)
hits, matrix_rows = analyze_window_contents(window_contents, accounts, threshold)
month_contents = fetch_month_contents(selected_month)

st.subheader("爆款识别")
st.caption("账号平均互动按同一 30 天窗口内全部内容计算（含当前内容）；平均互动为 0 时，爆款倍数显示“—”。")
if not window_contents:
    st.info("近 30 天暂无数据，请先上传")

for platform, platform_label in PLATFORM_LABELS.items():
    st.markdown(f"#### {platform_label}爆款")
    platform_hits = [row for row in hits if row["platform"] == platform]
    if not platform_hits:
        st.caption("暂无符合当前阈值的内容")
        continue
    hit_table = pd.DataFrame(
        [
            {
                "标记": "🔥爆款",
                "平台": platform_label,
                "账号": row["account_name"],
                "标题": row["content_title"],
                "发布时间": row["publish_time"],
                "播放/阅读": row["views"],
                "互动量": row["total_interactions"],
                "爆款倍数": f"{row['hit_ratio']:.2f} 倍"
                if row["hit_ratio"] is not None
                else "—",
                "链接": row["link"],
            }
            for row in platform_hits
        ]
    )
    st.dataframe(
        hit_table,
        width="stretch",
        hide_index=True,
        column_config={
            "链接": st.column_config.LinkColumn("链接", display_text="打开链接")
        },
    )

st.divider()
st.subheader("IP 矩阵")
if not window_contents:
    st.info("当前窗口无内容，以下保留 7 个账号并显示 0")
matrix_table = pd.DataFrame(
    [
        {
            "账号名称": row["account_name"],
            "平台": PLATFORM_LABELS.get(row["platform"], row["platform"]),
            "内容数": row["content_count"],
            "总曝光": row["views"],
            "总互动": row["total_interactions"],
            "平均互动": round(row["average_interactions"], 2),
            "爆款数": row["hit_count"],
            "最近发布时间": row["last_publish_time"] or "—",
        }
        for row in matrix_rows
    ]
)
heat_columns = ["内容数", "总曝光", "总互动", "平均互动", "爆款数"]
st.dataframe(
    matrix_table.style.apply(heat_cells, subset=heat_columns),
    width="stretch",
    hide_index=True,
)
st.caption("颜色按每列数值深浅标记；爆款数随上方阈值同步变化。")

st.divider()
st.subheader("多平台联动分析")
dimension = st.radio(
    "聚合维度",
    options=["topic", "content_type"],
    format_func=lambda value: "按主题（topic）" if value == "topic" else "按内容类型（content_type）",
    horizontal=True,
)
if not month_contents:
    st.info("本月暂无数据，请先上传")
else:
    cross_rows = aggregate_cross_platform(month_contents, dimension)
    label_column = "主题" if dimension == "topic" else "内容类型"
    cross_table = pd.DataFrame(
        [
            {
                label_column: row["label"],
                "平台": PLATFORM_LABELS.get(row["platform"], row["platform"]),
                "发布数量": row["content_count"],
                "总互动": row["total_interactions"],
                "平均互动": round(row["average_interactions"], 2),
            }
            for row in cross_rows
        ]
    )
    st.dataframe(cross_table, width="stretch", hide_index=True)
    st.caption("topic 为空归为“未标注主题”；content_type 为空归为“未标注类型”。")
