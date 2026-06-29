/**
 * 金额格式化（统一口径，全站共用）。
 *
 * 规则（B3.1）：
 *   - 单位统一为「元」，带千分位 + 2 位小数
 *   - 正数前缀 +，负数前缀 -，零无前缀
 *   - 绝对值 ≥ 10000 时，主显示「万」并用括号补完整元，避免大数一屏看不下：
 *       +19,234.50 元          (< 1万)
 *       +5.23万（52,314.50 元） (≥ 1万)
 *
 * 之前 StatsCards / SymbolSummaryTable / EquityCurve 各写一份，混用「万」和裸数字，
 * 单位口径不一致。三处统一调用本函数（EquityCurve 图表 tooltip 因空间有限可
 * 传入 {compact: true} 仅返回「万」简写）。
 */
export function formatMoney(value: number, opts?: { compact?: boolean }): string {
  const abs = Math.abs(value);
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  const yuan = abs.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (abs >= 10000) {
    const wan = (abs / 10000).toFixed(2);
    if (opts?.compact) {
      return `${sign}${wan}万`;
    }
    return `${sign}${wan}万（${yuan} 元）`;
  }
  return `${sign}${yuan} 元`;
}
