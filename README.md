# A股个股分析 Agent

基于 Claude Agent SDK 构建的 A 股四维分析系统。通过 Orchestrator + 4 个专项 Sub-Agent 的架构，对个股进行基本面、技术面、资金面、消息面的全方位分析，输出综合评分和投资建议。

> ⚠️ 本项目仅供学习和研究用途，分析结果不构成投资建议。投资有风险，入市需谨慎。

## 功能概览

- **四维分析**：基本面（盈利、成长、估值、财务健康）、技术面（趋势、动量、量价、关键价位）、资金面（主力、北向、融资融券、筹码）、消息面（公告、新闻、政策、研报）
- **综合评分**：0-100 分制，根据投资周期（短线/中线/长线）动态调整四维权重
- **多股对比**：支持 2-5 只股票同时对比，自动生成择优结论
- **双运行模式**：Mock 数据（离线演示）和 Real 数据（AKShare 实时行情）
- **可视化界面**：Streamlit 交互式仪表盘 + 独立 HTML 报告

## 系统架构

```
用户输入
  │
  ▼
┌─────────────────────────────────────────┐
│         Orchestrator Agent              │
│   意图识别 → 调度子Agent → 汇总评分     │
└──────┬──────┬──────┬──────┬─────────────┘
       │      │      │      │
       ▼      ▼      ▼      ▼
   ┌──────┐┌──────┐┌──────┐┌──────┐
   │基本面││技术面││资金面││消息面│
   │Agent ││Agent ││Agent ││Agent │
   └──┬───┘└──┬───┘└──┬───┘└──┬───┘
      │       │       │       │
      ▼       ▼       ▼       ▼
   ┌──────────────────────────────┐
   │      13 个 MCP Tools         │
   │  AKShare API / Mock Data     │
   └──────────────────────────────┘
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/cth001/a-share-agent.git
cd a-share-agent
```

### 2. 安装依赖

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. 启动可视化界面（Mock 模式，无需 API Key）

```bash
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，默认使用模拟数据，可立即体验全部功能。

### 4. 生成独立 HTML 报告

```bash
python generate_report.py
# 打开 visual_test_report.html 即可查看
```

## 配置

### 环境变量

复制模板并填入你的配置：

```bash
cp .env.example .env
```

`.env` 文件内容：

```env
# 数据模式：mock（默认） / real（真实行情）
DATA_MODE=mock

# Anthropic API Key（仅 Agent 模式需要）
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 切换到真实数据

将 `DATA_MODE` 设为 `real`，需要网络访问东方财富等数据源：

```bash
# 方式一：修改 .env
DATA_MODE=real

# 方式二：命令行临时指定
DATA_MODE=real streamlit run app.py
```

### 启动 Agent 模式（Claude 自主推理）

配置好 `ANTHROPIC_API_KEY` 后：

```bash
python main.py
# 在命令行输入: /analyze 600519
```

## 项目结构

```
a-share-agent/
├── app.py                  # Streamlit 可视化界面
├── main.py                 # CLI 入口 + Agent 编排（接 Claude API）
├── generate_report.py      # 独立 HTML 报告生成器
├── test_cli.py             # 自动化验证脚本
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── GUIDE.md                # 详细测试指南
├── prompts/                # Agent System Prompts
│   ├── orchestrator.md     # 主控 Agent（意图解析、调度、评分）
│   ├── fundamental_agent.md # 基本面分析
│   ├── technical_agent.md  # 技术面分析
│   ├── capital_flow_agent.md # 资金面分析
│   └── sentiment_agent.md  # 消息面分析
└── tools/                  # Tool 实现层
    ├── tool_definitions.py # 真实 AKShare API（13 个 Tool）
    ├── mock_tools.py       # Mock 实现（接口一致，可替换）
    └── mock_data.py        # 模拟数据集
```

## 可视化界面说明

### 侧边栏配置

| 功能 | 说明 |
|------|------|
| 股票选择 | 输入代码（600519）或名称（茅台），支持模糊匹配 |
| 对比模式 | 勾选后输入第二只股票，生成对比分析 |
| 投资周期 | 短线 / 中线 / 长线，影响四维权重分配 |
| 风险偏好 | 保守 / 稳健 / 激进，影响建议措辞 |

### 分析报告模块

| 模块 | 内容 |
|------|------|
| 综合评分 | 0-100 分 + 星级 + 投资建议 |
| 四维评分卡 | 每个维度的分数和一句话概要 |
| 雷达图 | 四维评分可视化 |
| 子维度详情 | 4 个子维度评分条 + 关键发现 + 风险点 |
| K 线走势 | 日 K 线 + MA5/MA20/MA60 + 成交量 |
| 技术指标 | 均线排列 / MACD / KDJ / RSI / BOLL |
| 资金流向 | 主力净流入 + 北向资金 + 融资融券 |
| 新闻研报 | 新闻列表 + 券商评级 + 评级饼图 |
| 多股对比 | 对比表格 + 双雷达图 + 择优结论 |

### 权重配置

| 维度 | 短线 | 中线 | 长线 |
|------|------|------|------|
| 基本面 | 15% | 35% | 45% |
| 技术面 | 40% | 25% | 15% |
| 资金面 | 30% | 20% | 15% |
| 消息面 | 15% | 20% | 25% |

## MCP Tools

项目提供 13 个数据工具，生产模式基于 AKShare 获取实时数据：

| Tool | 功能 |
|------|------|
| `resolve_stock_code` | 股票代码/名称模糊匹配 |
| `get_stock_quote` | 历史 K 线行情 |
| `get_financials` | 财务指标（ROE、营收、PE 等） |
| `calc_technical_indicators` | 技术指标计算（MA/MACD/KDJ/RSI/BOLL） |
| `get_capital_flow` | 主力资金流向 |
| `get_northbound_flow` | 北向资金（沪深港通） |
| `get_margin_data` | 融资融券数据 |
| `get_news` | 个股新闻 |
| `get_announcements` | 公司公告 |
| `get_industry_comparison` | 行业对比 |
| `get_sector_top_stocks` | 板块龙头股 |
| `get_sector_news` | 行业新闻与政策 |
| `search_analyst_reports` | 券商研报与评级 |

## 技术栈

- **Agent 框架**：Claude Agent SDK（Anthropic API + Tool Use）
- **数据源**：AKShare（东方财富、新浪财经等）
- **可视化**：Streamlit + Plotly
- **语言**：Python 3.10+

## License

MIT
