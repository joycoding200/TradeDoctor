interface StatsData {
  total_trades?: number;
  total_positions?: number;
  win_count?: number;
  win_rate?: number;
  total_pnl?: number;
  avg_holding_days?: number;
  max_win?: number;
  max_loss?: number;
  consecutive_losses?: number;
}

interface StatsCardsProps {
  stats: StatsData;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatMoney(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

export default function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    { label: "总交易次数", value: stats.total_positions ?? stats.total_trades ?? 0, format: "int" },
    { label: "胜率", value: stats.win_rate ?? 0, format: "pct" },
    { label: "总盈亏", value: stats.total_pnl ?? 0, format: "money" },
    { label: "最大盈利", value: stats.max_win ?? 0, format: "money" },
    { label: "最大亏损", value: stats.max_loss ?? 0, format: "money" },
    { label: "平均持仓天数", value: stats.avg_holding_days ?? 0, format: "days" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          style={{
            backgroundColor: "var(--bg-secondary)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          }}
          className="p-4"
        >
          <div className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
            {card.label}
          </div>
          <div
            className="text-xl font-semibold"
            style={{
              color:
                card.label === "最大亏损" || (card.label === "总盈亏" && card.value < 0)
                  ? "var(--danger)"
                  : card.label === "最大盈利" || (card.label === "总盈亏" && card.value > 0)
                  ? "var(--success)"
                  : card.label === "胜率" && card.value < 0.5
                  ? "var(--danger)"
                  : "var(--text-primary)",
            }}
          >
            {card.format === "pct"
              ? formatPercent(card.value)
              : card.format === "money"
              ? formatMoney(card.value)
              : card.format === "days"
              ? `${card.value.toFixed(1)}天`
              : String(card.value)}
          </div>
        </div>
      ))}
    </div>
  );
}
