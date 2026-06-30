import { LoadingSpinner, ErrorBox, Card, Collapsible } from "../../components/ui";
import { InsightTable } from "../../components/InsightTable";
import PatternChart from "../../components/PatternChart";
import { patternLabel, dimensionLabel } from "../../constants/patterns";

interface InsightTabProps {
  insight: {
    isLoading: boolean;
    error: Error | null;
    data: any;
  };
}

/** Format PnL for compact display. */
function fmtPnl(v: number): string {
  const abs = Math.abs(v);
  const sign = v >= 0 ? "+" : "-";
  if (abs >= 10000) return `${sign}${(abs / 10000).toFixed(1)}万`;
  return `${sign}${abs.toFixed(0)}元`;
}

export default function InsightTab({ insight }: InsightTabProps) {
  if (insight.isLoading) {
    return <LoadingSpinner text="正在加载行情数据并分析交易行为，预计 10-20 秒..." />;
  }
  if (insight.error) {
    return <ErrorBox message="分析失败，请刷新重试" />;
  }
  if (!insight.data) return null;

  const d = insight.data;
  const baseline = d.baseline_expectancy || 0;
  const best = d.best_pattern;
  const worst = d.worst_pattern;
  const cross = d.cross_analysis || [];

  // ── 诊断结论（纯规则，无 AI）───────────────────────────────────
  let conclusion: string;
  if (!best && !worst) {
    conclusion = "样本不足，无法生成诊断结论。建议上传更多交割单。";
  } else {
    const parts: string[] = [];
    if (best && best.count >= 5) {
      parts.push(`最大优势是「${patternLabel(best.pattern_name)}」，胜率 ${(best.win_rate * 100).toFixed(0)}%，贡献 ${fmtPnl(best.total_pnl)}`);
    }
    if (worst && worst.count >= 5) {
      parts.push(`最大问题是「${patternLabel(worst.pattern_name)}」，贡献 ${fmtPnl(worst.total_pnl)}`);
    }
    if (baseline > 0.01) {
      parts.push("你的交易系统整体有正期望，坚持执行就能赚钱");
    } else if (baseline < 0) {
      parts.push("你的交易系统整体负期望——需要调整策略，否则长期必亏");
    } else {
      // R-multiple 期望接近零，但金额口径可能仍亏损（胜率≈50% 时两种口径会冲突）
      const netPnl = (best?.total_pnl ?? 0) + (worst?.total_pnl ?? 0);
      if (netPnl < 0) {
        parts.push("虽然按收益率算期望接近零，但亏损笔金额大于盈利笔，整体仍在亏钱");
      } else {
        parts.push("你的交易系统期望接近零，扣除手续费后勉强打平");
      }
    }
    conclusion = parts.join("。") + "。";
  }

  // ── 赚钱 / 亏钱 行为 Top 3 ──────────────────────────────────────
  const behaviors = (d.behavior || []) as any[];
  const sorted = [...behaviors].sort((a, b) => b.total_pnl - a.total_pnl);
  const gainers = sorted.filter((p: any) => p.total_pnl > 0).slice(0, 3);
  const losers = sorted.filter((p: any) => p.total_pnl < 0).slice(-3).reverse();

  // ── 交叉分析 Top 6 ─────────────────────────────────────────────
  const crossSorted = [...cross]
    .filter((c: any) => c.count >= 3)
    .sort((a: any, b: any) => Math.abs(b.total_pnl) - Math.abs(a.total_pnl))
    .slice(0, 6);

  return (
    <div className="space-y-6">
      {/* ═══════════ 诊断结论 ═══════════ */}
      <Card className="p-5 border-l-2 border-l-accent">
        <div className="text-xs text-text-secondary mb-2">📋 诊断结论</div>
        <p className="text-sm leading-relaxed text-text-primary">{conclusion}</p>
      </Card>

      {/* ═══════════ 盈亏来源 ═══════════ */}
      {behaviors.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 赚钱来源 */}
          {gainers.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-medium text-success">💰 赚钱的行为</div>
              <div className="space-y-2">
                {gainers.map((p: any) => (
                  <Card key={p.pattern_name} className="p-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">{patternLabel(p.pattern_name)}</span>
                      <span className="text-sm text-success font-medium">{fmtPnl(p.total_pnl)}</span>
                    </div>
                    <div className="mt-1 text-xs text-text-secondary">
                      {p.count < 5 && <span className="text-accent">样本不足 · </span>}{p.count}次 · 胜率{(p.win_rate * 100).toFixed(0)}% · 预期{p.expectancy >= 0 ? "+" : ""}{(p.expectancy * 100).toFixed(1)}%
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
          {/* 亏钱来源 */}
          {losers.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-medium text-danger">📉 亏钱的行为</div>
              <div className="space-y-2">
                {losers.map((p: any) => (
                  <Card key={p.pattern_name} className="p-3 border-l-2 border-l-danger">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">{patternLabel(p.pattern_name)}</span>
                      <span className="text-sm text-danger font-medium">{fmtPnl(p.total_pnl)}</span>
                    </div>
                    <div className="mt-1 text-xs text-text-secondary">
                      {p.count < 5 && <span className="text-accent">样本不足 · </span>}{p.count}次 · 胜率{(p.win_rate * 100).toFixed(0)}% · 预期{(p.expectancy * 100).toFixed(1)}%
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════ 环境 × 行为 交叉分析 ═══════════ */}
      {crossSorted.length > 0 && (
        <div>
          <div className="mb-3 text-xs font-medium text-text-secondary">
            🔀 环境 × 行为 交叉分析（哪种环境下做什么最赚/最亏）
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {crossSorted.map((c: any) => (
              <Card
                key={`${c.market_env}-${c.behavior}`}
                className={`p-3 ${c.total_pnl >= 0 ? "" : "border-l-2 border-l-danger"}`}
              >
                <div className="text-xs text-text-secondary">
                  {patternLabel(c.market_env)} + {patternLabel(c.behavior)}
                </div>
                <div className={`mt-1 text-sm font-semibold ${c.total_pnl >= 0 ? "text-success" : "text-danger"}`}>
                  {fmtPnl(c.total_pnl)}
                </div>
                <div className="mt-0.5 text-xs text-text-secondary">
                  {c.count}次 · 胜率{(c.win_rate * 100).toFixed(0)}%
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ═══════════ 完整标签详情（折叠）═══════════ */}
      <Collapsible title="展开全部标签详情（四维度完整数据）">
        <div className="space-y-4 pt-2">
          {(["behavior", "market_env", "outcome", "psychology"] as const).map((dim) => {
            const items = d[dim];
            if (!items || items.length === 0) return null;
            return (
              <div key={dim}>
                <div className="mb-2 text-xs font-medium text-text-secondary">
                  {dimensionLabel(dim)}
                </div>
                <Card className="overflow-hidden">
                  <InsightTable patterns={items} baseline={baseline} />
                </Card>
              </div>
            );
          })}

          {d.patterns?.length > 0 && (
            <PatternChart data={d.patterns} />
          )}
        </div>
      </Collapsible>
    </div>
  );
}
