"""
Mock Tool 实现 — 使用 mock_data 替代真实 AKShare API
接口签名与 tool_definitions.py 完全一致，可直接替换
"""

import random
from typing import Optional

import pandas as pd

from tools.mock_data import MOCK_STOCK_LIST, MOCK_DATA, generate_klines


# ============================================================
# Tool 1: resolve_stock_code
# ============================================================

def resolve_stock_code(query: str) -> dict:
    """模糊匹配股票代码/名称"""
    matches = []

    # 精确匹配代码
    for s in MOCK_STOCK_LIST:
        if s["code"] == query:
            matches.append(_build_stock_info(s["code"], s["name"]))
            return {"status": "exact", "matches": matches}

    # 模糊匹配名称
    for s in MOCK_STOCK_LIST:
        if query in s["name"]:
            matches.append(_build_stock_info(s["code"], s["name"]))

    if len(matches) == 1:
        return {"status": "exact", "matches": matches}
    elif len(matches) > 1:
        return {"status": "multiple", "matches": matches}

    # 未找到
    suggestions = MOCK_STOCK_LIST[:3]
    suggestion_text = "、".join(f"{s['name']}({s['code']})" for s in suggestions)
    return {"status": "not_found", "matches": [], "suggestion": f"你是不是想说：{suggestion_text}？"}


def _build_stock_info(code: str, name: str) -> dict:
    market = "SH" if code.startswith(("6", "9")) else "SZ"
    if code.startswith("3"):
        board = "创业板"
    elif code.startswith("68"):
        board = "科创板"
    else:
        board = "主板"
    return {"stock_code": code, "stock_name": name, "market": market, "board": board}


# ============================================================
# Tool 2: get_stock_quote
# ============================================================

def get_stock_quote(stock_code: str, period: str = "daily", count: int = 120) -> dict:
    """获取历史K线（mock）"""
    data = MOCK_DATA.get(stock_code)
    if not data:
        return {"error": f"未找到 {stock_code} 的数据"}

    klines = generate_klines(data["base_price"], days=count + 40)[-count:]
    latest = klines[-1]
    prev = klines[-2] if len(klines) >= 2 else latest
    change_pct = round((latest["close"] - prev["close"]) / prev["close"] * 100, 2)

    return {
        "stock_code": stock_code,
        "period": period,
        "current_price": latest["close"],
        "change_pct": change_pct,
        "market_cap": int(latest["close"] * 1256200 * 100),  # 简化
        "klines": klines,
    }


# ============================================================
# Tool 3: get_financials
# ============================================================

def get_financials(stock_code: str, report_type: str = "all") -> dict:
    """获取财务指标（mock）"""
    data = MOCK_DATA.get(stock_code)
    if not data:
        return {"error": f"未找到 {stock_code} 的财务数据"}

    return {
        "stock_code": stock_code,
        "report_periods": ["2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"],
        "indicators": data["financials"],
        "quarterly_trend": data.get("quarterly_trend", []),
    }


# ============================================================
# Tool 4: calc_technical_indicators
# ============================================================

