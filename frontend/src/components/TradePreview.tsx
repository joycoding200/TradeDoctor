import { Button } from "./ui";

interface Trade {
  [key: string]: unknown;
}

interface TradePreviewProps {
  trades: Trade[];
  onImport: () => void;
  loading?: boolean;
}

const COLUMNS = ["编号", "股票代码", "方向", "数量", "价格", "手续费", "时间"];

export default function TradePreview({ trades, onImport, loading }: TradePreviewProps) {
  const display = trades.slice(0, 100);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-text-secondary">
          共解析 {trades.length} 条交易记录{trades.length > 100 ? "（仅显示前 100 条）" : ""}
        </span>
        <Button onClick={onImport} disabled={loading}>
          {loading ? "导入中..." : "确认导入"}
        </Button>
      </div>
      <div className="min-w-[600px] overflow-x-auto rounded-lg border border-border">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="bg-bg-tertiary">
              {COLUMNS.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap border-b border-border px-3 py-2 text-left font-medium text-text-secondary"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {display.map((trade, i) => (
              <tr
                key={i}
                className="border-b border-border even:bg-bg-secondary"
              >
                {COLUMNS.map((col) => (
                  <td
                    key={col}
                    className="whitespace-nowrap px-3 py-1.5 text-text-primary"
                  >
                    {String(trade[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
