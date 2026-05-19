# A 股个股分析 Agent — 可视化测试指南

## 快速开始（3 分钟跑起来）

### Step 1: 进入项目目录

```bash
cd a-share-agent
```

### Step 2: 创建虚拟环境并安装依赖

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### Step 3: 启动可视化界面

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`，你将看到完整的分析界面。

> 首次启动默认使用 **Mock 数据**（贵州茅台 + 五粮液的模拟数据），无需网络连接和 API Key，可以立刻体验全部功能。

---

## 界面功能说明

### 左侧边栏 — 分析配置

| 区域 | 功能 |
|-----|------|
| 股票选择 | 输入股票代码（如 600519）或名称（如 茅台） |
| 对比模式 | 勾选后可输入第二只股票，自动生成对比分析 |
| 投资周期 | 短线 / 中线 / 长线 — 影响四维权重分配 |
| 风险偏好 | 保守 / 稳健 / 激进 — 影响建议措辞和止损策略 |
| 权重展示 | 实时显示当前投资周期对应的四维权重 |

### 主界面 — 分析报告

| 模块 | 内容 |
|-----|------|
| 报告头部 | 综合评分（0-100）、星级评定、投资建议、最新股价 |
| 四维评分卡 | 基本面 / 技术面 / 资金面 / 消息面 各自的分数和一句话概要 |
| 雷达图 | 四维评分可视化，直观看到强弱维度 |
| 维度详情 | 点击下拉选择某个维度，展开子维度评分、关键发现、风险点 |
| K线走势 | 日 K 线 + MA5/MA20/MA60 均线 + 成交量柱状图 |
| 技术指标摘要 | 均线排列、MACD 信号、KDJ 状态、RSI 区域、BOLL 位置 |
| 资金流向 | 主力净流入柱状图 + 北向资金持仓趋势 |
| 新闻与研报 | 最新新闻列表 + 券商研报评级 + 评级分布饼图 |
| 多股对比 | 对比表格 + 双股雷达图重叠 + 择优结论 |

### 试试这些操作

1. **切换投资周期**：在侧边栏从「中线」切到「短线」，观察综合评分变化（技术面权重从 25% 升到 40%）
2. **开启对比模式**：勾选对比，输入 000858（五粮液），看双股雷达图
3. **深挖某个维度**：在「分析详情」区域切换下拉框，查看每个维度的子维度评分

---

## 切换到真实数据

当你验证完 Mock 模式，可以切换到真实 AKShare 数据：

```bash
# 方式 1: 环境变量
DATA_MODE=real streamlit run app.py

# 方式 2: Windows
set DATA_MODE=real
streamlit run app.py
```

> 真实数据模式需要网络访问东方财富等数据源。如果你的网络环境有限制，Mock 模式即可满足全部测试需求。

### 接入 Claude Agent（完整 Agent 模式）

如果想测试 Claude Agent 的推理能力（让 AI 自主调用 Tool 并生成分析），需要配置 API Key：

```bash
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Windows
set ANTHROPIC_API_KEY=sk-ant-xxxxx
```

然后运行 CLI 版本：

```bash
python main.py
```

在命令行中输入 `/analyze 600519` 即可触发完整 Agent 流程。

---

## 项目文件结构

```
a-share-agent/
├── app.py                         ← Streamlit 可视化界面
├── generate_report.py             ← 独立 HTML 报告生成器（无需 Streamlit）
├── visual_test_report.html        ← 生成的可视化测试报告（浏览器直接打开）
├── main.py                        ← CLI 入口 + Agent 编排（接 Claude API）
├── test_cli.py                    ← 自动化验证脚本
├── requirements.txt               ← Python 依赖
├── GUIDE.md                       ← 本指南
├── prompts/                       ← 5 个 Agent 的 System Prompt
│   ├── orchestrator.md            ← 主控 Agent
│   ├── fundamental_agent.md       ← 基本面分析 Agent
│   ├── technical_agent.md         ← 技术面分析 Agent
│   ├── capital_flow_agent.md      ← 资金面分析 Agent
│   └── sentiment_agent.md         ← 消息面分析 Agent
└── tools/                         ← Tool 实现层
    ├── tool_definitions.py        ← 真实 AKShare API（生产用）
    ├── mock_tools.py              ← Mock 数据 Tool（测试用）
    └── mock_data.py               ← 模拟数据集
