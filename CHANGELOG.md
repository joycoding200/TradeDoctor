# 变更日志

本项目所有重要变更记录在此文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [V4.0] — 2026-06-23

### 新增

- **净值曲线图**（Equity Curve）
  - 后端：`StatsResponse` 新增 `equity_curve: list[EquityPoint]` 字段
  - `EquityPoint = {date, cum_pnl, cum_pnl_pct}`，按持仓退出日期累计盈亏
  - 前端：新建 `EquityCurve.tsx`，使用 Recharts AreaChart 渲染
  - 盈利区域绿色半透明，亏损区域红色半透明，y=0 参考线
  - 放在统计概览页核心结果卡片上方

- **股票维度盈亏表**（Symbol Summary）
  - 后端：`StatsResponse` 新增 `symbol_summary: list[SymbolSummaryItem]` 字段
  - `SymbolSummaryItem = {symbol, trade_count, win_count, win_rate, total_pnl, avg_holding_days, first_trade_date, last_trade_date}`
  - 按个股汇总，仅统计 `cost_known=True` 的有效持仓（与 KPI 口径一致）
  - 前端：新建 `SymbolSummaryTable.tsx`，可排序表格，5 列
  - 默认按总盈亏降序，放在核心结果下方、进阶分析上方

- **AI Prompt 扩充**
  - `build_user_prompt()` 新增「风险指标」板块：profit_factor、expectancy、max_drawdown、max_drawdown_pct、consecutive_losses、avg_mae、avg_mfe、profit_capture_ratio、total_return_pct（共 10 项）
  - 新增「关键交易」板块：盈利 TOP3 + 亏损 TOP3
  - `_build_analysis_data()` 新增 `stats_data` 参数，从 StatsResponse 直接采集风险指标
  - Validator 新增 PF / max_drawdown_pct / consecutive_losses 软校验（±1% 容忍度）

- **测试**：`test_prompt.py` 新增 4 个测试，`test_validator.py` 新增 6 个测试（共 30 passed, 0 failed）

- **基础设施**：`.gitattributes`（统一行尾为 LF）、`vite.config.ts` 新增 `/api` proxy

### 变更

- `frontend/src/api/client.ts` BASE_URL 从 `http://localhost:8000` 改为 `""`（配合 vite proxy）
- `StatsCards.tsx` 集成 EquityCurve 和 SymbolSummaryTable 组件

---

## [V3.1] — 2026-06-22

### 修复

- 第三轮代码审查：8 阻塞 + 10 建议 + 4 小改进全量修复
- 前端 UI/UX 全面优化

---

## [V2.5] — 2026-06-20

### 新增

- `max_drawdown_pct`：最大回撤百分比（行业标准，对照 TradesViz/Edgewonk）
- `total_return_pct`：总收益率百分比
- `avg_win_pct` / `avg_loss_pct`：平均盈亏百分比

### 变更

- `is_small_sample` 字段：交易笔数 <5 时标记小样本，前端显示「样本不足」不评价

---

## [V2.3] — 2026-06-19

### 修复

- 真实券商导出适配（三层污染修复）：
  - GBK 编码探测（utf-8 → gb18030 → gbk）
  - 伪 `.xls` 文本格式回退（`read_excel` 失败后自动切换文本读取 + 分隔符探测）
  - `="..."` 外壳剥离（`_strip_formula_strings`）
  - 费用列 QUANTITY 守卫误杀修复（名称含费用关键词的列豁免）
- 新增 `tests/test_parsers/test_citic_xls.py` 固化真实 CITIC 特征为回归测试

---

## [V1.3] — 2026-06-15

### 新增

- **Expectancy（R-multiple）**：基于 pnl_pct 的预期收益，对照 TradesViz 标准
- **Shapley 归因**：公平归因各行为标签对总盈亏的贡献
- `baseline_expectancy` 字段用于标签对比

---

## [V1.2] — 2026-06-12

### 新增

- **MAE/MFE 风险分析**：持仓期间最大不利变动（浮亏）和最大有利变动（浮盈）
- `profit_capture_ratio`：止盈效率（浮盈兑现率）
- `mae_winners` / `mae_losers`：分盈亏组的 MAE 均值

### 修复

- PnL 计算扣除买卖双边费用
- 多费用列汇总（佣金、印花税、过户费、其他杂费）
- SmartParser 列类型推断修复（证券代码误选为数量列、价格列误判为费用列）

---

## [V1.1] — 2026-06-10

### 新增

- **4 维行为标签体系**：市场环境 / 交易行为 / 交易结果 / 心理推测
- **SmartParser**：基于数据值推断列类型，零配置自动识别券商格式
- **FIFO 持仓重建**：前序持仓标记（`cost_known`），软删除支持（`is_deleted`）
- **What-If 止损回测**：使用持仓期间日线 low 判断盘中触发
- JWT 认证（邮箱/手机号注册，密码强度校验）
- 支持多文件上传和历史分析记录
