import { describe, it, expect } from "vitest";
import { formatMoney } from "./format";

describe("formatMoney", () => {
  it("positive small value: +元 with 2 decimals", () => {
    expect(formatMoney(1234.5)).toBe("+1,234.50 元");
  });

  it("zero: no sign", () => {
    expect(formatMoney(0)).toBe("0.00 元");
  });

  it("negative small value: -元", () => {
    expect(formatMoney(-500)).toBe("-500.00 元");
  });

  it("≥1万: 万 shorthand + full 元 in parens", () => {
    expect(formatMoney(52314.5)).toBe("+5.23万（52,314.50 元）");
  });

  it("negative ≥1万: -万 + full 元", () => {
    expect(formatMoney(-19234.5)).toBe("-1.92万（19,234.50 元）");
  });

  it("compact mode: 万 only, no 元 parens", () => {
    expect(formatMoney(52314.5, { compact: true })).toBe("+5.23万");
  });

  it("compact mode under 1万: still 元", () => {
    expect(formatMoney(999, { compact: true })).toBe("+999.00 元");
  });

  it("thousands separator applied", () => {
    expect(formatMoney(1234567.89)).toBe("+123.46万（1,234,567.89 元）");
  });
});
