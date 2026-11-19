"""SQLite / PostgreSQL 通用数据库层。

- 本地运行：默认 SQLite，无需任何配置
- Streamlit Cloud / Supabase：从 st.secrets.db_url 或环境变量 DATABASE_URL 读取 PostgreSQL 连接串
- 适配层对上层代码透明，importer.py / metrics.py / analysis.py / reports.py 一行都不用改
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "media_dashboard.db"
SCHEMA_SQLITE_PATH = BASE_DIR / "db" / "schema.sql"
SCHEMA_POSTGRES_PATH = BASE_DIR / "db" / "schema_postgres.sql"
ACCOUNTS_PATH = BASE_DIR / "config" / "accounts.json"

PLATFORM_LABELS = {
    "douyin": "抖音",
    "wechat_video": "视频号",
    "wechat_mp": "公众号",
}

TABLES = ["accounts", "contents", "field_mappings", "upload_batches", "analysis_reports"]

# ---------------------------------------------------------------------------
# 后端选择
# ---------------------------------------------------------------------------


def _get_db_url() -> Optional[str]:
    """优先从 Streamlit secrets 读 DATABASE_URL，其次读环境变量。"""
    try:
        import streamlit as st
        secrets_db_url = (
            st.secrets.get("db_url")
            or st.secrets.get("database_url")
            or (st.secrets.get("connections", {}) or {}).get("postgres", {}).get("url")
        )
        if secrets_db_url:
            return secrets_db_url
    except Exception:
        pass
    return os.environ.get("DATABASE_URL")


def _is_postgres_url(url: str) -> bool:
    return url.startswith(("postgres://", "postgresql://"))


# ---------------------------------------------------------------------------
# 占位符 & SQL 适配
# ---------------------------------------------------------------------------


def _convert_placeholders(sql: str, is_postgres: bool) -> str:
    """SQLite 用 ?，PostgreSQL 用 %s / %(name)s。统一把 ? 换成 %s。"""
    if not is_postgres:
        return sql
    # 只替换真正的占位符，不要碰字符串里的 ?
    result = re.sub(r"\?", "%s", sql)
    return result


def _rewrite_sequences_for_postgres(sql: str) -> str:
    """PostgreSQL 的 SAVEPOINT 写法是一样的，但 ON CONFLICT 细节兼容。"""
    return sql


# ---------------------------------------------------------------------------
# 适配层：让 psycopg2 行为尽量接近 sqlite3
# ---------------------------------------------------------------------------


class _DbRow(dict):
    """同时支持 row['col'] 和 dict(row)。"""

    pass


class _PostgresCursor:
    """模拟 sqlite3.Cursor 的 psycopg2 封装。"""

    def __init__(self, pg_cursor):
        self._cursor = pg_cursor
        self.lastrowid: Optional[int] = None

    def execute(self, sql: str, params=None):
        sql = _convert_placeholders(sql, True)
        if params is None:
            params = ()
        # PostgreSQL 的 INSERT 没有 RETURNING 时拿不到 lastrowid
        sql_lower = sql.strip().lower()
        is_insert = sql_lower.startswith("insert") and "returning" not in sql_lower
        if is_insert:
            table_match = re.search(r"into\s+(\w+)", sql_lower)
            if table_match:
                table = table_match.group(1)
                sql = sql.rstrip().rstrip(";") + f" RETURNING id"
        try:
            self._cursor.execute(sql, params)
        except Exception as exc:
            raise exc
        if is_insert:
            row = self._cursor.fetchone()
            self.lastrowid = row[0] if row else None
        else:
            self.lastrowid = None
        return self

    def executemany(self, sql: str, params_seq):
        sql = _convert_placeholders(sql, True)
        return self._cursor.executemany(sql, list(params_seq))

    def fetchone(self) -> Optional[dict]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self._cursor.description]
        return dict(zip(cols, row))

    def fetchall(self) -> list[dict]:
        rows = self._cursor.fetchall()
        cols = [desc[0] for desc in self._cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class _DbConnection:
    """同时包装 sqlite3.Connection 和 psycopg2.Connection，对上层透明。"""

    def __init__(self, backend: str, native_conn):
        self._backend = backend  # "sqlite" | "postgres"
        self._conn = native_conn
        self._in_tx = False

    @property
    def backend(self) -> str:
        return self._backend

    def execute(self, sql: str, params=None):
        sql_lower = sql.strip().lower()

        # PostgreSQL 不需要 PRAGMA
        if self._backend == "postgres" and sql_lower.startswith("pragma"):
            return _PostgresCursor(self._conn.cursor())

        # SQLite 的 BEGIN 事务已由 conn 默认开启
        if self._backend == "postgres":
            wrapper = _PostgresCursor(self._conn.cursor())
            if params is None:
                params = ()
            wrapper.execute(sql, params)  # 关键：必须真正执行 SQL
            return wrapper

        # sqlite3 分支
        if params is None:
            return self._conn.execute(sql)
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_seq):
        if self._backend == "postgres":
            sql = _convert_placeholders(sql, True)
            pg_cursor = self._conn.cursor()
            pg_cursor.executemany(sql, list(params_seq))
            return _PostgresCursor(pg_cursor)
        return self._conn.executemany(sql, list(params_seq))

    def executescript(self, script: str):
        """逐行执行脚本（PostgreSQL 不支持 executescript）。"""
        if self._backend == "postgres":
            statements = [s.strip() for s in script.split(";") if s.strip()]
            for stmt in statements:
                stmt = _convert_placeholders(stmt, True)
                self._conn.execute(stmt)
            return
        self._conn.executescript(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        if self._backend == "sqlite":
            return self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._backend == "sqlite":
            return self._conn.__exit__(exc_type, exc_val, exc_tb)
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        return False


# ---------------------------------------------------------------------------
# 连接入口
# ---------------------------------------------------------------------------


def get_connection() -> _DbConnection:
    """返回适配后的连接对象，上层代码无需关心 SQLite / PostgreSQL。"""
    url = _get_db_url()

    if url and _is_postgres_url(url):
        try:
            import psycopg
        except ImportError:
            try:
                import psycopg2
                conn = psycopg2.connect(url)
                return _DbConnection("postgres", conn)
            except ImportError:
                print("[db] psycopg/psycopg2 未安装，回退到 SQLite")
                url = None
        else:
            # Supabase 连接池（transaction 模式）不支持服务端预编译语句，
            # psycopg3 默认会在重复执行后自动 PREPARE，导致
            # DuplicatePreparedStatement（_pg3_0 已存在）。关闭预编译即可。
            conn = psycopg.connect(url, prepare_threshold=None)
            return _DbConnection("postgres", conn)

    # 默认 SQLite
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error:
        pass
    return _DbConnection("sqlite", conn)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------


def init_db() -> None:
    """建表并同步账号（幂等）。"""
    url = _get_db_url()
    is_postgres = bool(url and _is_postgres_url(url))
    schema_path = SCHEMA_POSTGRES_PATH if is_postgres else SCHEMA_SQLITE_PATH
    schema = schema_path.read_text(encoding="utf-8")
    accounts = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))

    conn = get_connection()
    try:
        if is_postgres:
            for stmt in [s.strip() for s in schema.split(";") if s.strip()]:
                conn.execute(stmt)
        else:
            conn.executescript(schema)

        # 统一用 tuple 形式，? 占位符两种后端都能跑
        upsert_sql = """
            INSERT INTO accounts (account_id, platform, account_name, account_group, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (account_id) DO UPDATE SET
                platform = excluded.platform,
                account_name = excluded.account_name,
                account_group = excluded.account_group,
                status = excluded.status
        """
        rows = [
            (
                a["account_id"],
                a["platform"],
                a["account_name"],
                a.get("account_group"),
                a.get("status", "active"),
            )
            for a in accounts
        ]
        conn.executemany(upsert_sql, rows)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


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


def count_contents(
    platform: str | None = None,
    account_name: str | None = None,
    month: str | None = None,
) -> int:
    """统计 contents 中符合条件的记录数。"""
    where, params = _content_filters(platform, account_name, month)
    conn = get_connection()
    try:
        row = conn.execute(f"SELECT COUNT(*) AS c FROM contents{where}", params).fetchone()
    finally:
        conn.close()
    return row["c"] if isinstance(row, dict) else row[0]


def delete_contents(
    platform: str | None = None,
    account_name: str | None = None,
    month: str | None = None,
) -> int:
    """删除 contents 中符合条件的记录，返回删除条数。"""
    where, params = _content_filters(platform, account_name, month)
    conn = get_connection()
    try:
        before = conn.execute(f"SELECT COUNT(*) AS c FROM contents{where}", params).fetchone()
        total = before["c"] if isinstance(before, dict) else before[0]
        conn.execute(f"DELETE FROM contents{where}", params)
        conn.commit()
    finally:
        conn.close()
    return total


def _content_filters(
    platform: str | None, account_name: str | None, month: str | None
) -> tuple[str, tuple]:
    conditions: list[str] = []
    params: list[str] = []
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if account_name:
        conditions.append("account_name = ?")
        params.append(account_name)
    if month:
        conditions.append("substr(publish_time, 1, 7) = ?")
        params.append(month)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, tuple(params)


def check_connection() -> tuple[bool, str]:
    """检查数据库是否可连接，并返回各表记录数摘要。"""
    backend = get_connection().backend
    conn = get_connection()
    try:
        counts = {}
        for table in TABLES:
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            counts[table] = row["c"] if isinstance(row, dict) else row[0]
    except Exception as exc:
        return False, f"{backend}: {exc}"
    finally:
        conn.close()
    summary = "，".join(f"{table} {count} 条" for table, count in counts.items())
    return True, f"[{backend}] {summary}"


if __name__ == "__main__":
    init_db()
    ok, detail = check_connection()
    print("连接正常" if ok else f"连接失败：{detail}")
    if ok:
        print(f"记录数：{detail}")
