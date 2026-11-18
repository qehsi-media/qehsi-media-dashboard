"""三平台导出文件读取、字段映射、清洗与入库。"""

import math
import re
import sqlite3
from collections import Counter
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd

from db.database import get_connection

STANDARD_FIELDS = [
    ("content_title", "内容标题"),
    ("publish_time", "发布时间"),
    ("views", "播放量"),
    ("likes", "点赞数"),
    ("comments", "评论数"),
    ("shares", "分享数"),
    ("favorites", "收藏数"),
    ("link", "内容链接"),
    ("content_type", "内容类型"),
    ("topic", "主题标签"),
]
REQUIRED_MAPPING_FIELDS = {"content_title", "publish_time"}
NUMERIC_FIELDS = ["views", "likes", "comments", "shares", "favorites"]
TEXT_FIELDS = ["link", "content_type", "topic"]

DEFAULT_ALIASES = {
    "content_title": ["内容标题", "标题", "视频标题", "作品标题", "作品描述", "视频描述", "内容描述"],
    "publish_time": ["发布时间", "发布日期", "视频发布时间", "作品发布时间", "创建时间"],
    "views": ["播放量", "播放次数", "视频播放量", "总播放量", "播放数"],
    "likes": ["点赞", "点赞数", "点赞量", "获赞数", "点赞次数"],
    "comments": ["评论", "评论数", "评论量", "评论次数"],
    "shares": ["分享", "分享数", "分享量", "转发", "转发数"],
    "favorites": ["收藏", "收藏数", "收藏量", "收藏次数"],
    "link": ["链接", "内容链接", "视频链接", "作品链接", "播放链接"],
    "content_type": ["内容类型", "视频类型", "作品类型", "类型"],
    "topic": ["主题", "主题标签", "内容主题", "话题", "内容标签"],
}

PLATFORM_ALIASES = {
    "douyin": {},
    "wechat_video": {
        "content_title": ["视频标题", "作品标题", "视频描述", "内容标题"],
        "publish_time": ["视频发布时间", "发表时间", "发布时间"],
        "views": ["播放量", "播放数", "观看量", "观看次数", "观看数"],
        "comments": ["评论数", "评论量"],
        "shares": ["分享数", "分享", "转发数", "转发"],
        "favorites": ["收藏数", "收藏", "收藏量"],
        "link": ["视频链接", "作品链接", "内容链接"],
        "content_type": ["视频类型", "内容类型"],
    },
    "wechat_mp": {
        "content_title": ["文章标题", "图文标题", "内容标题", "标题"],
        "publish_time": ["发表时间", "发文时间", "发布时间", "发布日期"],
        "views": ["阅读数", "阅读量", "阅读次数", "阅读"],
        "likes": ["点赞数", "点赞", "点赞量"],
        "comments": ["留言数", "留言", "评论数", "评论"],
        "shares": ["转发", "分享", "转发数", "分享数", "转发次数", "分享次数"],
        "favorites": ["在看", "在看数", "收藏", "收藏数"],
        "link": ["文章链接", "图文链接", "原文链接", "内容链接"],
        "content_type": ["文章类型", "图文类型", "内容类型"],
    },
}


