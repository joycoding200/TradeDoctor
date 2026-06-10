"""Tests for pattern engine -- all 15 behavioral tags."""
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.engine.pattern import PatternEngine, PatternResult


# -- helpers ----------------------------------------------------------------

@dataclass
class _Position:
    """Minimal position-like object for testing patterns."""

    symbol: str = "000001"
    asset_type: str = "stock"
    entry_date: date = date(2024, 1, 2)
    exit_date: date = date(2024, 1, 10)
    holding_days: int = 8
    total_quantity: float = 100
    avg_entry_price: float = 10.0
    avg_exit_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    trade_ids: list[str] = field(default_factory=lambda: ["t1", "t2"])


def make_pos(
    holding_days: int = 8,
    pnl_pct: float = 0.1,
    symbol: str = "000001",
    entry_date: date | None = None,
    exit_date: date | None = None,
) -> _Position:
    """Create a test position with derived fields."""
    if entry_date is None:
        entry_date = date(2024, 1, 2)
    if exit_date is None:
        exit_date = entry_date + timedelta(days=holding_days)
    avg_entry = 10.0
    avg_exit = round(avg_entry * (1 + pnl_pct), 4)
    qty = 100
    return _Position(
        symbol=symbol,
        asset_type="stock",
        entry_date=entry_date,
        exit_date=exit_date,
        holding_days=holding_days,
        total_quantity=qty,
        avg_entry_price=avg_entry,
        avg_exit_price=avg_exit,
        pnl=round((avg_exit - avg_entry) * qty, 4),
        pnl_pct=pnl_pct,
    )


def tag_names(pos, all_positions=None, **kwargs) -> set[str]:
    """Convenience: return set of tag names for a position."""
    if all_positions is None:
        all_positions = [pos]
    return {t.pattern_name for t in PatternEngine.tag_position(pos, all_positions, **kwargs)}


# ============================================================================
# Module 2 -- Holding period
# ============================================================================


class TestScalpTag:
    def test_holding_less_than_3(self):
        pos = make_pos(holding_days=1)
        tags = tag_names(pos)
        assert "SCALP" in tags
        assert "SWING" not in tags
        assert "POSITION" not in tags

    def test_holding_2_days(self):
        pos = make_pos(holding_days=2)
        assert "SCALP" in tag_names(pos)

    def test_confidence_is_one(self):
        pos = make_pos(holding_days=1)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "SCALP":
                assert r.confidence == 1.0


class TestSwingTag:
    def test_holding_3_days(self):
        pos = make_pos(holding_days=3)
        tags = tag_names(pos)
        assert "SWING" in tags
        assert "SCALP" not in tags

    def test_holding_30_days(self):
        pos = make_pos(holding_days=30)
        assert "SWING" in tag_names(pos)

    def test_confidence_is_one(self):
        pos = make_pos(holding_days=10)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "SWING":
                assert r.confidence == 1.0


class TestPositionTag:
    def test_holding_greater_than_30(self):
        pos = make_pos(holding_days=31)
        tags = tag_names(pos)
        assert "POSITION" in tags
        assert "SWING" not in tags

    def test_confidence_is_one(self):
        pos = make_pos(holding_days=45)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "POSITION":
                assert r.confidence == 1.0


# ============================================================================
# Module 3 -- Risk & position management
# ============================================================================


class TestStopLossTag:
    def test_negative_pnl(self):
        pos = make_pos(pnl_pct=-0.05)
        assert "STOP_LOSS" in tag_names(pos)

    def test_confidence_point_six(self):
        pos = make_pos(pnl_pct=-0.05)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "STOP_LOSS":
                assert r.confidence == 0.6

    def test_not_tagged_when_profitable(self):
        pos = make_pos(pnl_pct=0.1)
        assert "STOP_LOSS" not in tag_names(pos)


class TestTakeProfitTag:
    def test_positive_pnl(self):
        pos = make_pos(pnl_pct=0.1)
        assert "TAKE_PROFIT" in tag_names(pos)

    def test_confidence_point_six(self):
        pos = make_pos(pnl_pct=0.1)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "TAKE_PROFIT":
                assert r.confidence == 0.6

    def test_not_tagged_when_losing(self):
        pos = make_pos(pnl_pct=-0.05)
        assert "TAKE_PROFIT" not in tag_names(pos)


