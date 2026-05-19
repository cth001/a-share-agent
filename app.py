"""
A股个股分析 Agent — Streamlit 可视化测试界面
运行方式: streamlit run app.py
"""

import sys
import os
import json
import time

from dotenv import load_dotenv
load_dotenv()  # 从 .env 文件加载环境变量（如 DATA_MODE, ANTHROPIC_API_KEY）

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ============================================================
# 数据源切换：Mock / Real
# ============================================================
# 在 .streamlit/secrets.toml 或环境变量中设置 DATA_MODE=real 使用真实数据
DATA_MODE = os.getenv("DATA_MODE", "mock")

if DATA_MODE == "real":
    from tools.tool_definitions import (
        resolve_stock_code, get_stock_quote, get_financials,
        calc_technical_indicators, get_capital_flow, get_northbound_flow,
        get_margin_data, get_news, get_announcements,
        get_industry_comparison, get_sector_top_stocks,
        get_sector_news, search_analyst_reports,
    )
else:
    from tools.mock_tools import (
        resolve_stock_code, get_stock_quote, get_financials,
        calc_technical_indicators, get_capital_flow, get_northbound_flow,
        get_margin_data, get_news, get_announcements,
        get_industry_comparison, get_sector_top_stocks,
        get_sector_news, search_analyst_reports,
    )


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="A股分析 Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 评分逻辑（从 main.py 复用）
# ============================================================

WEIGHT_PROFILES = {
    "短线": {"fundamental": 0.15, "technical": 0.40, "capital_flow": 0.30, "sentiment": 0.15},
    "中线": {"fundamental": 0.35, "technical": 0.25, "capital_flow": 0.20, "sentiment": 0.20},
    "长线": {"fundamental": 0.45, "technical": 0.15, "capital_flow": 0.15, "sentiment": 0.25},
}

RATING_MAP = [
    (85, "强烈推荐关注", "⭐⭐⭐⭐⭐", "green"),
    (70, "建议关注", "⭐⭐⭐⭐", "blue"),
    (55, "中性观望", "⭐⭐⭐", "orange"),
    (40, "谨慎观望", "⭐⭐", "red"),
    (0, "建议规避", "⭐", "darkred"),
]

DIM_LABELS = {
    "fundamental": "基本面",
    "technical": "技术面",
    "capital_flow": "资金面",
    "sentiment": "消息面",
}