def _text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清理表头与空行，保留原始中文列名。"""
    df = df.copy()
    df.columns = [_text(column) for column in df.columns]

    unnamed_nonempty = [
        column
        for column in df.columns
        if column.lower().startswith("unnamed:")
        and any(_text(value) for value in df[column].tolist())
    ]
    if unnamed_nonempty:
        raise ValueError("检测到表头为空的列，请检查文件第一行是否为完整列名。")

    empty_unnamed = [
        column
        for column in df.columns
        if column.lower().startswith("unnamed:")
    ]
    if empty_unnamed:
        df = df.drop(columns=empty_unnamed)

    duplicated = df.columns[df.columns.duplicated()].tolist()
    if duplicated:
        raise ValueError(f"列名重复：{'、'.join(duplicated)}")

    nonempty_rows = df.apply(
        lambda row: any(_text(value) for value in row.tolist()), axis=1
    )
    return df.loc[nonempty_rows].reset_index(drop=True)


def read_uploaded_file(file_name: str, content: bytes) -> pd.DataFrame:
    """读取 CSV/XLSX；CSV 依次尝试多种编码。"""
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        errors = []
        # 常见中文 CSV 编码：带 BOM 的 UTF-8、UTF-8、GBK、GB18030、UTF-16 LE/BE
        encodings_to_try = [
            "utf-8-sig",
            "utf-8",
            "gb18030",
            "gbk",
            "gb2312",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "big5",
            "latin-1",
        ]
        for encoding in encodings_to_try:
            try:
                df = pd.read_csv(
                    BytesIO(content),
                    encoding=encoding,
                    dtype=str,
                    keep_default_na=False,
                )
                # 成功读完后检查一下是不是乱码（如果所有列名都是 \uXXXX 或全问号）
                columns_text = " ".join(df.columns.astype(str))
                if "\ufffd" in columns_text or columns_text.count("?") > len(df.columns) * 0.5:
                    errors.append(f"{encoding}: 列名疑似乱码，跳过")
                    continue
                return _prepare_dataframe(df)
            except (UnicodeDecodeError, UnicodeError) as exc:
                errors.append(f"{encoding}: {exc}")
            except pd.errors.ParserError as exc:
                errors.append(f"{encoding}: {exc}")
        # 最后兜底：用 errors='replace' 强行读
        try:
            df = pd.read_csv(
                BytesIO(content),
                encoding="utf-8",
                encoding_errors="replace",
                dtype=str,
                keep_default_na=False,
            )
            return _prepare_dataframe(df)
        except Exception as exc:
            errors.append(f"utf-8+replace: {exc}")
        raise ValueError(
            f"CSV 读取失败，已尝试多种编码：{', '.join(errors[:3])}..."
        ) from None

    if suffix == ".xlsx":
        try:
            df = pd.read_excel(
                BytesIO(content),
                engine="openpyxl",
                keep_default_na=False,
            )
        except Exception as exc:
            raise ValueError(f"Excel 读取失败：{exc}") from exc
        return _prepare_dataframe(df)

    raise ValueError("仅支持 .csv 或 .xlsx 文件。")


def load_saved_mapping(platform: str) -> dict[str, str]:
    """返回 {标准字段: 源列名}。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT source_column, target_field FROM field_mappings WHERE platform = ?",
            (platform,),
        ).fetchall()
    finally:
        conn.close()
    return {row["target_field"]: row["source_column"] for row in rows}


def suggest_mapping(
    columns: list[str], saved_mapping: dict[str, str], platform: str = "douyin"
) -> dict:
    """优先复用该平台已保存映射，再按平台别名和通用别名匹配。"""
    result = {}
    used_columns = set()
    normalized_columns = {re.sub(r"\s+", "", column).casefold(): column for column in columns}

    for target_field, _ in STANDARD_FIELDS:
        saved_source = saved_mapping.get(target_field)
        if saved_source in columns and saved_source not in used_columns:
            result[target_field] = saved_source
            used_columns.add(saved_source)
            continue

        selected = None
        platform_aliases = PLATFORM_ALIASES.get(platform, {}).get(target_field, [])
        aliases = platform_aliases + DEFAULT_ALIASES[target_field]
        for alias in aliases:
            normalized_alias = re.sub(r"\s+", "", alias).casefold()
            source = normalized_columns.get(normalized_alias)
            if source is not None and source not in used_columns:
                selected = source
                break
        result[target_field] = selected
        if selected is not None:
            used_columns.add(selected)
    return result


def validate_mapping(mapping: dict) -> list[str]:
    errors = []
    labels = dict(STANDARD_FIELDS)
    for field in sorted(REQUIRED_MAPPING_FIELDS):
        if not mapping.get(field):
            errors.append(f"请映射必填字段“{labels[field]}”。")

    sources = [source for source in mapping.values() if source]
    duplicated = [source for source, count in Counter(sources).items() if count > 1]
    if duplicated:
        errors.append(f"同一源列不能映射到多个字段：{'、'.join(duplicated)}。")
    return errors


def _number(value) -> int:
    text = _text(value).replace(",", "").replace("，", "")
    if not text:
        return 0
    try:
        number = float(text)
        if not math.isfinite(number):
            return 0
        return int(round(number))
    except (TypeError, ValueError, OverflowError):
        return 0


def _parse_publish_time(value) -> tuple[str, bool, str]:
    """返回（入库值, 是否解析成功, 原始文本）；失败时保留原文。"""
    original = _text(value)
    if not original:
        return "", False, original

    parsed = None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        parsed = pd.Timestamp(value)
    else:
        if re.fullmatch(r"\d+(?:\.\d+)?", original):
            serial = float(original)
            if 1 <= serial <= 100000:
                parsed = pd.to_datetime(serial, unit="D", origin="1899-12-30")

        if parsed is None:
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d",
                "%Y.%m.%d",
                "%Y%m%d",
                "%Y年%m月%d日 %H:%M:%S",
                "%Y年%m月%d日 %H:%M",
                "%Y年%m月%d日",
            ]
            for date_format in formats:
                try:
                    parsed = datetime.strptime(original, date_format)
                    break
                except ValueError:
                    continue

        if parsed is None:
            fallback = pd.to_datetime(original, errors="coerce")
            if not pd.isna(fallback):
                parsed = fallback

    if parsed is None or pd.isna(parsed):
        return original, False, original

    timestamp = pd.Timestamp(parsed)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S"), True, original


