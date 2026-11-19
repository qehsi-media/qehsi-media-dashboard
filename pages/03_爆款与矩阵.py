"""③ IP 矩阵 + ④ 爆款内容 + ⑤ 多平台联动亮点。"""

from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import ui
from db.analysis import (
    aggregate_cross_platform,
    analyze_window_contents,
    fetch_month_contents,
    fetch_window_contents,
    month_analysis_window,
)
from db.database import PLATFORM_LABELS, fetch_accounts, init_db
from db.metrics import fetch_available_months

st.set_page_config(page_title="爆款与矩阵", page_icon="🔥", layout="wide")
ui.inject_css()
init_db()

current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
session_month = st.session_state.get("matrix_month", current_month)
if session_month not in months:
    months.insert(0, session_month)

ui.page_header(
    "IP 矩阵 · 爆款内容 · 联动亮点",
    "角色分工 × 能力雷达 × 三平台协同",
    f"{session_month[:4]} 年 {session_month[5:7]} 月",
    "真实上传数据",
)

control_left, control_right = st.columns([3, 1])
selected_month = control_left.selectbox(
    "统计月份",
    options=months,
    index=months.index(session_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
    key="matrix_month",
    label_visibility="collapsed",
)
threshold = control_right.number_input(
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
group_map = {(row["platform"], row["account_name"]): row.get("account_group") for row in accounts}
window_contents = fetch_window_contents(start_time, end_time)
hits, matrix_rows = analyze_window_contents(window_contents, accounts, threshold)
month_contents = fetch_month_contents(selected_month)

platform_order = {platform: index for index, platform in enumerate(PLATFORM_LABELS)}
matrix_rows.sort(key=lambda row: (platform_order.get(row["platform"], 9), -row["total_interactions"]))

# ---------------------------------------------------------------------------
# ③ IP 矩阵
# ---------------------------------------------------------------------------
ui.section("03", "IP 矩阵", "角色分工 × 能力雷达")

matrix_table_rows = []
for row in matrix_rows:
    matrix_table_rows.append(
        [
            f'<b>{ui.esc(row["account_name"])}</b>',
            f'<span class="cell-sub">{ui.esc(ui.account_role(row["platform"], group_map.get((row["platform"], row["account_name"]))))}</span>',
            f'<span class="q-plat {ui.PLATFORM_TAG_CLASS.get(row["platform"], "dy")}">{ui.esc(PLATFORM_LABELS.get(row["platform"], row["platform"]))}</span>',
            f'<span class="num">{row["content_count"]:,}</span>',
            f'<span class="num">{row["views"]:,}</span>',
            f'<span class="num">{row["total_interactions"]:,}</span>',
            f'<span class="num">{row["average_interactions"]:.2f}</span>',
            f'<span class="num">{row["hit_count"]:,}</span>',
            f'<span class="cell-sub">{ui.esc(row["last_publish_time"][:10] if row["last_publish_time"] else "—")}</span>',
        ]
    )
ui.html_table(
    ["账号名称", "角色", "平台", "内容数", "总曝光", "总互动", "平均互动", "爆款数", "最近发布"],
    matrix_table_rows,
    heat_columns={3, 4, 5, 6, 7},
)
st.caption("颜色按每列数值深浅标记；爆款数随上方阈值同步变化，平均互动 = 总互动 ÷ 内容数。")

platform_stats = {
    platform: {"content_count": 0, "views": 0, "interactions": 0, "hits": 0}
    for platform in PLATFORM_LABELS
}
for row in matrix_rows:
    stats = platform_stats[row["platform"]]
    stats["content_count"] += row["content_count"]
    stats["views"] += row["views"]
    stats["interactions"] += row["total_interactions"]
    stats["hits"] += row["hit_count"]

radar_dims = ["内容量", "总曝光", "总互动", "平均互动", "爆款数"]
raw_values = {}
for platform, stats in platform_stats.items():
    raw_values[platform] = [
        stats["content_count"],
        stats["views"],
        stats["interactions"],
        (stats["interactions"] / stats["content_count"]) if stats["content_count"] else 0,
        stats["hits"],
    ]
maxima = [max(raw_values[p][index] for p in raw_values) or 1 for index in range(len(radar_dims))]
radar_series = [
    {
        "name": PLATFORM_LABELS[platform],
        "color": ui.PLATFORM_COLORS[platform],
        "values": [round(raw_values[platform][index] / maxima[index] * 100, 1) for index in range(len(radar_dims))],
    }
    for platform in PLATFORM_LABELS
]

left, right = st.columns([1.05, 1])
with left:
    st.markdown("**三平台矩阵能力雷达**　<span class='q-hint'>5 维归一化对比</span>", unsafe_allow_html=True)
    ui.radar_svg(radar_series, radar_dims)
with right:
    st.markdown("**矩阵角色解读**", unsafe_allow_html=True)
    ui.render(
        """
        <div style="margin-top:.3rem">
          <div style="margin-bottom:.75rem">
            <div style="font-size:.84rem;font-weight:800">引流层 — 人格化 IP（阿拉丁神花 ×2）</div>
            <div style="font-size:.78rem;color:var(--muted);margin-top:.15rem;line-height:1.7">
              学生视角、高情绪、高收藏，负责把陌生流量第一次带进矩阵。</div>
          </div>
          <div style="margin-bottom:.75rem">
            <div style="font-size:.84rem;font-weight:800">信任层 — 官方主号（QEHSI / 青实高国际 ×2）</div>
            <div style="font-size:.78rem;color:var(--muted);margin-top:.15rem;line-height:1.7">
              权威发布、活动直播与品牌形象，承接 IP 引来的流量并完成“关注→信任”。</div>
          </div>
          <div style="margin-bottom:.75rem">
            <div style="font-size:.84rem;font-weight:800">转化层 — 垂类事件号（校内出分版 ×2）</div>
            <div style="font-size:.78rem;color:var(--muted);margin-top:.15rem;line-height:1.7">
              围绕出分 / offer 等高情绪事件制造爆款，是涨粉与咨询转化的尖刀。</div>
          </div>
          <div>
            <div style="font-size:.84rem;font-weight:800">沉淀层 — 公众号（青实高国际）</div>
            <div style="font-size:.78rem;color:var(--muted);margin-top:.15rem;line-height:1.7">
              长图文沉淀政策解读与喜报，承担搜索长尾流量与私域咨询入口，向报名转化。</div>
          </div>
        </div>
        """
    )

# ---------------------------------------------------------------------------
# ④ 爆款内容
# ---------------------------------------------------------------------------
ui.section("04", "爆款内容", "按平台查看近 30 天高互动内容")
st.caption(
    "判定规则：内容互动量 > 账号近 30 天平均互动量 × 阈值。"
    "平均互动为 0 时爆款倍数显示“—”。"
)

if not window_contents:
    st.info("近 30 天暂无数据，请先上传。")
elif not hits:
    st.info("当前阈值下没有识别到爆款，可下调上方“爆款倍数阈值”。")
else:
    average_map = {(row["platform"], row["account_name"]): row["average_interactions"] for row in matrix_rows}
    tabs = st.tabs([f"{label}爆款" for label in PLATFORM_LABELS.values()])
    for tab, (platform, label) in zip(tabs, PLATFORM_LABELS.items()):
        platform_hits = [row for row in hits if row["platform"] == platform]
        with tab:
            if not platform_hits:
                st.caption("暂无符合当前阈值的内容")
                continue
            cards = []
            for row in platform_hits:
                average = average_map.get((row["platform"], row["account_name"]), 0)
                ratio_text = f"{row['hit_ratio']:.2f} 倍" if row["hit_ratio"] is not None else "—"
                note = (
                    f"互动量为账号近 30 天均值的 {ratio_text}"
                    if row["hit_ratio"] is not None
                    else "账号平均互动为 0，按绝对互动量展示"
                )
                tags = [row["account_name"]]
                if row.get("content_type"):
                    tags.append(str(row["content_type"]))
                if row.get("topic"):
                    tags.append(str(row["topic"]))
                cards.append(
                    {
                        "title": row["content_title"],
                        "date": (row["publish_time"] or "")[:10],
                        "views": row["views"],
                        "interactions": row["total_interactions"],
                        "ratio": ratio_text,
                        "tags": tags,
                        "note": note,
                        "link": row.get("link"),
                    }
                )
            ui.hit_grid(cards)

# ---------------------------------------------------------------------------
# ⑤ 多平台联动亮点
# ---------------------------------------------------------------------------
ui.section("05", "联动亮点", f"{selected_month} 自然月 · 同主题跨平台表现")

topic_rows = [
    row
    for row in aggregate_cross_platform(month_contents, "topic")
    if row["label"] != "未标注主题"
]

if not topic_rows:
    st.info("本月暂无带 topic 标注的内容。上传时填写 topic 后即可自动生成跨平台联动分析。")
else:
    topic_totals: dict[str, dict] = {}
    for row in topic_rows:
        total = topic_totals.setdefault(
            row["label"], {"label": row["label"], "platforms": {}, "views": 0, "interactions": 0, "count": 0}
        )
        total["platforms"][row["platform"]] = row["content_count"]
        total["views"] += row["views"]
        total["interactions"] += row["total_interactions"]
        total["count"] += row["content_count"]

    top_topics = sorted(topic_totals.values(), key=lambda item: item["views"], reverse=True)[:6]
    topic_order = [item["label"] for item in top_topics]
    chart_df = pd.DataFrame(
        [
            {
                "主题": row["label"],
                "平台": PLATFORM_LABELS.get(row["platform"], row["platform"]),
                "曝光": row["views"],
                "互动": row["total_interactions"],
            }
            for row in topic_rows
            if row["label"] in topic_order
        ]
    )
    st.markdown("**热门主题各平台曝光对比**　<span class='q-hint'>按主题总曝光取前 6</span>", unsafe_allow_html=True)
    cross_chart = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("主题:N", sort=topic_order, title=None, axis=alt.Axis(labelAngle=-18, labelLimit=160)),
            xOffset=alt.XOffset("平台:N", sort=list(PLATFORM_LABELS.values())),
            y=alt.Y("曝光:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color(
                "平台:N",
                scale=alt.Scale(
                    domain=list(PLATFORM_LABELS.values()),
                    range=[ui.PLATFORM_COLORS[key] for key in PLATFORM_LABELS],
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=["主题", "平台", alt.Tooltip("曝光:Q", format=","), alt.Tooltip("互动:Q", format=",")],
        )
        .properties(height=320)
    )
    st.altair_chart(ui.style_chart(cross_chart), use_container_width=True)

    st.markdown("**跨平台联动案例**", unsafe_allow_html=True)
    cross_topics = [item for item in top_topics if len(item["platforms"]) >= 2]
    if not cross_topics:
        st.caption("本月主题均集中在单一平台，暂未形成跨平台联动。建议同题内容在抖音、视频号、公众号分别发布。")
    for item in cross_topics[:3]:
        platforms_text = "、".join(
            f"{PLATFORM_LABELS.get(platform, platform)} {count} 条"
            for platform, count in sorted(item["platforms"].items(), key=lambda pair: platform_order.get(pair[0], 9))
        )
        top_platform = max(
            item["platforms"].items(),
            key=lambda pair: next(
                (row["views"] for row in topic_rows if row["label"] == item["label"] and row["platform"] == pair[0]), 0
            ),
        )[0]
        top_views = next(
            (row["views"] for row in topic_rows if row["label"] == item["label"] and row["platform"] == top_platform), 0
        )
        share = top_views / item["views"] if item["views"] else 0
        status = "star" if len(item["platforms"]) >= 3 else "norm"
        ui.camp_card(
            {
                "name": f"「{item['label']}」跨平台联动",
                "status": status,
                "status_text": "标杆案例" if len(item["platforms"]) >= 3 else "跨平台联动",
                "period": selected_month,
                "desc": (
                    f"「{item['label']}」本月在 {len(item['platforms'])} 个平台共发布 {item['count']} 条内容，"
                    f"合计曝光 {item['views']:,}、互动 {item['interactions']:,}。"
                    f"{PLATFORM_LABELS.get(top_platform, top_platform)}贡献主要曝光，占比 {share:.1%}。"
                ),
                "flow": [platforms_text, f"共 {item['count']} 条内容", f"互动 {item['interactions']:,}"],
                "highlight": (
                    f"战报：{item['label']} 主题总曝光 {item['views']:,}，"
                    f"{PLATFORM_LABELS.get(top_platform, top_platform)}单平台 {top_views:,}（{share:.1%}）。"
                ),
            }
        )
