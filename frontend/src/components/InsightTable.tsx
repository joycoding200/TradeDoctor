import { patternLabel } from "../constants/patterns";

interface PatternRow {
  pattern_name: string;
  count: number;
  win_rate: number;
  expectancy: number;
  gross_profit?: number;
  gross_loss?: number;
}

export function InsightTable({ patterns, baseline }: { patterns: PatternRow[]; baseline: number }) {
  if (!patterns || patterns.length === 0) {
    return (
      <div className="p-3 text-center text-sm" style={{ color: "var(--text-secondary)" }}>
        无数据
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="w-full text-sm" style={{ minWidth: 600 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th className="p-3 text-left">标签</th>
            <th className="p-3 text-right">次数</th>
            <th className="p-3 text-right">胜率</th>
            <th className="p-3 text-right">预期值</th>
            <th className="p-3 text-right">盈亏比(PF)</th>
            <th className="p-3 text-left" style={{ maxWidth: 160 }}>评价</th>
          </tr>
        </thead>
        <tbody>
          {patterns.map((p) => {
            const isPos = p.expectancy > 0;
            const pf = (p.gross_loss ?? 0) > 0
              ? (p.gross_profit ?? 0) / (p.gross_loss ?? 1)
              : (p.gross_profit ?? 0) > 0 ? Infinity : 0;
            const isSmallSample = p.count < 5;

            let evalText: string, evalColor: string;
            if (isSmallSample) {
              evalText = `样本不足（${p.count}笔），暂不评价`;
              evalColor = "var(--text-secondary)";
            } else if (isPos && pf > 2) {
              evalText = "优秀：正期望且显著优于均值，核心盈利模式";
              evalColor = "var(--success)";
            } else if (isPos && p.expectancy > baseline) {
              evalText = "良好：优于均值，建议保持";
              evalColor = "var(--success)";
            } else if (isPos && p.expectancy <= baseline) {
              evalText = "正收益但低于最佳模式，可优化";
              evalColor = "var(--accent)";
            } else {
              evalText = "负期望：持续亏损，建议减少或改进";
              evalColor = "var(--danger)";
            }

            return (
              <tr
                key={p.pattern_name}
                style={{
                  borderBottom: "1px solid var(--border)",
                  backgroundColor: isPos ? "rgba(34,197,94,0.04)" : "rgba(239,68,68,0.04)",
                  opacity: isSmallSample ? 0.6 : 1,
                  transition: "background-color 0.15s",
                }}
              >
                <td className="p-3 font-medium" style={{ color: isPos ? "var(--success)" : p.expectancy < 0 ? "var(--danger)" : "var(--text-primary)" }}>
                  {isSmallSample ? "" : isPos ? "✓ " : "✗ "}{patternLabel(p.pattern_name)}
                </td>
                <td className="p-3 text-right">{p.count}</td>
                <td className="p-3 text-right" style={{ color: p.win_rate >= 0.5 ? "var(--success)" : "var(--danger)" }}>
                  {(p.win_rate * 100).toFixed(1)}%
                </td>
                <td className="p-3 text-right font-semibold" style={{ color: isPos ? "var(--success)" : "var(--danger)" }}>
                  {p.expectancy >= 0 ? "+" : ""}{(p.expectancy * 100).toFixed(1)}%
                </td>
                <td className="p-3 text-right" style={{ color: pf >= 1.5 ? "var(--success)" : pf >= 1 ? "var(--accent)" : "var(--danger)" }}>
                  {pf === Infinity ? "∞" : pf.toFixed(2)}
                </td>
                <td className="p-3 text-xs" style={{ color: evalColor, maxWidth: 160 }}>
                  {p.expectancy > baseline && !isSmallSample ? "↑ " : p.expectancy < baseline && !isSmallSample ? "↓ " : ""}{evalText}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