def clean_dataframe(df: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, list[dict]]:
    """按映射生成 contents 标准字段，并返回发布时间异常明细。"""
    cleaned = pd.DataFrame(index=df.index)

    for field, _ in STANDARD_FIELDS:
        source = mapping.get(field)
        cleaned[field] = df[source] if source else ""

    cleaned["content_title"] = cleaned["content_title"].map(_text).replace("", "未命名内容")
    for field in NUMERIC_FIELDS:
        cleaned[field] = cleaned[field].map(_number)
    for field in TEXT_FIELDS:
        cleaned[field] = cleaned[field].map(_text).replace("", None)

    publish_results = cleaned["publish_time"].map(_parse_publish_time)
    cleaned["publish_time"] = publish_results.map(lambda result: result[0])
    invalid_times = [
        {
            "行号": int(index) + 2,
            "原始发布时间": result[2] or "（空）",
            "入库保留值": result[0],
        }
        for index, result in publish_results.items()
        if not result[1]
    ]
    return cleaned, invalid_times


def import_contents(
    df: pd.DataFrame,
    platform: str,
    account_name: str,
    file_name: str,
    mapping: dict,
) -> dict:
    """保存映射并写入批次与内容；单行失败不影响其他行。"""
    cleaned, invalid_times = clean_dataframe(df, mapping)
    failures = []
    success_count = 0
    duplicate_count = 0

    conn = get_connection()
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM field_mappings WHERE platform = ?", (platform,))
        conn.executemany(
            """
            INSERT INTO field_mappings (platform, source_column, target_field)
            VALUES (?, ?, ?)
            """,
            [
                (platform, source, target)
                for target, source in mapping.items()
                if source
            ],
        )

        cursor = conn.execute(
            "INSERT INTO upload_batches (platform, file_name, row_count, status) VALUES (?, ?, ?, 'pending')",
            (platform, file_name, len(cleaned)),
        )
        batch_id = cursor.lastrowid

        for index, row in cleaned.iterrows():
            conn.execute("SAVEPOINT content_row")
            try:
                duplicate = conn.execute(
                    """
                    SELECT id FROM contents
                    WHERE platform = ? AND account_name = ? AND content_title = ? AND publish_time = ?
                    """,
                    (
                        platform,
                        account_name,
                        row["content_title"],
                        row["publish_time"],
                    ),
                ).fetchone()
                if duplicate:
                    duplicate_count += 1
                    conn.execute("RELEASE SAVEPOINT content_row")
                    continue

                conn.execute(
                    """
                    INSERT INTO contents (
                        platform, account_name, content_title, publish_time,
                        views, likes, comments, shares, favorites,
                        link, content_type, topic, upload_batch
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        account_name,
                        row["content_title"],
                        row["publish_time"],
                        int(row["views"]),
                        int(row["likes"]),
                        int(row["comments"]),
                        int(row["shares"]),
                        int(row["favorites"]),
                        row["link"],
                        row["content_type"],
                        row["topic"],
                        batch_id,
                    ),
                )
                success_count += 1
                conn.execute("RELEASE SAVEPOINT content_row")
            except (sqlite3.Error, TypeError, ValueError) as exc:
                conn.execute("ROLLBACK TO SAVEPOINT content_row")
                conn.execute("RELEASE SAVEPOINT content_row")
                failures.append({"行号": int(index) + 2, "原因": str(exc)})

        failed_count = len(failures)
        if failed_count == 0:
            status = "success"
        elif success_count > 0 or duplicate_count > 0:
            status = "partial"
        else:
            status = "failed"
        conn.execute(
            "UPDATE upload_batches SET status = ? WHERE id = ?",
            (status, batch_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    failure_summary = Counter(item["原因"] for item in failures)
    return {
        "batch_id": batch_id,
        "total_count": len(cleaned),
        "success_count": success_count,
        "failed_count": len(failures),
        "duplicate_count": duplicate_count,
        "status": status,
        "failures": failures,
        "failure_summary": dict(failure_summary),
        "invalid_times": invalid_times,
    }


def fetch_upload_batches(platform: str, limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT b.id, b.file_name, b.upload_time, b.row_count, b.status,
                   COUNT(c.id) AS success_count
            FROM upload_batches b
            LEFT JOIN contents c ON c.upload_batch = b.id
            WHERE b.platform = ?
            GROUP BY b.id
            ORDER BY b.id DESC
            LIMIT ?
            """,
            (platform, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]