class TestTurnTag:
    def test_same_day_entry_exit(self):
        pos = make_pos(holding_days=0, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 2))
        assert "TURN" in tag_names(pos)

    def test_not_tagged_for_multi_day(self):
        pos = make_pos(holding_days=5)
        assert "TURN" not in tag_names(pos)

    def test_confidence_point_seven(self):
        d = date(2024, 1, 2)
        pos = make_pos(holding_days=0, entry_date=d, exit_date=d)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "TURN":
                assert r.confidence == 0.7


class TestPyramidTag:
    def test_multiple_entries_higher_avg(self):
        """Second position with higher avg_entry than first gets PYRAMID."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=0.15, entry_date=d, exit_date=date(2024, 1, 8))
        # give p2 a higher avg_entry
        p2.avg_entry_price = 10.5
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "PYRAMID" in tags

    def test_single_position_no_pyramid(self):
        pos = make_pos()
        assert "PYRAMID" not in tag_names(pos)

    def test_confidence_point_eight(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, entry_date=d, exit_date=date(2024, 1, 8), pnl_pct=0.15)
        p2.avg_entry_price = 10.5
        results = PatternEngine.tag_position(p2, [p1, p2])
        for r in results:
            if r.pattern_name == "PYRAMID":
                assert r.confidence == 0.8


class TestAverageDownTag:
    def test_multiple_entries_with_loss(self):
        """Position with same symbol/entry_date and negative pnl gets AVERAGE_DOWN."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "AVERAGE_DOWN" in tags

    def test_not_tagged_when_profitable(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 8))
        assert "AVERAGE_DOWN" not in tag_names(p2, all_positions=[p1, p2])

    def test_confidence_point_eight(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        results = PatternEngine.tag_position(p2, [p1, p2])
        for r in results:
            if r.pattern_name == "AVERAGE_DOWN":
                assert r.confidence == 0.8


class TestCashTag:
    def test_first_position_in_period(self):
        pos = make_pos()
        assert "CASH" in tag_names(pos, all_positions=[pos])

    def test_gap_over_30_days(self):
        p1 = make_pos(holding_days=5, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 7))
        p2 = make_pos(holding_days=5, entry_date=date(2024, 2, 10), exit_date=date(2024, 2, 15))
        # gap = (2024-02-10) - (2024-01-07) = 34 days > 30
        assert "CASH" in tag_names(p2, all_positions=[p1, p2])

    def test_no_gap_no_cash(self):
        p1 = make_pos(holding_days=5, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 7))
        p2 = make_pos(holding_days=5, entry_date=date(2024, 1, 10), exit_date=date(2024, 1, 15))
        # gap = (2024-01-10) - (2024-01-07) = 3 days <= 30
        assert "CASH" not in tag_names(p2, all_positions=[p1, p2])


# ============================================================================
# Module 1 -- Market-dependent entry/exit patterns
# ============================================================================


def _market_data(
    dates: list[str],
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    ma20: float | None = 11.0,
    ma60: float | None = 10.0,
) -> dict:
    """Build minimal market-data dict for one symbol."""
    if highs is None:
        highs = [c * 1.02 for c in closes]
    if lows is None:
        lows = [c * 0.98 for c in closes]
    data = {}
    for i, d in enumerate(dates):
        data[d] = {
            "open": closes[i],
            "high": highs[i],
            "low": lows[i],
            "close": closes[i],
            "ma5": closes[i],
            "ma10": closes[i],
            "ma20": ma20 if ma20 is not None else closes[i],
            "ma60": ma60 if ma60 is not None else closes[i],
        }
    return {"000001": data}


def _market_tags(pos, market_data) -> set[str]:
    return {t.pattern_name for t in PatternEngine.tag_market_patterns(pos, market_data)}


class TestChaseTag:
    def test_chase_detected(self):
        """Entry close > 15% above 5-days-ago close."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]  # 2..26 = 25 days
        closes = [10.0] * 24 + [11.6]  # entry day (idx 24) close = 11.6 >= +16%
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes)
        assert "CHASE" in _market_tags(pos, md)

    def test_not_chase_when_flat(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 25
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes)
        assert "CHASE" not in _market_tags(pos, md)

    def test_not_chase_when_dropping(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 20 + [9.0] * 5
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes)
        assert "CHASE" not in _market_tags(pos, md)


class TestBottomTag:
    def test_bottom_detected(self):
        """Entry close < 15% below 5-days-ago close."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 20 + [8.4] * 5  # entry day (idx 24) close = 8.4 <= -16%
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes)
        assert "BOTTOM" in _market_tags(pos, md)

    def test_not_bottom_when_flat(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 25
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes)
        assert "BOTTOM" not in _market_tags(pos, md)


