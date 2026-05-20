"""
生成独立 HTML 可视化测试报告
运行: python generate_report.py
输出: visual_test_report.html
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from tools.mock_tools import (
    resolve_stock_code, get_stock_quote, get_financials,
    calc_technical_indicators, get_capital_flow, get_northbound_flow,
    get_margin_data, get_news, get_announcements,
    get_industry_comparison, search_analyst_reports,
)

# ============================================================
# 配置
# ============================================================

WEIGHT_PROFILES = {
    "短线": {"fundamental": 0.15, "technical": 0.40, "capital_flow": 0.30, "sentiment": 0.15},
    "中线": {"fundamental": 0.35, "technical": 0.25, "capital_flow": 0.20, "sentiment": 0.20},
    "长线": {"fundamental": 0.45, "technical": 0.15, "capital_flow": 0.15, "sentiment": 0.25},
}

DIM_LABELS = {"fundamental": "基本面", "technical": "技术面", "capital_flow": "资金面", "sentiment": "消息面"}
DIM_COLORS = {"fundamental": "#10B981", "technical": "#3B82F6", "capital_flow": "#8B5CF6", "sentiment": "#EC4899"}
DIM_ICONS  = {"fundamental": "📈", "technical": "📉", "capital_flow": "💰", "sentiment": "📰"}

MOCK_ANALYSIS = {
    "600519": {
        "fundamental": {
            "score": 82,
            "sub_scores": {"盈利能力": {"score": 90, "summary": "ROE 30.2%，行业顶尖"}, "成长性": {"score": 75, "summary": "营收增速15%，稳健增长"}, "估值水平": {"score": 70, "summary": "PE 25x，PEG 1.1合理"}, "财务健康": {"score": 92, "summary": "负债率25%，现金流充裕"}},
            "summary": "基本面优秀，盈利能力行业领先",
            "key_findings": ["ROE 30.2%，连续5年保持在28%以上", "近4季营收增速 15%-18%", "PE(TTM) 25倍，PEG 1.1合理", "经营现金流/净利润 = 1.15"],
            "risks": ["估值溢价较高，若增速放缓可能面临杀估值风险"],
        },
        "technical": {
            "score": 71,
            "sub_scores": {"趋势判断": {"score": 78, "summary": "日线多头排列"}, "动量指标": {"score": 65, "summary": "MACD金叉但柱状图缩短"}, "量价关系": {"score": 72, "summary": "近3日温和放量上涨"}, "关键价位": {"score": 68, "summary": "距上方压力位¥1880约3%"}},
            "summary": "短期多头但接近压力区",
            "key_findings": ["MA5上穿MA20形成金叉", "MACD零轴上方金叉", "上方¥1880为前期高点密集区", "布林带中轨上行"],
            "risks": ["接近前高压力区", "KDJ已进入超买区(K=82)"],
        },
        "capital_flow": {
            "score": 80,
            "sub_scores": {"主力资金": {"score": 85, "summary": "连续3日净流入共2.5亿"}, "北向资金": {"score": 78, "summary": "近5日增持120万股"}, "融资融券": {"score": 72, "summary": "融资余额小幅上升"}, "筹码集中": {"score": 82, "summary": "股东户数连续2季减少"}},
            "summary": "资金面偏多，主力和北向共振流入",
            "key_findings": ["近5日主力累计净流入2.5亿元", "北向资金持股比例升至8.2%", "融资余额环比增长3.2%", "股东户数环比减少5.3%"],
            "risks": ["主力单日净流入金额有递减趋势"],
        },
        "sentiment": {
            "score": 75,
            "sub_scores": {"公司公告": {"score": 80, "summary": "Q1超预期+10亿回购"}, "新闻情绪": {"score": 68, "summary": "正面新闻占比65%"}, "政策环境": {"score": 75, "summary": "促消费政策持续出台"}, "券商研报": {"score": 72, "summary": "15家覆盖，12家买入/增持"}},
            "summary": "消息面偏正面，业绩超预期叠加政策利好",
            "key_findings": ["Q1净利润同比增长18.5%", "董事会通过10亿元回购计划", "国务院发布促消费若干措施", "12家券商维持买入/增持"],
            "risks": ["部分自媒体报道消费降级担忧"],
        },
    },
    "000858": {
        "fundamental": {"score": 68, "sub_scores": {"盈利能力": {"score": 72, "summary": "ROE 22.1%"}, "成长性": {"score": 62, "summary": "营收增速12%"}, "估值水平": {"score": 78, "summary": "PE 18.5x低估"}, "财务健康": {"score": 65, "summary": "负债率28%"}}, "summary": "基本面良好，估值有性价比", "key_findings": ["ROE 22.1%", "PE 18.5x低于行业中位数"], "risks": ["增速可能放缓"]},
        "technical": {"score": 75, "sub_scores": {"趋势判断": {"score": 80, "summary": "周线企稳回升"}, "动量指标": {"score": 72, "summary": "MACD即将金叉"}, "量价关系": {"score": 70, "summary": "底部温和放量"}, "关键价位": {"score": 76, "summary": "站上60日均线"}}, "summary": "技术面企稳，底部放量回升", "key_findings": ["周线级别企稳", "站上60日均线"], "risks": ["上方套牢盘较重"]},
        "capital_flow": {"score": 65, "sub_scores": {"主力资金": {"score": 60, "summary": "主力流入流出交替"}, "北向资金": {"score": 68, "summary": "北向小幅减持"}, "融资融券": {"score": 65, "summary": "融资余额变动不大"}, "筹码集中": {"score": 70, "summary": "股东户数持平"}}, "summary": "资金面中性偏弱", "key_findings": ["主力资金方向不明", "北向持仓基本稳定"], "risks": ["缺乏持续资金推动力"]},
        "sentiment": {"score": 70, "sub_scores": {"公司公告": {"score": 72, "summary": "提高分红比例"}, "新闻情绪": {"score": 65, "summary": "新闻偏正面"}, "政策环境": {"score": 75, "summary": "消费政策利好"}, "券商研报": {"score": 68, "summary": "以增持为主"}}, "summary": "消息面温和正面", "key_findings": ["分红比例提高", "政策利好消费"], "risks": ["市场关注度不如龙头"]},
    },
}

RATING_MAP = [(85, "强烈推荐关注", "⭐⭐⭐⭐⭐"), (70, "建议关注", "⭐⭐⭐⭐"), (55, "中性观望", "⭐⭐⭐"), (40, "谨慎观望", "⭐⭐"), (0, "建议规避", "⭐")]

def calc_total(analysis, period):
    w = WEIGHT_PROFILES[period]
    total = round(sum(analysis[d]["score"] * w[d] for d in w))
    for t, rec, stars in RATING_MAP:
        if total >= t:
            return total, rec, stars
    return total, "建议规避", "⭐"


# ============================================================
# 生成所有图表
# ============================================================

charts = {}
stock_code = "600519"
stock_name = "贵州茅台"
period = "中线"
analysis = MOCK_ANALYSIS[stock_code]
total_score, recommendation, stars = calc_total(analysis, period)

# --- 1. 雷达图 ---
dim_keys = ["fundamental", "technical", "capital_flow", "sentiment"]
categories = [DIM_LABELS[d] for d in dim_keys]
scores = [analysis[d]["score"] for d in dim_keys]

fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=scores + [scores[0]], theta=categories + [categories[0]],
    fill='toself', fillcolor='rgba(59, 130, 246, 0.15)',
    line=dict(color='#3B82F6', width=2), name=stock_name,
))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickvals=[20, 40, 60, 80, 100])),
    showlegend=False, height=400, margin=dict(l=80, r=80, t=40, b=40),
    title=dict(text="四维评分雷达图", x=0.5),
)
charts["radar"] = fig_radar.to_html(full_html=False, include_plotlyjs=False)

# --- 2. K线图 ---
quote_data = get_stock_quote(stock_code, "daily", 90)
klines = quote_data["klines"]
df_k = pd.DataFrame(klines)
df_k["date"] = pd.to_datetime(df_k["date"])
for w in [5, 20, 60]:
    df_k[f"ma{w}"] = df_k["close"].rolling(w).mean()

fig_kline = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
fig_kline.add_trace(go.Candlestick(
    x=df_k["date"], open=df_k["open"], high=df_k["high"], low=df_k["low"], close=df_k["close"],
    name="K线", increasing_line_color="#EF4444", decreasing_line_color="#10B981",
), row=1, col=1)
for w, color in [(5, "#F59E0B"), (20, "#3B82F6"), (60, "#8B5CF6")]:
    fig_kline.add_trace(go.Scatter(x=df_k["date"], y=df_k[f"ma{w}"], mode="lines", name=f"MA{w}", line=dict(color=color, width=1.2)), row=1, col=1)
vol_colors = ["#EF4444" if c >= o else "#10B981" for c, o in zip(df_k["close"], df_k["open"])]
fig_kline.add_trace(go.Bar(x=df_k["date"], y=df_k["volume"], name="成交量", marker_color=vol_colors, opacity=0.6), row=2, col=1)
fig_kline.update_layout(height=500, xaxis_rangeslider_visible=False, showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=40, b=0), title=dict(text="日K线走势（MA5/MA20/MA60 + 成交量）", x=0.5))
fig_kline.update_yaxes(title_text="价格", row=1, col=1)
fig_kline.update_yaxes(title_text="成交量", row=2, col=1)
charts["kline"] = fig_kline.to_html(full_html=False, include_plotlyjs=False)

# --- 3. 资金流向柱状图 ---
flow_data = get_capital_flow(stock_code, 7)
df_flow = pd.DataFrame(flow_data["daily_flows"])
df_flow["color"] = df_flow["main_net_inflow"].apply(lambda x: "#EF4444" if x > 0 else "#10B981")
df_flow["inflow_yi"] = df_flow["main_net_inflow"] / 1e8

fig_flow = go.Figure()
fig_flow.add_trace(go.Bar(x=df_flow["date"], y=df_flow["inflow_yi"], marker_color=df_flow["color"], name="主力净流入(亿)"))
fig_flow.update_layout(height=350, yaxis_title="净流入（亿元）", margin=dict(l=0, r=0, t=40, b=0),
    title=dict(text="主力资金净流入（亿元）", x=0.5))
charts["capital_flow"] = fig_flow.to_html(full_html=False, include_plotlyjs=False)

# --- 4. 研报评级饼图 ---
reports = search_analyst_reports(stock_code, 10)
rs = reports.get("rating_summary", {})
fig_pie = go.Figure(go.Pie(labels=list(rs.keys()), values=list(rs.values()), hole=0.4,
    marker_colors=["#10B981", "#3B82F6", "#F59E0B", "#EF4444"]))
fig_pie.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0), title=dict(text="券商评级分布", x=0.5))
charts["rating_pie"] = fig_pie.to_html(full_html=False, include_plotlyjs=False)

# --- 5. 对比雷达图 ---
code_2, name_2 = "000858", "五粮液"
analysis_2 = MOCK_ANALYSIS[code_2]
total_2, rec_2, stars_2 = calc_total(analysis_2, period)
scores_2 = [analysis_2[d]["score"] for d in dim_keys]

fig_compare = go.Figure()
fig_compare.add_trace(go.Scatterpolar(r=scores + [scores[0]], theta=categories + [categories[0]],
    fill='toself', fillcolor='rgba(59, 130, 246, 0.15)', line=dict(color='#3B82F6', width=2), name=stock_name))
fig_compare.add_trace(go.Scatterpolar(r=scores_2 + [scores_2[0]], theta=categories + [categories[0]],
    fill='toself', fillcolor='rgba(236, 72, 153, 0.15)', line=dict(color='#EC4899', width=2), name=name_2))
fig_compare.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    height=400, margin=dict(l=80, r=80, t=40, b=40), title=dict(text="茅台 vs 五粮液 对比雷达图", x=0.5))
charts["compare_radar"] = fig_compare.to_html(full_html=False, include_plotlyjs=False)

# --- 6. 技术指标数据 ---
tech = calc_technical_indicators(stock_code)
tech_summary = {}
if "ma" in tech:
    tech_summary["均线排列"] = {"bullish": "🟢 多头", "bearish": "🔴 空头", "mixed": "🟡 交织"}.get(tech["ma"].get("alignment", ""), "N/A")
if "macd" in tech:
    tech_summary["MACD"] = {"golden_cross": "🟢 金叉", "death_cross": "🔴 死叉", "bullish": "🟢 偏多", "bearish": "🔴 偏空"}.get(tech["macd"].get("signal", ""), "N/A")
if "kdj" in tech:
    tech_summary["KDJ"] = {"overbought": "🔴 超买", "oversold": "🟢 超卖", "neutral": "🟡 中性"}.get(tech["kdj"].get("zone", ""), "N/A") + f" (K={tech['kdj'].get('k', '')})"
if "rsi" in tech:
    tech_summary["RSI"] = {"overbought": "🔴 超买", "oversold": "🟢 超卖", "neutral": "🟡 中性"}.get(tech["rsi"].get("zone", ""), "N/A") + f" (RSI14={tech['rsi'].get('rsi_14', '')})"
if "boll" in tech:
    tech_summary["BOLL"] = {"upper_band": "🔴 上轨", "upper_half": "🟡 上半区", "lower_half": "🟡 下半区", "lower_band": "🟢 下轨"}.get(tech["boll"].get("position", ""), "N/A")

# --- 7. 新闻数据 ---
news_data = get_news(stock_code, 7, 5)

# --- 8. 北向资金 ---
nb = get_northbound_flow(stock_code)

# --- 9. 子维度评分柱状图 ---
sub_charts = {}
for dim in dim_keys:
    d = analysis[dim]
    if "sub_scores" in d:
        names = list(d["sub_scores"].keys())
        vals = [d["sub_scores"][n]["score"] for n in names]
        fig_sub = go.Figure(go.Bar(x=vals, y=names, orientation='h', marker_color=DIM_COLORS[dim], text=vals, textposition='auto'))
        fig_sub.update_layout(height=220, margin=dict(l=0, r=0, t=30, b=0), xaxis=dict(range=[0, 100]),
            title=dict(text=f"{DIM_LABELS[dim]}子维度评分", x=0.5, font=dict(size=14)))
        sub_charts[dim] = fig_sub.to_html(full_html=False, include_plotlyjs=False)


# ============================================================
# 权重对比柱状图（三种投资周期）
# ============================================================
periods = ["短线", "中线", "长线"]
weight_scores = {}
for p in periods:
    t, r, s = calc_total(analysis, p)
    weight_scores[p] = t

fig_weight = go.Figure()
fig_weight.add_trace(go.Bar(x=periods, y=[weight_scores[p] for p in periods],
    marker_color=["#F59E0B", "#3B82F6", "#8B5CF6"], text=[weight_scores[p] for p in periods], textposition='auto'))
fig_weight.update_layout(height=300, yaxis=dict(range=[0, 100], title="综合评分"),
    margin=dict(l=0, r=0, t=40, b=0), title=dict(text="不同投资周期下的综合评分", x=0.5))
charts["weight_compare"] = fig_weight.to_html(full_html=False, include_plotlyjs=False)


# ============================================================
# 组装 HTML
# ============================================================

def score_card_html(dim, data):
    s = data["score"]
    color = DIM_COLORS[dim]
    icon = DIM_ICONS[dim]
    return f'''
    <div style="flex:1; border-left:4px solid {color}; padding:16px; border-radius:8px;
                background:linear-gradient(135deg, {color}10, {color}05); min-width:200px;">
        <div style="font-size:14px; font-weight:600; color:{color};">{icon} {DIM_LABELS[dim]}</div>
        <div style="font-size:36px; font-weight:700; margin:6px 0;">{s}<span style="font-size:16px;color:#888;">/100</span></div>
        <div style="font-size:13px; color:#666;">{data["summary"]}</div>
    </div>'''

def findings_html(dim, data):
    items = "".join(f'<li style="margin:4px 0;font-size:13px;">{f}</li>' for f in data.get("key_findings", []))
    risks = "".join(f'<div style="background:#FEF3C7;border-left:3px solid #F59E0B;padding:8px 12px;margin:4px 0;border-radius:4px;font-size:13px;">⚠️ {r}</div>' for r in data.get("risks", []))
    return f'''
    <div style="margin-bottom:20px;">
        <h4 style="color:{DIM_COLORS[dim]};">{DIM_ICONS[dim]} {DIM_LABELS[dim]}分析</h4>
        <b>关键发现:</b><ul>{items}</ul>
        {f"<b>风险点:</b>{risks}" if risks else ""}
    </div>'''

score_cards = '<div style="display:flex;gap:16px;flex-wrap:wrap;margin:20px 0;">' + "".join(score_card_html(d, analysis[d]) for d in dim_keys) + '</div>'

# 子维度详情（对齐 app.py：progress bar + 关键发现 + 风险，每维度一个折叠块）
def dim_detail_block(dim, data):
    color = DIM_COLORS[dim]
    icon = DIM_ICONS[dim]
    label = DIM_LABELS[dim]
    # progress bars for sub_scores
    bars = ""
    if "sub_scores" in data:
        for sub_name, sub_info in data["sub_scores"].items():
            pct = sub_info["score"]
            bars += f'''<div style="margin:6px 0;">
                <div style="display:flex;justify-content:space-between;font-size:13px;">
                    <span>{sub_name}: {sub_info["summary"]}</span><span><b>{pct}</b>分</span>
                </div>
                <div style="background:#e5e7eb;border-radius:4px;height:8px;margin-top:3px;">
                    <div style="background:{color};height:8px;border-radius:4px;width:{pct}%;"></div>
                </div>
            </div>'''
    # key findings
    findings = ""
    for f in data.get("key_findings", []):
        findings += f'<li style="margin:3px 0;font-size:13px;">{f}</li>'
    # risks
    risks = ""
    for r in data.get("risks", []):
        risks += f'<div style="background:#FEF3C7;border-left:3px solid #F59E0B;padding:8px 12px;margin:4px 0;border-radius:4px;font-size:13px;">⚠️ {r}</div>'
    return f'''
    <details style="margin-bottom:12px;border:1px solid #eee;border-radius:8px;padding:12px;" {"open" if dim == "fundamental" else ""}>
        <summary style="cursor:pointer;font-weight:600;color:{color};font-size:15px;">{icon} {label} ({data["score"]}分)</summary>
        <div style="margin-top:10px;">{bars}</div>
        <div style="margin-top:10px;"><b>📌 关键发现</b><ul style="padding-left:20px;">{findings}</ul></div>
        {f'<div style="margin-top:8px;"><b>⚠️ 风险点</b>{risks}</div>' if risks else ''}
    </details>'''

dim_detail_html = "".join(dim_detail_block(d, analysis[d]) for d in dim_keys)

tech_cards = "".join(f'<div style="flex:1;text-align:center;padding:12px;background:#f8f9fa;border-radius:8px;min-width:120px;"><div style="font-size:12px;color:#666;">{k}</div><div style="font-size:18px;font-weight:600;margin-top:4px;">{v}</div></div>' for k, v in tech_summary.items())

news_items = "".join(f'<div style="padding:10px 0;border-bottom:1px solid #eee;"><b>{n["date"][:10]}</b> · <span style="color:#888;">{n["source"]}</span><br>{n["title"]}</div>' for n in news_data.get("news", [])[:5])

# 权重进度条（对齐 app.py sidebar 的 st.progress 展示）
cur_weights = WEIGHT_PROFILES[period]
weight_bars_html = ""
for dim_key, w_val in cur_weights.items():
    pct = int(w_val * 100)
    weight_bars_html += f'''<div style="margin:8px 0;">
        <div style="font-size:13px;margin-bottom:3px;">{DIM_LABELS[dim_key]}: {pct}%</div>
        <div style="background:#e5e7eb;border-radius:4px;height:10px;">
            <div style="background:{DIM_COLORS[dim_key]};height:10px;border-radius:4px;width:{pct}%;"></div>
        </div>
    </div>'''

RATING_EMOJI = {"买入": "🟢", "增持": "🔵", "中性": "🟡", "减持": "🔴"}
def _report_item(r):
    tp = r.get("target_price")
    tp_str = f" | 目标价 ¥{tp}" if tp else ""
    rating = r.get("rating", "")
    emoji = RATING_EMOJI.get(rating, "⚪")
    return f'<div style="padding:8px 0;border-bottom:1px solid #eee;">{emoji} <b>{r.get("broker","")}</b> — {rating}{tp_str}<br><span style="font-size:13px;color:#666;">{r.get("title","")}</span></div>'
report_items = "".join(_report_item(r) for r in reports.get("reports", [])[:5])

compare_table = f'''
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
<tr style="background:#f0f0f0;"><th style="padding:10px;text-align:left;">指标</th><th style="padding:10px;text-align:center;">{stock_name}</th><th style="padding:10px;text-align:center;">{name_2}</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee;">综合评分</td><td style="text-align:center;font-weight:700;">{total_score}</td><td style="text-align:center;font-weight:700;">{total_2}</td></tr>
{"".join(f'<tr><td style="padding:8px;border-bottom:1px solid #eee;">{DIM_LABELS[d]}</td><td style="text-align:center;">{analysis[d]["score"]}</td><td style="text-align:center;">{analysis_2[d]["score"]}</td></tr>' for d in dim_keys)}
<tr><td style="padding:8px;">投资建议</td><td style="text-align:center;">{recommendation}</td><td style="text-align:center;">{rec_2}</td></tr>
</table>'''

winner = stock_name if total_score > total_2 else (name_2 if total_2 > total_score else "平局")
winner_text = f"🏆 综合最优：<b>{winner}</b>（{max(total_score, total_2)}分 vs {min(total_score, total_2)}分）" if winner != "平局" else "两者评分相同"

# 资金面摘要
flow_summary = flow_data.get("summary", {})
nb_trend_map = {"increasing": "📈 增持", "decreasing": "📉 减持", "stable": "➡️ 持平"}
nb_trend_cn = nb_trend_map.get(nb.get("trend", "stable"), "N/A")
flow_metrics = f'''
<div style="display:flex;gap:12px;flex-wrap:wrap;">
    <div style="flex:1;text-align:center;padding:16px;background:#f8f9fa;border-radius:8px;">
        <div style="font-size:12px;color:#666;">5日主力净流入</div>
        <div style="font-size:22px;font-weight:700;color:#EF4444;">{flow_summary.get("total_main_net_5d",0)/1e8:.2f} 亿</div>
    </div>
    <div style="flex:1;text-align:center;padding:16px;background:#f8f9fa;border-radius:8px;">
        <div style="font-size:12px;color:#666;">连续净流入</div>
        <div style="font-size:22px;font-weight:700;">{flow_summary.get("consecutive_inflow_days",0)} 天</div>
    </div>
    <div style="flex:1;text-align:center;padding:16px;background:#f8f9fa;border-radius:8px;">
        <div style="font-size:12px;color:#666;">北向持股比例</div>
        <div style="font-size:22px;font-weight:700;color:#3B82F6;">{nb.get("holding_ratio","N/A")}%</div>
    </div>
    <div style="flex:1;text-align:center;padding:16px;background:#f8f9fa;border-radius:8px;">
        <div style="font-size:12px;color:#666;">北向趋势</div>
        <div style="font-size:22px;font-weight:700;">{nb_trend_cn}</div>
    </div>
</div>'''


html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股分析 Agent — 可视化测试报告</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
  .metric-card {{ text-align: center; padding: 16px; }}
  .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .section h2 {{ font-size: 18px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #eee; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .grid-2-1 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
  .checklist {{ background: #f0fdf4; border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
  .checklist h2 {{ color: #166534; }}
  .check-item {{ padding: 8px 0; border-bottom: 1px solid #dcfce7; font-size: 14px; }}
  .check-item input {{ margin-right: 8px; }}
  .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
  .winner {{ background: #f0fdf4; border: 2px solid #10B981; padding: 16px; border-radius: 12px; text-align: center; font-size: 16px; }}
  @media (max-width: 768px) {{ .grid-2 {{ grid-template-columns: 1fr; }} .grid-4 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="section">
    <h1 style="font-size:24px;margin-bottom:4px;">📊 A股个股分析 Agent</h1>
    <div style="font-size:13px;color:#888;margin-bottom:16px;">Claude Agent SDK · 四维分析 · 可视化测试 · Mock 数据模式</div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:16px;">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;">
        <div class="metric-card">
            <div style="font-size:13px;color:#666;">{stock_name} ({stock_code})</div>
            <div style="font-size:36px;font-weight:700;">{total_score} 分</div>
            <div style="font-size:14px;color:#10B981;">▲ {recommendation}</div>
        </div>
        <div class="metric-card">
            <div style="font-size:13px;color:#666;">星级评定</div>
            <div style="font-size:28px;margin:8px 0;">{stars}</div>
            <div style="font-size:13px;color:#888;">配置：稳健 / 中线 / 全面分析</div>
        </div>
        <div class="metric-card">
            <div style="font-size:13px;color:#666;">最新价</div>
            <div style="font-size:36px;font-weight:700;">¥{quote_data["current_price"]:.2f}</div>
            <div style="font-size:14px;color:{"#EF4444" if quote_data["change_pct"] >= 0 else "#10B981"};">{quote_data["change_pct"]:+.2f}%</div>
        </div>
    </div>
</div>

<!-- 1. 四维评分卡 -->
<div class="section">
    <h2>四维评分</h2>
    {score_cards}
</div>

<!-- 2. 雷达图 + 子维度详情 -->
<div class="section">
    <h2>分析详情</h2>
    <div class="grid-2">
        <div>{charts["radar"]}</div>
        <div>{dim_detail_html}</div>
    </div>
</div>

<!-- 4. K线图 + 技术指标（同一section，对齐 app.py） -->
<div class="section">
    <h2>K线走势与技术指标</h2>
    {charts["kline"]}
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px;">{tech_cards}</div>
</div>

<!-- 6. 资金流向 -->
<div class="section">
    <h2>资金流向</h2>
    <div class="grid-2-1">
        <div>{charts["capital_flow"]}</div>
        <div>{flow_metrics}</div>
    </div>
</div>

<!-- 7. 新闻与研报 -->
<div class="section">
    <h2>新闻与公告</h2>
    <div class="grid-2">
        <div>
            <h3 style="font-size:15px;margin-bottom:12px;">📰 最新新闻</h3>
            {news_items}
        </div>
        <div>
            <h3 style="font-size:15px;margin-bottom:12px;">📋 券商研报</h3>
            {report_items}
            <div style="margin-top:16px;"><b>评级分布</b>{charts["rating_pie"]}</div>
        </div>
    </div>
</div>

<!-- 8. 当前权重配置（对齐 app.py 侧边栏） -->
<div class="section">
    <h2>当前权重配置（中线）</h2>
    {weight_bars_html}
    <div style="margin-top:16px;font-size:13px;color:#888;">
        切换投资周期会改变四维权重分配，从而影响综合评分。短线侧重技术面和资金面，长线侧重基本面和消息面。
    </div>
</div>

<!-- 9. 多股对比 -->
<div class="section">
    <h2>📊 多股对比</h2>
    {compare_table}
    <div class="grid-2">
        <div>{charts["compare_radar"]}</div>
        <div style="display:flex;align-items:center;"><div class="winner">{winner_text}</div></div>
    </div>
</div>

<!-- 10. 测试检查清单 -->
<div class="checklist">
    <h2>✅ 可视化测试检查清单</h2>
    <p style="font-size:13px;color:#666;margin-bottom:12px;">逐项确认以下功能点是否正确渲染：</p>
    <div class="check-item"><input type="checkbox"> 报告头部 — 综合评分 {total_score} 分、星级 {stars}、建议「{recommendation}」</div>
    <div class="check-item"><input type="checkbox"> 四维评分卡 — 4张卡片，分数在 0-100 范围内</div>
    <div class="check-item"><input type="checkbox"> 雷达图 — 四轴正确渲染，形状反映评分差异</div>
    <div class="check-item"><input type="checkbox"> 子维度柱状图 — 每维度4个子项，水平条正确</div>
    <div class="check-item"><input type="checkbox"> 关键发现 — 每维度列出3-4条发现</div>
    <div class="check-item"><input type="checkbox"> 风险提示 — 黄色警告框正确显示</div>
    <div class="check-item"><input type="checkbox"> K线图 — 红涨绿跌，MA5/MA20/MA60 三条均线</div>
    <div class="check-item"><input type="checkbox"> 成交量 — 底部柱状图颜色与K线涨跌一致</div>
    <div class="check-item"><input type="checkbox"> 技术指标 — 5个摘要卡片正确显示信号状态</div>
    <div class="check-item"><input type="checkbox"> 资金流向 — 柱状图红正绿负，数值合理</div>
    <div class="check-item"><input type="checkbox"> 北向资金 — 持股比例和趋势正确</div>
    <div class="check-item"><input type="checkbox"> 新闻列表 — 显示5条新闻标题+来源+日期</div>
    <div class="check-item"><input type="checkbox"> 研报评级 — 显示5条研报 + 评级饼图</div>
    <div class="check-item"><input type="checkbox"> 权重对比 — 三种周期评分差异合理（短线≠中线≠长线）</div>
    <div class="check-item"><input type="checkbox"> 多股对比 — 表格+双雷达图+择优结论</div>
    <div class="check-item"><input type="checkbox"> 响应式 — 缩小浏览器窗口，布局不破碎</div>
</div>

<div class="footer">
    ⚠️ 以上为 AI 辅助分析（Mock 数据），不构成投资建议。投资有风险，入市需谨慎。<br>
    A股分析 Agent · Claude Agent SDK · {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}
</div>

</div>
</body>
</html>'''

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visual_test_report.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Report generated: " + output_path)
print("File size: %.1f KB" % (os.path.getsize(output_path) / 1024))
print("Charts: %d main + %d sub" % (len(charts), len(sub_charts)))
