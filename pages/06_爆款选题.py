"""⑧ 爆款选题建议：基于本月真实数据推导方向、避坑、发布时间与周历。"""

from datetime import datetime

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
from db.metrics import fetch_account_performance, fetch_available_months, fetch_core_metrics

st.set_page_config(page_title="爆款选题建议", page_icon="🧭", layout="wide")
ui.inject_css()
init_db()

current_month = datetime.now().strftime("%Y-%m")
months = sorted(set(fetch_available_months() + [current_month]), reverse=True)
session_month = st.session_state.get("plan_month", current_month)
if session_month not in months:
    months.insert(0, session_month)

ui.page_header(
    "爆款选题建议",
    "基于本月真实爆款规律推导 · 每条标注建议发布账号",
    f"{session_month[:4]} 年 {session_month[5:7]} 月",
    "规则推导",
)
ui.banner("🎯 看板二 · 活动作战 & 内容爆点推荐", "选题方向、避坑清单、发布时间与四周周历", "amber")

selected_month = st.selectbox(
    "统计月份",
    options=months,
    index=months.index(session_month),
    format_func=lambda value: f"{value[:4]} 年 {value[5:7]} 月",
    key="plan_month",
    label_visibility="collapsed",
)

core = fetch_core_metrics(selected_month)
if core["content_count"] == 0:
    st.info("本月暂无数据，无法推导选题建议。请先到「数据上传」页上传数据。")
    st.stop()

start_time, end_time = month_analysis_window(selected_month)
accounts = fetch_accounts()
window_contents = fetch_window_contents(start_time, end_time)
hits, matrix_rows = analyze_window_contents(window_contents, accounts, 2.0)
month_contents = fetch_month_contents(selected_month)
account_rows = fetch_account_performance(selected_month)
account_rows = [row for row in account_rows if row["content_count"] > 0]

platform_views = {
    platform: sum(row["views"] for row in account_rows if row["platform"] == platform)
    for platform in PLATFORM_LABELS
}
top_platform = max(platform_views, key=platform_views.get)
top_platform_label = PLATFORM_LABELS[top_platform]

topic_stats: dict[str, dict] = {}
for row in aggregate_cross_platform(month_contents, "topic"):
    if row["label"] == "未标注主题":
        continue
    stat = topic_stats.setdefault(
        row["label"], {"label": row["label"], "platforms": set(), "views": 0, "interactions": 0, "count": 0}
    )
    stat["platforms"].add(row["platform"])
    stat["views"] += row["views"]
    stat["interactions"] += row["total_interactions"]
    stat["count"] += row["content_count"]
ranked_topics = sorted(topic_stats.values(), key=lambda item: item["interactions"], reverse=True)
top_topic = ranked_topics[0] if ranked_topics else None
cross_topic = next((item for item in ranked_topics if len(item["platforms"]) >= 2), None)
best_account = max(account_rows, key=lambda row: row["total_interactions"])
lowest_account = min(account_rows, key=lambda row: row["content_count"])
untagged = sum(1 for row in month_contents if not (row["topic"] or "").strip())
hits_all = hits

def account_label(platform: str, name: str) -> str:
    return f"{PLATFORM_LABELS.get(platform, platform)}·{name}"


ui.section("08", "爆款选题建议", "方向卡 · 避坑 · 发布时间 · 周历")

intro = (
    "<b>爆款公式：</b>真实事件 / 福利触发点 ＋ 现场画面 ＋ 家长转发动机　"
    "<span style='color:#5c6b85;font-size:.8rem'>以下方向均来自本月真实数据，不包含假设数据。</span>"
)
ui.render(
    f'<div class="q-card" style="background:linear-gradient(135deg,rgba(255,170,80,.08),rgba(64,196,255,.08));'
    f'border:1px dashed #2f6bff;margin-bottom:1rem;font-size:.88rem">{intro}</div>'
)

directions: list[dict] = []

if hits_all:
    top_hit = hits_all[0]
    directions.append(
        {
            "account": account_label(top_hit["platform"], top_hit["account_name"]),
            "title": f"《{top_hit['content_title']}》续集：同一事件的下一条",
            "platform": "下月同题材 · 优先原账号首发",
            "basis": (
                f"本月互动最高内容（{top_hit['total_interactions']:,} 次，"
                f"为账号均值的 {(top_hit['hit_ratio'] or 0):.2f} 倍），事件型内容已被验证。"
            ),
            "expected": f"参考曝光 {top_hit['views']:,} · 互动 {top_hit['total_interactions']:,}",
            "tips": "复刻开头 3 秒的冲突画面与标题结构，续集要给出新信息增量，不做旧素材合集。",
            "tags": ["爆款续集", PLATFORM_LABELS.get(top_hit["platform"], "")],
        }
    )

