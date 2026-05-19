"""
Mock 数据层 — 用于本地验证 Agent 流程逻辑
提供贵州茅台(600519)和五粮液(000858)的模拟数据
"""

import random
from datetime import datetime, timedelta

# ============================================================
# 股票基础信息
# ============================================================

MOCK_STOCK_LIST = [
    {"code": "600519", "name": "贵州茅台"},
    {"code": "000858", "name": "五粮液"},
    {"code": "000568", "name": "泸州老窖"},
    {"code": "600809", "name": "山西汾酒"},
    {"code": "002304", "name": "洋河股份"},
    {"code": "000001", "name": "平安银行"},
    {"code": "600036", "name": "招商银行"},
    {"code": "300750", "name": "宁德时代"},
    {"code": "601318", "name": "中国平安"},
    {"code": "000333", "name": "美的集团"},
]


# ============================================================
# K线数据生成器
# ============================================================

def generate_klines(base_price: float, days: int = 120, volatility: float = 0.02):
    """生成模拟K线数据"""
    klines = []
    price = base_price
    base_date = datetime(2026, 5, 16)

    for i in range(days):
        date = base_date - timedelta(days=days - i)
        if date.weekday() >= 5:  # 跳过周末
            continue
        change = random.gauss(0.001, volatility)
        open_p = price
        close_p = price * (1 + change)
        high_p = max(open_p, close_p) * (1 + abs(random.gauss(0, 0.005)))
        low_p = min(open_p, close_p) * (1 - abs(random.gauss(0, 0.005)))
        volume = int(random.gauss(25000, 5000))
        amount = volume * close_p * 100

        klines.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume,
            "amount": round(amount, 0),
            "turnover_rate": round(random.uniform(0.3, 0.8), 2),
        })
        price = close_p

    return klines


# ============================================================
# 各 Tool 的 Mock 数据
# ============================================================

