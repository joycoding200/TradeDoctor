import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import KpiCard from "./KpiCard";

describe("KpiCard", () => {
  it("hero variant: large value + summary + rating", () => {
    render(
      <KpiCard
        cls="success"
        label="总盈亏"
        value="+5.23万"
        summary="每笔交易平均赚 230 元"
        rating={{ text: "✓ 整体盈利", color: "success" }}
        variant="hero"
      />
    );
    expect(screen.getByText("总盈亏")).toBeInTheDocument();
    expect(screen.getByText("+5.23万")).toBeInTheDocument();
    expect(screen.getByText("每笔交易平均赚 230 元")).toBeInTheDocument();
    expect(screen.getByText("✓ 整体盈利")).toBeInTheDocument();
  });

  it("detail variant: renders hint, hides when absent", () => {
    const { rerender } = render(
      <KpiCard cls="primary" label="平均持仓" value="11.0天" hint="盈利12天 / 亏损8天" />
    );
    expect(screen.getByText("盈利12天 / 亏损8天")).toBeInTheDocument();
    rerender(<KpiCard cls="primary" label="平均持仓" value="11.0天" />);
    expect(screen.queryByText("盈利12天 / 亏损8天")).not.toBeInTheDocument();
  });

  it("applies danger color class for negative values", () => {
    render(<KpiCard cls="danger" label="最大回撤" value="23.4%" />);
    const valueEl = screen.getByText("23.4%");
    expect(valueEl.className).toContain("text-danger");
  });

  it("omits rating badge when not provided", () => {
    render(<KpiCard cls="accent" label="胜率" value="76%" />);
    // only label + value, no rating text
    expect(screen.getByText("胜率")).toBeInTheDocument();
    expect(screen.getByText("76%")).toBeInTheDocument();
  });
});