# 模拟子 Agent 分析结果（Mock 模式下使用）
MOCK_ANALYSIS = {
    "600519": {
        "fundamental": {
            "score": 82,
            "sub_scores": {
                "盈利能力": {"score": 90, "summary": "ROE 30.2%，行业顶尖"},
                "成长性": {"score": 75, "summary": "营收增速15%，稳健增长"},
                "估值水平": {"score": 70, "summary": "PE 25x，PEG 1.1合理"},
                "财务健康": {"score": 92, "summary": "负债率25%，现金流充裕"},
            },
            "summary": "基本面优秀，盈利能力行业领先",
            "key_findings": [
                "ROE 30.2%，连续5年保持在28%以上，行业排名第1",
                "近4季营收增速 15%-18%，保持稳健增长",
                "PE(TTM) 25倍，高于行业中位数20倍，但PEG 1.1处于合理区间",
                "经营现金流/净利润 = 1.15，利润含金量高",
            ],
            "risks": ["估值溢价较高，若增速放缓可能面临杀估值风险"],
        },
        "technical": {
            "score": 71,
            "sub_scores": {
                "趋势判断": {"score": 78, "summary": "日线多头排列，5日线上行"},
                "动量指标": {"score": 65, "summary": "MACD金叉但柱状图缩短"},
                "量价关系": {"score": 72, "summary": "近3日温和放量上涨"},
                "关键价位": {"score": 68, "summary": "距上方压力位¥1880约3%"},
            },
            "summary": "短期多头但接近压力区",
            "key_findings": [
                "MA5上穿MA20形成金叉，短期趋势向好",
                "MACD零轴上方金叉，中期偏强",
                "上方¥1880为前期高点密集区",
                "布林带中轨上行，通道向上",
            ],
            "risks": ["接近前高压力区，缩量则可能回踩", "KDJ已进入超买区(K=82)"],
        },
        "capital_flow": {
            "score": 80,
            "sub_scores": {
                "主力资金": {"score": 85, "summary": "连续3日净流入共2.5亿"},
                "北向资金": {"score": 78, "summary": "近5日增持120万股"},
                "融资融券": {"score": 72, "summary": "融资余额小幅上升"},
                "筹码集中": {"score": 82, "summary": "股东户数连续2季减少"},
            },
            "summary": "资金面偏多，主力和北向共振流入",
            "key_findings": [
                "近5日主力累计净流入2.5亿元，超大单占比65%",
                "北向资金持股比例升至8.2%，近20日增持趋势明显",
                "融资余额环比增长3.2%，看多情绪增强",
                "最新季报股东户数环比减少5.3%",
            ],
            "risks": ["主力单日净流入金额有递减趋势"],
        },
        "sentiment": {
            "score": 75,
            "sub_scores": {
                "公司公告": {"score": 80, "summary": "Q1超预期+10亿回购"},
                "新闻情绪": {"score": 68, "summary": "正面新闻占比65%"},
                "政策环境": {"score": 75, "summary": "促消费政策持续出台"},
                "券商研报": {"score": 72, "summary": "15家覆盖，12家买入/增持"},
            },
            "summary": "消息面偏正面，业绩超预期叠加政策利好",
            "key_findings": [
                "Q1净利润同比增长18.5%，超市场预期",
                "董事会通过10亿元回购计划",
                "国务院发布促消费若干措施，白酒行业受益",
                "12家券商维持买入/增持评级",
            ],
            "risks": ["部分自媒体报道消费降级担忧"],
        },
    },
    "000858": {
        "fundamental": {
            "score": 68,
            "sub_scores": {
                "盈利能力": {"score": 72, "summary": "ROE 22.1%，行业中上"},
                "成长性": {"score": 62, "summary": "营收增速12%，温和增长"},
                "估值水平": {"score": 78, "summary": "PE 18.5x，PEG 0.85低估"},
                "财务健康": {"score": 65, "summary": "负债率28%，基本健康"},
            },
            "summary": "基本面良好，估值有性价比",
            "key_findings": ["ROE 22.1%", "PE 18.5x低于行业中位数", "PEG 0.85存在低估"],
            "risks": ["增速可能进一步放缓"],
        },
        "technical": {
            "score": 75,
            "sub_scores": {
                "趋势判断": {"score": 80, "summary": "周线企稳回升"},
                "动量指标": {"score": 72, "summary": "MACD即将金叉"},
                "量价关系": {"score": 70, "summary": "底部温和放量"},
                "关键价位": {"score": 76, "summary": "站上60日均线"},
            },
            "summary": "技术面企稳，底部放量回升",
            "key_findings": ["周线级别企稳", "站上60日均线", "底部放量"],
            "risks": ["上方套牢盘较重"],
        },
        "capital_flow": {
            "score": 65,
            "sub_scores": {
                "主力资金": {"score": 60, "summary": "主力流入流出交替"},
                "北向资金": {"score": 68, "summary": "北向小幅减持"},
                "融资融券": {"score": 65, "summary": "融资余额变动不大"},
                "筹码集中": {"score": 70, "summary": "股东户数基本持平"},
            },
            "summary": "资金面中性偏弱",
            "key_findings": ["主力资金方向不明", "北向持仓基本稳定"],
            "risks": ["缺乏持续资金推动力"],
        },
        "sentiment": {
            "score": 70,
            "sub_scores": {
                "公司公告": {"score": 72, "summary": "提高分红比例"},
                "新闻情绪": {"score": 65, "summary": "新闻偏正面"},
                "政策环境": {"score": 75, "summary": "消费政策利好"},
                "券商研报": {"score": 68, "summary": "以增持为主"},
            },
            "summary": "消息面温和正面",
            "key_findings": ["分红比例提高", "政策利好消费"],
            "risks": ["市场关注度不如龙头"],
        },
    },
}


def get_analysis(stock_code: str) -> dict:
    """获取分析结果（Mock 模式直接返回，Real 模式调用 Agent）"""
    return MOCK_ANALYSIS.get(stock_code, MOCK_ANALYSIS.get("600519"))


