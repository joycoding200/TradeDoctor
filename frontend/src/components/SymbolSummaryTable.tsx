import { useState } from "react";

interface SymbolSummaryItem {
  symbol: string;
  trade_count: number;
  win_count: number;
  win_rate: number;
  total_pnl: number;
  avg_holding_days: number;
  first_trade_date: string;
  last_trade_date: string;
}

interface SymbolSummaryTableProps {
  data: SymbolSummaryItem[];
}

type SortKey = "symbol" | "trade_count" | "win_rate" | "total_pnl" | "avg_holding_days";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "股票代码" },
  { key: "trade_count", label: "交易次数" },
  { key: "win_rate", label: "胜率" },
  { key: "total_pnl", label: "总盈亏" },
  { key: "avg_holding_days", label: "平均持仓天数" },
];

function formatMoney(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function SymbolSummaryTable({ data }: SymbolSummaryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("total_pnl");
  const [sortAsc, setSortAsc] = useState(false);

  if (!data || data.length === 0) {
    return (
      <div
        className="text-sm py-6 text-center rounded-lg"
        style={{ color: "var(--text-secondary)" }}
      >
        暂无交易数据
      </div>
    );
  }

  const sorted = [...data].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    const dir = sortAsc ? 1 : -1;
    if (typeof aVal === "number" && typeof bVal === "number") {
      return (aVal - bVal) * dir;
    }
    return String(aVal).localeCompare(String(bVal)) * dir;
  });

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key !== "total_pnl"); // default desc for PnL, asc for others
    }
  };

  const sortIndicator = (key: SortKey) => {
    if (key !== sortKey) return "";
    return sortAsc ? " ↑" : " ↓";
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: `1px solid var(--border)` }}>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className="py-2 px-3 text-left cursor-pointer select-none whitespace-nowrap"
                style={{ color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 500 }}
              >
                {col.label}
                <span style={{ opacity: 0.5 }}>{sortIndicator(col.key)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => (
            <tr
              key={item.symbol}
              style={{ borderBottom: `1px solid var(--border)` }}
              className="hover:brightness-110"
            >
              <td
                className="py-2 px-3 font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {item.symbol}
              </td>
              <td className="py-2 px-3" style={{ color: "var(--text-secondary)" }}>
                {item.trade_count}
              </td>
              <td className="py-2 px-3" style={{ color: "var(--text-secondary)" }}>
                {formatPct(item.win_rate)}
              </td>
              <td
                className="py-2 px-3 font-medium"
                style={{
                  color:
                    item.total_pnl > 0
                      ? "var(--success)"
                      : item.total_pnl < 0
                        ? "var(--danger)"
                        : "var(--text-secondary)",
                }}
              >
                {formatMoney(item.total_pnl)}
              </td>
              <td className="py-2 px-3" style={{ color: "var(--text-secondary)" }}>
                {item.avg_holding_days.toFixed(1)}天
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
