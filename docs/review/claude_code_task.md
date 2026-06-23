# Implementation Task: 短期优先级冲刺（3个P0任务）

你是 TradingJournalAnalyzer 项目的开发者。请先阅读 CLAUDE.md 了解项目背景，然后实现以下 3 个任务。

参考文档: docs/review/PRD_短期冲刺_2026-06-23.md

---

## Task 1: 净值曲线图 (Equity Curve)

### 后端

1. 在 `backend/app/schemas/analysis.py` 中新增:
   - `EquityPoint` 模型: `date: str`, `cum_pnl: float`, `cum_pnl_pct: float`
   - 在 `StatsResponse` 中新增字段: `equity_curve: list[EquityPoint] = []`

2. 在 `backend/app/api/analysis.py` 的 `get_stats()` 函数中:
   - 在现有的 max drawdown 计算循环附近（约 line 241-253），同时收集 equity curve 数据点
   - 起点: `{"date": str(首笔exit_date), "cum_pnl": 0.0, "cum_pnl_pct": 0.0}`
   - 遍历 sorted_positions，每笔累加 pnl，记录 `{"date": str(p.exit_date), "cum_pnl": round(cum_pnl, 2), "cum_pnl_pct": round(cum_pnl / total_invested, 4) if total_invested > 0 else 0.0}`
   - 将结果赋给 StatsResponse 的 equity_curve 字段

### 前端

3. 创建 `frontend/src/components/EquityCurve.tsx`:
   - 使用 Recharts 的 AreaChart + Area + XAxis + YAxis + Tooltip + ResponsiveContainer
   - import 已有的: `import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"`
   - 数据来自 `stats.equity_curve`（数组: {date, cum_pnl, cum_pnl_pct}）
   - 面积颜色: 盈利时填充 `rgba(34,197,94,0.15)`，stroke `var(--success)`；亏损时 `rgba(239,68,68,0.15)`，stroke `var(--danger)`
   - 在 0 线画 ReferenceLine
   - Tooltip 显示: 日期 + 累计盈亏金额（+/-格式）
   - 组件接收 props: `{ data: Array<{date: string, cum_pnl: number, cum_pnl_pct: number}> }`
   - 如果数据为空或只有1个点，显示提示文字"暂无足够数据生成曲线"
   - 高度 280px

4. 在 `frontend/src/pages/tabs/StatsTab.tsx` 中:
   - import EquityCurve 组件
   - 在 `StatsCards` 渲染的返回值中，在 "核心结果" 标题之前插入 `<EquityCurve data={stats.data.equity_curve || []} />`
   - 需要把 stats.data 传下去（StatsTab 已有 stats.data）

5. 在 `frontend/src/components/StatsCards.tsx` 的 props 接口 `StatsData` 中新增:
   - `equity_curve?: Array<{date: string, cum_pnl: number, cum_pnl_pct: number}>`

---

## Task 2: 股票维度盈亏表 (Symbol Summary)

### 后端

6. 在 `backend/app/schemas/analysis.py` 中新增:
   - `SymbolSummaryItem` 模型: `symbol: str`, `trade_count: int`, `win_count: int`, `win_rate: float`, `total_pnl: float`, `avg_holding_days: float`, `first_trade_date: str`, `last_trade_date: str`
   - 在 `StatsResponse` 中新增字段: `symbol_summary: list[SymbolSummaryItem] = []`

7. 在 `backend/app/api/analysis.py` 的 `get_stats()` 函数中:
   - 在 valid_positions 计算完成后，按 symbol 分组
   - 每组计算: trade_count, win_count (pnl>0), win_rate, total_pnl (sum), avg_holding_days, first_trade_date (min exit_date), last_trade_date (max exit_date)
   - 按 total_pnl 降序排列
   - 将结果赋给 StatsResponse 的 symbol_summary 字段

### 前端

8. 创建 `frontend/src/components/SymbolSummaryTable.tsx`:
   - 可排序表格，列: 股票代码 | 交易次数 | 胜率 | 总盈亏 | 平均持仓天数
   - 总盈亏正值绿色，负值红色，带 +/- 前缀
   - 默认按总盈亏降序
   - 点击表头可切换排序方向
   - 使用项目现有样式: `var(--border)`, `var(--text-primary)`, `var(--text-secondary)`, `var(--success)`, `var(--danger)`
   - 组件接收 props: `{ data: Array<SymbolSummaryItem> }`
   - 如果数据为空显示"暂无交易数据"

