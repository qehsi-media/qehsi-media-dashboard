"""⑦ 活动作战方案：手工录入活动、建议账号与打法，生成作战卡。"""

from datetime import date, datetime

import streamlit as st

import ui
from db.activities import add_activity, delete_activity, fetch_activities
from db.database import PLATFORM_LABELS, fetch_accounts, init_db

st.set_page_config(page_title="活动作战", page_icon="🎯", layout="wide")
ui.inject_css()
init_db()

ui.page_header(
    "活动作战方案",
    "同场多线打法 · 每条爆点标注建议发布账号",
    datetime.now().strftime("%Y 年 %m 月"),
    "手工录入",
)

ui.banner("🎯 看板二 · 活动作战 & 内容爆点推荐", "录入活动名称、日期、目标与建议账号，自动生成作战卡", "amber")

accounts = fetch_accounts()
account_options = {
    f"{PLATFORM_LABELS.get(row['platform'], row['platform'])}·{row['account_name']}": row
    for row in accounts
}

ui.section("07", "活动作战方案", "每个活动一张作战卡")

with st.expander("＋ 新增活动作战方案", expanded=not fetch_activities()):
    with st.form("activity_form", clear_on_submit=True):
        name = st.text_input("活动名称", placeholder="例如：11.6 赏秋节 · 单词擂台")
        col_date, col_status = st.columns([1, 1])
        activity_date = col_date.date_input("活动日期", value=date.today(), format="YYYY-MM-DD")
        status = col_status.selectbox("状态", options=["筹备中", "进行中", "已结束"], index=0)
        goal = st.text_input("作战目标", placeholder="例如：三端协同，事件总曝光 1.5 万-2 万")
        selected_accounts = st.multiselect(
            "建议发布账号",
            options=list(account_options),
            help="可多选；作战卡会按顺序展示建议账号。",
        )
        battle_plan = st.text_area(
            "作战打法（每行一个步骤）",
            placeholder="现场拍摄：擂台抢答 / 开箱 / 乐队 / 花花空降\n当晚抖音首发：QEHSI 号发对决快剪\n当晚视频号：官方号发完整叙事版\n次日公众号：图文战报 + 名单公示钩子",
            height=140,
        )
        submitted = st.form_submit_button("保存作战方案", type="primary")

if submitted:
    if not name.strip():
        st.warning("请填写活动名称。")
    else:
        add_activity(
            activity_name=name,
            activity_date=str(activity_date),
            goal=goal,
            suggested_accounts="、".join(selected_accounts),
            battle_plan=battle_plan,
            status=status,
        )
        st.toast("作战方案已保存")
        st.rerun()

activities = fetch_activities()
if not activities:
    st.info("还没有活动作战方案，请在上方展开“新增活动作战方案”录入。")
else:
    status_style = {"进行中": "hot", "筹备中": "star", "已结束": "norm"}
    for item in activities:
        flow = [line.strip() for line in (item["battle_plan"] or "").splitlines() if line.strip()]
        highlight = f"建议发布账号：{item['suggested_accounts']}" if item["suggested_accounts"] else ""
        card_col, action_col = st.columns([11, 1])
        with card_col:
            ui.camp_card(
                {
                    "name": item["activity_name"],
                    "status": status_style.get(item["status"], "norm"),
                    "status_text": item["status"],
                    "period": item["activity_date"] or "",
                    "desc": item["goal"] or "尚未填写作战目标。",
                    "flow": flow,
                    "highlight": highlight,
                }
            )
        with action_col:
            if st.button("删除", key=f"delete_activity_{item['id']}"):
                delete_activity(item["id"])
                st.toast("已删除该作战方案")
                st.rerun()
