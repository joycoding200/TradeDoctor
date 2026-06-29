import { useMemo, useState } from "react";

interface SymbolSummaryItem {
  symbol: string;
  symbol_name?: string;
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

type SortKey =
  | "symbol"
  | "trade_count"
  | "win_rate"
  | "total_pnl"
  | "avg_holding_days";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "股票" },
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

function symbolDisplay(item: SymbolSummaryItem): { primary: string; secondary?: string } {
  if (item.symbol_name && item.symbol_name !== item.symbol) {
    return { primary: item.symbol_name, secondary: item.symbol };
  }
  return { primary: item.symbol };
}

export default function SymbolSummaryTable({ data }: SymbolSummaryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("total_pnl");
  const [sortAsc, setSortAsc] = useState(false);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return data;
    return data.filter((item) => {
      if (item.symbol.toLowerCase().includes(q)) return true;
      if (item.symbol_name && item.symbol_name.toLowerCase().includes(q)) return true;
      return false;
    });
  }, [data, query]);

  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg py-6 text-center text-sm text-text-secondary">
        暂无交易数据
      </div>
    );
  }

  const sorted = [...filtered].sort((a, b) => {
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
    <div>
      {/* B2.4 search box */}
      <div className="mb-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索股票代码或名称"
          aria-label="搜索股票"
          className="w-full rounded-md border border-border bg-bg-tertiary px-3 py-1.5 text-sm text-text-primary placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent sm:max-w-xs"
        />
      </div>

      {sorted.length === 0 ? (
        <div className="rounded-lg py-6 text-center text-sm text-text-secondary">
          没有匹配的股票
        </div>
      ) : (
        <>
          {/* B2.3 mobile card view (default on small screens) */}
          <div className="grid grid-cols-1 gap-2 md:hidden">
            {sorted.map((item) => {
              const disp = symbolDisplay(item);
              return (
                <div
                  key={item.symbol}
                  className="rounded-lg border border-border bg-bg-secondary p-3"
                >
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-text-primary">
                        {disp.primary}
                      </div>
                      {disp.secondary && (
                        <div className="truncate text-xs text-text-secondary">
                          {disp.secondary}
                        </div>
                      )}
                    </div>
                    <div
                      className={[
                        "shrink-0 text-sm font-semibold",
                        item.total_pnl > 0
                          ? "text-success"
                          : item.total_pnl < 0
                            ? "text-danger"
                            : "text-text-secondary",
                      ].join(" ")}
                    >
                      {formatMoney(item.total_pnl)}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary">
                    <span>交易 {item.trade_count} 笔</span>
                    <span>胜率 {formatPct(item.win_rate)}</span>
                    <span>持仓 {item.avg_holding_days.toFixed(1)} 天</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Desktop table view */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  {COLUMNS.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className="cursor-pointer select-none whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-text-secondary hover:text-text-primary"
                    >
                      {col.label}
                      <span className="opacity-50">{sortIndicator(col.key)}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((item) => {
                  const disp = symbolDisplay(item);
                  return (
                    <tr
                      key={item.symbol}
                      className="border-b border-border transition-[filter] hover:brightness-110"
                    >
                      <td className="px-3 py-2">
                        <div className="font-medium text-text-primary">
                          {disp.primary}
                        </div>
                        {disp.secondary && (
                          <div className="text-xs text-text-secondary">
                            {disp.secondary}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-text-secondary">
                        {item.trade_count}
                      </td>
                      <td className="px-3 py-2 text-text-secondary">
                        {formatPct(item.win_rate)}
                      </td>
                      <td
                        className={[
                          "px-3 py-2 font-medium",
                          item.total_pnl > 0
                            ? "text-success"
                            : item.total_pnl < 0
                              ? "text-danger"
                              : "text-text-secondary",
                        ].join(" ")}
                      >
                        {formatMoney(item.total_pnl)}
                      </td>
                      <td className="px-3 py-2 text-text-secondary">
                        {item.avg_holding_days.toFixed(1)}天
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
