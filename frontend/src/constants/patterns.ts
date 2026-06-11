/**
 * Pattern label mappings — source of truth: /pattern_definition.yaml
 * Update the YAML file first, then sync this file.
 * Generated from: pattern_definition.yaml (15 patterns, 3 modules)
 */
export const PATTERN_LABELS: Record<string, string> = {
  // 模块一：入场行为（行情依赖）
  CHASE: "追涨",
  BOTTOM: "抄底",
  BREAKOUT: "突破",
  TREND: "趋势",
  COUNTER_TREND: "逆势",
  BREAKDOWN: "破位",
  // 模块二：持仓周期
  SCALP: "短线",
  SWING: "波段",
  POSITION: "长持",
  // 模块三：仓位与风控
  PYRAMID: "加仓",
  AVERAGE_DOWN: "补仓",
  TURN: "做T",
  STOP_LOSS: "止损",
  TAKE_PROFIT: "止盈",
  CASH: "空仓",
};

export const PATTERN_MODULES: Record<string, string> = {
  CHASE: "entry", BOTTOM: "entry", BREAKOUT: "entry",
  TREND: "entry", COUNTER_TREND: "entry", BREAKDOWN: "entry",
  SCALP: "holding", SWING: "holding", POSITION: "holding",
  PYRAMID: "risk", AVERAGE_DOWN: "risk", TURN: "risk",
  STOP_LOSS: "risk", TAKE_PROFIT: "risk", CASH: "risk",
};

export function patternLabel(name: string): string {
  return PATTERN_LABELS[name] || name;
}
