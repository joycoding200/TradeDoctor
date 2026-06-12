# TradingJournalAnalyzer — 交易日志分析器

上传交割单，AI 分析亏损原因并生成改善建议。A 股散户 + 期货散户的交易行为诊断工具。

**核心卖点：Profit Attribution 利润归因** — 按行为类别归因盈亏，量化每种行为对账户的贡献。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vite + React 18 + Tailwind CSS + Recharts + React Query |
| 后端 | FastAPI + SQLAlchemy + Pandas |
| AI | OpenAI / Claude / DeepSeek（环境变量切换） |
| 数据库 | PostgreSQL 17 |
| 行情数据 | [a-stock-data](https://github.com/simonlin1212/a-stock-data)（mootdx + 腾讯优先，不封 IP） |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 17

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 创建数据库
psql -U postgres -c "CREATE DATABASE tradelens;"

# 配置环境变量 .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradelens
SECRET_KEY=change-me

# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173

### 运行测试

```bash
cd backend && pytest tests/ -q    # 343 tests
python e2e/api_contract_tests.py  # 56 contract checks
python e2e/user_flow_e2e.py       # 19 user flow checks
```

## 核心架构：6 层数据管道

```
原始交割单 → Trade → Position → Pattern → Insight → ProfitAttribution → AI 解释器 → 诊断报告
```

1. **Trade** — SmartParser 值分类器，任何券商格式自动识别（不看列名，看数据值）
2. **Position** — FIFO 持仓重建 + 前序持仓标记（`cost_known`）
3. **Pattern** — 按 category 分类标签：entry / market / holding / risk，每 category 一个标签
4. **Insight Engine** — 按 category 分别归因，样本量加权排序，无重复归因
5. **ProfitAttribution** — 按主 Pattern 归因利润变化
6. **AI 解释器 + 验证层** — 自然语言报告 + 数字校验

## 行为标签体系（`pattern_definition.yaml`）

| Category | 标签 | 说明 |
|----------|------|------|
| **entry** | CHASE, BOTTOM, BREAKOUT, FOMO | 入场方式 |
| **market** | TREND, COUNTER_TREND, BREAKDOWN | 市场环境 |
| **holding** | SCALP, SWING, POSITION | 持仓周期 |
| **risk** | PYRAMID, AVERAGE_DOWN, TURN | 仓位管理 |
| **exit** | TIGHT_STOP, TRAILING_STOP, TIME_EXIT, LARGE_LOSS_EXIT | 离场行为 |

Outcome（结果分类）独立于行为标签，不参与归因统计。

## 支持的券商/终端

| 类别 | 来源 |
|------|------|
| A 股 API 终端 | QMT、VN.PY、东方财富、同花顺 |
| 期货终端 | 文华财经、博易大师、CTP/快期/易盛 |
| 券商 APP | 华泰涨乐、中信信e投、国君君弘、广发易淘金、海通e海通财… |
| **通用** | SmartParser（基于数据值推断，零配置） |

## 项目结构

```
TradingJournalAnalyzer/
├── backend/
│   ├── app/
│   │   ├── api/          # REST 端点 (auth, upload, analysis, report)
│   │   ├── engine/        # 计算引擎 (position, pattern, insight, whatif)
│   │   ├── parsers/       # 解析器 (smart.py + 10 券商插件)
│   │   ├── ai/            # AI 层 (provider, prompt, validator)
│   │   ├── models/        # SQLAlchemy 模型 (8 张表)
│   │   └── auth/          # JWT 认证
│   └── tests/             # 343 tests
├── frontend/
│   └── src/
│       ├── pages/         # 7 页面 (upload, analysis, report, history)
│       ├── components/    # StatsCards, PatternChart, WhatIfChart
│       └── constants/     # patterns.ts (同步 pattern_definition.yaml)
├── e2e/                   # API 契约 + E2E 测试
├── pattern_definition.yaml # 标签定义（单一真相源）
└── docs/                  # 设计文档
```

## 设计原则

**AI 负责解释，程序负责计算。** 所有数字由 Python 计算，AI 只做自然语言文本生成。报告中的每个数字都经过验证层比对。

**行为 ≠ 结果。** Pattern 只描述交易行为（入场/持仓/风控），不描述结果（盈亏分类）。结果独立为 Outcome，不参与行为归因。

## License

MIT + Commons Clause — 非商业用途开源
