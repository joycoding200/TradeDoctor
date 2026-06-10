"""Prompt templates for the AI trading coach."""

SYSTEM_PROMPT = """你是 TradeLens（交易日志分析器）的 AI 交易教练。你的任务是基于用户的交易数据，生成一份《交易行为诊断书》。

## 核心原则
1. **只分析行为，不预测市场。** 不推荐股票，不预测涨跌。
2. **基于数据说话。** 每一条结论都必须有数据支撑。
3. **建设性。** 指出问题的同时，给出可执行的改善建议。
4. **简明扼要。** 用简洁的段落呈现，避免冗长。

## 输出结构
- **核心结论（一句话）**
- **优势清单：** 用户做得好的 2-3 个行为
- **风险警示：** 用户最危险的 2-3 个行为
- **改善建议：** 基于数据的具体改进方向"""


def build_user_prompt(analysis_data: dict) -> str:
    """Build a structured user prompt from analysis data.

    Args:
        analysis_data: Dict with keys:
            total_trades, win_rate, total_pnl, avg_holding_days,
            patterns (list of dicts with pattern_name, count, win_rate, total_pnl),
            what_if (list of dicts with removed_pattern, delta, damage_score).

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
                f"伤害度 {w['damage_score']:.2f}"
            )
    else:
        lines.append("（暂无回测数据）")

    lines.append("")
    lines.append("请按照系统提示的格式输出《交易行为诊断书》。")

    return "\n".join(lines)
