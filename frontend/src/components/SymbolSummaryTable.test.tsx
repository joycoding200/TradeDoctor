import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import SymbolSummaryTable from "./SymbolSummaryTable";

const DATA = [
  { symbol: "600330", symbol_name: "天通股份", trade_count: 10, win_count: 6, win_rate: 0.6, total_pnl: 10137.79, avg_holding_days: 11, first_trade_date: "2026-01-05", last_trade_date: "2026-03-20" },
  { symbol: "000993", symbol_name: "闽东电力", trade_count: 5, win_count: 2, win_rate: 0.4, total_pnl: -3200, avg_holding_days: 8, first_trade_date: "2026-01-10", last_trade_date: "2026-02-15" },
  { symbol: "300058", symbol_name: "蓝色光标", trade_count: 8, win_count: 5, win_rate: 0.625, total_pnl: 5200, avg_holding_days: 6, first_trade_date: "2026-01-08", last_trade_date: "2026-03-01" },
];

// jsdom doesn't apply `hidden`/`md:` classes, so both the mobile card list and
// the desktop table render simultaneously. We scope assertions to the desktop
// <table> to avoid "multiple elements found" errors.
function tableRows() {
  const table = document.querySelector("table");
  if (!table) throw new Error("table not rendered");
  return within(table).getAllByRole("row");
}
function inTable(text: string) {
  const table = document.querySelector("table");
  if (!table) return false;
  return within(table).queryAllByText(text).length > 0;
}

describe("SymbolSummaryTable", () => {
  it("renders empty state when no data", () => {
    render(<SymbolSummaryTable data={[]} />);
    expect(screen.getByText("暂无交易数据")).toBeInTheDocument();
  });

  it("renders all rows by default", () => {
    render(<SymbolSummaryTable data={DATA} />);
    expect(inTable("天通股份")).toBe(true);
    expect(inTable("闽东电力")).toBe(true);
    expect(inTable("蓝色光标")).toBe(true);
  });

  it("filters by symbol code", () => {
    render(<SymbolSummaryTable data={DATA} />);
    fireEvent.change(screen.getByLabelText("搜索股票"), { target: { value: "600330" } });
    expect(inTable("天通股份")).toBe(true);
    expect(inTable("闽东电力")).toBe(false);
    expect(inTable("蓝色光标")).toBe(false);
  });

  it("filters by symbol name", () => {
    render(<SymbolSummaryTable data={DATA} />);
    fireEvent.change(screen.getByLabelText("搜索股票"), { target: { value: "蓝色" } });
    expect(inTable("蓝色光标")).toBe(true);
    expect(inTable("天通股份")).toBe(false);
  });

  it("X clear button restores full list", () => {
    render(<SymbolSummaryTable data={DATA} />);
    const input = screen.getByLabelText("搜索股票") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "600330" } });
    expect(inTable("闽东电力")).toBe(false);
    fireEvent.click(screen.getByLabelText("清空搜索"));
    expect(input.value).toBe("");
    expect(inTable("闽东电力")).toBe(true);
  });

  it("shows 'no match' when search matches nothing", () => {
    render(<SymbolSummaryTable data={DATA} />);
    fireEvent.change(screen.getByLabelText("搜索股票"), { target: { value: "zzz" } });
    expect(screen.getByText("没有匹配的股票")).toBeInTheDocument();
  });

  it("sorts by total_pnl descending by default", () => {
    render(<SymbolSummaryTable data={DATA} />);
    const rows = tableRows();
    // rows[0] is header; first data row should be highest pnl (天通股份 +10137)
    expect(rows[1].textContent).toContain("天通股份");
  });
});