9. 在 `frontend/src/components/StatsCards.tsx` 的 `StatsData` 接口中新增:
   - `symbol_summary?: Array<{symbol: string, trade_count: number, win_count: number, win_rate: number, total_pnl: number, avg_holding_days: number, first_trade_date: string, last_trade_date: string}>`

10. 在 `frontend/src/components/StatsCards.tsx` 的返回 JSX 中:
    - 在"核心结果" grid 之后、"进阶分析"标题之前，插入 SymbolSummaryTable
    - 添加小标题"股票维度盈亏"
    - `<SymbolSummaryTable data={stats.symbol_summary || []} />`

---

## Task 3: 扩充 AI Prompt

### 后端

11. 修改 `backend/app/api/report.py` 的 `_build_analysis_data()` 函数:
    - 函数签名改为接收额外参数: `stats_data: dict = None`
    - 从 stats_data 中提取并加入返回 dict:
      - `profit_factor`, `expectancy`, `max_drawdown`, `max_drawdown_pct`, `consecutive_losses`
      - `avg_mae`, `avg_mfe`, `profit_capture_ratio`, `win_loss_ratio`, `total_return_pct`
    - 新增 `positions_summary`: 从 positions 中取盈利 TOP3 + 亏损 BOTTOM3
      - 每条: `{symbol, pnl, pnl_pct, holding_days, entry_date, exit_date}`
    - 新增 `outcome_distribution`: 从 stats_data 传入

12. 修改 `backend/app/api/report.py` 的 `generate_report()` 函数:
    - 在调用 `_build_analysis_data()` 之前，先计算 stats 级别的指标
    - 可以直接在 generate_report() 中复用 analysis.py get_stats() 的计算逻辑，或者简化为：
      从 positions 直接计算 profit_factor, expectancy, max_drawdown, consecutive_losses, avg_mae/mfe, profit_capture_ratio 等
    - 将这些值打包成 stats_data dict 传给 _build_analysis_data()

13. 修改 `backend/app/ai/prompt.py` 的 `build_user_prompt()`:
    - 在现有内容之后，新增以下板块:
    
    ```
    风险指标：
    - 盈亏比(PF): {pf}
    - 预期收益(Expectancy): {expectancy}%
    - 最大回撤: {max_drawdown} ({max_drawdown_pct}%)
    - 连续亏损: {consecutive_losses}次
    - 最大回撤容忍度(MAE): {avg_mae}%
    - 最大浮盈(MFE): {avg_mfe}%
    - 止盈效率: {profit_capture_ratio}%
    - 总收益率: {total_return_pct}%
    
    关键交易：
    - 盈利最多: {top3 winners}
    - 亏损最多: {top3 losers}
    ```

14. 修改 `backend/app/ai/validator.py`:
    - 在 validate() 方法中新增对 `profit_factor`, `max_drawdown_pct`, `consecutive_losses` 的数值校验
    - 从 AI 输出中正则提取这些数字，与 analysis_data 中的值比对（±1% 容忍度）
    - 如果 AI 没提到这些指标不算错误（软校验），但如果提到了数字不对则标记

15. 更新测试:
    - `backend/tests/test_ai/test_prompt.py`: 为新增字段添加测试用例
    - `backend/tests/test_ai/test_validator.py`: 为新校验字段添加测试

---

## 约束与规范

- 遵循 CLAUDE.md 中的所有设计决策
- 所有显示文本中文优先
- 每个指标加评级（优秀/良好/一般/较差）
- 小样本（<5 笔）不评价
- None 值处理: PF/Payoff 无亏损时为 None，前端显示 ∞
- 不要修改现有的金融指标计算逻辑
- 保持现有代码风格和缩进
- 修改完成后运行测试验证: `cd backend && python -m pytest tests/test_ai/ -q`
- 前端不需要运行测试，确保 TypeScript 类型正确即可

## 执行顺序

先做后端 Task 1 和 Task 2（schemas → analysis.py），再做 Task 3（report.py → prompt.py → validator.py → tests），最后做前端组件。
