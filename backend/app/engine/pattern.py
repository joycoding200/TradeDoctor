"""Pattern engine for tagging positions with behavioral labels.

Produces 15 behavior tags across three modules:
  Module 1 - Entry behavior (market-data dependent)
  Module 2 - Holding period
  Module 3 - Risk & position management
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class PatternResult:
    """A single behavioral pattern tag attached to a position."""

    pattern_name: str
    confidence: float
    context: dict[str, Any] = field(default_factory=dict)


class PatternEngine:
    """Assign behavioral pattern tags to positions."""

    # ------------------------------------------------------------------
    # Module 2 & 3 -- available without market data
    # ------------------------------------------------------------------

    @staticmethod
    def tag_position(
        pos, all_positions: list, **kwargs
    ) -> list[PatternResult]:
        """Tag a position with holding-period and risk-management patterns.

        Args:
            pos: A position-like object with holding_days, pnl_pct,
                symbol, entry_date, exit_date, avg_entry_price.
            all_positions: All positions in the analysis period.
            **kwargs: Reserved for future extension.

        Returns:
            List of PatternResult instances.
        """
        tags: list[PatternResult] = []

        # ----- Module 2: Holding period ---------------------------------
        if pos.holding_days < 3:
            tags.append(
                PatternResult(
                    "SCALP",
                    1.0,
                    {"holding_days": pos.holding_days},
                )
            )
        elif pos.holding_days <= 30:
            tags.append(
                PatternResult(
                    "SWING",
                    1.0,
                    {"holding_days": pos.holding_days},
                )
            )
        else:
            tags.append(
                PatternResult(
                    "POSITION",
                    1.0,
                    {"holding_days": pos.holding_days},
                )
            )

        # ----- Module 3: Risk & position management ---------------------
        # PYRAMID / AVERAGE_DOWN -- need sibling positions
        same_ep = [
            p
            for p in all_positions
            if p.symbol == pos.symbol
            and p.entry_date == pos.entry_date
        ]
        if len(same_ep) > 1:
            same_ep_sorted = sorted(same_ep, key=lambda p: p.exit_date)
            first_avg = same_ep_sorted[0].avg_entry_price
            if pos.avg_entry_price > first_avg:
                tags.append(
                    PatternResult(
                        "PYRAMID",
                        0.8,
                        {
                            "avg_entry": pos.avg_entry_price,
                            "first_entry_avg": first_avg,
                        },
                    )
                )
            if pos.pnl_pct < 0:
                tags.append(
                    PatternResult(
                        "AVERAGE_DOWN",
                        0.8,
                        {"pnl_pct": pos.pnl_pct},
                    )
                )

        # TURN -- intraday round trip
        if pos.entry_date == pos.exit_date:
            tags.append(
                PatternResult(
                    "TURN",
                    0.7,
                    {"entry_date": str(pos.entry_date)},
                )
            )

        # STOP_LOSS / TAKE_PROFIT
        if pos.pnl_pct < 0:
            tags.append(
                PatternResult(
                    "STOP_LOSS",
                    0.6,
                    {"pnl_pct": pos.pnl_pct},
                )
            )
        if pos.pnl_pct > 0:
            tags.append(
                PatternResult(
                    "TAKE_PROFIT",
                    0.6,
                    {"pnl_pct": pos.pnl_pct},
                )
            )

        # CASH -- gap since last position > 30 calendar days
        earlier = [p for p in all_positions if p.exit_date < pos.entry_date]
        if not earlier:
            tags.append(
                PatternResult(
                    "CASH", 0.5, {"reason": "first position in period"}
                )
            )
        else:
            last_exit = max(p.exit_date for p in earlier)
            gap = (pos.entry_date - last_exit).days
            if gap > 30:
                tags.append(
                    PatternResult(
                        "CASH",
                        0.5,
                        {
                            "gap_days": gap,
                            "last_exit": str(last_exit),
                        },
                    )
                )

        return tags

    # ------------------------------------------------------------------
    # Module 1 -- requires market-data dictionary
    # ------------------------------------------------------------------

    @staticmethod
    def tag_market_patterns(
        pos, market_data: dict[str, dict[str, dict[str, float]]]
    ) -> list[PatternResult]:
        """Tag entry/exit behavior using price & moving-average data.

        Args:
            pos: A position-like object with symbol, entry_date, exit_date.
            market_data: Nested dict keyed by symbol -> date_str ->
                {open, high, low, close, ma5, ma10, ma20, ma60}.

        Returns:
            List of PatternResult instances.
        """
        tags: list[PatternResult] = []

        symbol_data = market_data.get(pos.symbol)
        if not symbol_data:
            return tags

        entry_str = pos.entry_date.isoformat()
        exit_str = pos.exit_date.isoformat()
        entry_data = symbol_data.get(entry_str)
        exit_data = symbol_data.get(exit_str)

        if not entry_data:
            return tags

        dates = sorted(symbol_data.keys())
        entry_idx = dates.index(entry_str)
        entry_close = entry_data["close"]

        # -- CHASE: entry close vs 5 days ago > +15% --------------------
        if entry_idx >= 5:
            d5 = dates[entry_idx - 5]
            close_5 = symbol_data[d5]["close"]
            chg = (entry_close - close_5) / close_5
            if chg > 0.15:
                tags.append(
                    PatternResult(
                        "CHASE",
                        0.7,
                        {
                            "change_pct": round(chg, 4),
                            "from_date": d5,
                        },
                    )
                )

        # -- BOTTOM: entry close vs 5 days ago < -15% -------------------
        if entry_idx >= 5:
            d5 = dates[entry_idx - 5]
            close_5 = symbol_data[d5]["close"]
            chg = (entry_close - close_5) / close_5
            if chg < -0.15:
                tags.append(
                    PatternResult(
                        "BOTTOM",
                        0.7,
                        {
                            "change_pct": round(chg, 4),
                            "from_date": d5,
                        },
                    )
                )

        # -- BREAKOUT: entry close > max(prev 20d high) ----------------
        if entry_idx >= 20:
            prev_highs = [
                symbol_data[dates[i]]["high"]
                for i in range(entry_idx - 20, entry_idx)
            ]
            max_high = max(prev_highs)
            if entry_close > max_high:
                tags.append(
                    PatternResult(
                        "BREAKOUT",
                        0.7,
                        {
                            "entry_close": entry_close,
                            "max_prev_20_high": max_high,
                        },
                    )
                )

        # -- TREND / COUNTER_TREND: MA relationship --------------------
        _maybe_ma_tag(tags, entry_data, "TREND", lambda ma20, ma60: ma20 > ma60)
        _maybe_ma_tag(
            tags, entry_data, "COUNTER_TREND", lambda ma20, ma60: ma20 < ma60
        )

        # -- BREAKDOWN: exit close < min(prev 20d low) -----------------
        if exit_data and exit_str in dates:
            exit_idx = dates.index(exit_str)
            if exit_idx >= 20:
                prev_lows = [
                    symbol_data[dates[i]]["low"]
                    for i in range(exit_idx - 20, exit_idx)
                ]
                min_low = min(prev_lows)
                if exit_data["close"] < min_low:
                    tags.append(
                        PatternResult(
                            "BREAKDOWN",
                            0.7,
                            {
                                "exit_close": exit_data["close"],
                                "min_prev_20_low": min_low,
                            },
                        )
                    )

        return tags


# -- helpers ----------------------------------------------------------------

def _maybe_ma_tag(
    tags: list[PatternResult],
    day_data: dict,
    name: str,
    predicate,
) -> None:
    """Append a trend/counter-trend tag if both MAs exist and predicate holds."""
    ma20 = day_data.get("ma20")
    ma60 = day_data.get("ma60")
    if ma20 is not None and ma60 is not None and predicate(ma20, ma60):
        tags.append(
            PatternResult(
                name, 0.7, {"ma20": ma20, "ma60": ma60}
            )
        )
