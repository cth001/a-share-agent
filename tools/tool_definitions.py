"""
A股个股分析 Agent — MCP Tool 定义
基于 Claude Agent SDK 的 Tool 注册方式，底层数据源为 AKShare（主）+ Tushare（辅）

每个 Tool 函数包含：
  - 完整的参数和返回值类型注解
  - docstring 作为 Tool 的 description（Claude 会看到）
  - 数据获取 + 标准化处理逻辑
"""

import json
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd

# ============================================================
# Tool 1: resolve_stock_code — 股票代码解析与模糊匹配
# ============================================================

def resolve_stock_code(query: str) -> dict:
    """根据用户输入的股票代码或名称，匹配 A 股股票。
    支持完整代码（600519）、简称（茅台、贵州茅台）、拼音首字母（gzmt）。

    Args:
        query: 用户输入的股票代码或名称关键词

    Returns:
        {
            "status": "exact" | "multiple" | "not_found",
            "matches": [
                {
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                    "market": "SH",       # SH=沪市, SZ=深市
                    "board": "主板",       # 主板/创业板/科创板/北交所
                    "industry": "白酒"
                }
            ],
            "suggestion": "你是不是想说：贵州茅台(600519)？"  # 仅 not_found 时
        }
    """
    # 获取全量 A 股列表（建议启动时加载到内存缓存）
    try:
        stock_list = ak.stock_info_a_code_name()  # columns: [code, name]
    except Exception as e:
        return {"status": "error", "message": f"获取股票列表失败: {str(e)}"}

    matches = []

    # Step 1: 精确匹配代码
    exact_code = stock_list[stock_list["code"] == query]
    if not exact_code.empty:
        row = exact_code.iloc[0]
        matches.append(_build_stock_info(row["code"], row["name"]))
        return {"status": "exact", "matches": matches}

    # Step 2: 模糊匹配名称
    name_matches = stock_list[stock_list["name"].str.contains(query, na=False)]
    if len(name_matches) == 1:
        row = name_matches.iloc[0]
        matches.append(_build_stock_info(row["code"], row["name"]))
        return {"status": "exact", "matches": matches}
    elif len(name_matches) > 1:
        for _, row in name_matches.head(5).iterrows():
            matches.append(_build_stock_info(row["code"], row["name"]))
        return {"status": "multiple", "matches": matches}

    # Step 3: 未找到，尝试模糊建议
    # 简单编辑距离或拼音匹配（此处简化处理）
    suggestions = stock_list[stock_list["name"].str.contains(query[:2], na=False)].head(3)
    if not suggestions.empty:
        suggestion_text = "、".join(
            f"{r['name']}({r['code']})" for _, r in suggestions.iterrows()
        )
        return {"status": "not_found", "matches": [], "suggestion": f"你是不是想说：{suggestion_text}？"}

    return {"status": "not_found", "matches": [], "suggestion": "未找到匹配的股票，请检查输入。"}


def _build_stock_info(code: str, name: str) -> dict:
    """构建股票基本信息"""
    market = "SH" if code.startswith(("6", "9")) else "SZ"
    if code.startswith("3"):
        board = "创业板"
    elif code.startswith("68"):
        board = "科创板"
    elif code.startswith(("8", "4")):
        board = "北交所"
    else:
        board = "主板"
    return {
        "stock_code": code,
        "stock_name": name,
        "market": market,
        "board": board,
    }


# ============================================================
# Tool 2: get_stock_quote — 获取行情数据
# ============================================================

