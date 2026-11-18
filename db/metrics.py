"""数据看板的 SQLite 统计查询。"""

from db.database import get_connection

MONTH_FILTER = "substr(publish_time, 1, 7) = ?"


def fetch_available_months() -> list[str]:
    """返回内容表中可识别的月份，格式 YYYY-MM。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT substr(publish_time, 1, 7) AS month
            FROM contents
            WHERE publish_time GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-*'
              AND substr(publish_time, 6, 2) BETWEEN '01' AND '12'
            ORDER BY month DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return [row["month"] for row in rows]


def fetch_core_metrics(month: str) -> dict:
    """查询月度核心指标，覆盖账号按“平台 + 账号名称”去重。"""
    conn = get_connection()
    try:
        totals = conn.execute(
            f"""
            SELECT COUNT(*) AS content_count,
                   COALESCE(SUM(views), 0) AS views,
                   COALESCE(SUM(likes), 0) AS likes,
                   COALESCE(SUM(comments), 0) AS comments,
                   COALESCE(SUM(shares), 0) AS shares,
                   COALESCE(SUM(favorites), 0) AS favorites
            FROM contents
            WHERE {MONTH_FILTER}
            """,
            (month,),
        ).fetchone()
        covered = conn.execute(
            f"""
            SELECT COUNT(*) AS account_count
            FROM (
                SELECT DISTINCT platform, account_name
                FROM contents
                WHERE {MONTH_FILTER}
            )
            """,
            (month,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "content_count": totals["content_count"],
        "views": totals["views"],
        "likes": totals["likes"],
        "comments": totals["comments"],
        "shares": totals["shares"],
        "favorites": totals["favorites"],
        "account_count": covered["account_count"],
    }


def fetch_account_performance(month: str) -> list[dict]:
    """返回全部账号的月度表现，无内容账号保留为 0。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT a.platform,
                   a.account_name,
                   COUNT(c.id) AS content_count,
                   COALESCE(SUM(c.views), 0) AS views,
                   COALESCE(SUM(c.likes + c.comments + c.shares + c.favorites), 0)
                       AS total_interactions
            FROM accounts a
            LEFT JOIN contents c
              ON c.platform = a.platform
             AND c.account_name = a.account_name
             AND {MONTH_FILTER.replace('publish_time', 'c.publish_time')}
            GROUP BY a.platform, a.account_name
            ORDER BY total_interactions DESC, views DESC, a.platform, a.account_name
            """
            ,
            (month,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]