if top_topic:
    topic_platforms = "、".join(
        PLATFORM_LABELS[platform]
        for platform in sorted(top_topic["platforms"], key=lambda p: list(PLATFORM_LABELS).index(p))
    )
    directions.append(
        {
            "account": topic_platforms,
            "title": f"「{top_topic['label']}」系列化：拆成 3 条连续内容",
            "platform": f"下月连续三周 · {topic_platforms}",
            "basis": (
                f"本月互动最高主题（{top_topic['interactions']:,} 次互动、"
                f"{top_topic['count']} 条内容、{len(top_topic['platforms'])} 个平台参与）。"
            ),
            "expected": f"参考曝光 {top_topic['views']:,} · 互动 {top_topic['interactions']:,}",
            "tips": "每条只讲一个进展，形成“预告 → 现场 → 结果”的连续剧结构，结尾统一埋下一条钩子。",
            "tags": ["主题系列化", "多平台"],
        }
    )

directions.append(
    {
        "account": best_account["account_name"],
        "title": f"复制「{best_account['account_name']}」的高互动结构到其他账号",
        "platform": f"下月 · {PLATFORM_LABELS[best_account['platform']]}为首发，其他账号改编",
        "basis": (
            f"该账号本月互动 {best_account['total_interactions']:,} 次，"
            f"发布 {best_account['content_count']} 条，互动效率矩阵领先。"
        ),
        "expected": f"对标互动 {best_account['total_interactions']:,}",
        "tips": "拆解标题、前 3 秒、互动引导三件事，按各平台语态改写，不做直接搬运。",
        "tags": ["头部账号", "结构复用"],
    }
)

directions.append(
    {
        "account": top_platform_label,
        "title": f"巩固{top_platform_label}主阵地：同题材加更一条",
        "platform": f"下月每周 · {top_platform_label}",
        "basis": (
            f"{top_platform_label}本月曝光 {platform_views[top_platform]:,}，"
            f"占全矩阵 {platform_views[top_platform] / core['views']:.1%}。"
        ),
        "expected": f"参考平台曝光 {platform_views[top_platform]:,}",
        "tips": "优先保障高互动主题的更新节奏，同题材换角度再发一条，测试平台流量上限。",
        "tags": ["主阵地", "加更"],
    }
)

directions.append(
    {
        "account": lowest_account["account_name"],
        "title": f"补齐「{lowest_account['account_name']}」的月度最低更新量",
        "platform": f"下月 · {PLATFORM_LABELS[lowest_account['platform']]}",
        "basis": (
            f"该账号本月仅发布 {lowest_account['content_count']} 条，"
            f"互动 {lowest_account['total_interactions']:,}，产出不足限制了矩阵整体声量。"
        ),
        "expected": "目标：至少 4 条 / 月，先恢复更新节奏",
        "tips": "从主阵地已爆的选题中挑选适配角度进行二创，降低单条制作成本。",
        "tags": ["补位", "更新节奏"],
    }
)

if cross_topic:
    directions.append(
        {
            "account": "、".join(PLATFORM_LABELS[p] for p in sorted(cross_topic["platforms"], key=lambda p: list(PLATFORM_LABELS).index(p))),
            "title": f"围绕「{cross_topic['label']}」做同题三端协同",
            "platform": "下月固定档期 · 同一天三端分发",
            "basis": (
                f"该主题已在 {len(cross_topic['platforms'])} 个平台跑通，"
                f"合计曝光 {cross_topic['views']:,}、互动 {cross_topic['interactions']:,}。"
            ),
            "expected": "目标：同题内容三端合计曝光超过本月单平台峰值",
            "tips": "抖音发冲突快剪、视频号发完整叙事、公众号发长图文沉淀，形成流量接力。",
            "tags": ["跨平台联动", "同题协同"],
        }
    )
else:
    directions.append(
        {
            "account": "全平台",
            "title": "建立同题协同机制：一个选题，三端表达",
            "platform": "下月每周一个主题",
            "basis": "本月尚无明显跨平台主题，矩阵协同仍有较大提升空间。",
            "expected": "目标：每月至少 2 个主题实现三端联动",
            "tips": "周一定题、周二至周四分平台制作、周五至周日错峰发布，统一话题标签。",
            "tags": ["协同机制", "从 0 到 1"],
        }
    )

