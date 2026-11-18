"""抖音、视频号、公众号数据手动上传、字段映射与入库。"""

import hashlib

import pandas as pd
import streamlit as st

from db.database import PLATFORM_LABELS, fetch_accounts, init_db
from db.importer import (
    REQUIRED_MAPPING_FIELDS,
    STANDARD_FIELDS,
    fetch_upload_batches,
    import_contents,
    load_saved_mapping,
    read_uploaded_file,
    suggest_mapping,
    validate_mapping,
)

STATUS_LABELS = {
    "pending": "处理中",
    "success": "成功",
    "partial": "部分成功",
    "failed": "失败",
}

st.set_page_config(page_title="数据上传", page_icon="📤", layout="wide")
st.title("数据上传")
st.caption("支持抖音、视频号、公众号。数据仅来自手动上传的 CSV/XLSX 文件，不使用自动登录或数据抓取。")

init_db()
all_accounts = fetch_accounts()
platform = st.selectbox(
    "平台",
    options=list(PLATFORM_LABELS),
    format_func=lambda value: PLATFORM_LABELS[value],
)
accounts = [account for account in all_accounts if account["platform"] == platform]
if not accounts:
    st.error(f"accounts 表中没有{PLATFORM_LABELS[platform]}账号，请先检查账号初始化。")
    st.stop()

account_name = st.selectbox(
    "导入到账号",
    options=[account["account_name"] for account in accounts],
    help="一个上传文件对应一个账号，请与平台后台导出的账号保持一致。",
)
uploaded_file = st.file_uploader(
    f"选择{PLATFORM_LABELS[platform]}后台导出的文件",
    type=["csv", "xlsx"],
    accept_multiple_files=False,
)

if uploaded_file is None:
    st.info("请先上传 CSV 或 XLSX 文件。CSV 将自动尝试 UTF-8 和 GBK 编码。")
else:
    content = uploaded_file.getvalue()
    try:
        source_df = read_uploaded_file(uploaded_file.name, content)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    st.subheader("文件预览")
    st.caption(f"共 {len(source_df)} 行数据，以下显示前 10 行。")
    preview_df = source_df.head(10).copy()
    for column in preview_df.columns:
        preview_df[column] = preview_df[column].map(
            lambda value: "" if value is None or pd.isna(value) else str(value)
        )
    st.dataframe(preview_df, width="stretch", hide_index=True)
    st.markdown("**全部列名**")
    st.code(" | ".join(source_df.columns), language=None)

    saved_mapping = load_saved_mapping(platform)
    default_mapping = suggest_mapping(list(source_df.columns), saved_mapping, platform)
    if saved_mapping:
        st.success("已加载该平台上次保存的映射；列名一致的字段会自动套用。")

    file_token = f"{platform}_{hashlib.sha1(content).hexdigest()[:12]}"
    st.subheader("字段映射")
    st.caption("内容标题和发布时间必须映射；其余字段不映射时按空值或 0 入库。点击入库时保存本次映射。")

    with st.form(f"mapping_form_{file_token}"):
        left, right = st.columns(2)
        mapping = {}
        for index, (target_field, label) in enumerate(STANDARD_FIELDS):
            options = [None] + list(source_df.columns)
            default_source = default_mapping.get(target_field)
            default_index = options.index(default_source) if default_source in options else 0
            suffix = "（必填）" if target_field in REQUIRED_MAPPING_FIELDS else ""
            container = left if index % 2 == 0 else right
            field_label = "阅读量" if target_field == "views" and platform == "wechat_mp" else label
            mapping[target_field] = container.selectbox(
                f"{field_label}{suffix}",
                options=options,
                index=default_index,
                format_func=lambda value: "（不映射）" if value is None else value,
                key=f"mapping_{file_token}_{target_field}",
            )
        submitted = st.form_submit_button("保存映射并入库", type="primary")

    if submitted:
        mapping_errors = validate_mapping(mapping)
        if mapping_errors:
            for error in mapping_errors:
                st.error(error)
        elif len(source_df) == 0:
            st.error("文件中没有可导入的数据行。")
        else:
            try:
                result = import_contents(
                    source_df,
                    platform,
                    account_name,
                    uploaded_file.name,
                    mapping,
                )
            except Exception as exc:
                st.error(f"入库失败：{type(exc).__name__}: {exc}")
            else:
                st.subheader("本次入库结果")
                if result["failed_count"] == 0:
                    st.success(f"批次 #{result['batch_id']} 处理完成，映射已保存。")
                else:
                    st.warning(f"批次 #{result['batch_id']} 部分行未入库，映射已保存。")

                metric_columns = st.columns(4)
                metric_columns[0].metric("本次上传行数", result["total_count"])
                metric_columns[1].metric("成功入库行数", result["success_count"])
                metric_columns[2].metric("失败行数", result["failed_count"])
                metric_columns[3].metric("重复跳过行数", result["duplicate_count"])

                if result["duplicate_count"]:
                    st.info("重复内容按“平台 + 账号 + 标题 + 发布时间”识别并跳过。")

                st.markdown("**失败原因摘要**")
                if result["failure_summary"]:
                    st.dataframe(
                        [
                            {"失败原因": reason, "行数": count}
                            for reason, count in result["failure_summary"].items()
                        ],
                        width="stretch",
                        hide_index=True,
                    )
                    with st.expander("查看失败行明细"):
                        st.dataframe(result["failures"], width="stretch", hide_index=True)
                else:
                    st.caption("无失败行。")

                if result["invalid_times"]:
                    st.warning(
                        f"有 {len(result['invalid_times'])} 行发布时间无法解析，已保留原文入库；"
                        "这些行可能无法纳入后续按月份统计。"
                    )
                    with st.expander("查看发布时间异常行"):
                        st.dataframe(
                            result["invalid_times"],
                            width="stretch",
                            hide_index=True,
                        )

st.divider()
st.subheader("最近上传批次（当前平台）")
batches = fetch_upload_batches(platform)
if batches:
    st.dataframe(
        [
            {
                "批次": batch["id"],
                "文件名": batch["file_name"],
                "上传时间": batch["upload_time"],
                "文件行数": batch["row_count"],
                "当前入库行数": batch["success_count"],
                "状态": STATUS_LABELS.get(batch["status"], batch["status"]),
            }
            for batch in batches
        ],
        width="stretch",
        hide_index=True,
    )
else:
    st.caption(f"暂无{PLATFORM_LABELS[platform]}上传记录。")
