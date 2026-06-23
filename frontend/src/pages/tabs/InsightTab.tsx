import { useState } from "react";
import { LoadingSpinner, ErrorBox, Card } from "../../components/ui";
import { InsightTable } from "../../components/InsightTable";
import PatternChart from "../../components/PatternChart";
import { dimensionLabel, DIMENSION_ORDER } from "../../constants/patterns";

type InsightDim = "market_env" | "behavior" | "outcome" | "psychology";

interface InsightTabProps {
  insight: {
    isLoading: boolean;
    error: Error | null;
    data: any;
  };
}

export default function InsightTab({ insight }: InsightTabProps) {
  const [insightDim, setInsightDim] = useState<InsightDim>("behavior");

  if (insight.isLoading) {
    return <LoadingSpinner text="正在加载行情数据并分析交易行为，预计 10-20 秒..." />;
  }
  if (insight.error) {
    return <ErrorBox message="分析失败，请刷新重试" />;
  }

  if (!insight.data) return null;

  const baseline = insight.data.baseline_expectancy || 0;

  return (
    <div className="space-y-6">
      {/* Dimension sub-tabs */}
      <div className="flex gap-1" style={{ borderBottom: "1px solid var(--border)" }} role="tablist">
        {DIMENSION_ORDER.map((dim) => (
          <button
            key={dim}
            role="tab"
            aria-selected={insightDim === dim}
            onClick={() => setInsightDim(dim as InsightDim)}
            style={{
              backgroundColor: "transparent",
              border: "none",
              borderBottom: insightDim === dim ? "2px solid var(--accent)" : "2px solid transparent",
              color: insightDim === dim ? "var(--accent)" : "var(--text-secondary)",
              padding: "8px 14px",
              cursor: "pointer",
              marginBottom: "-1px",
              transition: "color 0.15s, border-color 0.15s",
            }}
            className="text-xs font-medium"
          >
            {dimensionLabel(dim)}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        <InsightTable
          patterns={insight.data[insightDim] || []}
          baseline={baseline}
        />
      </Card>

      {insight.data.patterns?.length > 0 && (
        <PatternChart data={insight.data.patterns} />
      )}
    </div>
  );
}