directions.append(
    {
        "account": "公众号·" + (accounts[-1]["account_name"] if accounts else "青实高国际"),
        "title": "公众号长图文沉淀：本月爆款复盘 + 下月预告",
        "platform": "下月初 · 公众号",
        "basis": "公众号承担搜索长尾与私域沉淀，是唯一能放长图文并被搜一搜收录的阵地。",
        "expected": "目标：月内至少 2 篇长图文，与视频号互相导流",
        "tips": "文末放视频号内容嵌入与下期预告，形成“短视频引流 → 图文沉淀 → 关注转化”闭环。",
        "tags": ["公众号沉淀", "导流闭环"],
    }
)

for index in range(0, len(directions), 2):
    left, right = st.columns(2)
    with left:
        ui.plan_card(directions[index])
    if index + 1 < len(directions):
        with right:
            ui.plan_card(directions[index + 1])

# ---------------------------------------------------------------------------
# 避坑清单
# ---------------------------------------------------------------------------
avoid_items = []
if lowest_account["content_count"] < 2:
    avoid_items.append(
        f"❌ 低产出账号「{lowest_account['account_name']}」本月仅 {lowest_account['content_count']} 条，"
        "继续追热点不如先恢复稳定更新。"
    )
if untagged:
    avoid_items.append(
        f"❌ {untagged} 条内容未填写 topic，无法进入跨平台联动统计；上传时补齐主题标签。"
    )
else:
    avoid_items.append("❌ 内容全部集中单一平台：同题内容应在抖音、视频号、公众号分别表达，而不是一次发完了事。")
avoid_items.append("❌ 官方主号发布过度精致的宣传片：家长更愿意转发真实现场与真实反馈。")
avoid_items.append("❌ 公众号只发纯通知：缺少情绪触发点，分享率通常偏低。")

ui.render(
    '<div class="q-card" style="margin-bottom:1rem">'
    '<div style="font-size:.92rem;font-weight:800;margin-bottom:.5rem">本月避坑</div>'
    + "".join(
        f'<div style="font-size:.82rem;color:#5c6b85;line-height:1.8">{ui.esc(item)}</div>'
        for item in avoid_items
    )
    + "</div>"
)

# ---------------------------------------------------------------------------
# 发布时间建议
# ---------------------------------------------------------------------------
timing = [
    ("抖音", "每周三 / 周五 18:00-20:00", "工作日晚间家长下班刷抖音，事件型内容适合此时首发。"),
    ("视频号", "每周四 / 周六 20:00-22:00", "家长睡前刷朋友圈，社交裂变链路在晚间更强。"),
    ("公众号", "每周五 17:00", "周五傍晚打开率相对更高，适合长图文与周末活动预告。"),
]
ui.render(
    '<div class="q-card" style="margin-bottom:1rem">'
    '<div style="font-size:.92rem;font-weight:800;margin-bottom:.5rem">发布时间建议</div>'
    + "".join(
        f'<div style="display:flex;gap:.7rem;font-size:.82rem;line-height:1.8">'
        f'<b style="min-width:56px;color:#2f6bff">{ui.esc(platform)}</b>'
        f'<span style="min-width:180px">{ui.esc(window)}</span>'
        f'<span style="color:#5c6b85">{ui.esc(basis)}</span></div>'
        for platform, window, basis in timing
    )
    + "</div>"
)

# ---------------------------------------------------------------------------
# 四周周历
# ---------------------------------------------------------------------------
focus_title = top_topic["label"] if top_topic else "本月高互动主题"
calendar_rows = [
    ["第 1 周", "视频号 + 抖音", f"复用「{focus_title}」做续集或系列第一条，优先原爆款账号首发"],
    ["第 1 周", "公众号", "发本月复盘长图文，嵌入视频号内容，文末预告下期选题"],
    [
        "第 2 周",
        "全平台",
        f"同题协同：抖音快剪、视频号完整叙事、公众号长图文，统一话题标签",
    ],
    ["第 3 周", PLATFORM_LABELS[lowest_account["platform"]], f"补齐低产出账号更新，「{lowest_account['account_name']}」至少 2 条"],
    ["第 4 周", "公众号 + 视频号", "月末数据复盘 + 下月活动预告，形成固定更新节奏"],
]
ui.html_table(["周次", "平台", "内容安排"], calendar_rows)
st.caption("周历按“复用爆款 → 同题协同 → 补位更新 → 月末沉淀”的节奏生成，可按实际活动日期平移。")
