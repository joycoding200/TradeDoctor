import { LoadingSpinner, ErrorBox, Card, EmptyState } from "../../components/ui";
import { ShapleyPanel } from "../../components/ShapleyPanel";
import { patternLabel } from "../../constants/patterns";

interface WhatIfTabProps {
  whatIf: {
    isLoading: boolean;
    error: Error | null;
    data: any;
  };
}

export default function WhatIfTab({ whatIf }: WhatIfTabProps) {
  if (whatIf.isLoading) {
    return <LoadingSpinner text="加载回测数据..." />;
  }
  if (whatIf.error) {
    return <ErrorBox message="请先导入交易数据" />;
  }
  if (!whatIf.data?.items || whatIf.data.items.length === 0) {
    return (
      <EmptyState
        icon="📊"
        message="暂无回测数据"
      />
    );
  }

  const { data } = whatIf;

  return (
    <div className="space-y-6">
      {/* Shapley attribution */}
      {data.shapley && data.shapley.length > 0 && (
        <ShapleyPanel data={data.shapley} />
      )}

      {/* Stop Loss with conclusion */}
      {data.stop_loss && (
        <div>
          <h2 className="text-sm font-medium mb-3">止损规则回测</h2>
          <p className="text-xs mb-3" style={{ color: "var(--text-secondary)" }}>
            遍历持仓期间每日最低价，判断是否盘中触及止损线。
          </p>
          <Card className="p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">设置 5% 止损</span>
              <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                盘中触发 {data.stop_loss.affected_positions} 笔
              </span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span style={{ color: "var(--text-secondary)" }}>原始收益: {(data.stop_loss.original_return * 100).toFixed(1)}%</span>
              <span style={{ color: "var(--text-secondary)" }}>止损后: {(data.stop_loss.what_if_return * 100).toFixed(1)}%</span>
              <span style={{ color: data.stop_loss.delta >= 0 ? "var(--success)" : "var(--danger)" }}>
                Δ {data.stop_loss.delta >= 0 ? "+" : ""}{(data.stop_loss.delta * 100).toFixed(1)}%
              </span>
            </div>
            <div className="mt-3 pt-3 text-xs font-medium" style={{
              borderTop: "1px solid var(--border)",
              color: data.stop_loss.delta > 0 ? "var(--success)"
                : data.stop_loss.delta < -0.03 ? "var(--danger)"
                : "var(--accent)",
            }}>
              {data.stop_loss.delta > 0
                ? "✅ 结论：历史数据支持设置5%止损，可有效减少损失"
                : data.stop_loss.delta < -0.03
                ? "⚠️ 结论：5%止损会严重损害收益，你的交易风格不适合机械止损，建议放宽至8-10%或采用移动止损"
                : `结论：5%止损对收益影响较小（${(data.stop_loss.delta * 100).toFixed(1)}%），可作为辅助风控手段`}
            </div>
          </Card>
        </div>
      )}

      {/* Factor Contribution Analysis */}
      <div>
        <h2 className="text-sm font-medium mb-3">因子贡献分析</h2>
        <p className="text-xs mb-3" style={{ color: "var(--text-secondary)" }}>
          展示每种行为模式对总盈亏的金额贡献。此分析反映持仓组合的盈亏构成，并非反事实回测。
        </p>
        {data.items.map((item: any) => (
          <Card key={item.removed_pattern} className="p-4 mb-3">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">{patternLabel(item.removed_pattern)}</span>
              <span className="text-sm" style={{ color: item.absolute_impact >= 0 ? "var(--success)" : "var(--danger)" }}>
                金额贡献: {item.absolute_impact >= 0 ? "+" : ""}{item.absolute_impact.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-xs" style={{ color: "var(--text-secondary)" }}>
              <span>占比: {(item.contribution_pct * 100).toFixed(0)}%</span>
              <span>原始收益: {(item.original_return * 100).toFixed(1)}%</span>
              <span>剔除后: {(item.what_if_return * 100).toFixed(1)}%</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
