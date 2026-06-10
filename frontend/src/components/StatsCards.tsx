interface StatsData {
  total_trades?: number;
  win_rate?: number;
  profit_loss_ratio?: number;
  max_profit?: number;
  max_loss?: number;
  avg_holding_days?: number;
  consecutive_losses?: number;
  [key: string]: unknown;
}

interface StatsCardsProps {
  stats: StatsData;
}

const CARD_LABELS: Record<string, string> = {
  total_trades: "总交易次数",
  win_rate: "胜率",
  profit_loss_ratio: "盈亏比",
  max_profit: "最大盈利",
  max_loss: "最大亏损",
  avg_holding_days: "平均持仓天数",
  consecutive_losses: "连续亏损次数",
};

function formatValue(key: string, value: number): string {
  if (key === "win_rate") return `${(value * 100).toFixed(1)}%`;
  if (key === "profit_loss_ratio") return value.toFixed(2);
  if (key === "avg_holding_days") return value.toFixed(1);
  if (key === "total_trades" || key === "consecutive_losses") return String(Math.round(value));
  if (key === "max_profit" || key === "max_loss") return value.toFixed(2);
  return String(value);
}

function isSignificant(key: string): boolean {
  return ["total_trades", "win_rate", "profit_loss_ratio", "max_profit", "max_loss", "avg_holding_days", "consecutive_losses"].includes(key);
}

export default function StatsCards({ stats }: StatsCardsProps) {
  const entries = Object.entries(stats).filter(([k]) => isSignificant(k));

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {entries.map(([key, value]) => (
        <div
          key={key}
          style={{
            backgroundColor: "var(--bg-secondary)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          }}
          className="p-4"
        >
          <div className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
            {CARD_LABELS[key] || key}
          </div>
          <div
            className="text-xl font-semibold"
            style={{
              color:
                key === "max_loss" || (key === "win_rate" && (value as number) < 0.5)
                  ? "var(--danger)"
                  : key === "max_profit"
                  ? "var(--success)"
                  : "var(--text-primary)",
            }}
          >
            {formatValue(key, value as number)}
          </div>
        </div>
      ))}
    </div>
  );
}