class TestBreakoutTag:
    def test_breakout_with_mock_data(self):
        """Entry day close exceeds max of prior 20 days high."""
        # Build 25 trading days
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]  # 2..26 = 25 days
        # Days 0..23 have highs in range 10-11.5
        # Day 24 (entry) close = 12.5 > max prev high = 11.5
        highs = []
        closes = []
        for i in range(24):
            h = 10.0 + (i % 8) * 0.2  # peaks at 11.6
            highs.append(h)
            closes.append(h * 0.98)
        # Entry day
        highs.append(13.0)
        closes.append(12.5)

        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes, highs=highs)

        tags = _market_tags(pos, md)
        assert "BREAKOUT" in tags

    def test_confidence(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        highs = []
        closes = []
        for i in range(24):
            h = 10.0 + (i % 8) * 0.2
            highs.append(h)
            closes.append(h * 0.98)
        highs.append(13.0)
        closes.append(12.5)

        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _market_data(dates, closes, highs=highs)
        results = PatternEngine.tag_market_patterns(pos, md)
        for r in results:
            if r.pattern_name == "BREAKOUT":
                assert r.confidence == 0.7


class TestTrendTag:
    def test_trend_when_ma20_above_ma60(self):
        pos = make_pos(entry_date=date(2024, 1, 15))
        md = _market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=11.0,
            ma60=10.0,
        )
        assert "TREND" in _market_tags(pos, md)

    def test_not_trend_when_ma20_below_ma60(self):
        pos = make_pos(entry_date=date(2024, 1, 15))
        md = _market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=10.0,
            ma60=11.0,
        )
        assert "TREND" not in _market_tags(pos, md)


class TestCounterTrendTag:
    def test_counter_trend_when_ma20_below_ma60(self):
        pos = make_pos(entry_date=date(2024, 1, 15))
        md = _market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=10.0,
            ma60=11.0,
        )
        assert "COUNTER_TREND" in _market_tags(pos, md)

    def test_not_counter_trend_when_ma20_above_ma60(self):
        pos = make_pos(entry_date=date(2024, 1, 15))
        md = _market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=11.0,
            ma60=10.0,
        )
        assert "COUNTER_TREND" not in _market_tags(pos, md)


class TestBreakdownTag:
    def test_breakdown_on_exit(self):
        """Exit close < min(prev 20 days low)."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 28)]  # 2..27 = 26 days
        # First 25 days: lows stable at ~9.8
        # Day 26 (exit): close = 9.0 < min prev low = 9.8
        lows = [9.8] * 25 + [8.5]
        closes = [10.0] * 25 + [9.0]
        highs = [10.5] * 25 + [9.5]

        pos = make_pos(
            entry_date=date(2024, 1, 2),
            exit_date=date(2024, 1, 27),
            holding_days=25,
        )
        md = _market_data(dates, closes, highs=highs, lows=lows)
        assert "BREAKDOWN" in _market_tags(pos, md)

    def test_not_breakdown_when_normal(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 28)]
        lows = [9.8] * 26
        closes = [10.0] * 26
        pos = make_pos(
            entry_date=date(2024, 1, 2),
            exit_date=date(2024, 1, 27),
            holding_days=25,
        )
        md = _market_data(dates, closes, lows=lows)
        assert "BREAKDOWN" not in _market_tags(pos, md)


# ============================================================================
# Edge cases
# ============================================================================


class TestNoMarketData:
    def test_empty_market_data_returns_empty(self):
        pos = make_pos()
        assert PatternEngine.tag_market_patterns(pos, {}) == []

    def test_missing_symbol_returns_empty(self):
        pos = make_pos()
        md = {"OTHER": {}}
        assert PatternEngine.tag_market_patterns(pos, md) == []

    def test_missing_entry_date_returns_empty(self):
        pos = make_pos()
        md = {"000001": {"2024-02-01": {"close": 10}}}
        assert PatternEngine.tag_market_patterns(pos, md) == []


class TestTagCoexistence:
    def test_scalp_and_turn_can_coexist(self):
        """A same-day trade can be both SCALP and TURN."""
        d = date(2024, 1, 2)
        pos = make_pos(holding_days=0, entry_date=d, exit_date=d)
        tags = tag_names(pos, all_positions=[pos])
        assert "SCALP" in tags
        assert "TURN" in tags

    def test_stop_loss_and_average_down_can_coexist(self):
        """A losing position in a multi-entry day is both."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "AVERAGE_DOWN" in tags
        assert "STOP_LOSS" in tags
