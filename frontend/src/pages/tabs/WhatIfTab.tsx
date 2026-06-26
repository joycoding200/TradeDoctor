import { LoadingSpinner, ErrorBox, Card, EmptyState, Collapsible } from "../../components/ui";
import { ShapleyPanel } from "../../components/ShapleyPanel";
import { patternLabel } from "../../constants/patterns";

interface WhatIfTabProps {
  whatIf: {
    isLoading: boolean;
    error: Error | null;
    data: any;
  };
}

/** Format yuan values in a human-readable way. */
function fmtYuan(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 10000) {
    return `${(v >= 0 ? "+" : "-")}${(abs / 10000).toFixed(1)}万`;
  }
  return `${(v >= 0 ? "+" : "-")}${abs.toFixed(0)}元`;
}

export default function WhatIfTab({ whatIf }: WhatIfTabProps) {
  if (whatIf.isLoading) {
    return <LoadingSpinner text="加载回测数据..." />;
  }
  if (whatIf.error) {
    return <ErrorBox message="请先导入交易数据" />;
  }
  if (!whatIf.data?.items || whatIf.data.items.length === 0) {
    return <EmptyState icon="📊" message="暂无回测数据" />;
  }

  const { data } = whatIf;

  // ── 通俗版分析：找出赚最多和亏最多的 2 个标签 ──────────
  const sorted = [...data.items].sort(
    (a: any, b: any) => b.absolute_impact - a.absolute_impact
  );
  const topGainers = sorted.filter((i: any) => i.absolute_impact > 0).slice(0, 2);
  const topLosers = sorted.filter((i: any) => i.absolute_impact < 0).slice(-2).reverse();

  return (
    <div className="space-y-6">
      {/* ═══════════════════════════════════════════════════════════
          SECTION 1: Stop Loss Backtest — most actionable
          ═══════════════════════════════════════════════════════════ */}
      {data.stop_loss && (
        <div>
          <h2 className="text-sm font-medium mb-3">💡 止损效果模拟</h2>
          <p className="text-xs mb-3 text-text-secondary">
            假设每次开仓设置 5% 止损线，盘中触发即卖出，你的收益会变成怎样。
          </p>
          <Card className="p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">5% 止损线</span>
              <span className="text-xs text-text-secondary">
                触发 {data.stop_loss.affected_positions} 次
              </span>
            </div>
            <div className="flex justify-between text-sm mt-2 text-text-secondary">
              <span>当前收益: {(data.stop_loss.original_return * 100).toFixed(1)}%</span>
              <span>止损后: {(data.stop_loss.what_if_return * 100).toFixed(1)}%</span>
              <span className={data.stop_loss.delta >= 0 ? "text-success" : "text-danger"}>
                变化 {data.stop_loss.delta >= 0 ? "+" : ""}{(data.stop_loss.delta * 100).toFixed(1)}%
              </span>
            </div>
            <div className={`mt-3 border-t border-border pt-3 text-xs font-medium ${
              data.stop_loss.delta > 0 ? "text-success"
                : data.stop_loss.delta < -0.03 ? "text-danger"
                : "text-accent"
            }`}>
              {data.stop_loss.delta > 0
                ? "✅ 设止损能帮你减少亏损，建议严格执行"
                : data.stop_loss.delta < -0.03
                ? "⚠️ 5%止损对你的交易风格太紧，建议放宽或改用移动止损"
                : `建议：5%止损对你的收益影响很小（${(data.stop_loss.delta * 100).toFixed(1)}%），可作为兜底风控`}
            </div>
          </Card>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          SECTION 2: 通俗版分析 — what made you money, what lost it
          ═══════════════════════════════════════════════════════════ */}
      <div>
        <h2 className="text-sm font-medium mb-3">📋 盈亏来源速览</h2>
        <p className="text-xs mb-3 text-text-secondary">
          你的交易行为如何影响最终收益。赚钱靠什么，亏钱因为什么，一目了然。
        </p>

        {topGainers.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-medium text-success mb-2">💰 赚钱靠这些</div>
            {topGainers.map((item: any) => (
              <Card key={item.removed_pattern} className="p-3 mb-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">{patternLabel(item.removed_pattern)}</span>
                  <span className="text-sm text-success font-medium">{fmtYuan(item.absolute_impact)}</span>
                </div>
                <div className="mt-1 text-xs text-text-secondary">
                  贡献了总收益的 {(item.contribution_pct * 100).toFixed(0)}%
                </div>
              </Card>
            ))}
          </div>
        )}

        {topLosers.length > 0 && (
          <div>
            <div className="text-xs font-medium text-danger mb-2">📉 亏钱因为</div>
            {topLosers.map((item: any) => (
              <Card key={item.removed_pattern} className="p-3 mb-2 border-l-2 border-l-danger">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">{patternLabel(item.removed_pattern)}</span>
                  <span className="text-sm text-danger font-medium">{fmtYuan(item.absolute_impact)}</span>
                </div>
                <div className="mt-1 text-xs text-text-secondary">
                  贡献了总亏损的 {(Math.abs(item.contribution_pct) * 100).toFixed(0)}%
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 3: Advanced — Shapley + Factor Contribution
          ═══════════════════════════════════════════════════════════ */}
      <Collapsible title="展开高级分析（Shapley 归因 + 因子贡献详情）">
        <div className="space-y-6 pt-2">
          {/* Shapley */}
          {data.shapley && data.shapley.length > 0 && (
            <ShapleyPanel data={data.shapley} />
          )}

          {/* Factor contribution detail */}
          <div>
            <h2 className="text-sm font-medium mb-2">因子贡献详情</h2>
            <p className="text-xs mb-3 text-text-secondary">
              每种行为模式独立贡献了多少盈亏。数值为正说明该行为在赚钱，为负则在亏钱。
            </p>
            {data.items.map((item: any) => (
              <Card key={item.removed_pattern} className="p-3 mb-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium">{patternLabel(item.removed_pattern)}</span>
                  <span className={`text-sm ${item.absolute_impact >= 0 ? "text-success" : "text-danger"}`}>
                    {fmtYuan(item.absolute_impact)}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-text-secondary">
                  <span>占比: {(item.contribution_pct * 100).toFixed(0)}%</span>
                  <span>当前收益: {(item.original_return * 100).toFixed(1)}%</span>
                  <span>剔除后: {(item.what_if_return * 100).toFixed(1)}%</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </Collapsible>
    </div>
  );
}
