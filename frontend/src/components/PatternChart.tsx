import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface PatternData {
  pattern: string;
  win_rate: number;
  count: number;
  [key: string]: unknown;
}

interface PatternChartProps {
  data: PatternData[];
}

const PATTERN_LABELS: Record<string, string> = {
  CHASE: "追涨",
  BOTTOM: "抄底",
  BREAKOUT: "突破",
  TREND: "趋势",
  COUNTER_TREND: "逆势",
  SCALP: "短线",
  SWING: "波段",
  POSITION: "长持",
  PYRAMID: "加仓",
  AVERAGE_DOWN: "补仓",
};

export default function PatternChart({ data }: PatternChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8" style={{ color: "var(--text-secondary)" }}>
        暂无行为标签数据
      </div>
    );
  }

  const chartData = data.map((d) => ({
    name: PATTERN_LABELS[d.pattern] || d.pattern,
    winRate: d.win_rate,
    count: d.count,
  }));

  return (
    <div style={{ backgroundColor: "var(--bg-secondary)", borderRadius: "12px", border: "1px solid var(--border)" }} className="p-4">
      <h3 className="text-sm font-medium mb-4" style={{ color: "var(--text-secondary)" }}>
        各行为标签胜率
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          />
          <Tooltip
            formatter={(value) => `${(Number(value) * 100).toFixed(1)}%`}
            contentStyle={{
              backgroundColor: "var(--bg-tertiary)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              color: "var(--text-primary)",
            }}
          />
          <Bar dataKey="winRate" fill="var(--accent)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
