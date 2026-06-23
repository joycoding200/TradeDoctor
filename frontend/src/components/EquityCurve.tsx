import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface EquityPoint {
  date: string;
  cum_pnl: number;
  cum_pnl_pct: number;
}

interface EquityCurveProps {
  data: EquityPoint[];
}

function formatMoney(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

export default function EquityCurve({ data }: EquityCurveProps) {
  if (!data || data.length <= 1) {
    return (
      <div
        className="flex items-center justify-center rounded-lg mb-6"
        style={{
          height: 280,
          backgroundColor: "var(--card-bg, rgba(255,255,255,0.03))",
          border: "1px solid var(--border)",
          color: "var(--text-secondary)",
          fontSize: "0.875rem",
        }}
      >
        暂无足够数据生成曲线
      </div>
    );
  }

  // Determine overall trend for color
  const lastPoint = data[data.length - 1];
  const isPositive = (lastPoint?.cum_pnl ?? 0) >= 0;
  const strokeColor = isPositive ? "var(--success, #22c55e)" : "var(--danger, #ef4444)";
  const fillColor = isPositive
    ? "rgba(34,197,94,0.15)"
    : "rgba(239,68,68,0.15)";

  return (
    <div className="mb-6">
      <div
        className="text-xs font-medium mb-2"
        style={{ color: "var(--text-secondary)" }}
      >
        净值曲线
      </div>
      <div
        className="rounded-lg p-4"
        style={{
          backgroundColor: "var(--card-bg, rgba(255,255,255,0.03))",
          border: "1px solid var(--border)",
        }}
      >
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={isPositive ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"} />
                <stop offset="100%" stopColor={isPositive ? "rgba(34,197,94,0.02)" : "rgba(239,68,68,0.02)"} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(0)}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--card-bg, #1a1a2e)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                fontSize: "0.8125rem",
                color: "var(--text-primary)",
              }}
              formatter={(value: number, name: string) => {
                if (name === "cum_pnl") return [formatMoney(value), "累计盈亏"];
                return [value, name];
              }}
              labelFormatter={(label: string) => `日期: ${label}`}
            />
            <ReferenceLine
              y={0}
              stroke="var(--border)"
              strokeDasharray="4 4"
            />
            <Area
              type="monotone"
              dataKey="cum_pnl"
              stroke={strokeColor}
              strokeWidth={2}
              fill="url(#equityGradient)"
              dot={false}
              activeDot={{ r: 4, fill: strokeColor }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
