"""
A股个股分析 Agent — 编排入口
基于 Claude Agent SDK 构建 Orchestrator + 4 Sub-Agent 架构

目录结构:
  a-share-agent/
  ├── main.py                      ← 本文件（入口 + Agent 编排）
  ├── prompts/
  │   ├── orchestrator.md          ← 主控 Agent Prompt
  │   ├── fundamental_agent.md     ← 基本面子 Agent Prompt
  │   ├── technical_agent.md       ← 技术面子 Agent Prompt
  │   ├── capital_flow_agent.md    ← 资金面子 Agent Prompt
  │   └── sentiment_agent.md       ← 消息面子 Agent Prompt
  └── tools/
      └── tool_definitions.py      ← MCP Tool 实现
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # 从 .env 文件加载环境变量（如 ANTHROPIC_API_KEY）

import anthropic
from anthropic import Anthropic

from tools.tool_definitions import (
    resolve_stock_code,
    get_stock_quote,
    get_financials,
    calc_technical_indicators,
    get_capital_flow,
    get_northbound_flow,
    get_margin_data,
    get_news,
    get_announcements,
    get_industry_comparison,
    get_sector_top_stocks,
    get_sector_news,
    search_analyst_reports,
)

# ============================================================
# 配置
# ============================================================

MODEL = "claude-sonnet-4-20250514"
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(filename: str) -> str:
    """加载 prompt 文件"""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


# ============================================================
# Tool Schema 定义（Claude API Tool Use 格式）
# ============================================================

TOOL_SCHEMAS = [
    {
        "name": "resolve_stock_code",
        "description": "根据用户输入的股票代码或名称，模糊匹配A股股票。支持代码、简称、拼音首字母。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户输入的股票代码或名称关键词，如 '600519'、'茅台'、'贵州茅台'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_stock_quote",
        "description": "获取股票历史K线行情数据，包含开高低收、成交量和换手率。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码，如 '600519'"},
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"],
                    "description": "K线周期，默认 daily"
                },
                "count": {"type": "integer", "description": "获取K线数量，默认 120"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_financials",
        "description": "获取股票核心财务指标和三大报表摘要（利润表、资产负债表、现金流量表）。包含ROE、毛利率、净利率、营收增速、负债率等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "report_type": {
                    "type": "string",
                    "enum": ["all", "indicators", "income", "balance", "cashflow"],
                    "description": "报表类型，默认 all"
                }
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "calc_technical_indicators",
        "description": "计算股票技术指标，包含均线(MA)、MACD、KDJ、RSI、布林带(BOLL)、量能均线。返回指标数值和信号判断（金叉/死叉、超买/超卖、均线排列等）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "indicators": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["ma", "macd", "kdj", "rsi", "boll", "volume_ma"]},
                    "description": "需要计算的指标列表，默认全部"
                },
                "period": {"type": "string", "enum": ["daily", "weekly"], "description": "K线周期"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_capital_flow",
        "description": "获取个股主力资金净流入/流出数据，包含超大单、大单、中单、小单拆分，以及连续流入天数等汇总。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "days": {"type": "integer", "description": "最近多少个交易日，默认 20"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_northbound_flow",
        "description": "获取个股北向资金（沪股通/深股通）持仓数据，包含持股数量、占比和变动趋势。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "days": {"type": "integer", "description": "最近多少个交易日，默认 20"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_margin_data",
        "description": "获取个股融资融券数据，包含融资余额、融券余额和融资融券比。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "days": {"type": "integer", "description": "最近多少个交易日，默认 20"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_news",
        "description": "获取个股相关新闻列表，包含标题、来源、日期和摘要。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "days": {"type": "integer", "description": "最近多少天，默认 7"},
                "limit": {"type": "integer", "description": "最多返回条数，默认 20"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_announcements",
        "description": "获取上市公司最近的公告列表，包含定期报告、临时公告等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "days": {"type": "integer", "description": "最近多少天，默认 30"},
                "limit": {"type": "integer", "description": "最多返回条数，默认 15"}
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_industry_comparison",
        "description": "获取同行业可比公司的关键指标对比（PE、PB、ROE、增速等），包含行业中位数和排名。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "对比指标列表"
                }
            },
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_sector_top_stocks",
        "description": "获取指定板块/行业内市值最大的股票列表，用于板块级分析时推荐对比标的。",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector_name": {"type": "string", "description": "板块名称，如 '白酒'、'新能源'"},
                "top_n": {"type": "integer", "description": "返回前N只，默认 5"}
            },
            "required": ["sector_name"]
        }
    },
    {
        "name": "get_sector_news",
        "description": "获取指定行业/板块的政策新闻和行业动态，用于分析行业政策环境。",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector_name": {"type": "string", "description": "行业/板块名称，如 '白酒'、'新能源'"},
                "days": {"type": "integer", "description": "最近多少天，默认 14"}
            },
            "required": ["sector_name"]
        }
    },
    {
        "name": "search_analyst_reports",
        "description": "搜索券商对指定股票的研究报告摘要和评级，包含评级分布、目标价和分析师信息。",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock_code": {"type": "string", "description": "6位股票代码"},
                "limit": {"type": "integer", "description": "最多返回条数，默认 10"}
            },
            "required": ["stock_code"]
        }
    },
]

# Tool 名称 → 函数映射
TOOL_FUNCTIONS = {
    "resolve_stock_code": resolve_stock_code,
    "get_stock_quote": get_stock_quote,
    "get_financials": get_financials,
    "calc_technical_indicators": calc_technical_indicators,
    "get_capital_flow": get_capital_flow,
    "get_northbound_flow": get_northbound_flow,
    "get_margin_data": get_margin_data,
    "get_news": get_news,
    "get_announcements": get_announcements,
    "get_industry_comparison": get_industry_comparison,
    "get_sector_top_stocks": get_sector_top_stocks,
    "get_sector_news": get_sector_news,
    "search_analyst_reports": search_analyst_reports,
}


# ============================================================
# Sub-Agent 定义
# ============================================================

# 每个子 Agent 只能使用自己职责范围内的 Tool
SUB_AGENT_CONFIG = {
    "fundamental": {
        "prompt_file": "fundamental_agent.md",
        "tools": ["get_financials", "get_stock_quote", "get_industry_comparison"],
    },
    "technical": {
        "prompt_file": "technical_agent.md",
        "tools": ["get_stock_quote", "calc_technical_indicators"],
    },
    "capital_flow": {
        "prompt_file": "capital_flow_agent.md",
        "tools": ["get_capital_flow", "get_northbound_flow", "get_margin_data", "get_stock_quote"],
    },
    "sentiment": {
        "prompt_file": "sentiment_agent.md",
        "tools": ["get_news", "get_announcements", "get_sector_news", "search_analyst_reports"],
    },
}


# ============================================================
# Agent 运行器
# ============================================================

class SubAgentRunner:
    """运行单个子 Agent 完成一次分析任务"""

    def __init__(self, client: Anthropic, agent_type: str):
        self.client = client
        self.agent_type = agent_type
        config = SUB_AGENT_CONFIG[agent_type]
        self.system_prompt = load_prompt(config["prompt_file"])
        self.tools = [t for t in TOOL_SCHEMAS if t["name"] in config["tools"]]

    def run(self, stock_code: str, stock_name: str, user_profile: dict, analysis_depth: str = "full") -> dict:
        """执行子 Agent 分析，返回结构化结果"""

        user_message = json.dumps({
            "stock_code": stock_code,
            "stock_name": stock_name,
            "user_profile": user_profile,
            "analysis_depth": analysis_depth,
            "context": {"compare_mode": False, "compare_stocks": []},
        }, ensure_ascii=False)

        messages = [{"role": "user", "content": user_message}]

        # Agent loop：支持多轮 tool use
        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

            # 检查是否需要调用 Tool
            if response.stop_reason == "tool_use":
                # 提取 tool_use blocks
                tool_results = []
                assistant_content = response.content

                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        # 执行 Tool
                        if tool_name in TOOL_FUNCTIONS:
                            result = TOOL_FUNCTIONS[tool_name](**tool_input)
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        })

                # 追加 assistant message 和 tool results
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                # Agent 完成分析，提取最终回复
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                # 尝试从回复中解析 JSON 结果
                try:
                    # 查找 JSON 块
                    json_start = final_text.find("{")
                    json_end = final_text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        result = json.loads(final_text[json_start:json_end])
                        return result
                except json.JSONDecodeError:
                    pass

                # JSON 解析失败，返回原始文本
                return {
                    "dimension": self.agent_type,
                    "score": None,
                    "summary": final_text[:200],
                    "error": "无法解析为结构化结果",
                    "raw_text": final_text,
                }
            else:
                return {"error": f"Unexpected stop reason: {response.stop_reason}"}


# ============================================================
# Orchestrator
# ============================================================

class Orchestrator:
    """主控 Agent — 协调用户交互和子 Agent 调度"""

    # 默认权重配置（按投资周期）
    WEIGHT_PROFILES = {
        "短线": {"fundamental": 0.15, "technical": 0.40, "capital_flow": 0.30, "sentiment": 0.15},
        "中线": {"fundamental": 0.35, "technical": 0.25, "capital_flow": 0.20, "sentiment": 0.20},
        "长线": {"fundamental": 0.45, "technical": 0.15, "capital_flow": 0.15, "sentiment": 0.25},
    }

    RATING_MAP = [
        (85, "强烈推荐关注", "⭐⭐⭐⭐⭐"),
        (70, "建议关注", "⭐⭐⭐⭐"),
        (55, "中性观望", "⭐⭐⭐"),
        (40, "谨慎观望", "⭐⭐"),
        (0, "建议规避", "⭐"),
    ]

    def __init__(self):
        self.client = Anthropic()
        self.system_prompt = load_prompt("orchestrator.md")
        self.analysis_cache: dict[str, dict] = {}
        self.user_profile: dict = {
            "period": "中线",
            "risk": "稳健",
            "focus": "全面",
        }

        # 初始化子 Agent
        self.sub_agents = {
            name: SubAgentRunner(self.client, name)
            for name in SUB_AGENT_CONFIG
        }

    def analyze_stock(self, stock_code: str, stock_name: str) -> dict:
        """对单只股票执行四维分析"""

        # 检查缓存
        if stock_code in self.analysis_cache:
            print(f"  [缓存命中] {stock_name}({stock_code})")
            return self.analysis_cache[stock_code]

        print(f"  正在分析 {stock_name}({stock_code})...")

        # 确定需要调度的子 Agent
        focus = self.user_profile.get("focus", "全面")
        depth_map = {
            "全面": {k: "full" for k in SUB_AGENT_CONFIG},
            "偏基本面": {"fundamental": "full", "technical": "brief", "capital_flow": "brief", "sentiment": "brief"},
            "偏技术面": {"fundamental": "brief", "technical": "full", "capital_flow": "brief", "sentiment": "brief"},
            "快速概览": {k: "brief" for k in SUB_AGENT_CONFIG},
        }
        depths = depth_map.get(focus, depth_map["全面"])

        # 依次运行子 Agent（生产环境应改为并行）
        results = {}
        for agent_name, agent in self.sub_agents.items():
            print(f"    ▸ {agent_name} 分析中...")
            result = agent.run(
                stock_code=stock_code,
                stock_name=stock_name,
                user_profile=self.user_profile,
                analysis_depth=depths[agent_name],
            )
            results[agent_name] = result
            score = result.get("score", "N/A")
            print(f"    ✓ {agent_name} 完成 — 得分: {score}")

        # 计算综合评分
        weights = self.WEIGHT_PROFILES.get(self.user_profile["period"], self.WEIGHT_PROFILES["中线"])
        total_score = 0
        total_weight = 0
        for dim, weight in weights.items():
            score = results.get(dim, {}).get("score")
            if score is not None:
                total_score += score * weight
                total_weight += weight

        if total_weight > 0:
            total_score = round(total_score / total_weight)
        else:
            total_score = None

        # 映射评级
        recommendation, stars = "数据不足", "—"
        if total_score is not None:
            for threshold, rec, st in self.RATING_MAP:
                if total_score >= threshold:
                    recommendation, stars = rec, st
                    break

        analysis_result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "total_score": total_score,
            "recommendation": recommendation,
            "stars": stars,
            "dimensions": results,
            "weights": weights,
            "user_profile": self.user_profile.copy(),
        }

        # 写入缓存
        self.analysis_cache[stock_code] = analysis_result
        return analysis_result

    def compare_stocks(self, stocks: list[dict]) -> dict:
        """多股对比分析

        Args:
            stocks: [{"stock_code": "600519", "stock_name": "贵州茅台"}, ...]
        """
        results = {}
        for stock in stocks:
            result = self.analyze_stock(stock["stock_code"], stock["stock_name"])
            results[stock["stock_code"]] = result

        # 找出综合最优
        best_code = max(results, key=lambda k: results[k].get("total_score") or 0)
        best = results[best_code]

        return {
            "mode": "compare",
            "stocks": results,
            "best_stock": {
                "stock_code": best_code,
                "stock_name": best["stock_name"],
                "total_score": best["total_score"],
            },
        }

    def format_single_report(self, result: dict) -> str:
        """格式化单股分析报告（适配微信/飞书文本消息）"""
        dims = result["dimensions"]

        def _dim_line(key, label):
            d = dims.get(key, {})
            score = d.get("score", "—")
            summary = d.get("summary", "")
            return f"▸ {label}  {score}分 — {summary}"

        core_findings = []
        for dim in dims.values():
            for f in dim.get("key_findings", [])[:1]:
                core_findings.append(f)

        risks = []
        for dim in dims.values():
            for r in dim.get("risks", [])[:1]:
                risks.append(r)

        report = f"""📊 {result['stock_name']}({result['stock_code']}) 分析报告
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 综合评分：{result['total_score']}/100  {result['stars']}
💡 投资建议：{result['recommendation']}