def calc_total_score(analysis: dict, period: str) -> tuple:
    """计算综合评分"""
    weights = WEIGHT_PROFILES[period]
    total = sum(analysis[dim]["score"] * w for dim, w in weights.items())
    total = round(total)
    for threshold, rec, stars, color in RATING_MAP:
        if total >= threshold:
            return total, rec, stars, color
    return total, "建议规避", "⭐", "darkred"


# ============================================================
# 侧边栏
# ============================================================

with st.sidebar:
    st.title("⚙️ 分析配置")

    st.markdown("---")

    # 数据模式指示
    mode_label = "🟡 Mock 数据" if DATA_MODE == "mock" else "🟢 实时数据"
    st.caption(f"数据模式: {mode_label}")

    # 股票输入
    st.subheader("股票选择")
    stock_input = st.text_input("输入股票代码或名称", value="600519", placeholder="如: 600519 或 茅台")

    # 对比模式
    compare_mode = st.checkbox("开启对比模式")
    stock_input_2 = ""
    if compare_mode:
        stock_input_2 = st.text_input("对比股票", value="000858", placeholder="第二只股票")

    st.markdown("---")

    # 用户偏好
    st.subheader("投资偏好")
    period = st.radio("投资周期", ["短线", "中线", "长线"], index=1)
    risk = st.radio("风险偏好", ["保守", "稳健", "激进"], index=1)

    st.markdown("---")

    # 权重展示
    st.subheader("当前权重配置")
    weights = WEIGHT_PROFILES[period]
    for dim, w in weights.items():
        st.progress(w, text=f"{DIM_LABELS[dim]}: {int(w*100)}%")

    st.markdown("---")
    st.caption("⚠️ AI 辅助分析，不构成投资建议")


# ============================================================
# 主界面
# ============================================================

st.title("📊 A股个股分析 Agent")
st.caption("Claude Agent SDK · 四维分析 · 可视化测试")

# 解析股票
resolved = resolve_stock_code(stock_input)
if resolved["status"] == "not_found":
    st.error(f"未找到股票。{resolved.get('suggestion', '')}")
    st.stop()
elif resolved["status"] == "multiple":
    options = {f"{m['stock_name']}({m['stock_code']})": m for m in resolved["matches"]}
    choice = st.selectbox("找到多个匹配，请选择：", list(options.keys()))
    stock = options[choice]
else:
    stock = resolved["matches"][0]

stock_code = stock["stock_code"]
stock_name = stock["stock_name"]

# 分析按钮
col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    run_analysis = st.button("🚀 开始分析", type="primary", use_container_width=True)

if not run_analysis and "analysis_done" not in st.session_state:
    st.info(f"已选择 **{stock_name}({stock_code})**，点击「开始分析」启动四维分析。")
    st.stop()

# 执行分析（带进度条）
if run_analysis:
    st.session_state["analysis_done"] = True
    st.session_state["stock_code"] = stock_code

    progress = st.progress(0, text="正在启动分析...")
    steps = [
        (0.15, "📥 拉取行情数据..."),
        (0.35, "📊 计算技术指标..."),
        (0.55, "💰 分析资金流向..."),
        (0.75, "📰 扫描新闻舆情..."),
        (0.90, "🧮 汇总评分中..."),
        (1.0, "✅ 分析完成！"),
    ]
    for pct, text in steps:
        time.sleep(0.3)
        progress.progress(pct, text=text)
    time.sleep(0.2)
    progress.empty()

# 获取分析数据
analysis = get_analysis(stock_code)
total_score, recommendation, stars, rec_color = calc_total_score(analysis, period)

# ============================================================
# 报告头部
# ============================================================

st.markdown("---")

header_col1, header_col2, header_col3 = st.columns([2, 2, 2])

with header_col1:
    st.metric(
        label=f"{stock_name} ({stock_code})",
        value=f"{total_score} 分",
        delta=recommendation,
    )

with header_col2:
    st.markdown(f"### {stars}")
    st.caption(f"配置：{risk} / {period} / 全面分析")

with header_col3:
    # 实时行情
    quote = get_stock_quote(stock_code, "daily", 5)
    if "error" not in quote:
        price = quote["current_price"]
        change = quote["change_pct"]
        delta_color = "normal" if change >= 0 else "inverse"
        st.metric("最新价", f"¥{price:.2f}", f"{change:+.2f}%", delta_color=delta_color)


