"""活动作战方案的手工录入与读取。"""

from db.database import get_connection


def fetch_activities() -> list[dict]:
    """按活动日期升序返回全部活动作战方案。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, activity_name, activity_date, goal,
                   suggested_accounts, battle_plan, status, created_at
            FROM activities
            ORDER BY activity_date ASC, id DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def add_activity(
    activity_name: str,
    activity_date: str,
    goal: str,
    suggested_accounts: str,
    battle_plan: str,
    status: str,
) -> int:
    """新增一条活动作战方案，返回记录 ID。"""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO activities
                (activity_name, activity_date, goal, suggested_accounts, battle_plan, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                activity_name.strip(),
                activity_date.strip(),
                goal.strip(),
                suggested_accounts.strip(),
                battle_plan.strip(),
                status,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def delete_activity(activity_id: int) -> None:
    """删除指定活动作战方案。"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        conn.commit()
    finally:
        conn.close()