def get_stock_quote(
    stock_code: str,
    period: str = "daily",
    count: int = 120
) -> dict:
    """获取股票的历史 K 线行情数据，包含开高低收和成交量。

    Args:
        stock_code: 6位股票代码，如 "600519"
        period: K线周期，可选 "daily"(日线), "weekly"(周线), "monthly"(月线)
        count: 获取的 K 线数量，默认 120 根

    Returns:
        {
            "stock_code": "600519",
            "period": "daily",
            "current_price": 1825.0,
            "change_pct": 1.35,
            "market_cap": 2290000000000,     # 总市值（元）
            "float_market_cap": 2290000000000, # 流通市值
            "klines": [
                {
                    "date": "2026-05-16",
                    "open": 1810.0,
                    "high": 1832.0,
                    "low": 1805.0,
                    "close": 1825.0,
                    "volume": 25680,            # 手
                    "amount": 4680000000,        # 成交额（元）
                    "turnover_rate": 0.52        # 换手率 %
                }
            ]
        }
    """
    period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
    ak_period = period_map.get(period, "daily")

    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period=ak_period,
            start_date=(datetime.now() - timedelta(days=count * 2)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq"  # 前复权
        )
        df = df.tail(count)
    except Exception as e:
        return {"error": f"获取行情数据失败: {str(e)}"}

    klines = []
    for _, row in df.iterrows():
        klines.append({
            "date": str(row["日期"]),
            "open": float(row["开盘"]),
            "high": float(row["最高"]),
            "low": float(row["最低"]),
            "close": float(row["收盘"]),
            "volume": int(row["成交量"]),
            "amount": float(row["成交额"]),
            "turnover_rate": float(row.get("换手率", 0)),
        })

    latest = klines[-1] if klines else {}
    prev_close = klines[-2]["close"] if len(klines) >= 2 else latest.get("close", 0)
    change_pct = round((latest["close"] - prev_close) / prev_close * 100, 2) if prev_close else 0

    return {
        "stock_code": stock_code,
        "period": period,
        "current_price": latest.get("close"),
        "change_pct": change_pct,
        "klines": klines,
    }


# ============================================================
# Tool 3: get_financials — 获取财务数据
# ============================================================

def get_financials(
    stock_code: str,
    report_type: str = "all"
) -> dict:
    """获取股票的财务数据，包含核心财务指标和三大报表摘要。

    Args:
        stock_code: 6位股票代码
        report_type: 报表类型
            - "all": 全部（核心指标 + 三大报表摘要）
            - "indicators": 仅核心财务指标
            - "income": 利润表
            - "balance": 资产负债表
            - "cashflow": 现金流量表

    Returns:
        {
            "stock_code": "600519",
            "report_periods": ["2025-12-31", "2025-09-30", ...],
            "indicators": {
                "roe": 30.2,                   # 净资产收益率 %
                "roe_diluted": 29.8,
                "gross_margin": 91.5,          # 毛利率 %
                "net_margin": 52.3,            # 净利率 %
                "revenue": 150000000000,       # 营业收入（元）
                "revenue_yoy": 16.2,           # 营收同比 %
                "net_profit": 78000000000,     # 归母净利润（元）
                "net_profit_yoy": 18.5,        # 净利润同比 %
                "pe_ttm": 25.3,
                "pb": 8.1,
                "ps_ttm": 15.2,
                "peg": 1.1,
                "dividend_yield": 1.8,
                "debt_ratio": 25.3,            # 资产负债率 %
                "current_ratio": 3.8,          # 流动比率
                "ocf_to_profit": 1.15,         # 经营现金流/净利润
                "goodwill_ratio": 0.0,         # 商誉/净资产 %
                "receivable_turnover_days": 12, # 应收账款周转天数
            },
            "quarterly_trend": [
                {
                    "period": "2025Q4",
                    "revenue_yoy": 16.2,
                    "profit_yoy": 18.5,
                    "gross_margin": 91.5,
                    "roe": 30.2
                }
            ],
            "income_summary": { ... },
            "balance_summary": { ... },
            "cashflow_summary": { ... }
        }
    """
    result = {"stock_code": stock_code}

    try:
        # 核心财务指标
        indicator_df = ak.stock_financial_analysis_indicator(symbol=stock_code)
        if not indicator_df.empty:
            latest = indicator_df.iloc[0]
            result["indicators"] = {
                "roe": _safe_float(latest.get("净资产收益率(%)")),
                "gross_margin": _safe_float(latest.get("销售毛利率(%)")),
                "net_margin": _safe_float(latest.get("销售净利率(%)")),
                "debt_ratio": _safe_float(latest.get("资产负债率(%)")),
                "current_ratio": _safe_float(latest.get("流动比率")),
            }

            # 近4季趋势
            quarterly = []
            for i in range(min(4, len(indicator_df))):
                row = indicator_df.iloc[i]
                quarterly.append({
                    "period": str(row.get("日期", "")),
                    "roe": _safe_float(row.get("净资产收益率(%)")),
                    "gross_margin": _safe_float(row.get("销售毛利率(%)")),
                })
            result["quarterly_trend"] = quarterly

    except Exception as e:
        result["error"] = f"获取财务数据失败: {str(e)}"

    return result


