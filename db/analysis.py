"""爆款识别、IP 矩阵和多平台联动分析。"""

import calendar
from datetime import datetime, timedelta

from db.database import PLATFORM_LABELS, get_connection

CONTENT_COLUMNS = """
    id, platform, account_name, content_title, publish_time,
    views, likes, comments, shares, favorites, link, content_type, topic
"""


def month_analysis_window(month: str) -> tuple[str, str]:
    """当月截至今天，历史月份截至月末，向前取 30 个自然日。"""
    year, month_number = (int(part) for part in month.split("-"))
    month_end = datetime(year, month_number, calendar.monthrange(year, month_number)[1]).date()
    today = datetime.now().date()
    end_date = min(today, month_end) if month == today.strftime("%Y-%m") else month_end
    start_date = end_date - timedelta(days=29)
    return (
        f"{start_date:%Y-%m-%d} 00:00:00",
        f"{end_date:%Y-%m-%d} 23:59:59",
    )


def fetch_window_contents(start_time: str, end_time: str) -> list[dict]:
    """读取指定闭区间内的有效发布时间内容。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT {CONTENT_COLUMNS}
            FROM contents
            WHERE publish_time BETWEEN ? AND ?
              AND publish_time GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'
            ORDER BY publish_time DESC, id DESC
            """,
            (start_time, end_time),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def fetch_month_contents(month: str) -> list[dict]:
    """读取指定自然月内容，供主题联动聚合。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT {CONTENT_COLUMNS}
            FROM contents
            WHERE substr(publish_time, 1, 7) = ?
            ORDER BY publish_time DESC, id DESC
            """,
            (month,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _interactions(row: dict) -> int:
    return row["likes"] + row["comments"] + row["shares"] + row["favorites"]


def analyze_window_contents(
    contents: list[dict], accounts: list[dict], threshold: float
) -> tuple[list[dict], list[dict]]:
    """返回爆款列表和全账号矩阵；平均互动包含当前内容，判定使用严格大于。"""
    stats = {}
    for account in accounts:
        key = (account["platform"], account["account_name"])
        stats[key] = {
            "platform": account["platform"],
            "account_name": account["account_name"],
            "content_count": 0,
            "views": 0,
            "total_interactions": 0,
            "average_interactions": 0.0,
            "hit_count": 0,
            "last_publish_time": "",
        }

    for row in contents:
        key = (row["platform"], row["account_name"])
        if key not in stats:
            stats[key] = {
                "platform": row["platform"],
                "account_name": row["account_name"],
                "content_count": 0,
                "views": 0,
                "total_interactions": 0,
                "average_interactions": 0.0,
                "hit_count": 0,
                "last_publish_time": "",
            }
        stat = stats[key]
        stat["content_count"] += 1
        stat["views"] += row["views"]
        stat["total_interactions"] += _interactions(row)
        stat["last_publish_time"] = max(
            stat["last_publish_time"], row["publish_time"]
        )

    for stat in stats.values():
        if stat["content_count"]:
            stat["average_interactions"] = (
                stat["total_interactions"] / stat["content_count"]
            )

    hits = []
    for row in contents:
        stat = stats[(row["platform"], row["account_name"])]
        average = stat["average_interactions"]
        interactions = _interactions(row)
        if interactions > average * threshold:
            ratio = interactions / average if average else None
            hits.append(
                {
                    "platform": row["platform"],
                    "account_name": row["account_name"],
                    "content_title": row["content_title"],
                    "publish_time": row["publish_time"],
                    "views": row["views"],
                    "total_interactions": interactions,
                    "hit_ratio": ratio,
                    "link": row["link"],
                }
            )
            stat["hit_count"] += 1

    hits.sort(
        key=lambda row: (
            row["hit_ratio"] if row["hit_ratio"] is not None else float("inf"),
            row["total_interactions"],
        ),
        reverse=True,
    )
    return hits, list(stats.values())


def aggregate_cross_platform(contents: list[dict], dimension: str) -> list[dict]:
    """按主题/内容类型与平台聚合发布数量、总互动和平均互动。"""
    if dimension not in {"topic", "content_type"}:
        raise ValueError("不支持的聚合维度")

    empty_label = "未标注主题" if dimension == "topic" else "未标注类型"
    grouped = {}
    for row in contents:
        raw_label = row[dimension]
        label = str(raw_label).strip() if raw_label is not None else ""
        label = label or empty_label
        key = (label, row["platform"])
        if key not in grouped:
            grouped[key] = {
                "label": label,
                "platform": row["platform"],
                "content_count": 0,
                "total_interactions": 0,
            }
        grouped[key]["content_count"] += 1
        grouped[key]["total_interactions"] += _interactions(row)

    platform_order = {platform: index for index, platform in enumerate(PLATFORM_LABELS)}
    result = []
    for row in grouped.values():
        row["average_interactions"] = (
            row["total_interactions"] / row["content_count"]
        )
        result.append(row)
    return sorted(
        result,
        key=lambda row: (row["label"], platform_order.get(row["platform"], 99)),
    )
