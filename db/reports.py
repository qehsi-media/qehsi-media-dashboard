"""基于规则模板和 SQLite 数据的月度报告生成与保存。"""

from datetime import datetime
from typing import Optional

from db.analysis import (
    aggregate_cross_platform,
    analyze_window_contents,
    fetch_month_contents,
    fetch_window_contents,
    month_analysis_window,
)
from db.database import PLATFORM_LABELS, fetch_accounts, get_connection
from db.metrics import fetch_account_performance, fetch_core_metrics

HIT_THRESHOLD = 2.0


def _md(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _markdown_table(headers: list[str], rows: list[list]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(_md(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def _topic_stats(month_contents: list[dict]) -> dict:
    stats = {}
    for row in aggregate_cross_platform(month_contents, "topic"):
        if row["label"] == "未标注主题":
            continue
        label = row["label"]
        if label not in stats:
            stats[label] = {
                "label": label,
                "platforms": set(),
                "content_count": 0,
                "total_interactions": 0,
            }
        stats[label]["platforms"].add(row["platform"])
        stats[label]["content_count"] += row["content_count"]
        stats[label]["total_interactions"] += row["total_interactions"]
    return stats


def _topic_description(stat: dict) -> str:
    return (
        f"「{_md(stat['label'])}」（{len(stat['platforms'])} 个平台，"
        f"发布 {stat['content_count']} 条，互动 {stat['total_interactions']:,}）"
    )


def _service_summary(
    core: dict, total_interactions: int, platforms: list[dict], active_accounts: list[dict], hit_count: int
) -> str:
    top_platform = max(platforms, key=lambda row: row["views"])
    best_account = max(
        active_accounts, key=lambda row: (row["total_interactions"], row["views"])
    )
    summary = (
        f"本月新媒体矩阵共发布{core['content_count']}条内容，覆盖{core['account_count']}个账号，"
        f"获得总曝光{core['views']}次、总互动{total_interactions}次。"
        f"{top_platform['label']}贡献主要曝光，占比{top_platform['share']:.1%}，"
        f"{best_account['account_name']}互动表现领先，本月共识别爆款{hit_count}条。"
        "整体传播已形成多平台触达基础，但账号产出与互动效率仍存在差异。"
        "建议下月复用高互动选题和爆款表达，加强低效账号更新与跨平台协同，"
        "并持续跟踪数据变化，提升校园品牌传播、招生宣传和家校沟通的实际成效。"
    )
    if len(summary) < 150:
        summary += "同时重视内容质量与发布节奏，避免只追求发布数量。"
    if len(summary) > 250:
        summary = (
            f"本月矩阵共发布{core['content_count']}条内容，覆盖{core['account_count']}个账号，"
            f"获得总曝光{core['views']}次、总互动{total_interactions}次，识别爆款{hit_count}条。"
            f"{top_platform['label']}为主要传播阵地，曝光占比{top_platform['share']:.1%}。"
            "本月宣传已形成多平台触达基础，头部内容对互动形成带动，但账号之间仍有表现差异。"
            "下月应复用高互动选题，改善低效账号更新，推动同题内容跨平台协同，"
            "持续提升校园品牌传播、招生宣传和家校沟通实效。"
        )
    return summary


def _recommendations(
    platforms: list[dict],
    account_rows: list[dict],
    active_accounts: list[dict],
    month_hits: list[dict],
    topic_stats: dict,
) -> list[str]:
    top_platform = max(platforms, key=lambda row: row["views"])
    best = max(active_accounts, key=lambda row: (row["total_interactions"], row["views"]))
    weakest = min(active_accounts, key=lambda row: (row["total_interactions"], row["views"]))
    ranked_topics = sorted(
        topic_stats.values(), key=lambda row: row["total_interactions"], reverse=True
    )
    cross_topics = [row for row in ranked_topics if len(row["platforms"]) >= 2]
    inactive = [row for row in account_rows if row["content_count"] == 0]

    suggestions = [
        f"巩固{top_platform['label']}主阵地：该平台本月曝光占比{top_platform['share']:.1%}，优先保障高互动选题的更新节奏。",
        f"复用头部账号经验：拆解「{_md(best['account_name'])}」的高互动内容结构，在其他账号进行同主题差异化改编。",
        f"改善相对低效账号：「{_md(weakest['account_name'])}」本月总互动{weakest['total_interactions']}，建议优化选题、标题和互动引导。",
    ]
    if ranked_topics:
        suggestions.append(
            f"深化高互动主题：围绕{ _topic_description(ranked_topics[0]) }策划连续内容，形成系列化表达。"
        )
    else:
        suggestions.append("补充主题标注：后续上传时完善 topic，建立主题与互动效果的可持续对比口径。")

    if month_hits:
        suggestions.append(
            f"复盘爆款表达：重点拆解《{_md(month_hits[0]['content_title'])}》的标题、开头和互动设计，并测试同类选题。"
        )
    else:
        suggestions.append("加强爆款测试：本月暂无默认规则下的爆款，建议对标题、开头和互动引导开展小步对照测试。")

    if cross_topics:
        suggestions.append(
            f"扩大跨平台联动：延续{ _topic_description(cross_topics[0]) }的协同发布，并按平台特点调整呈现形式。"
        )
    else:
        suggestions.append("建立同题协同机制：选择下月高互动主题，在抖音、视频号和公众号分别采用短视频、动态与图文表达。")

    if inactive:
        names = "、".join(f"「{_md(row['account_name'])}」" for row in inactive)
        suggestions.append(f"恢复停更账号：{names}本月无内容，建议明确最低更新计划或调整账号定位。")
    return suggestions


def generate_monthly_report(month: str) -> Optional[str]:
    """生成完整 Markdown 报告；所选月份无内容时返回 None。"""
    core = fetch_core_metrics(month)
    if core["content_count"] == 0:
        return None

    account_rows = fetch_account_performance(month)
    active_accounts = [row for row in account_rows if row["content_count"] > 0]
    month_contents = fetch_month_contents(month)
    start_time, end_time = month_analysis_window(month)
    window_contents = fetch_window_contents(start_time, end_time)
    hits, _ = analyze_window_contents(window_contents, fetch_accounts(), HIT_THRESHOLD)
    month_hits = [row for row in hits if row["publish_time"].startswith(month)]
    total_interactions = (
        core["likes"] + core["comments"] + core["shares"] + core["favorites"]
    )

    platforms = []
    for platform, label in PLATFORM_LABELS.items():
        subset = [row for row in account_rows if row["platform"] == platform]
        views = sum(row["views"] for row in subset)
        platforms.append(
            {
                "platform": platform,
                "label": label,
                "content_count": sum(row["content_count"] for row in subset),
                "views": views,
                "total_interactions": sum(row["total_interactions"] for row in subset),
                "share": views / core["views"] if core["views"] else 0.0,
            }
        )

    best = max(active_accounts, key=lambda row: (row["total_interactions"], row["views"]))
    weakest = min(active_accounts, key=lambda row: (row["total_interactions"], row["views"]))
    topic_stats = _topic_stats(month_contents)
    cross_topics = sorted(
        (row for row in topic_stats.values() if len(row["platforms"]) >= 2),
        key=lambda row: (len(row["platforms"]), row["content_count"], row["total_interactions"]),
        reverse=True,
    )
    interactive_topics = sorted(
        topic_stats.values(), key=lambda row: row["total_interactions"], reverse=True
    )

    lines = [
        "# 青岛实验高中国际部新媒体月度报告",
        "",
        f"> 统计月份：{month}  ",
        f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}  ",
        "> 生成方式：规则模板 + SQLite 数据填充，不依赖外部 AI API。",
        "",
        "## 一、本月核心数据",
        "",
        _markdown_table(
            ["总曝光", "总互动", "内容数", "爆款数", "覆盖账号数"],
            [[core["views"], total_interactions, core["content_count"], len(month_hits), core["account_count"]]],
        ),
        "",
        "## 二、各平台表现",
        "",
        _markdown_table(
            ["平台", "内容数", "曝光", "互动", "曝光占比"],
            [
                [row["label"], row["content_count"], row["views"], row["total_interactions"], f"{row['share']:.2%}"]
                for row in platforms
            ],
        ),
        "",
        "## 三、各账号表现",
        "",
        f"- 最好账号：「{_md(best['account_name'])}」（{PLATFORM_LABELS[best['platform']]}），总互动 {best['total_interactions']:,}。",
        f"- 最弱账号：「{_md(weakest['account_name'])}」（{PLATFORM_LABELS[weakest['platform']]}），总互动 {weakest['total_interactions']:,}。",
        "- 最好/最弱账号仅在本月有内容的账号中比较。",
        "",
        "### 互动排名",
        "",
        _markdown_table(
            ["排名", "账号", "平台", "内容数", "总曝光", "总互动"],
            [
                [index, row["account_name"], PLATFORM_LABELS[row["platform"]], row["content_count"], row["views"], row["total_interactions"]]
                for index, row in enumerate(account_rows, start=1)
            ],
        ),
        "",
        "## 四、爆款摘要",
        "",
        f"> 爆款规则：内容互动量 > 账号近 30 天平均互动量 × {HIT_THRESHOLD:g}；仅统计 {month} 发布的内容。",
        "",
    ]

    for platform, label in PLATFORM_LABELS.items():
        platform_hits = [row for row in month_hits if row["platform"] == platform]
        lines.append(f"### {label}：{len(platform_hits)} 条")
        lines.append("")
        if not platform_hits:
            lines.append("本月无符合规则的内容。")
        else:
            for index, hit in enumerate(platform_hits[:3], start=1):
                ratio = f"{hit['hit_ratio']:.2f} 倍" if hit["hit_ratio"] is not None else "—"
                lines.append(
                    f"{index}. 《{_md(hit['content_title'])}》｜{_md(hit['account_name'])}｜互动 {hit['total_interactions']:,}｜{ratio}"
                )
        lines.append("")

    lines.extend(
        [
            "## 五、多平台联动摘要",
            "",
            f"- 已标注主题共 {len(topic_stats)} 个，其中 {len(cross_topics)} 个实现跨平台发布。",
            "- 跨平台发布最多："
            + ("；".join(_topic_description(row) for row in cross_topics[:3]) if cross_topics else "本月暂无同一主题跨平台发布。"),
            "- 互动最好主题："
            + ("；".join(_topic_description(row) for row in interactive_topics[:3]) if interactive_topics else "本月主题标注不足，暂无法比较。"),
            "",
            "## 六、服务价值小结",
            "",
            _service_summary(core, total_interactions, platforms, active_accounts, len(month_hits)),
            "",
            "## 七、后期内容规划建议",
            "",
        ]
    )
    suggestions = _recommendations(platforms, account_rows, active_accounts, month_hits, topic_stats)
    lines.extend(f"{index}. {text}" for index, text in enumerate(suggestions, start=1))
    lines.append("")
    return "\n".join(lines)


def save_analysis_report(month: str, content: str) -> int:
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO analysis_reports (report_month, report_content) VALUES (?, ?)",
                (month, content),
            )
        return cursor.lastrowid
    finally:
        conn.close()


def fetch_latest_analysis_report(month: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, report_month, report_content, created_at
            FROM analysis_reports
            WHERE report_month = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (month,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None
