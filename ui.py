"""看板统一样式层：主题 CSS、卡片组件、HTML 表格与雷达图。

所有页面复用这里的渲染函数，保证与参考页一致的视觉语言：
浅蓝渐变背景、半透明白卡片、渐变数字、平台语义色。
"""

from __future__ import annotations

import html as _html
import math

import streamlit as st

PLATFORM_COLORS = {
    "douyin": "#fe2c55",
    "wechat_video": "#07c160",
    "wechat_mp": "#576b95",
}
PLATFORM_LABELS = {
    "douyin": "抖音",
    "wechat_video": "视频号",
    "wechat_mp": "公众号",
}
PLATFORM_TAG_CLASS = {
    "douyin": "dy",
    "wechat_video": "sph",
    "wechat_mp": "gzh",
}


def esc(value) -> str:
    """转义用户内容，避免 HTML 注入。"""
    return _html.escape("" if value is None else str(value))


def fmt_int(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_pct(value) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "—"


def account_role(platform: str, group: str | None) -> str:
    """按平台与账号分组推断矩阵角色。"""
    group = group or ""
    if platform == "wechat_mp":
        return "深度内容门户"
    if "阿拉丁" in group:
        return "人格化IP号"
    if "出分" in group:
        return "垂类事件号"
    return "官方主号"


def delta_html(current, previous, suffix: str = "环比上月") -> str:
    """生成环比涨跌 HTML；上月为 0 时显示“新增”。"""
    try:
        current = float(current or 0)
        previous = float(previous or 0)
    except (TypeError, ValueError):
        return f'<span class="q-muted">{esc(suffix)} —</span>'
    if previous <= 0:
        text = "新增" if current > 0 else "—"
        return f'<b class="up">▲ {text}</b> <span class="q-muted">{esc(suffix)}</span>' if current > 0 else f'<span class="q-muted">{esc(suffix)} —</span>'
    rate = (current - previous) / previous
    arrow = "▲" if rate >= 0 else "▼"
    klass = "up" if rate >= 0 else "down"
    return (
        f'<b class="{klass}">{arrow} {abs(rate):.1%}</b> '
        f'<span class="q-muted">{esc(suffix)}</span>'
    )


# ---------------------------------------------------------------------------
# 主题
# ---------------------------------------------------------------------------

CSS = """
<style>
:root {
  --bg: #f4f6fc;
  --card: rgba(255, 255, 255, 0.80);
  --ink: #17203a;
  --muted: #5c6b85;
  --rule: rgba(23, 32, 58, 0.10);
  --accent: #2f6bff;
  --accent2: #7c3aed;
  --good: #0e9f6e;
  --p-douyin: #fe2c55;
  --p-shipinhao: #07c160;
  --p-gzh: #576b95;
  --radius: 16px;
  --shadow: 0 8px 28px rgba(47, 107, 255, 0.08), 0 2px 6px rgba(23, 32, 58, 0.04);
}

html, body, [class*="css"], .stApp {
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", "Segoe UI", sans-serif;
  color: var(--ink);
}
.stApp {
  background-color: var(--bg);
  background-image:
    radial-gradient(720px 480px at 8% -4%, rgba(47, 107, 255, 0.10), transparent 62%),
    radial-gradient(640px 460px at 96% 2%, rgba(124, 58, 237, 0.08), transparent 60%),
    radial-gradient(760px 520px at 50% 108%, rgba(7, 193, 96, 0.06), transparent 62%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding: 1.1rem 1.4rem 3rem; max-width: 1280px; }
[data-testid="stSidebar"] { background: rgba(255, 255, 255, 0.86); }

/* 顶栏 */
.q-topbar {
  display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap;
  padding: 0.85rem 1.15rem; margin-bottom: 0.6rem;
  border: 1px solid var(--rule); border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow);
}
.q-brand { display: flex; align-items: center; gap: 0.7rem; min-width: 0; }
.q-logo {
  width: 42px; height: 42px; border-radius: 12px; flex: none;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff; font-weight: 800; font-size: 0.72rem; letter-spacing: 0.02em;
  display: flex; align-items: center; justify-content: center;
}
.q-brand h1 { font-size: 1.06rem; font-weight: 700; line-height: 1.3; margin: 0; }
.q-sub { font-size: 0.74rem; color: var(--muted); line-height: 1.4; }
.q-topright { margin-left: auto; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.q-badge {
  display: inline-flex; align-items: center; font-size: 0.74rem; font-weight: 600;
  padding: 0.22rem 0.6rem; border-radius: 999px;
  background: rgba(47, 107, 255, 0.10); color: var(--accent); white-space: nowrap;
}
.q-badge.live { background: rgba(14, 159, 110, 0.10); color: var(--good); }

.q-banner {
  display: flex; align-items: baseline; gap: 0.8rem; flex-wrap: wrap;
  margin: 0.2rem 0 1.2rem; padding: 0.9rem 1.2rem; border-radius: 14px; color: #fff;
}
.q-banner.navy { background: linear-gradient(135deg, #12315e, #1d4d8f); }
.q-banner.amber { background: linear-gradient(135deg, #7a3d0d, #b8620f); }
.q-banner b { font-weight: 900; font-size: 1.1rem; }
.q-banner span { font-size: 0.78rem; opacity: 0.88; }

/* 板块标题 */
.q-sec { display: flex; align-items: baseline; gap: 0.65rem; margin: 1.5rem 0 0.9rem; flex-wrap: wrap; }
.q-sec-num {
  font-size: 0.76rem; font-weight: 800; color: var(--accent);
  background: rgba(47, 107, 255, 0.10); border-radius: 8px; padding: 0.14rem 0.5rem;
}
.q-sec h2 { font-size: 1.22rem; font-weight: 800; margin: 0; letter-spacing: 0.01em; }
.q-hint { font-size: 0.78rem; color: var(--muted); }
.q-muted { color: var(--muted); }

/* 卡片 */
.q-card {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 1.05rem 1.15rem;
}

/* KPI */
.q-kpi-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.8rem; }
.q-kpi {
  position: relative; overflow: hidden; padding: 0.95rem 1rem;
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.q-kpi::after {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(180deg, var(--accent), var(--accent2));
}
.q-kpi-label { font-size: 0.74rem; color: var(--muted); font-weight: 600; }
.q-kpi-value {
  font-size: 1.55rem; font-weight: 800; line-height: 1.25; margin-top: 0.25rem;
  background: linear-gradient(120deg, var(--ink), var(--accent));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.q-kpi-delta { font-size: 0.72rem; margin-top: 0.2rem; color: var(--muted); }
.q-kpi-delta b.up { color: var(--good); font-weight: 700; }
.q-kpi-delta b.down { color: var(--p-douyin); font-weight: 700; }

/* 账号卡片 */
.q-acc-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; }
.q-acc {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 0.95rem 1rem; display: flex; flex-direction: column; gap: 0.4rem;
}
.q-acc-top { display: flex; align-items: center; gap: 0.45rem; }
.q-plat {
  font-size: 0.66rem; font-weight: 700; color: #fff; border-radius: 6px;
  padding: 0.14rem 0.45rem; flex: none; letter-spacing: 0.02em;
}
.q-plat.dy { background: var(--p-douyin); }
.q-plat.sph { background: var(--p-shipinhao); }
.q-plat.gzh { background: var(--p-gzh); }
.q-acc-name { font-size: 0.84rem; font-weight: 700; line-height: 1.35; }
.q-acc-role { font-size: 0.72rem; color: var(--accent); font-weight: 600; }
.q-acc-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.3rem; margin-top: 0.15rem; }
.q-acc-stat .n { font-size: 0.95rem; font-weight: 800; }
.q-acc-stat .l { font-size: 0.65rem; color: var(--muted); }
.q-acc-foot {
  font-size: 0.72rem; color: var(--muted);
  border-top: 1px dashed var(--rule); padding-top: 0.42rem; margin-top: auto;
}
.q-acc-foot b { color: var(--good); }

/* 爆款卡片 */
.q-hit-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; }
.q-hit {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 1rem 1.05rem; display: flex; flex-direction: column; gap: 0.5rem;
}
.q-hit-head { display: flex; justify-content: space-between; gap: 0.5rem; align-items: flex-start; }
.q-hit-title { font-size: 0.88rem; font-weight: 700; line-height: 1.45; }
a.q-hit-link { color: inherit; text-decoration: none; }
a.q-hit-link:hover { color: var(--accent); }
.q-hit-date { font-size: 0.7rem; color: var(--muted); flex: none; }
.q-hit-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.4rem; }
.q-hit-metric .n { font-size: 1rem; font-weight: 800; color: var(--accent); }
.q-hit-metric .l { font-size: 0.65rem; color: var(--muted); }
.q-hit-tags { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.q-tag {
  font-size: 0.66rem; font-weight: 600; color: var(--accent2);
  background: rgba(124, 58, 237, 0.08); padding: 0.1rem 0.5rem; border-radius: 999px;
}
.q-hit-note { font-size: 0.74rem; color: var(--muted); border-top: 1px dashed var(--rule); padding-top: 0.45rem; }

/* 战役卡片 */
.q-camp {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 1.2rem 1.3rem; margin-bottom: 0.9rem;
}
.q-camp-head { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 0.35rem; }
.q-camp-head h3 { font-size: 1rem; font-weight: 800; margin: 0; }
.q-camp-status { font-size: 0.68rem; font-weight: 700; padding: 0.12rem 0.55rem; border-radius: 999px; }
.q-camp-status.hot { background: rgba(254, 44, 85, 0.09); color: var(--p-douyin); }
.q-camp-status.star { background: rgba(254, 179, 8, 0.14); color: #b45309; }
.q-camp-status.norm { background: rgba(47, 107, 255, 0.09); color: var(--accent); }
.q-camp-period { font-size: 0.72rem; color: var(--muted); }
.q-camp-desc { font-size: 0.83rem; color: var(--muted); margin: 0.4rem 0 0.65rem; line-height: 1.7; }
.q-flow { display: flex; align-items: center; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.65rem; }
.q-flow-step {
  font-size: 0.72rem; font-weight: 600; background: #fff;
  border: 1px solid var(--rule); border-radius: 8px; padding: 0.26rem 0.6rem;
}
.q-flow-arrow { color: var(--accent); font-weight: 800; font-size: 0.78rem; }
.q-camp-highlight {
  font-size: 0.8rem; background: rgba(14, 159, 110, 0.07);
  border-left: 3px solid var(--good); border-radius: 0 8px 8px 0; padding: 0.5rem 0.75rem;
  line-height: 1.65;
}

/* 价值 & 规划 */
.q-value-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin-bottom: 0.9rem; }
.q-value {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 1rem; text-align: center;
}
.q-value .v {
  font-size: 1.45rem; font-weight: 800;
  background: linear-gradient(120deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.q-value .l { font-size: 0.78rem; font-weight: 700; margin-top: 0.1rem; }
.q-value .d { font-size: 0.7rem; color: var(--muted); margin-top: 0.2rem; line-height: 1.5; }
.q-text { font-size: 0.86rem; line-height: 1.8; }
.q-text p { margin: 0 0 0.6rem; }
.q-text b { color: var(--accent); }

.q-plan-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.8rem; margin-bottom: 0.9rem; }
.q-plan {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 1rem 1.1rem;
}
.q-plan h4 { font-size: 0.9rem; font-weight: 800; margin: 0 0 0.3rem; line-height: 1.5; }
.q-plan p { font-size: 0.78rem; color: var(--muted); margin: 0.25rem 0; line-height: 1.65; }
.q-plan-acct { font-size: 0.72rem; color: var(--accent); font-weight: 700; }
.q-plan-tags { margin-top: 0.5rem; display: flex; gap: 0.35rem; flex-wrap: wrap; }

/* 表格 */
.q-table-wrap {
  overflow-x: auto; border-radius: var(--radius); border: 1px solid var(--rule);
  background: var(--card); box-shadow: var(--shadow); margin-bottom: 0.8rem;
}
table.q-table { width: 100%; border-collapse: collapse; font-size: 0.81rem; min-width: 720px; }
table.q-table thead th {
  text-align: left; font-size: 0.72rem; color: var(--muted); font-weight: 700;
  padding: 0.6rem 0.8rem; border-bottom: 1px solid var(--rule); white-space: nowrap;
  background: #fff; position: sticky; top: 0; z-index: 2;
}
table.q-table tbody td { padding: 0.58rem 0.8rem; border-bottom: 1px solid var(--rule); vertical-align: top; }
table.q-table tbody tr:last-child td { border-bottom: none; }
table.q-table tbody tr:hover { background: rgba(47, 107, 255, 0.04); }
table.q-table .num { font-variant-numeric: tabular-nums; font-weight: 600; white-space: nowrap; }
table.q-table .cell-sub { font-size: 0.72rem; color: var(--muted); }
/* 热力 */
td.h0 { background: rgba(255, 112, 67, 0.04); }
td.h1 { background: rgba(255, 112, 67, 0.10); }
td.h2 { background: rgba(255, 112, 67, 0.18); }
td.h3 { background: rgba(255, 112, 67, 0.27); }
td.h4 { background: rgba(255, 112, 67, 0.36); }

/* Streamlit 原生控件微调 */
.stTabs [data-baseweb="tab-list"] { gap: 0.45rem; }
.stTabs [data-baseweb="tab"] {
  border: 1px solid var(--rule); border-radius: 999px; padding: 0.28rem 0.95rem;
  background: #fff; color: var(--muted); font-weight: 700; font-size: 0.82rem;
}
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--accent), var(--accent2)); border: none;
}
[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-radius: var(--radius); border-color: var(--rule);
  background: var(--card); box-shadow: var(--shadow); padding: 0.35rem 0.4rem;
}
[data-testid="stMetricValue"] { font-size: 1.5rem; }

@media (max-width: 1080px) {
  .q-kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .q-acc-grid { grid-template-columns: repeat(2, 1fr); }
  .q-hit-grid { grid-template-columns: repeat(2, 1fr); }
  .q-value-grid { grid-template-columns: repeat(2, 1fr); }
  .q-plan-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .q-kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .q-acc-grid, .q-hit-grid { grid-template-columns: 1fr; }
  .block-container { padding: 0.8rem 0.8rem 2rem; }
}
</style>
"""


def inject_css() -> None:
    """注入全局主题样式，每页调用一次。"""
    st.markdown(CSS, unsafe_allow_html=True)


def render(fragment: str) -> None:
    """渲染 HTML 片段；压掉缩进与空行，避免被 Markdown 解析成代码块。"""
    compact = " ".join(line.strip() for line in fragment.strip().splitlines() if line.strip())
    st.markdown(compact, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, month_label: str = "", state: str = "真实上传数据") -> None:
    badges = ""
    if month_label:
        badges += f'<span class="q-badge">{esc(month_label)}</span>'
    badges += f'<span class="q-badge live">{esc(state)}</span>'
    render(
        f"""
        <div class="q-topbar">
          <div class="q-brand">
            <div class="q-logo">QEHSI</div>
            <div>
              <h1>{esc(title)}</h1>
              <div class="q-sub">{esc(subtitle)}</div>
            </div>
          </div>
          <div class="q-topright">{badges}</div>
        </div>
        """
    )


def banner(title: str, subtitle: str, tone: str = "navy") -> None:
    render(f'<div class="q-banner {tone}"><b>{esc(title)}</b><span>{esc(subtitle)}</span></div>')


def section(num: str, title: str, hint: str = "") -> None:
    render(
        f'<div class="q-sec"><span class="q-sec-num">{esc(num)}</span>'
        f"<h2>{esc(title)}</h2><span class='q-hint'>{esc(hint)}</span></div>"
    )


def kpi_grid(items: list[dict]) -> None:
    cards = "".join(
        f"""
        <div class="q-kpi">
          <div class="q-kpi-label">{esc(item.get('label'))}</div>
          <div class="q-kpi-value">{esc(item.get('value'))}</div>
          <div class="q-kpi-delta">{item.get('delta', '')}</div>
        </div>
        """
        for item in items
    )
    render(f'<div class="q-kpi-grid">{cards}</div>')


def account_grid(rows: list[dict]) -> None:
    cards = []
    for row in rows:
        platform = row["platform"]
        cards.append(
            f"""
            <div class="q-acc">
              <div class="q-acc-top">
                <span class="q-plat {PLATFORM_TAG_CLASS.get(platform, 'dy')}">
                  {esc(PLATFORM_LABELS.get(platform, platform))}</span>
                <span class="q-acc-name">{esc(row['account_name'])}</span>
              </div>
              <div class="q-acc-role">{esc(row.get('role', ''))}</div>
              <div class="q-acc-stats">
                <div class="q-acc-stat"><div class="n">{fmt_int(row['content_count'])}</div><div class="l">内容数</div></div>
                <div class="q-acc-stat"><div class="n">{fmt_int(row['views'])}</div><div class="l">曝光</div></div>
                <div class="q-acc-stat"><div class="n">{fmt_int(row['interactions'])}</div><div class="l">互动</div></div>
              </div>
              <div class="q-acc-foot">互动率 <b>{fmt_pct(row.get('rate'))}</b></div>
            </div>
            """
        )
    render(f'<div class="q-acc-grid">{"".join(cards)}</div>')


def hit_grid(hits: list[dict]) -> None:
    cards = []
    for hit in hits:
        tags = "".join(f'<span class="q-tag">{esc(tag)}</span>' for tag in hit.get("tags", []))
        title = esc(hit["title"])
        if hit.get("link"):
            title = (
                f'<a class="q-hit-link" href="{esc(hit["link"])}" target="_blank" '
                f'rel="noopener noreferrer">{title}</a>'
            )
        cards.append(
            f"""
            <div class="q-hit">
              <div class="q-hit-head">
                <div class="q-hit-title">{title}</div>
                <div class="q-hit-date">{esc(hit.get('date', ''))}</div>
              </div>
              <div class="q-hit-metrics">
                <div class="q-hit-metric"><div class="n">{fmt_int(hit['views'])}</div><div class="l">曝光</div></div>
                <div class="q-hit-metric"><div class="n">{fmt_int(hit['interactions'])}</div><div class="l">互动</div></div>
                <div class="q-hit-metric"><div class="n">{esc(hit.get('ratio', '—'))}</div><div class="l">爆款倍数</div></div>
              </div>
              <div class="q-hit-tags">{tags}</div>
              <div class="q-hit-note">{esc(hit.get('note', ''))}</div>
            </div>
            """
        )
    render(f'<div class="q-hit-grid">{"".join(cards)}</div>')


def camp_card(item: dict) -> None:
    """作战卡：名称 / 状态 / 时间 / 描述 / 流程 / 亮点。"""
    status = item.get("status", "norm")
    flow = item.get("flow") or []
    flow_html = ""
    if flow:
        steps = []
        for index, step in enumerate(flow):
            if index:
                steps.append('<span class="q-flow-arrow">→</span>')
            steps.append(f'<span class="q-flow-step">{esc(step)}</span>')
        flow_html = f'<div class="q-flow">{"".join(steps)}</div>'
    highlight = item.get("highlight")
    highlight_html = f'<div class="q-camp-highlight">{esc(highlight)}</div>' if highlight else ""
    render(
        f"""
        <div class="q-camp">
          <div class="q-camp-head">
            <h3>{esc(item.get('name'))}</h3>
            <span class="q-camp-status {esc(status)}">{esc(item.get('status_text', ''))}</span>
            <span class="q-camp-period">{esc(item.get('period', ''))}</span>
          </div>
          <div class="q-camp-desc">{esc(item.get('desc', ''))}</div>
          {flow_html}
          {highlight_html}
        </div>
        """
    )


def value_grid(items: list[dict]) -> None:
    cards = "".join(
        f"""
        <div class="q-value">
          <div class="v">{esc(item.get('value'))}</div>
          <div class="l">{esc(item.get('label'))}</div>
          <div class="d">{esc(item.get('detail', ''))}</div>
        </div>
        """
        for item in items
    )
    render(f'<div class="q-value-grid">{cards}</div>')


def text_card(paragraphs: list[str]) -> None:
    body = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
    render(f'<div class="q-card q-text">{body}</div>')


def plan_card(item: dict) -> None:
    tags = "".join(f'<span class="q-tag">{esc(tag)}</span>' for tag in item.get("tags", []))
    render(
        f"""
        <div class="q-plan">
          <div class="q-plan-acct">{esc(item.get('account', ''))}</div>
          <h4>{esc(item.get('title', ''))}</h4>
          <p><b>发布：</b>{esc(item.get('platform', ''))}</p>
          <p><b>依据：</b>{esc(item.get('basis', ''))}</p>
          <p><b>预期：</b>{esc(item.get('expected', ''))}</p>
          <p><b>拍法：</b>{esc(item.get('tips', ''))}</p>
          <div class="q-plan-tags">{tags}</div>
        </div>
        """
    )


def _numeric(value) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _heat_class(value: float, maximum: float) -> str:
    """按列最大值分五档，返回热力类名。"""
    if maximum <= 0:
        return ""
    ratio = value / maximum
    if ratio >= 0.8:
        return "h4"
    if ratio >= 0.6:
        return "h3"
    if ratio >= 0.4:
        return "h2"
    if ratio >= 0.2:
        return "h1"
    return "h0"


def html_table(headers: list[str], rows: list[list], heat_columns: set[int] | None = None) -> None:
    """渲染参考页风格表格；heat_columns 为需要按列热力上色的列索引。"""
    head = "".join(f"<th>{esc(header)}</th>" for header in headers)
    heat_columns = heat_columns or set()
    maxima: dict[int, float] = {}
    for index in heat_columns:
        values = [value for value in (_numeric(row[index]) if index < len(row) else None for row in rows)]
        maxima[index] = max((value for value in values if value is not None), default=0.0)
    body_rows = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            klass = ""
            if index in heat_columns:
                number = _numeric(cell)
                if number is not None:
                    heat = _heat_class(number, maxima.get(index, 0.0))
                    klass = f' class="{heat}"' if heat else ""
            cells.append(f"<td{klass}>{cell}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    render(
        f"""
        <div class="q-table-wrap">
          <table class="q-table">
            <thead><tr>{head}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
          </table>
        </div>
        """
    )


def radar_svg(series: list[dict], dimensions: list[str], size: int = 440) -> None:
    """绘制三平台能力雷达图（纯 SVG，不依赖额外绘图库）。"""
    width, height = size, int(size * 0.86)
    cx, cy, radius = width / 2, height / 2 - 8, min(width, height) * 0.30
    count = len(dimensions)
    angles = [-math.pi / 2 + 2 * math.pi * index / count for index in range(count)]

    def point(angle: float, ratio: float) -> tuple[float, float]:
        return cx + radius * ratio * math.cos(angle), cy + radius * ratio * math.sin(angle)

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-height:360px">']
    for ring in (0.2, 0.4, 0.6, 0.8, 1.0):
        coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(a, ring) for a in angles))
        parts.append(
            f'<polygon points="{coords}" fill="none" '
            f'stroke="rgba(23,32,58,0.10)" stroke-width="1"/>'
        )
    for angle in angles:
        x, y = point(angle, 1.0)
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="rgba(23,32,58,0.10)" stroke-width="1"/>'
        )
    for angle, label in zip(angles, dimensions):
        x, y = point(angle, 1.18)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#5c6b85" font-size="11" '
            f'text-anchor="{anchor}" dominant-baseline="middle">{esc(label)}</text>'
        )
    for item in series:
        coords = " ".join(
            f"{x:.1f},{y:.1f}"
            for x, y in (point(angle, max(0.0, min(1.0, value / 100))) for angle, value in zip(angles, item["values"]))
        )
        color = item.get("color", "#2f6bff")
        parts.append(
            f'<polygon points="{coords}" fill="{color}" fill-opacity="0.12" '
            f'stroke="{color}" stroke-width="2"/>'
        )
        for angle, value in zip(angles, item["values"]):
            x, y = point(angle, max(0.0, min(1.0, value / 100)))
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
    legend_x = 16
    for item in series:
        color = item.get("color", "#2f6bff")
        parts.append(
            f'<rect x="{legend_x}" y="{height - 20}" width="10" height="10" rx="2" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{legend_x + 15}" y="{height - 11}" fill="#5c6b85" font-size="11">{esc(item["name"])}</text>'
        )
        legend_x += 24 + 11 * len(str(item["name"])) + 18
    parts.append("</svg>")
    render("".join(parts))


def style_chart(chart):
    """统一 Altair 图表的字体、坐标轴与透明背景。"""
    return (
        chart.properties(background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#5c6b85",
            titleColor="#5c6b85",
            gridColor="rgba(23, 32, 58, 0.08)",
            domainColor="rgba(23, 32, 58, 0.10)",
            tickColor="rgba(23, 32, 58, 0.10)",
            labelFontSize=11,
            titleFontSize=11,
            title=None,
        )
        .configure_legend(labelColor="#5c6b85", titleColor="#5c6b85", orient="bottom", direction="horizontal")
        .configure(font="PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif")
    )
