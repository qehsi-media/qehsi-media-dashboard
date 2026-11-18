"""SQLite 连接与数据库初始化。"""

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "media_dashboard.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
ACCOUNTS_PATH = BASE_DIR / "config" / "accounts.json"

PLATFORM_LABELS = {
    "douyin": "抖音",
    "wechat_video": "视频号",
    "wechat_mp": "公众号",
}

TABLES = ["accounts", "contents", "field_mappings", "upload_batches", "analysis_reports"]


def get_connection() -> sqlite3.Connection:
    """返回 SQLite 连接（行可按键访问）。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表并同步 config/accounts.json 中的账号（幂等，可重复执行）。"""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    accounts = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))

    conn = get_connection()
    try:
        with conn:
            conn.executescript(schema)
            conn.executemany(
                """
                INSERT INTO accounts (account_id, platform, account_name, account_group, status)
                VALUES (:account_id, :platform, :account_name, :account_group, :status)
                ON CONFLICT (account_id) DO UPDATE SET
                    platform = excluded.platform,
                    account_name = excluded.account_name,
                    account_group = excluded.account_group,
                    status = excluded.status
                """,
                accounts,
            )
    finally:
        conn.close()


def fetch_accounts() -> list[dict]:
    """按平台顺序返回全部账号。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT account_id, platform, account_name, account_group, status
            FROM accounts
            ORDER BY CASE platform
                         WHEN 'douyin' THEN 1
                         WHEN 'wechat_video' THEN 2
                         WHEN 'wechat_mp' THEN 3
                         ELSE 4
                     END,
                     account_id
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def check_connection() -> tuple[bool, str]:
    """检查数据库是否可连接，并返回各表记录数摘要。"""
    try:
        conn = get_connection()
        try:
            counts = {}
            for table in TABLES:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return False, str(exc)
    summary = "，".join(f"{table} {count} 条" for table, count in counts.items())
    return True, summary


if __name__ == "__main__":
    init_db()
    ok, detail = check_connection()
    print(f"数据库：{DB_PATH}")
    print("连接正常" if ok else f"连接失败：{detail}")
    if ok:
        print(f"记录数：{detail}")