MOCK_DATA = {
    "600519": {
        "name": "贵州茅台",
        "base_price": 1825.0,
        "financials": {
            "roe": 30.2,
            "roe_diluted": 29.8,
            "gross_margin": 91.5,
            "net_margin": 52.3,
            "revenue": 150000000000,
            "revenue_yoy": 16.2,
            "net_profit": 78000000000,
            "net_profit_yoy": 18.5,
            "pe_ttm": 25.3,
            "pb": 8.1,
            "ps_ttm": 15.2,
            "peg": 1.1,
            "dividend_yield": 1.8,
            "debt_ratio": 25.3,
            "current_ratio": 3.8,
            "ocf_to_profit": 1.15,
            "goodwill_ratio": 0.0,
            "receivable_turnover_days": 12,
        },
        "quarterly_trend": [
            {"period": "2025Q4", "revenue_yoy": 16.2, "profit_yoy": 18.5, "gross_margin": 91.5, "roe": 30.2},
            {"period": "2025Q3", "revenue_yoy": 15.8, "profit_yoy": 17.2, "gross_margin": 91.3, "roe": 29.8},
            {"period": "2025Q2", "revenue_yoy": 17.1, "profit_yoy": 19.3, "gross_margin": 91.8, "roe": 30.5},
            {"period": "2025Q1", "revenue_yoy": 15.5, "profit_yoy": 16.8, "gross_margin": 91.2, "roe": 29.5},
        ],
        "capital_flow": {
            "daily_flows": [
                {"date": "2026-05-16", "main_net_inflow": 125000000, "main_net_ratio": 2.67},
                {"date": "2026-05-15", "main_net_inflow": 88000000, "main_net_ratio": 1.92},
                {"date": "2026-05-14", "main_net_inflow": 42000000, "main_net_ratio": 0.95},
                {"date": "2026-05-13", "main_net_inflow": -15000000, "main_net_ratio": -0.35},
                {"date": "2026-05-12", "main_net_inflow": 65000000, "main_net_ratio": 1.45},
                {"date": "2026-05-09", "main_net_inflow": -30000000, "main_net_ratio": -0.68},
                {"date": "2026-05-08", "main_net_inflow": 52000000, "main_net_ratio": 1.18},
            ],
            "consecutive_inflow_days": 3,
        },
        "northbound": {
            "is_eligible": True,
            "shares_held": 82000000,
            "holding_ratio": 8.2,
            "shares_change_5d": 1200000,
            "shares_change_20d": 3500000,
            "trend": "increasing",
        },
        "margin": {
            "is_eligible": True,
            "margin_buy_balance": 3500000000,
            "short_sell_balance": 120000000,
            "margin_balance_change_pct": 3.2,
        },
        "news": [
            {"date": "2026-05-15", "title": "贵州茅台一季度净利润同比增长18.5%，超市场预期", "source": "中国证券报", "summary": "公司公布2026年Q1报告，实现营收约420亿元，归母净利润约210亿元。"},
            {"date": "2026-05-13", "title": "茅台集团启动新一轮数字化转型战略", "source": "上海证券报", "summary": "茅台集团宣布投资50亿元推动数字化转型。"},
            {"date": "2026-05-12", "title": "白酒板块集体走强，消费复苏预期升温", "source": "新浪财经", "summary": "受益于促消费政策预期，白酒板块今日领涨两市。"},
            {"date": "2026-05-10", "title": "贵州茅台拟10亿元回购股份", "source": "巨潮资讯", "summary": "董事会通过回购方案，拟以不超过2000元/股回购公司股份。"},
            {"date": "2026-05-08", "title": "多家券商上调贵州茅台目标价至2000元以上", "source": "东方财富", "summary": "中信证券、华泰证券等上调目标价。"},
        ],
        "announcements": [
            {"date": "2026-05-10", "title": "关于回购公司股份方案的公告", "type": "临时公告"},
            {"date": "2026-05-08", "title": "2026年第一季度报告", "type": "定期报告"},
            {"date": "2026-04-25", "title": "2025年年度报告", "type": "定期报告"},
        ],
        "analyst_reports": [
            {"date": "2026-05-14", "broker": "中信证券", "title": "Q1超预期，上调目标价", "rating": "买入", "target_price": 2050},
            {"date": "2026-05-12", "broker": "华泰证券", "title": "业绩稳健增长，估值合理", "rating": "买入", "target_price": 2000},
            {"date": "2026-05-10", "broker": "招商证券", "title": "消费复苏确定性标的", "rating": "增持", "target_price": 1950},
            {"date": "2026-05-08", "broker": "国泰君安", "title": "龙头地位稳固，长期看好", "rating": "买入", "target_price": 2100},
            {"date": "2026-05-05", "broker": "海通证券", "title": "量价齐升趋势延续", "rating": "增持", "target_price": 1980},
        ],
        "industry": "白酒",
        "industry_peers": [
            {"code": "000858", "name": "五粮液", "pe_ttm": 18.5, "pb": 4.2, "roe": 22.1, "revenue_yoy": 12.3, "market_cap": 580000000000},
            {"code": "000568", "name": "泸州老窖", "pe_ttm": 20.1, "pb": 5.8, "roe": 21.3, "revenue_yoy": 14.5, "market_cap": 320000000000},
            {"code": "600809", "name": "山西汾酒", "pe_ttm": 28.3, "pb": 9.2, "roe": 26.8, "revenue_yoy": 20.1, "market_cap": 280000000000},
            {"code": "002304", "name": "洋河股份", "pe_ttm": 15.2, "pb": 3.1, "roe": 18.5, "revenue_yoy": 8.2, "market_cap": 180000000000},
        ],
        "industry_median": {"pe_ttm": 20.1, "pb": 4.8, "roe": 18.5, "revenue_yoy": 10.5, "profit_yoy": 12.0},
    },
    "000858": {
        "name": "五粮液",
        "base_price": 158.0,
        "financials": {
            "roe": 22.1,
            "gross_margin": 75.8,
            "net_margin": 37.5,
            "revenue_yoy": 12.3,
            "net_profit_yoy": 14.5,
            "pe_ttm": 18.5,
            "pb": 4.2,
            "peg": 0.85,
            "dividend_yield": 3.2,
            "debt_ratio": 28.5,
            "current_ratio": 3.2,
            "ocf_to_profit": 1.08,
            "goodwill_ratio": 0.5,
            "receivable_turnover_days": 18,
        },
        "quarterly_trend": [
            {"period": "2025Q4", "revenue_yoy": 12.3, "profit_yoy": 14.5, "gross_margin": 75.8, "roe": 22.1},
            {"period": "2025Q3", "revenue_yoy": 11.5, "profit_yoy": 13.2, "gross_margin": 75.2, "roe": 21.5},
        ],
        "capital_flow": {
            "daily_flows": [
                {"date": "2026-05-16", "main_net_inflow": 45000000, "main_net_ratio": 1.52},
                {"date": "2026-05-15", "main_net_inflow": -22000000, "main_net_ratio": -0.75},
                {"date": "2026-05-14", "main_net_inflow": 38000000, "main_net_ratio": 1.30},
                {"date": "2026-05-13", "main_net_inflow": 15000000, "main_net_ratio": 0.52},
                {"date": "2026-05-12", "main_net_inflow": -8000000, "main_net_ratio": -0.28},
            ],
            "consecutive_inflow_days": 1,
        },
        "northbound": {
            "is_eligible": True,
            "shares_held": 450000000,
            "holding_ratio": 5.8,
            "shares_change_5d": -200000,
            "trend": "stable",
        },
        "news": [
            {"date": "2026-05-14", "title": "五粮液发布股东回报规划，承诺提高分红比例", "source": "证券日报", "summary": "公司承诺未来三年分红比例不低于50%。"},
            {"date": "2026-05-11", "title": "五粮液经典装出厂价稳定，渠道库存处于低位", "source": "中国证券报", "summary": "渠道调研显示库存健康。"},
        ],
        "announcements": [
            {"date": "2026-05-08", "title": "2026年第一季度报告", "type": "定期报告"},
        ],
        "analyst_reports": [
            {"date": "2026-05-12", "broker": "中信证券", "title": "估值性价比突出", "rating": "买入", "target_price": 185},
            {"date": "2026-05-08", "broker": "广发证券", "title": "分红提升增强吸引力", "rating": "增持", "target_price": 175},
        ],
        "industry": "白酒",
    },
}