# ============================================================
# Tool 4: calc_technical_indicators — 计算技术指标
# ============================================================

def calc_technical_indicators(
    stock_code: str,
    indicators: list[str] = None,
    period: str = "daily"
) -> dict:
    """计算股票的技术分析指标。

    Args:
        stock_code: 6位股票代码
        indicators: 需要计算的指标列表，可选：
            ["ma", "macd", "kdj", "rsi", "boll", "volume_ma"]
            默认全部计算
        period: K线周期 "daily" | "weekly"

    Returns:
        {
            "stock_code": "600519",
            "period": "daily",
            "calc_date": "2026-05-16",
            "ma": {
                "ma5": 1810.5, "ma10": 1798.3, "ma20": 1785.3,
                "ma60": 1750.2, "ma120": 1720.8, "ma250": 1680.5,
                "alignment": "bullish"  # bullish/bearish/mixed
            },
            "macd": {
                "dif": 15.3, "dea": 12.1, "histogram": 3.2,
                "signal": "golden_cross",  # golden_cross/death_cross/bullish/bearish
                "divergence": null         # "top_divergence"/"bottom_divergence"/null
            },
            "kdj": {
                "k": 82.5, "d": 75.3, "j": 96.9,
                "zone": "overbought"  # overbought/oversold/neutral
            },
            "rsi": {
                "rsi_6": 68.5, "rsi_14": 62.1, "rsi_24": 58.3,
                "zone": "neutral"
            },
            "boll": {
                "upper": 1890.5, "middle": 1790.2, "lower": 1689.9,
                "width": 200.6,
                "position": "upper_half",  # upper_band/upper_half/middle/lower_half/lower_band
                "squeeze": false           # 布林带收口
            },
            "volume_ma": {
                "vol_ma5": 28500, "vol_ma10": 26300,
                "vol_ratio": 1.35,         # 当日量 / MA5量
                "volume_trend": "increasing"  # increasing/decreasing/stable
            }
        }
    """
    if indicators is None:
        indicators = ["ma", "macd", "kdj", "rsi", "boll", "volume_ma"]

    # 获取足够多的K线用于计算（至少250根）
    quote = get_stock_quote(stock_code, period=period, count=300)
    if "error" in quote:
        return {"error": quote["error"]}

    klines = quote["klines"]
    if len(klines) < 30:
        return {"error": "K线数据不足，无法计算技术指标"}

    closes = pd.Series([k["close"] for k in klines])
    highs = pd.Series([k["high"] for k in klines])
    lows = pd.Series([k["low"] for k in klines])
    volumes = pd.Series([k["volume"] for k in klines])

    result = {
        "stock_code": stock_code,
        "period": period,
        "calc_date": klines[-1]["date"],
    }

    # MA 均线
    if "ma" in indicators:
        ma_values = {}
        for window in [5, 10, 20, 60, 120, 250]:
            if len(closes) >= window:
                ma_values[f"ma{window}"] = round(closes.rolling(window).mean().iloc[-1], 2)
        # 判断均线排列
        ma_keys = [k for k in ["ma5", "ma10", "ma20", "ma60"] if k in ma_values]
        if len(ma_keys) >= 3:
            vals = [ma_values[k] for k in ma_keys]
            if all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)):
                ma_values["alignment"] = "bullish"
            elif all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)):
                ma_values["alignment"] = "bearish"
            else:
                ma_values["alignment"] = "mixed"
        result["ma"] = ma_values

    # MACD
    if "macd" in indicators:
        ema12 = closes.ewm(span=12).mean()
        ema26 = closes.ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        histogram = (dif - dea) * 2

        macd_result = {
            "dif": round(dif.iloc[-1], 3),
            "dea": round(dea.iloc[-1], 3),
            "histogram": round(histogram.iloc[-1], 3),
        }
        # 金叉/死叉判断
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            macd_result["signal"] = "golden_cross"
        elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
            macd_result["signal"] = "death_cross"
        elif dif.iloc[-1] > dea.iloc[-1]:
            macd_result["signal"] = "bullish"
        else:
            macd_result["signal"] = "bearish"
        macd_result["divergence"] = None  # 背离检测需更复杂逻辑，此处占位
        result["macd"] = macd_result

    # KDJ
    if "kdj" in indicators:
        low_min = lows.rolling(9).min()
        high_max = highs.rolling(9).max()
        rsv = (closes - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        j = 3 * k - 2 * d
        zone = "overbought" if k.iloc[-1] > 80 else ("oversold" if k.iloc[-1] < 20 else "neutral")
        result["kdj"] = {
            "k": round(k.iloc[-1], 1),
            "d": round(d.iloc[-1], 1),
            "j": round(j.iloc[-1], 1),
            "zone": zone,
        }

    # RSI
    if "rsi" in indicators:
        rsi_result = {}
        for w in [6, 14, 24]:
            delta = closes.diff()
            gain = delta.clip(lower=0).rolling(w).mean()
            loss = (-delta.clip(upper=0)).rolling(w).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_result[f"rsi_{w}"] = round(rsi.iloc[-1], 1)
        rsi_14 = rsi_result.get("rsi_14", 50)
        rsi_result["zone"] = "overbought" if rsi_14 > 70 else ("oversold" if rsi_14 < 30 else "neutral")
        result["rsi"] = rsi_result

    # 布林带
    if "boll" in indicators:
        mid = closes.rolling(20).mean()
        std = closes.rolling(20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std
        price = closes.iloc[-1]
        width = upper.iloc[-1] - lower.iloc[-1]

        if price >= upper.iloc[-1]:
            position = "upper_band"
        elif price >= mid.iloc[-1]:
            position = "upper_half"
        elif price >= lower.iloc[-1]:
            position = "lower_half"
        else:
            position = "lower_band"

        # 布林带收口检测
        prev_width = (upper.iloc[-20] - lower.iloc[-20]) if len(upper) >= 20 else width
        squeeze = width < prev_width * 0.6

        result["boll"] = {
            "upper": round(upper.iloc[-1], 2),
            "middle": round(mid.iloc[-1], 2),
            "lower": round(lower.iloc[-1], 2),
            "width": round(width, 2),
            "position": position,
            "squeeze": bool(squeeze),
        }

    # 成交量均线
    if "volume_ma" in indicators:
        vol_ma5 = int(volumes.rolling(5).mean().iloc[-1])
        vol_ma10 = int(volumes.rolling(10).mean().iloc[-1])
        vol_ratio = round(volumes.iloc[-1] / vol_ma5, 2) if vol_ma5 > 0 else 0
        # 量能趋势
        recent_vols = volumes.tail(5).tolist()
        if all(recent_vols[i] <= recent_vols[i + 1] for i in range(len(recent_vols) - 1)):
            vol_trend = "increasing"
        elif all(recent_vols[i] >= recent_vols[i + 1] for i in range(len(recent_vols) - 1)):
            vol_trend = "decreasing"
        else:
            vol_trend = "stable"
        result["volume_ma"] = {
            "vol_ma5": vol_ma5,
            "vol_ma10": vol_ma10,
            "vol_ratio": vol_ratio,
            "volume_trend": vol_trend,
        }

    return result


# ============================================================
# Tool 5: get_capital_flow — 主力资金流向
# ============================================================

def get_capital_flow(stock_code: str, days: int = 20) -> dict:
    """获取个股的主力资金净流入/流出数据。

    Args:
        stock_code: 6位股票代码
        days: 获取最近多少个交易日的数据，默认 20

    Returns:
        {
            "stock_code": "600519",
            "daily_flows": [
                {
                    "date": "2026-05-16",
                    "main_net_inflow": 125000000,       # 主力净流入（元）
                    "super_large_net": 80000000,         # 超大单净流入
                    "large_net": 45000000,               # 大单净流入
                    "medium_net": -20000000,             # 中单净流入
                    "small_net": -105000000,             # 小单净流入
                    "main_net_ratio": 2.67               # 主力净流入占成交额 %
                }
            ],
            "summary": {
                "total_main_net_5d": 250000000,
                "total_main_net_10d": 380000000,
                "total_main_net_20d": 580000000,
                "consecutive_inflow_days": 3,
                "avg_daily_main_net": 29000000,
                "super_large_ratio": 0.65                # 超大单占主力流入比
            }
        }
    """
    try:
        df = ak.stock_individual_fund_flow(stock=stock_code, market="sh" if stock_code.startswith("6") else "sz")
        df = df.tail(days)
    except Exception as e:
        return {"error": f"获取资金流向失败: {str(e)}"}

    daily_flows = []
    for _, row in df.iterrows():
        daily_flows.append({
            "date": str(row.get("日期", "")),
            "main_net_inflow": _safe_float(row.get("主力净流入-净额")),
            "main_net_ratio": _safe_float(row.get("主力净流入-净占比")),
        })

    # 计算汇总
    main_nets = [d["main_net_inflow"] for d in daily_flows if d["main_net_inflow"] is not None]
    consecutive = 0
    for v in reversed(main_nets):
        if v > 0:
            consecutive += 1
        else:
            break

    summary = {
        "total_main_net_5d": sum(main_nets[-5:]) if len(main_nets) >= 5 else sum(main_nets),
        "total_main_net_10d": sum(main_nets[-10:]) if len(main_nets) >= 10 else sum(main_nets),
        "total_main_net_20d": sum(main_nets),
        "consecutive_inflow_days": consecutive,
    }

    return {
        "stock_code": stock_code,
        "daily_flows": daily_flows,
        "summary": summary,
    }


# ============================================================
# Tool 6: get_northbound_flow — 北向资金
# ============================================================

def get_northbound_flow(stock_code: str, days: int = 20) -> dict:
    """获取个股的北向资金（沪股通/深股通）持仓变动数据。

    Args:
        stock_code: 6位股票代码
        days: 获取最近多少个交易日的数据

    Returns:
        {
            "stock_code": "600519",
            "is_eligible": true,    # 是否为陆股通标的
            "holding_data": [
                {
                    "date": "2026-05-16",
                    "shares_held": 82000000,         # 持股数量
                    "holding_ratio": 8.2,            # 占流通股比 %
                    "shares_change": 120000,         # 日变动
                    "market_value": 149650000000     # 持仓市值（元）
                }
            ],
            "summary": {
                "shares_change_5d": 1200000,
                "shares_change_20d": 3500000,
                "holding_ratio_current": 8.2,
                "holding_ratio_20d_ago": 7.9,
                "trend": "increasing"   # increasing/decreasing/stable
            }
        }
    """
    try:
        df = ak.stock_hsgt_individual_em(symbol=stock_code)
        if df.empty:
            return {"stock_code": stock_code, "is_eligible": False}
        df = df.tail(days)
    except Exception:
        return {"stock_code": stock_code, "is_eligible": False}

    holding_data = []
    for _, row in df.iterrows():
        holding_data.append({
            "date": str(row.get("日期", "")),
            "shares_held": _safe_int(row.get("持股数量")),
            "holding_ratio": _safe_float(row.get("持股占比")),
        })

    return {
        "stock_code": stock_code,
        "is_eligible": True,
        "holding_data": holding_data,
    }


# ============================================================
# Tool 7: get_margin_data — 融资融券
# ============================================================

def get_margin_data(stock_code: str, days: int = 20) -> dict:
    """获取个股融资融券数据。

    Args:
        stock_code: 6位股票代码
        days: 获取最近多少个交易日的数据

    Returns:
        {
            "stock_code": "600519",
            "is_eligible": true,
            "margin_data": [
                {
                    "date": "2026-05-16",
                    "margin_buy_balance": 3500000000,    # 融资余额（元）
                    "short_sell_balance": 120000000,      # 融券余额（元）
                    "margin_net_buy": 50000000,           # 融资净买入（元）
                    "long_short_ratio": 29.2              # 融资/融券比
                }
            ]
        }
    """
    try:
        df = ak.stock_margin_detail_szse(date=datetime.now().strftime("%Y%m%d"))
        stock_data = df[df["证券代码"] == stock_code]
        if stock_data.empty:
            return {"stock_code": stock_code, "is_eligible": False}
    except Exception:
        return {"stock_code": stock_code, "is_eligible": False}

    # 简化返回结构
    return {
        "stock_code": stock_code,
        "is_eligible": True,
        "margin_data": [],  # 实际实现需按日期循环获取
    }


# ============================================================
# Tool 8: get_news — 获取新闻
# ============================================================

def get_news(
    stock_code: str,
    days: int = 7,
    limit: int = 20
) -> dict:
    """获取与指定股票相关的新闻列表。

    Args:
        stock_code: 6位股票代码
        days: 获取最近多少天的新闻
        limit: 最多返回条数

    Returns:
        {
            "stock_code": "600519",
            "news_count": 15,
            "news": [
                {
                    "date": "2026-05-16",
                    "title": "贵州茅台一季度净利润同比增长18%",
                    "source": "新浪财经",
                    "url": "https://...",
                    "summary": "公司公布2026年第一季度报告..."
                }
            ]
        }
    """
    try:
        df = ak.stock_news_em(symbol=stock_code)
        df = df.head(limit)
    except Exception as e:
        return {"error": f"获取新闻失败: {str(e)}"}

    news_list = []
    for _, row in df.iterrows():
        news_list.append({
            "date": str(row.get("发布时间", "")),
            "title": str(row.get("新闻标题", "")),
            "source": str(row.get("文章来源", "")),
            "url": str(row.get("新闻链接", "")),
            "summary": str(row.get("新闻内容", ""))[:200],  # 截取前200字
        })

    return {
        "stock_code": stock_code,
        "news_count": len(news_list),
        "news": news_list,
    }


# ============================================================
# Tool 9: get_industry_comparison — 行业对比
# ============================================================

def get_industry_comparison(
    stock_code: str,
    metrics: list[str] = None
) -> dict:
    """获取同行业可比公司的关键指标对比数据。

    Args:
        stock_code: 6位股票代码
        metrics: 对比指标列表，默认 ["pe", "pb", "roe", "revenue_yoy", "profit_yoy"]

    Returns:
        {
            "target_stock": "600519",
            "industry": "白酒",
            "peers": [
                {
                    "stock_code": "000858",
                    "stock_name": "五粮液",
                    "pe_ttm": 18.5,
                    "pb": 4.2,
                    "roe": 22.1,
                    "revenue_yoy": 12.3,
                    "profit_yoy": 14.5,
                    "market_cap": 580000000000
                }
            ],
            "industry_median": {
                "pe_ttm": 20.1,
                "pb": 4.8,
                "roe": 18.5,
                "revenue_yoy": 10.5,
                "profit_yoy": 12.0
            },
            "target_rank": {
                "pe_ttm": "3/12",
                "roe": "1/12"
            }
        }
    """
    # 获取行业成分股 + 财务指标（简化骨架）
    try:
        industry_df = ak.stock_board_industry_cons_em(symbol="白酒")  # 需动态获取行业
        # 实际实现：遍历成分股获取财务指标
    except Exception as e:
        return {"error": f"获取行业对比数据失败: {str(e)}"}

    return {
        "target_stock": stock_code,
        "industry": "",
        "peers": [],
        "industry_median": {},
    }


# ============================================================
# Tool 10: get_sector_top_stocks — 板块龙头股
# ============================================================

def get_sector_top_stocks(
    sector_name: str,
    top_n: int = 5
) -> dict:
    """获取指定板块/行业内市值最大的 N 只股票。
    用于用户提出板块级问题时推荐对比标的。

    Args:
        sector_name: 板块/行业名称，如 "白酒"、"新能源"、"半导体"
        top_n: 返回前 N 只，默认 5

    Returns:
        {
            "sector_name": "白酒",
            "stocks": [
                {
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                    "market_cap": 2290000000000,
                    "pe_ttm": 25.3,
                    "change_pct_ytd": 12.5
                }
            ]
        }
    """
    try:
        df = ak.stock_board_industry_cons_em(symbol=sector_name)
        # 按市值排序取 Top N（实际实现需补充市值字段）
        df = df.head(top_n)
    except Exception as e:
        return {"error": f"获取板块数据失败: {str(e)}"}

    stocks = []
    for _, row in df.iterrows():
        stocks.append({
            "stock_code": str(row.get("代码", "")),
            "stock_name": str(row.get("名称", "")),
        })

    return {
        "sector_name": sector_name,
        "stocks": stocks,
    }


# ============================================================
# Tool 11: get_announcements — 公司公告
# ============================================================

def get_announcements(
    stock_code: str,
    days: int = 30,
    limit: int = 15
) -> dict:
    """获取上市公司最近的公告列表。

    Args:
        stock_code: 6位股票代码
        days: 获取最近多少天的公告
        limit: 最多返回条数

    Returns:
        {
            "stock_code": "600519",
            "announcements": [
                {
                    "date": "2026-05-10",
                    "title": "2026年第一季度报告",
                    "type": "定期报告",
                    "url": "https://..."
                }
            ]
        }
    """
    try:
        df = ak.stock_notice_report(symbol=stock_code)
        df = df.head(limit)
    except Exception as e:
        return {"error": f"获取公告失败: {str(e)}"}

    announcements = []
    for _, row in df.iterrows():
        announcements.append({
            "date": str(row.get("公告日期", "")),
            "title": str(row.get("公告标题", "")),
            "url": str(row.get("公告链接", "")),
        })

    return {
        "stock_code": stock_code,
        "announcements": announcements,
    }


# ============================================================
# Tool 12: get_sector_news — 行业/板块新闻
# ============================================================

def get_sector_news(sector_name: str, days: int = 14) -> dict:
    """获取指定行业/板块的政策新闻和行业动态。

    Args:
        sector_name: 行业/板块名称，如 "白酒"、"新能源"、"半导体"
        days: 获取最近多少天的新闻

    Returns:
        {
            "sector_name": "白酒",
            "news": [
                {
                    "date": "2026-05-14",
                    "title": "国务院发布促消费若干措施",
                    "source": "新华社",
                    "summary": "...",
                    "impact": "positive"
                }
            ],
            "policy_keywords": ["促消费", "内需", "扩大内需"]
        }
    """
    try:
        df = ak.stock_board_industry_info_em(symbol=sector_name)
        # AKShare 的行业新闻接口有限，实际部署可接入新闻搜索 API 补充
    except Exception:
        pass

    # 备选：用通用新闻接口按关键词搜索
    try:
        df = ak.stock_news_em(symbol=sector_name)
        df = df.head(15)
    except Exception as e:
        return {"error": f"获取行业新闻失败: {str(e)}"}

    news_list = []
    for _, row in df.iterrows():
        news_list.append({
            "date": str(row.get("发布时间", "")),
            "title": str(row.get("新闻标题", "")),
            "source": str(row.get("文章来源", "")),
            "summary": str(row.get("新闻内容", ""))[:200],
        })

    return {
        "sector_name": sector_name,
        "news": news_list,
    }


# ============================================================
# Tool 13: search_analyst_reports — 券商研报搜索
# ============================================================

def search_analyst_reports(stock_code: str, limit: int = 10) -> dict:
    """搜索券商对指定股票的研究报告摘要和评级。

    Args:
        stock_code: 6位股票代码
        limit: 最多返回条数，默认 10

    Returns:
        {
            "stock_code": "600519",
            "report_count": 8,
            "reports": [
                {
                    "date": "2026-05-12",
                    "broker": "中信证券",
                    "title": "Q1超预期，维持买入评级",
                    "rating": "买入",
                    "target_price": 1950.0,
                    "analyst": "张三"
                }
            ],
            "rating_summary": {
                "buy": 6,
                "overweight": 2,
                "neutral": 0,
                "underweight": 0,
                "sell": 0
            }
        }
    """
    try:
        df = ak.stock_analyst_detail_em(symbol=stock_code)
        df = df.head(limit)
    except Exception as e:
        return {"error": f"获取研报数据失败: {str(e)}"}

    reports = []
    for _, row in df.iterrows():
        reports.append({
            "date": str(row.get("日期", "")),
            "broker": str(row.get("券商", "")),
            "title": str(row.get("标题", "")),
            "rating": str(row.get("评级", "")),
        })

    return {
        "stock_code": stock_code,
        "report_count": len(reports),
        "reports": reports,
    }


# ============================================================
# Utility functions
# ============================================================

def _safe_float(val, default=None) -> Optional[float]:
    """安全转换为 float"""
    try:
        return round(float(val), 4)
    except (TypeError, ValueError):
        return default

def _safe_int(val, default=None) -> Optional[int]:
    """安全转换为 int"""
    try:
        return int(val)
    except (TypeError, ValueError):
        return default
