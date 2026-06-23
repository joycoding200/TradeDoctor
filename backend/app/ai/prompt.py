"""Prompt templates for the AI trading coach."""

SYSTEM_PROMPT = """你是 TradingJournalAnalyzer（交易日志分析器）的 AI 交易教练。你的任务是基于用户的交易数据，生成一份《交易行为诊断书》。

## 核心原则
1. **只分析行为，不预测市场。** 不推荐股票，不预测涨跌。
2. **基于数据说话。** 每一条结论都必须有数据支撑。
3. **建设性。** 指出问题的同时，给出可执行的改善建议。
4. **简明扼要。** 用简洁的段落呈现，避免冗长。
5. **面向散户。** 考虑对象为非专业投资者，尽量用大白话说明白。

## 语言要求（重要）
- **必须全部使用中文输出。** 禁止在正文中使用英文术语、英文缩写或中英混杂。
- 所有指标必须附带中文解释（例：盈亏比即赚的钱除以亏的钱，大于1表示整体盈利）。
- 所有英文缩写首次出现时必须替换为中文全称（例：用"最大不利变动"替代"MAE"，用"最大有利变动"替代"MFE"）。

## 输出结构
### 核心结论
一句话概括当前交易状态。

### 优势清单
做得好的 2-3 个交易行为，每条包含：
- 行为名称（中文，如：及时止损、顺势交易、仓位管理）
- 数据支撑（如：止损交易平均亏损仅 X%，远低于不止损交易）
- 一句话肯定

### 风险警示
最危险的 2-3 个交易行为，每条包含：
- 行为名称（中文）
- 数据支撑（如：该行为贡献了总亏损的 X%）
- 潜在原因推测
- 警示等级（⚠️ 注意 / 🔴 严重 / 🚨 高危）

### 改善建议
基于数据的 3-5 条具体可执行措施，每条必须是：
1. **一个具体动作**（如"单笔亏损超过总资金 2% 时强制止损"），不是泛泛的"控制风险"
2. **一个可量化目标**（如"将平均亏损控制在 X 元以内"），不是"少亏一些"
3. **一个执行触发条件**（如"持仓超过 X 天未盈利则重新评估"），不是"要有耐心"

建议格式：
> 建议一：[具体动作]
> 当前：[你的数据现状]
> 目标：[可量化的改善目标]
> 执行：[什么情况下触发此规则]"""


def build_user_prompt(analysis_data: dict) -> str:
    """Build a structured user prompt from analysis data.

    Args:
        analysis_data: Dict with keys:
            total_trades, win_rate, total_pnl, avg_holding_days,
            patterns (list of dicts with pattern_name, count, win_rate, total_pnl),
            what_if (list of dicts with removed_pattern, delta, contribution_pct).

    Returns:
        A formatted prompt string for the LLM.
    """
    lines = [
        "请根据以下交易数据分析我的交易行为并生成诊断书：",
        "",
        f"总交易次数：{analysis_data.get('total_trades', 'N/A')}",
        f"胜率：{analysis_data.get('win_rate', 'N/A')}%",
        f"总盈亏：{analysis_data.get('total_pnl', 'N/A')}",
        f"平均持仓天数：{analysis_data.get('avg_holding_days', 'N/A')}",
        "",
        "行为标签统计：",
    ]

    patterns = analysis_data.get("patterns", [])
    if patterns:
        for p in patterns:
            lines.append(
                f"- {p['pattern_name']}: {p['count']}次, "
                f"胜率{p['win_rate']:.1%}, 总盈亏{p['total_pnl']:+.2f}"
            )
    else:
        lines.append("（暂无行为标签数据）")

    lines.append("")
    lines.append("反事实回测（What If）：")
    what_if = analysis_data.get("what_if", [])
    if what_if:
        for w in what_if:
            lines.append(
                f"- 移除 {w['removed_pattern']}: 收益变化 {w['delta']:+.4f}, "
                f"影响度 {w['contribution_pct']:.2f}"
            )
    else:
        lines.append("（暂无回测数据）")

    # V4.0: risk metrics section
    if any(k in analysis_data for k in ("profit_factor", "max_drawdown", "expectancy")):
        lines.append("")
        lines.append("风险指标：")
        pf = analysis_data.get("profit_factor")
        lines.append(f"- 盈亏比（赚的钱÷亏的钱，>1表示整体盈利）: {'∞（无亏损交易）' if pf is None else f'{pf:.2f}'}")
        expect = analysis_data.get("expectancy")
        if expect is not None:
            lines.append(f"- 预期收益（每笔交易的平均预期盈亏百分比）: {expect}%")
        dd = analysis_data.get("max_drawdown")
        ddpct = analysis_data.get("max_drawdown_pct")
        if dd is not None and ddpct is not None:
            lines.append(f"- 最大回撤（账户从最高点回落的最大幅度）: {dd}元 ({ddpct * 100:.1f}%)")
        cl = analysis_data.get("consecutive_losses")
        if cl is not None:
            lines.append(f"- 最大连续亏损（连续亏损的最多笔数）: {cl}次")
        mae = analysis_data.get("avg_mae")
        if mae is not None:
            lines.append(f"- 平均最大不利变动（持仓期间浮亏的最大幅度）: {mae * 100:.1f}%")
        mfe = analysis_data.get("avg_mfe")
        if mfe is not None:
            lines.append(f"- 平均最大有利变动（持仓期间浮盈的最大幅度）: {mfe * 100:.1f}%")
        pcr = analysis_data.get("profit_capture_ratio")
        if pcr is not None:
            lines.append(f"- 止盈效率（最终获利÷最高浮盈，越高越能拿住利润）: {pcr * 100:.1f}%")
        tr = analysis_data.get("total_return_pct")
        if tr is not None:
            lines.append(f"- 总收益率: {tr * 100:.1f}%")

    # V4.0: key trades section
    ps = analysis_data.get("positions_summary")
    if ps:
        lines.append("")
        lines.append("关键交易：")
        top_winners = ps.get("top_winners", [])
        if top_winners:
            lines.append("- 盈利最多:")
            for w in top_winners:
                lines.append(
                    f"  • {w['symbol']}: {w['pnl']:+.2f} ({w['pnl_pct'] * 100:.1f}%), "
                    f"持仓{w['holding_days']}天 ({w['entry_date']} → {w['exit_date']})"
                )
        top_losers = ps.get("top_losers", [])
        if top_losers:
            lines.append("- 亏损最多:")
            for l in top_losers:
                lines.append(
                    f"  • {l['symbol']}: {l['pnl']:+.2f} ({l['pnl_pct'] * 100:.1f}%), "
                    f"持仓{l['holding_days']}天 ({l['entry_date']} → {l['exit_date']})"
                )

    lines.append("")
    lines.append("请按照系统提示的格式输出《交易行为诊断书》。")

    return "\n".join(lines)