{_dim_line('fundamental', '基本面')}
{_dim_line('technical', '技术面')}
{_dim_line('capital_flow', '资金面')}
{_dim_line('sentiment', '消息面')}

📌 核心逻辑：
{'；'.join(core_findings[:3]) if core_findings else '数据不足，无法生成'}

⚠️ 风险提示：
{'；'.join(risks[:3]) if risks else '暂无显著风险'}

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 以上为 AI 辅助分析，不构成投资建议。投资有风险，入市需谨慎。

想深入了解？回复：
① 基本面详情  ② 技术面详情  ③ 资金面详情
④ 消息面详情  ⑤ 同行对比    ⑥ 换一只股票"""
        return report


# ============================================================
# CLI 入口（开发调试用）
# ============================================================

def main():
    """命令行交互模式"""
    print("=" * 50)
    print("  A股个股分析 Agent v0.1")
    print("  输入股票代码或名称开始分析")
    print("  输入 /help 查看指令  输入 /quit 退出")
    print("=" * 50)

    orch = Orchestrator()

    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue
        if user_input == "/quit":
            print("再见！")
            break
        if user_input == "/help":
            print("指令列表：")
            print("  /analyze 600519     — 分析单只股票")
            print("  /compare 600519 000858 — 对比多只股票")
            print("  /quick 600519       — 快速概览")
            print("  /set period=短线    — 设置偏好")
            print("  /quit               — 退出")
            continue

        # 简化的意图解析（生产环境交给 Orchestrator Agent 处理）
        if user_input.startswith("/analyze "):
            code = user_input.split()[1]
            resolved = resolve_stock_code(code)
            if resolved["status"] == "exact":
                stock = resolved["matches"][0]
                result = orch.analyze_stock(stock["stock_code"], stock["stock_name"])
                print(orch.format_single_report(result))
            else:
                print(f"未能识别股票：{code}")
                if resolved.get("suggestion"):
                    print(resolved["suggestion"])

        elif user_input.startswith("/compare "):
            codes = user_input.split()[1:]
            stocks = []
            for code in codes:
                resolved = resolve_stock_code(code)
                if resolved["status"] == "exact":
                    stocks.append(resolved["matches"][0])
            if len(stocks) >= 2:
                compare_result = orch.compare_stocks(stocks)
                best = compare_result["best_stock"]
                print(f"\n🏆 综合最优：{best['stock_name']}({best['stock_code']}) — {best['total_score']}分")
            else:
                print("至少需要2只股票进行对比")

        else:
            # 自然语言输入 → 尝试解析股票
            resolved = resolve_stock_code(user_input)
            if resolved["status"] == "exact":
                stock = resolved["matches"][0]
                result = orch.analyze_stock(stock["stock_code"], stock["stock_name"])
                print(orch.format_single_report(result))
            elif resolved["status"] == "multiple":
                print("找到多个匹配：")
                for i, m in enumerate(resolved["matches"]):
                    print(f"  {i+1}. {m['stock_name']}({m['stock_code']})")
                print("请输入编号或完整代码")
            else:
                print(resolved.get("suggestion", "无法识别，请输入股票代码或名称"))


if __name__ == "__main__":
    main()