# ============================================================
# 四维评分卡
# ============================================================

st.markdown("### 四维评分")

score_cols = st.columns(4)
dim_keys = ["fundamental", "technical", "capital_flow", "sentiment"]
dim_colors = ["#10B981", "#3B82F6", "#8B5CF6", "#EC4899"]
dim_icons = ["📈", "📉", "💰", "📰"]

for i, (dim, color, icon) in enumerate(zip(dim_keys, dim_colors, dim_icons)):
    with score_cols[i]:
        score = analysis[dim]["score"]
        summary = analysis[dim]["summary"]
        st.markdown(f"""
        <div style="border-left: 4px solid {color}; padding: 12px; border-radius: 4px;
                    background: linear-gradient(135deg, {color}08, {color}03);">
            <div style="font-size: 14px; font-weight: 600; color: {color};">
                {icon} {DIM_LABELS[dim]}
            </div>
            <div style="font-size: 32px; font-weight: 700; margin: 4px 0;">{score}<span style="font-size:16px;color:#888;">/100</span></div>
            <div style="font-size: 12px; color: #666;">{summary}</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# 雷达图 + 子维度详情
# ============================================================

st.markdown("### 分析详情")

radar_col, detail_col = st.columns([1, 1])

with radar_col:
    # 雷达图
    categories = [DIM_LABELS[d] for d in dim_keys]
    scores = [analysis[d]["score"] for d in dim_keys]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=scores + [scores[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(59, 130, 246, 0.15)',
        line=dict(color='#3B82F6', width=2),
        name=stock_name,
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickvals=[20, 40, 60, 80, 100]),
        ),
        showlegend=False,
        height=380,
        margin=dict(l=60, r=60, t=30, b=30),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with detail_col:
    # 子维度展开
    selected_dim = st.selectbox(
        "选择维度查看详情",
        dim_keys,
        format_func=lambda x: f"{DIM_LABELS[x]} ({analysis[x]['score']}分)",
    )

    dim_data = analysis[selected_dim]

    # 子维度评分条
    if "sub_scores" in dim_data:
        for sub_name, sub_info in dim_data["sub_scores"].items():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.progress(sub_info["score"] / 100, text=f"{sub_name}: {sub_info['summary']}")
            with col_b:
                st.markdown(f"**{sub_info['score']}**分")

    # 关键发现
    st.markdown("**📌 关键发现**")
    for finding in dim_data.get("key_findings", []):
        st.markdown(f"- {finding}")

    # 风险提示
    if dim_data.get("risks"):
        st.markdown("**⚠️ 风险点**")
        for risk_item in dim_data["risks"]:
            st.warning(risk_item, icon="⚠️")


# ============================================================
# K线图 + 技术指标
# ============================================================

st.markdown("### K线走势与技术指标")

quote_data = get_stock_quote(stock_code, "daily", 90)
if "error" not in quote_data:
    klines = quote_data["klines"]
    df_klines = pd.DataFrame(klines)
    df_klines["date"] = pd.to_datetime(df_klines["date"])

    # 计算均线
    for w in [5, 20, 60]:
        df_klines[f"ma{w}"] = df_klines["close"].rolling(w).mean()

    fig_kline = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
    )

    # K线
    fig_kline.add_trace(go.Candlestick(
        x=df_klines["date"],
        open=df_klines["open"], high=df_klines["high"],
        low=df_klines["low"], close=df_klines["close"],
        name="K线",
        increasing_line_color="#EF4444",   # 涨=红（A股习惯）
        decreasing_line_color="#10B981",   # 跌=绿
    ), row=1, col=1)

    # 均线
    for w, color in [(5, "#F59E0B"), (20, "#3B82F6"), (60, "#8B5CF6")]:
        fig_kline.add_trace(go.Scatter(
            x=df_klines["date"], y=df_klines[f"ma{w}"],
            mode="lines", name=f"MA{w}",
            line=dict(color=color, width=1.2),
        ), row=1, col=1)

    # 成交量
    colors = ["#EF4444" if c >= o else "#10B981" for c, o in zip(df_klines["close"], df_klines["open"])]
    fig_kline.add_trace(go.Bar(
        x=df_klines["date"], y=df_klines["volume"],
        name="成交量", marker_color=colors, opacity=0.6,
    ), row=2, col=1)

    fig_kline.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    fig_kline.update_yaxes(title_text="价格", row=1, col=1)
    fig_kline.update_yaxes(title_text="成交量", row=2, col=1)
    st.plotly_chart(fig_kline, use_container_width=True)

# 技术指标摘要
tech = calc_technical_indicators(stock_code)
if "error" not in tech:
    tech_cols = st.columns(5)
    with tech_cols[0]:
        alignment = tech.get("ma", {}).get("alignment", "N/A")
        alignment_cn = {"bullish": "🟢 多头", "bearish": "🔴 空头", "mixed": "🟡 交织"}.get(alignment, alignment)
        st.metric("均线排列", alignment_cn)
    with tech_cols[1]:
        signal = tech.get("macd", {}).get("signal", "N/A")
        signal_cn = {"golden_cross": "🟢 金叉", "death_cross": "🔴 死叉", "bullish": "🟢 偏多", "bearish": "🔴 偏空"}.get(signal, signal)
        st.metric("MACD", signal_cn)
    with tech_cols[2]:
        zone = tech.get("kdj", {}).get("zone", "N/A")
        zone_cn = {"overbought": "🔴 超买", "oversold": "🟢 超卖", "neutral": "🟡 中性"}.get(zone, zone)
        st.metric("KDJ", zone_cn, f"K={tech.get('kdj', {}).get('k', '')}")
    with tech_cols[3]:
        rsi_zone = tech.get("rsi", {}).get("zone", "N/A")
        rsi_cn = {"overbought": "🔴 超买", "oversold": "🟢 超卖", "neutral": "🟡 中性"}.get(rsi_zone, rsi_zone)
        st.metric("RSI", rsi_cn, f"RSI14={tech.get('rsi', {}).get('rsi_14', '')}")
    with tech_cols[4]:
        boll_pos = tech.get("boll", {}).get("position", "N/A")
        boll_cn = {"upper_band": "🔴 上轨", "upper_half": "🟡 上半区", "lower_half": "🟡 下半区", "lower_band": "🟢 下轨"}.get(boll_pos, boll_pos)
        st.metric("BOLL", boll_cn)


# ============================================================
# 资金面可视化
# ============================================================

st.markdown("### 资金流向")

flow_data = get_capital_flow(stock_code, 7)
if "error" not in flow_data and flow_data.get("daily_flows"):
    df_flow = pd.DataFrame(flow_data["daily_flows"])

    flow_col1, flow_col2 = st.columns([2, 1])

    with flow_col1:
        if "main_net_inflow" in df_flow.columns:
            df_flow["color"] = df_flow["main_net_inflow"].apply(lambda x: "#EF4444" if x > 0 else "#10B981")
            df_flow["inflow_yi"] = df_flow["main_net_inflow"] / 1e8

            fig_flow = go.Figure()
            fig_flow.add_trace(go.Bar(
                x=df_flow["date"], y=df_flow["inflow_yi"],
                marker_color=df_flow["color"],
                name="主力净流入(亿)",
            ))
            fig_flow.update_layout(
                height=300,
                yaxis_title="净流入（亿元）",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_flow, use_container_width=True)

    with flow_col2:
        summary = flow_data.get("summary", {})
        st.metric("5日主力净流入", f"{summary.get('total_main_net_5d', 0)/1e8:.2f} 亿")
        st.metric("连续净流入", f"{summary.get('consecutive_inflow_days', 0)} 天")

        nb = get_northbound_flow(stock_code)
        if nb.get("is_eligible"):
            st.metric("北向持股比例", f"{nb.get('holding_ratio', 0)}%")
            trend = nb.get("trend", "stable")
            trend_cn = {"increasing": "📈 增持", "decreasing": "📉 减持", "stable": "➡️ 持平"}.get(trend, trend)
            st.metric("北向趋势", trend_cn)


# ============================================================
# 消息面
# ============================================================

st.markdown("### 新闻与公告")

news_col, report_col = st.columns(2)

with news_col:
    st.markdown("**📰 最新新闻**")
    news_data = get_news(stock_code, 7, 5)
    if "error" not in news_data:
        for n in news_data.get("news", [])[:5]:
            st.markdown(f"**{n['date'][:10]}** · {n['source']}")
            st.markdown(f"  {n['title']}")
            st.markdown("---")

with report_col:
    st.markdown("**📋 券商研报**")
    reports = search_analyst_reports(stock_code, 5)
    if "error" not in reports:
        for r in reports.get("reports", [])[:5]:
            rating_color = {"买入": "🟢", "增持": "🔵", "中性": "🟡", "减持": "🔴"}.get(r.get("rating", ""), "⚪")
            tp = f" | 目标价 ¥{r['target_price']}" if r.get("target_price") else ""
            st.markdown(f"{rating_color} **{r.get('broker', '')}** — {r.get('rating', '')}{tp}")
            st.markdown(f"  {r.get('title', '')}")
            st.markdown("---")

        if reports.get("rating_summary"):
            st.markdown("**评级分布**")
            rs = reports["rating_summary"]
            fig_rating = go.Figure(go.Pie(
                labels=list(rs.keys()),
                values=list(rs.values()),
                hole=0.4,
                marker_colors=["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#991B1B"],
            ))
            fig_rating.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), showlegend=True)
            st.plotly_chart(fig_rating, use_container_width=True)


# ============================================================
# 多股对比（如果开启）
# ============================================================

if compare_mode and stock_input_2:
    st.markdown("---")
    st.markdown("### 📊 多股对比")

    resolved_2 = resolve_stock_code(stock_input_2)
    if resolved_2["status"] != "not_found":
        stock_2 = resolved_2["matches"][0]
        code_2, name_2 = stock_2["stock_code"], stock_2["stock_name"]
        analysis_2 = get_analysis(code_2)
        total_2, rec_2, stars_2, color_2 = calc_total_score(analysis_2, period)

        # 对比表格
        compare_data = {
            "指标": ["综合评分", "基本面", "技术面", "资金面", "消息面", "投资建议"],
            stock_name: [total_score, analysis["fundamental"]["score"], analysis["technical"]["score"],
                        analysis["capital_flow"]["score"], analysis["sentiment"]["score"], recommendation],
            name_2: [total_2, analysis_2["fundamental"]["score"], analysis_2["technical"]["score"],
                     analysis_2["capital_flow"]["score"], analysis_2["sentiment"]["score"], rec_2],
        }
        df_compare = pd.DataFrame(compare_data)
        st.dataframe(df_compare, use_container_width=True, hide_index=True)

        # 对比雷达图
        fig_compare = go.Figure()
        categories = [DIM_LABELS[d] for d in dim_keys]

        scores_1 = [analysis[d]["score"] for d in dim_keys]
        scores_2 = [analysis_2[d]["score"] for d in dim_keys]

        fig_compare.add_trace(go.Scatterpolar(
            r=scores_1 + [scores_1[0]], theta=categories + [categories[0]],
            fill='toself', fillcolor='rgba(59, 130, 246, 0.15)',
            line=dict(color='#3B82F6', width=2), name=stock_name,
        ))
        fig_compare.add_trace(go.Scatterpolar(
            r=scores_2 + [scores_2[0]], theta=categories + [categories[0]],
            fill='toself', fillcolor='rgba(236, 72, 153, 0.15)',
            line=dict(color='#EC4899', width=2), name=name_2,
        ))
        fig_compare.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=400,
            margin=dict(l=80, r=80, t=30, b=30),
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        # 择优结论
        if total_score > total_2:
            st.success(f"🏆 综合最优：**{stock_name}** ({total_score}分 vs {total_2}分)")
        elif total_2 > total_score:
            st.success(f"🏆 综合最优：**{name_2}** ({total_2}分 vs {total_score}分)")
        else:
            st.info(f"两者综合评分相同（{total_score}分），建议结合自身偏好选择。")
    else:
        st.error(f"未找到对比股票：{stock_input_2}")


# ============================================================
# 底部免责
# ============================================================

st.markdown("---")
st.caption("⚠️ 以上为 AI 辅助分析，不构成投资建议。投资有风险，入市需谨慎。")
st.caption(f"数据模式: {DATA_MODE} | 分析时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
