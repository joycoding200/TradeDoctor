import { Collapsible } from "./ui";
import { patternLabel } from "../constants/patterns";

interface ShapleyItem {
  pattern_name: string;
  shapley_value: number;
  pct_of_total: string;
}

export function ShapleyPanel({ data }: { data: ShapleyItem[] }) {
  if (!data || data.length === 0) return null;

  return (
    <Collapsible title="赚钱来源分析（公平归因，点击展开）">
      <p className="text-xs mb-3" style={{ color: "var(--text-secondary)" }}>
        各标签对总收益的贡献占比，总和=100%，消除重复计算。
      </p>
      {data.map((s) => (
        <div key={s.pattern_name} className="mb-2">
          <div className="flex justify-between text-xs mb-1">
            <span>{patternLabel(s.pattern_name)}</span>
            <span style={{ color: s.shapley_value >= 0 ? "var(--success)" : "var(--danger)" }}>
              {s.shapley_value >= 0 ? "+" : ""}{s.shapley_value.toFixed(2)}（{s.pct_of_total}%）
            </span>
          </div>
          <div style={{ backgroundColor: "var(--border)", borderRadius: 4, height: 6, overflow: "hidden" }}>
            <div style={{
              width: `${Math.abs(parseFloat(s.pct_of_total))}%`,
              height: "100%",
              backgroundColor: s.shapley_value >= 0 ? "var(--success)" : "var(--danger)",
              borderRadius: 4,
              transition: "width 0.3s",
            }} />
          </div>
        </div>
      ))}
    </Collapsible>
  );
}