```

---

## 方式 B：独立 HTML 可视化报告（无需 Streamlit）

如果你的环境不方便运行 Streamlit（例如远程服务器、CI 环境），可以直接生成一个自包含的 HTML 报告：

```bash
cd a-share-agent
python generate_report.py
```

运行后会在当前目录生成 `visual_test_report.html`（约 116 KB），双击即可在浏览器中打开。

报告包含以下全部可视化模块：

| 模块 | 内容 |
|-----|------|
| 报告头部 | 综合评分、星级、投资建议、最新价 |
| 四维评分卡 | 4 张评分卡片 + 一句话概要 |
| 雷达图 | 四维评分雷达 + 4 组子维度水平柱状图 |
| 各维度详情 | 关键发现列表 + 风险提示框 |
| K 线走势 | 日 K 线 + MA5/MA20/MA60 + 成交量 |
| 技术指标 | 均线排列 / MACD / KDJ / RSI / BOLL 摘要 |
| 资金流向 | 主力净流入柱状图 + 北向资金持仓指标 |
| 新闻与研报 | 新闻列表 + 券商研报 + 评级饼图 |
| 权重对比 | 短线/中线/长线 三种周期综合评分对比 |
| 多股对比 | 茅台 vs 五粮液 对比表格 + 双雷达图 + 择优结论 |
| 测试检查清单 | 内嵌可勾选的 16 项验证 checklist |

> HTML 报告使用 Plotly CDN，首次打开需要网络加载 plotly.js（约 3MB），之后图表可交互（缩放、悬浮查看数值）。

---

## 测试检查清单

在可视化界面中依次验证以下功能点：

- [ ] **股票解析** — 输入 "600519" 能正确解析为贵州茅台
- [ ] **模糊匹配** — 输入 "茅台" 能自动匹配到贵州茅台
- [ ] **四维评分** — 四个维度评分卡正确显示，分数在 0-100 范围内
- [ ] **雷达图** — 四维雷达图正确渲染，形状反映评分差异
- [ ] **子维度展开** — 每个维度点击后展示 4 个子维度评分条
- [ ] **K 线图** — 日 K 线、三条均线、成交量正确显示
- [ ] **技术指标** — 5 个指标摘要卡片正确显示信号状态
- [ ] **资金流向** — 柱状图红绿正确（正值红、负值绿）
- [ ] **新闻列表** — 显示近期新闻标题和来源
- [ ] **研报评级** — 显示评级分布饼图
- [ ] **权重切换** — 切换「短线/中线/长线」后综合评分随之变化
- [ ] **对比模式** — 勾选对比 → 输入第二只股票 → 对比表格和双雷达图正确
- [ ] **择优结论** — 对比模式下底部显示"综合最优"结论

---

## 常见问题

**Q: streamlit 启动报错 ModuleNotFoundError**
A: 确保在虚拟环境中运行，并已执行 `pip install -r requirements.txt`

**Q: K 线图每次刷新数据不一样？**
A: 正常。Mock 模式下 K 线使用随机生成器，每次刷新会产生不同的行情数据。真实模式下是固定的历史数据。

**Q: 如何添加更多 Mock 股票？**
A: 编辑 `tools/mock_data.py`，在 `MOCK_DATA` 字典中添加新的股票数据，格式参考 600519 的结构。同时在 `app.py` 的 `MOCK_ANALYSIS` 中添加对应的分析结果。

**Q: 如何修改评分权重？**
A: 修改 `app.py` 中的 `WEIGHT_PROFILES` 字典，或在 `prompts/orchestrator.md` 中调整权重定义。

**Q: 真实数据模式下某些 Tool 报错？**
A: AKShare 的 API 偶尔会变更字段名。检查 `tools/tool_definitions.py` 中的字段映射是否与最新版 AKShare 一致。运行 `pip install --upgrade akshare` 更新到最新版本。