def calc_technical_indicators(stock_code: str, indicators: list = None, period: str = "daily") -> dict:
    """计算技术指标（mock，真实计算逻辑）"""
    if indicators is None:
        indicators = ["ma", "macd", "kdj", "rsi", "boll", "volume_ma"]

    quote = get_stock_quote(stock_code, period=period, count=300)
    if "error" in quote:
        return {"error": quote["error"]}

    klines = quote["klines"]
    closes = pd.Series([k["close"] for k in klines])
    highs = pd.Series([k["high"] for k in klines])
    lows = pd.Series([k["low"] for k in klines])
    volumes = pd.Series([k["volume"] for k in klines])

    result = {"stock_code": stock_code, "period": period, "calc_date": klines[-1]["date"]}

    if "ma" in indicators:
        ma_vals = {}
        for w in [5, 10, 20, 60, 120, 250]:
            if len(closes) >= w:
                ma_vals[f"ma{w}"] = round(closes.rolling(w).mean().iloc[-1], 2)
        ma_keys = [k for k in ["ma5", "ma10", "ma20", "ma60"] if k in ma_vals]
        if len(ma_keys) >= 3:
            vals = [ma_vals[k] for k in ma_keys]
            if all(vals[i] >= vals[i+1] for i in range(len(vals)-1)):
                ma_vals["alignment"] = "bullish"
            elif all(vals[i] <= vals[i+1] for i in range(len(vals)-1)):
                ma_vals["alignment"] = "bearish"
            else:
                ma_vals["alignment"] = "mixed"
        result["ma"] = ma_vals

    if "macd" in indicators:
        ema12 = closes.ewm(span=12).mean()
        ema26 = closes.ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        hist = (dif - dea) * 2
        signal = "bullish"
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            signal = "golden_cross"
        elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
            signal = "death_cross"
        elif dif.iloc[-1] < dea.iloc[-1]:
            signal = "bearish"
        result["macd"] = {
            "dif": round(dif.iloc[-1], 3), "dea": round(dea.iloc[-1], 3),
            "histogram": round(hist.iloc[-1], 3), "signal": signal, "divergence": None
        }

    if "kdj" in indicators:
        low_min = lows.rolling(9).min()
        high_max = highs.rolling(9).max()
        rsv = ((closes - low_min) / (high_max - low_min) * 100).fillna(50)
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        j = 3 * k - 2 * d
        zone = "overbought" if k.iloc[-1] > 80 else ("oversold" if k.iloc[-1] < 20 else "neutral")
        result["kdj"] = {"k": round(k.iloc[-1], 1), "d": round(d.iloc[-1], 1), "j": round(j.iloc[-1], 1), "zone": zone}

    if "rsi" in indicators:
        rsi_r = {}
        for w in [6, 14, 24]:
            delta = closes.diff()
            gain = delta.clip(lower=0).rolling(w).mean()
            loss = (-delta.clip(upper=0)).rolling(w).mean()
            rs = gain / loss
            rsi_r[f"rsi_{w}"] = round((100 - 100 / (1 + rs)).iloc[-1], 1)
        rsi14 = rsi_r.get("rsi_14", 50)
        rsi_r["zone"] = "overbought" if rsi14 > 70 else ("oversold" if rsi14 < 30 else "neutral")
        result["rsi"] = rsi_r

    if "boll" in indicators:
        mid = closes.rolling(20).mean()
        std = closes.rolling(20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std
        price = closes.iloc[-1]
        if price >= upper.iloc[-1]: pos = "upper_band"
        elif price >= mid.iloc[-1]: pos = "upper_half"
        elif price >= lower.iloc[-1]: pos = "lower_half"
        else: pos = "lower_band"
        result["boll"] = {
            "upper": round(upper.iloc[-1], 2), "middle": round(mid.iloc[-1], 2),
            "lower": round(lower.iloc[-1], 2), "position": pos,
        }

    if "volume_ma" in indicators:
        vol_ma5 = int(volumes.rolling(5).mean().iloc[-1])
        vol_ratio = round(volumes.iloc[-1] / vol_ma5, 2) if vol_ma5 else 0
        result["volume_ma"] = {"vol_ma5": vol_ma5, "vol_ratio": vol_ratio}

    return result


# ============================================================
# Tool 5: get_capital_flow
# ============================================================

def get_capital_flow(stock_code: str, days: int = 20) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    cf = data.get("capital_flow", {})
    flows = cf.get("daily_flows", [])
    main_nets = [d["main_net_inflow"] for d in flows]
    return {
        "stock_code": stock_code,
        "daily_flows": flows,
        "summary": {
            "total_main_net_5d": sum(main_nets[:5]),
            "total_main_net_20d": sum(main_nets),
            "consecutive_inflow_days": cf.get("consecutive_inflow_days", 0),
        },
    }


# ============================================================
# Tool 6: get_northbound_flow
# ============================================================

def get_northbound_flow(stock_code: str, days: int = 20) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    nb = data.get("northbound", {"is_eligible": False})
    return {"stock_code": stock_code, **nb}


# ============================================================
# Tool 7: get_margin_data
# ============================================================

def get_margin_data(stock_code: str, days: int = 20) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    mg = data.get("margin", {"is_eligible": False})
    return {"stock_code": stock_code, **mg}


# ============================================================
# Tool 8: get_news
# ============================================================

def get_news(stock_code: str, days: int = 7, limit: int = 20) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    news = data.get("news", [])[:limit]
    return {"stock_code": stock_code, "news_count": len(news), "news": news}


# ============================================================
# Tool 9: get_announcements
# ============================================================

def get_announcements(stock_code: str, days: int = 30, limit: int = 15) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    anns = data.get("announcements", [])[:limit]
    return {"stock_code": stock_code, "announcements": anns}


# ============================================================
# Tool 10: get_industry_comparison
# ============================================================

def get_industry_comparison(stock_code: str, metrics: list = None) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    return {
        "target_stock": stock_code,
        "industry": data.get("industry", ""),
        "peers": data.get("industry_peers", []),
        "industry_median": data.get("industry_median", {}),
    }


# ============================================================
# Tool 11: get_sector_top_stocks
# ============================================================

def get_sector_top_stocks(sector_name: str, top_n: int = 5) -> dict:
    stocks = [
        {"stock_code": s["code"], "stock_name": s["name"]}
        for s in MOCK_STOCK_LIST
        if MOCK_DATA.get(s["code"], {}).get("industry") == sector_name
    ][:top_n]
    return {"sector_name": sector_name, "stocks": stocks}


# ============================================================
# Tool 12: get_sector_news
# ============================================================

def get_sector_news(sector_name: str, days: int = 14) -> dict:
    return {
        "sector_name": sector_name,
        "news": [
            {"date": "2026-05-14", "title": f"国务院发布促消费若干措施，{sector_name}行业受益", "source": "新华社", "summary": "政策利好消费行业"},
            {"date": "2026-05-10", "title": f"{sector_name}板块景气度回升，机构看好下半年", "source": "中国证券报", "summary": "行业景气指数环比上升"},
        ],
        "policy_keywords": ["促消费", "内需", "扩大内需"],
    }


# ============================================================
# Tool 13: search_analyst_reports
# ============================================================

def search_analyst_reports(stock_code: str, limit: int = 10) -> dict:
    data = MOCK_DATA.get(stock_code, {})
    reports = data.get("analyst_reports", [])[:limit]
    ratings = {}
    for r in reports:
        rt = r.get("rating", "中性")
        ratings[rt] = ratings.get(rt, 0) + 1
    return {
        "stock_code": stock_code,
        "report_count": len(reports),
        "reports": reports,
        "rating_summary": ratings,
    }
