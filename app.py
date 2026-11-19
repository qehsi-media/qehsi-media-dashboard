"""qehsi-media-dashboard 首页。"""

import streamlit as st

from db.database import (
    DB_PATH,
    PLATFORM_LABELS,
    check_connection,
    fetch_accounts,
    init_db,
)

PROJECT_NAME = "qehsi-media-dashboard"
PROJECT_TITLE = "青岛实验高中国际部 · 新媒体数据看板"

st.set_page_config(page_title=PROJECT_TITLE, page_icon="📊", layout="wide")

st.title(PROJECT_TITLE)
st.caption(f"项目名称：{PROJECT_NAME}　|　数据来源：手动上传平台导出的 Excel/CSV 文件")

st.divider()

# ---------- 数据库状态 ----------
st.subheader("数据库连接状态")
try:
    init_db()
    ok, detail = check_connection()
except Exception as exc:  # 初始化失败时在页面上直接暴露原因
    ok, detail = False, f"{type(exc).__name__}: {exc}"

if ok:
    st.success(f"数据库连接正常")
    st.caption(f"{detail}")
else:
    st.error(f"数据库连接失败：{detail}")

st.divider()

# ---------- 账号清单 ----------
st.subheader("账号清单")

try:
    accounts = fetch_accounts()
except Exception as exc:
    accounts = []
    st.error(f"读取 accounts 表失败：{type(exc).__name__}: {exc}")

if accounts:
    st.metric("账号总数", f"{len(accounts)} 个")

    for platform, label in PLATFORM_LABELS.items():
        platform_accounts = [a for a in accounts if a["platform"] == platform]
        st.markdown(f"**{label}（{platform}）· {len(platform_accounts)} 个账号**")
        if not platform_accounts:
            st.caption("暂无账号")
            continue
        st.dataframe(
            [
                {
                    "账号 ID": a["account_id"],
                    "账号名称": a["account_name"],
                    "账号分组": a["account_group"],
                    "状态": "正常" if a["status"] == "active" else a["status"],
                }
                for a in platform_accounts
            ],
            width="stretch",
            hide_index=True,
        )
else:
    st.warning("accounts 表中暂无账号，请检查 config/accounts.json。")

st.divider()

with st.expander("功能导航"):
    st.markdown(
        "- **数据上传**：上传抖音 / 视频号 / 公众号导出的 CSV/XLSX，支持字段映射与撤回\n"
        "- **数据看板**：① 核心数据 + ② 各账号表现\n"
        "- **爆款与矩阵**：③ IP 矩阵 + ④ 爆款内容 + ⑤ 联动亮点\n"
        "- **月度报告**：⑥ 服务价值小结 + 规则模板月度报告\n"
        "- **活动作战**：⑦ 手工录入活动，自动生成作战卡\n"
        "- **爆款选题**：⑧ 基于本月真实数据的选题方向、避坑与周历"
    )
