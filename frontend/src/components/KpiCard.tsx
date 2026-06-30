/**
 * Shared KPI card — used for both the 4 hero metrics and the detail cards.
 *
 * Replaces the two near-identical local functions `heroCard` / `detailCard`
 * that lived in StatsCards.tsx. The only real differences were the value
 * font size (text-2xl vs text-lg) and the outer padding (p-5 vs p-4), both
 * driven by the `variant` prop here.
 */
import { Card } from "./ui";

export interface Rating {
  text: string;
  color: string; // key into COLOR_CLASS
}

const COLOR_CLASS: Record<string, string> = {
  success: "text-success",
  danger: "text-danger",
  accent: "text-accent",
  primary: "text-text-primary",
  secondary: "text-text-secondary",
};

export interface KpiCardProps {
  /** Color bucket for the value text. */
  cls: string;
  /** Metric label (e.g. "总盈亏"). Also used as the React key. */
  label: string;
  /** Formatted value (e.g. "+5.23万（52,314.50 元）"). */
  value: string;
  /** Optional short hint shown under the value (detail variant only). */
  hint?: string;
  /** Optional rating badge (e.g. "优秀"/"良好"). */
  rating?: Rating;
  /** Optional longer summary line shown at the bottom. */
  summary?: string;
  /** hero = the 4 large top cards; detail = the smaller metric cards. */
  variant?: "hero" | "detail";
}

export default function KpiCard({
  cls,
  label,
  value,
  hint,
  rating,
  summary,
  variant = "detail",
}: KpiCardProps) {
  const isHero = variant === "hero";
  return (
    <Card key={label} className={isHero ? "p-5" : "p-4"}>
      <div className="mb-1 text-xs text-text-secondary">{label}</div>
      <div
        className={[
          isHero ? "text-2xl font-bold" : "text-lg font-semibold",
          COLOR_CLASS[cls] ?? "text-text-primary",
        ].join(" ")}
      >
        {value}
      </div>
      {rating && (
        <div
          className={[
            isHero ? "mt-1" : "mt-0.5",
            "text-xs font-medium",
            COLOR_CLASS[rating.color] ?? "",
          ].join(" ")}
        >
          {rating.text}
        </div>
      )}
      {hint && (
        <div className="mt-0.5 text-xs text-text-secondary opacity-70">{hint}</div>
      )}
      {summary && (
        <div
          className={[
            isHero ? "mt-1.5" : "mt-1",
            "text-xs text-text-secondary leading-relaxed",
            isHero ? "" : "opacity-80",
          ].join(" ")}
        >
          {summary}
        </div>
      )}
    </Card>
  );
}
