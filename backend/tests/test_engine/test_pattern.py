"""Tests for pattern engine -- all 20 behavioral tags (Phase 3)."""
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


@dataclass
class _Trade:
    """Minimal trade-like object for testing TURN detection."""
    symbol: str = "000001"
    side: str = "BUY"
    date: date = date(2024, 1, 2)


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


def _make_market_data(
    dates: list[str],
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    ma20: float | None = 11.0,
    ma60: float | None = 10.0,
    ma5: float | None = None,
    ma10: float | None = None,
    volume: list[float] | None = None,
    avg_volume_20d: float | None = None,
) -> dict:
    """Build market-data dict for one symbol, with optional volume data."""
    if highs is None:
        highs = [c * 1.02 for c in closes]
    if lows is None:
        lows = [c * 0.98 for c in closes]
    data = {}
    for i, d in enumerate(dates):
        entry = {
            "open": closes[i],
            "high": highs[i],
            "low": lows[i],
            "close": closes[i],
            "ma5": ma5 if ma5 is not None else closes[i],
            "ma10": ma10 if ma10 is not None else closes[i],
            "ma20": ma20 if ma20 is not None else closes[i],
            "ma60": ma60 if ma60 is not None else closes[i],
        }
        if volume is not None:
            entry["volume"] = volume[i]
        if avg_volume_20d is not None:
            entry["avg_volume_20d"] = avg_volume_20d
        data[d] = entry
    return {"000001": data}


def _market_tags(pos, market_data) -> set[str]:
    return {t.pattern_name for t in PatternEngine.tag_market_patterns(pos, market_data)}


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


class TestSmallLossExitTag:
    def test_small_loss_within_stop(self):
        """Loss within -8% and held <= 10 days is a small loss exit."""
        pos = make_pos(pnl_pct=-0.05, holding_days=5)
        assert "SMALL_LOSS_EXIT" in tag_names(pos)

    def test_at_boundary_minus_eight(self):
        """Loss at exactly -8% boundary still qualifies."""
        pos = make_pos(pnl_pct=-0.08, holding_days=3)
        assert "SMALL_LOSS_EXIT" in tag_names(pos)

    def test_confidence_point_six(self):
        pos = make_pos(pnl_pct=-0.05)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "SMALL_LOSS_EXIT":
                assert r.confidence == 0.6

    def test_not_tagged_when_profitable(self):
        pos = make_pos(pnl_pct=0.1)
        assert "SMALL_LOSS_EXIT" not in tag_names(pos)

    def test_not_tagged_when_loss_exceeds_eight_percent(self):
        """Loss > 8% (e.g. bagholding) should NOT be tagged as small loss exit."""
        pos = make_pos(pnl_pct=-0.09, holding_days=5)
        assert "SMALL_LOSS_EXIT" not in tag_names(pos)

    def test_not_tagged_when_held_too_long(self):
        """Loss held > 10 days should NOT be tagged as small loss exit."""
        pos = make_pos(pnl_pct=-0.05, holding_days=11)
        assert "SMALL_LOSS_EXIT" not in tag_names(pos)


class TestTakeProfitTag:
    def test_quick_profit(self):
        """Small profit < 5% held < 5 days is QUICK_PROFIT."""
        pos = make_pos(pnl_pct=0.03, holding_days=2)
        tags = tag_names(pos)
        assert "QUICK_PROFIT" in tags
        assert "NORMAL_PROFIT" not in tags
        assert "BIG_WIN" not in tags

    def test_normal_profit(self):
        """Profit between 5% and 20% is NORMAL_PROFIT."""
        pos = make_pos(pnl_pct=0.10, holding_days=8)
        tags = tag_names(pos)
        assert "NORMAL_PROFIT" in tags
        assert "QUICK_PROFIT" not in tags
        assert "BIG_WIN" not in tags

    def test_normal_profit_boundary_lower(self):
        """Profit at exactly 5% qualifies as NORMAL_PROFIT."""
        pos = make_pos(pnl_pct=0.05, holding_days=5)
        tags = tag_names(pos)
        assert "NORMAL_PROFIT" in tags
        assert "QUICK_PROFIT" not in tags

    def test_normal_profit_boundary_upper(self):
        """Profit at exactly 20% qualifies as NORMAL_PROFIT."""
        pos = make_pos(pnl_pct=0.20, holding_days=8)
        tags = tag_names(pos)
        assert "NORMAL_PROFIT" in tags
        assert "BIG_WIN" not in tags

    def test_big_win(self):
        """Profit > 20% is BIG_WIN."""
        pos = make_pos(pnl_pct=0.25, holding_days=10)
        tags = tag_names(pos)
        assert "BIG_WIN" in tags
        assert "NORMAL_PROFIT" not in tags
        assert "QUICK_PROFIT" not in tags

    def test_not_tagged_when_losing(self):
        pos = make_pos(pnl_pct=-0.05)
        tags = tag_names(pos)
        assert "QUICK_PROFIT" not in tags
        assert "NORMAL_PROFIT" not in tags
        assert "BIG_WIN" not in tags

    def test_quick_profit_confidence(self):
        pos = make_pos(pnl_pct=0.03, holding_days=2)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "QUICK_PROFIT":
                assert r.confidence == 0.6

    def test_normal_profit_confidence(self):
        pos = make_pos(pnl_pct=0.10)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "NORMAL_PROFIT":
                assert r.confidence == 0.6

    def test_big_win_confidence(self):
        pos = make_pos(pnl_pct=0.25)
        results = PatternEngine.tag_position(pos, [pos])
        for r in results:
            if r.pattern_name == "BIG_WIN":
                assert r.confidence == 0.6


class TestTurnTag:
    def test_same_day_entry_exit_fallback(self):
        """Same-day entry/exit with multiple sibling positions gets TURN (fallback)."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=0, entry_date=d, exit_date=d, pnl_pct=0.01)
        p2 = make_pos(holding_days=0, entry_date=d, exit_date=d, pnl_pct=0.02)
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "TURN" in tags

    def test_same_day_single_position_no_turn_fallback(self):
        """Single same-day position without trades param should NOT get TURN (needs same_ep > 1)."""
        d = date(2024, 1, 2)
        pos = make_pos(holding_days=0, entry_date=d, exit_date=d)
        tags = tag_names(pos, all_positions=[pos])
        assert "TURN" not in tags

    def test_not_tagged_for_multi_day(self):
        pos = make_pos(holding_days=5)
        assert "TURN" not in tag_names(pos)

    def test_confidence_point_seven(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=0, entry_date=d, exit_date=d, pnl_pct=0.01)
        p2 = make_pos(holding_days=0, entry_date=d, exit_date=d, pnl_pct=0.02)
        results = PatternEngine.tag_position(p2, [p1, p2])
        for r in results:
            if r.pattern_name == "TURN":
                assert r.confidence == 0.7

    def test_trades_with_both_sides_gets_turn(self):
        """Trades with same symbol and date having both BUY/SELL gets TURN."""
        d = date(2024, 1, 2)
        pos = make_pos(holding_days=5, entry_date=d, exit_date=date(2024, 1, 7))
        trades = [
            _Trade(symbol="000001", side="BUY", date=d),
            _Trade(symbol="000001", side="SELL", date=d),
        ]
        tags = tag_names(pos, all_positions=[pos], trades=trades)
        assert "TURN" in tags

    def test_trades_no_opposite_side_no_turn(self):
        """Trades with only BUY side should NOT get TURN."""
        d = date(2024, 1, 2)
        pos = make_pos(holding_days=5, entry_date=d, exit_date=date(2024, 1, 7))
        trades = [
            _Trade(symbol="000001", side="BUY", date=d),
        ]
        tags = tag_names(pos, all_positions=[pos], trades=trades)
        assert "TURN" not in tags


class TestPyramidTag:
    def test_position_with_profit_gets_pyramid(self):
        """Position in profit (pnl_pct >= 0) on a multi-entry day gets PYRAMID."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=0.15, entry_date=d, exit_date=date(2024, 1, 8))
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "PYRAMID" in tags

    def test_losing_position_no_pyramid(self):
        """Position in loss (pnl_pct < 0) should NOT get PYRAMID even with higher avg_entry."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        p2.avg_entry_price = 10.5
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "PYRAMID" not in tags

    def test_single_position_no_pyramid(self):
        pos = make_pos()
        assert "PYRAMID" not in tag_names(pos)

    def test_confidence_point_eight(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, entry_date=d, exit_date=date(2024, 1, 8), pnl_pct=0.15)
        results = PatternEngine.tag_position(p2, [p1, p2])
        for r in results:
            if r.pattern_name == "PYRAMID":
                assert r.confidence == 0.8


class TestAverageDownTag:
    def test_multiple_entries_with_loss(self):
        """Position with same symbol/entry_date, lower avg_entry, and negative pnl gets AVERAGE_DOWN."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        p2.avg_entry_price = 9.5  # lower than first position's 10.0
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "AVERAGE_DOWN" in tags

    def test_loss_without_lower_avg_not_average_down(self):
        """Losing position but avg_entry >= first_entry_avg should NOT get AVERAGE_DOWN."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "AVERAGE_DOWN" not in tags

    def test_not_tagged_when_profitable(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 8))
        assert "AVERAGE_DOWN" not in tag_names(p2, all_positions=[p1, p2])

    def test_confidence_point_eight(self):
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        p2.avg_entry_price = 9.5
        results = PatternEngine.tag_position(p2, [p1, p2])
        for r in results:
            if r.pattern_name == "AVERAGE_DOWN":
                assert r.confidence == 0.8


class TestCashTag:
    def test_first_position_in_period(self):
        pos = make_pos()
        results = PatternEngine.detect_cooldowns(pos, [pos])
        names = {r.pattern_name for r in results}
        assert "CASH" in names

    def test_gap_over_30_days(self):
        p1 = make_pos(holding_days=5, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 7))
        p2 = make_pos(holding_days=5, entry_date=date(2024, 2, 10), exit_date=date(2024, 2, 15))
        # gap = (2024-02-10) - (2024-01-07) = 34 days > 30
        results = PatternEngine.detect_cooldowns(p2, [p1, p2])
        names = {r.pattern_name for r in results}
        assert "CASH" in names

    def test_no_gap_no_cash(self):
        p1 = make_pos(holding_days=5, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 7))
        p2 = make_pos(holding_days=5, entry_date=date(2024, 1, 10), exit_date=date(2024, 1, 15))
        # gap = (2024-01-10) - (2024-01-07) = 3 days <= 30
        results = PatternEngine.detect_cooldowns(p2, [p1, p2])
        names = {r.pattern_name for r in results}
        assert "CASH" not in names

    def test_not_emitted_from_tag_position(self):
        """CASH should NOT appear in tag_position() output."""
        pos = make_pos()
        tags = PatternEngine.tag_position(pos, [pos])
        assert "CASH" not in {t.pattern_name for t in tags}


# ============================================================================
# Module 1 -- Market-dependent entry/exit patterns
# ============================================================================


class TestChaseTag:
    def test_chase_detected(self):
        """Entry close > 15% above 5-days-ago close."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]  # 2..26 = 25 days
        closes = [10.0] * 24 + [11.6]  # entry day (idx 24) close = 11.6 >= +16%
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)
        assert "CHASE" in _market_tags(pos, md)

    def test_not_chase_when_flat(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 25
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)
        assert "CHASE" not in _market_tags(pos, md)

    def test_not_chase_when_dropping(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 20 + [9.0] * 5
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)
        assert "CHASE" not in _market_tags(pos, md)

    def test_chase_full_confidence(self):
        """All conditions met (5d return, MA deviation, high proximity) -> 0.7."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        # entry_close=13.0, 5d return=30%, ma20=11 -> 13>12.1,
        # prev_20d_high=10.2 -> 13>=9.89
        closes = [10.0] * 24 + [13.0]
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)
        results = PatternEngine.tag_market_patterns(pos, md)
        for r in results:
            if r.pattern_name == "CHASE":
                assert r.confidence == 0.7

    def test_chase_low_confidence_without_ma_deviation(self):
        """Only 5d return holds, MA deviation fails -> 0.5."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        # entry_close=11.6, ma20=11 -> 11.6 > 12.1? No -> MA condition fails
        # prev_20d_high=10.2 -> 11.6 >= 9.89? Yes -> high proximity OK
        closes = [10.0] * 24 + [11.6]
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)
        results = PatternEngine.tag_market_patterns(pos, md)
        for r in results:
            if r.pattern_name == "CHASE":
                assert r.confidence == 0.5


class TestBottomTag:
    def test_bottom_detected(self):
        """Entry close < 15% below 5-days-ago close, with downtrend."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 20 + [8.4] * 5  # entry day (idx 24) close = 8.4 <= -16%
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes, ma20=10.0, ma60=11.0)  # downtrend
        assert "BOTTOM" in _market_tags(pos, md)

    def test_not_bottom_when_flat(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 25
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes, ma20=10.0, ma60=11.0)
        assert "BOTTOM" not in _market_tags(pos, md)

    def test_not_bottom_when_uptrend(self):
        """5d drop > 15% but in uptrend (ma20 > ma60) -> no BOTTOM."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 20 + [8.4] * 5
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)  # default ma20=11, ma60=10 -> uptrend
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
        md = _make_market_data(dates, closes, highs=highs)

        tags = _market_tags(pos, md)
        assert "BREAKOUT" in tags

    def test_breakout_backward_compat_confidence(self):
        """Without volume data, confidence is 0.5 (backward compat)."""
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
        md = _make_market_data(dates, closes, highs=highs)
        results = PatternEngine.tag_market_patterns(pos, md)
        for r in results:
            if r.pattern_name == "BREAKOUT":
                assert r.confidence == 0.5

    def test_breakout_with_volume_confirmation(self):
        """Breakout with sufficient volume gets confidence 0.7."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        highs = []
        closes = []
        volumes = []
        for i in range(24):
            h = 10.0 + (i % 8) * 0.2
            highs.append(h)
            closes.append(h * 0.98)
            volumes.append(100000)
        # Entry day
        highs.append(13.0)
        closes.append(12.5)
        volumes.append(300000)  # 300k > 1.5 * 150k = 225k

        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(
            dates, closes, highs=highs,
            volume=volumes, avg_volume_20d=150000.0,
        )
        tags = _market_tags(pos, md)
        assert "BREAKOUT" in tags

        results = PatternEngine.tag_market_patterns(pos, md)
        for r in results:
            if r.pattern_name == "BREAKOUT":
                assert r.confidence == 0.7

    def test_not_breakout_insufficient_volume(self):
        """Price breaks out but volume is insufficient -> no tag."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        highs = []
        closes = []
        volumes = []
        for i in range(24):
            h = 10.0 + (i % 8) * 0.2
            highs.append(h)
            closes.append(h * 0.98)
            volumes.append(100000)
        # Entry day
        highs.append(13.0)
        closes.append(12.5)
        volumes.append(100000)  # 100k < 1.5 * 150k = 225k -> insufficient

        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(
            dates, closes, highs=highs,
            volume=volumes, avg_volume_20d=150000.0,
        )
        assert "BREAKOUT" not in _market_tags(pos, md)


class TestTrendTag:
    def test_trend_when_ma20_above_ma60_and_price_above_ma20(self):
        """ma20 > ma60 and close > ma20 -> TREND."""
        pos = make_pos(entry_date=date(2024, 1, 15))
        # entry_date = Jan 15, which is index 13 in the dates list
        # set entry day close > ma20=11.0
        closes = [10.0] * 13 + [12.0] + [10.0] * 4
        md = _make_market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            closes,
            ma20=11.0,
            ma60=10.0,
        )
        assert "TREND" in _market_tags(pos, md)

    def test_not_trend_when_ma20_below_ma60(self):
        pos = make_pos(entry_date=date(2024, 1, 15))
        md = _make_market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=10.0,
            ma60=11.0,
        )
        assert "TREND" not in _market_tags(pos, md)

    def test_not_trend_when_price_below_ma20(self):
        """ma20 > ma60 but price below ma20 -> no TREND."""
        pos = make_pos(entry_date=date(2024, 1, 15))
        ma20 = 11.0
        # entry close = 10.0 < ma20 = 11.0 -> price confirmation fails
        md = _make_market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=ma20,
            ma60=10.0,
        )
        assert "TREND" not in _market_tags(pos, md)


class TestCounterTrendTag:
    def test_counter_trend_when_ma20_below_ma60_and_price_below_ma20(self):
        """ma20 < ma60 and close < ma20 -> COUNTER_TREND."""
        pos = make_pos(entry_date=date(2024, 1, 15))
        # entry_date = Jan 15 (index 13), set close < ma20=10.0
        closes = [10.0] * 13 + [9.5] + [10.0] * 4
        md = _make_market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            closes,
            ma20=10.0,
            ma60=11.0,
        )
        assert "COUNTER_TREND" in _market_tags(pos, md)

    def test_not_counter_trend_when_ma20_above_ma60(self):
        pos = make_pos(entry_date=date(2024, 1, 15))
        md = _make_market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            [10.0] * 18,
            ma20=11.0,
            ma60=10.0,
        )
        assert "COUNTER_TREND" not in _market_tags(pos, md)

    def test_not_counter_trend_when_price_above_ma20(self):
        """ma20 < ma60 but price above ma20 -> no COUNTER_TREND."""
        pos = make_pos(entry_date=date(2024, 1, 15))
        # entry close = 12.0 > ma20 = 10.0 -> price confirmation fails
        closes = [10.0] * 13 + [12.0] + [10.0] * 4
        md = _make_market_data(
            [f"2024-01-{d:02d}" for d in range(2, 20)],
            closes,
            ma20=10.0,
            ma60=11.0,
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
        md = _make_market_data(dates, closes, highs=highs, lows=lows)
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
        md = _make_market_data(dates, closes, lows=lows)
        assert "BREAKDOWN" not in _market_tags(pos, md)


# ============================================================================
# Phase 3 — Psychological behavior tags (risk module)
# ============================================================================


class TestRevengeTag:
    """REVENGE: new trade within 24h after a significant losing position with increased position."""

    def test_revenge_after_loss(self):
        """New position within 1 day after a significant loser with increased position gets REVENGE."""
        d = date(2024, 1, 2)
        # Losing position 1: small loss
        p1 = make_pos(pnl_pct=-0.01, entry_date=d, exit_date=d + timedelta(days=3), holding_days=3, symbol="A")
        # Losing position 2 (prior): large loss
        p2 = make_pos(pnl_pct=-0.10, entry_date=d + timedelta(days=4), exit_date=d + timedelta(days=7), holding_days=3, symbol="B")
        # p2 exit = Jan 9, p3 entry = Jan 10 => gap = 1 day
        # avg_loss = (abs(p1.pnl) + abs(p2.pnl)) / 2
        p3 = make_pos(entry_date=d + timedelta(days=8), symbol="C")
        p3.total_quantity = 200  # > p2's 100
        tags = tag_names(p3, all_positions=[p1, p2, p3])
        assert "REVENGE" in tags

    def test_not_revenge_when_profitable_prior(self):
        """Prior position with profit does not trigger REVENGE."""
        p1 = make_pos(pnl_pct=0.05, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), holding_days=3)
        p2 = make_pos(entry_date=date(2024, 1, 6))
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "REVENGE" not in tags

    def test_not_revenge_when_gap_too_large(self):
        """Gap > 1 day does not trigger REVENGE."""
        p1 = make_pos(pnl_pct=-0.05, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), holding_days=3)
        p2 = make_pos(entry_date=date(2024, 1, 10))  # gap = 5 days
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "REVENGE" not in tags

    def test_not_revenge_when_no_prior(self):
        """No prior position -> no REVENGE."""
        pos = make_pos()
        tags = tag_names(pos, all_positions=[pos])
        assert "REVENGE" not in tags

    def test_not_revenge_when_insufficient_loss(self):
        """Prior loss + gap <= 1 day but loss not significant enough -> no REVENGE."""
        d = date(2024, 1, 2)
        # Only one losing position: avg_loss = abs(p1.pnl)
        # abs(p1.pnl) > avg_loss * 1.5 is impossible with only one loser
        p1 = make_pos(pnl_pct=-0.05, entry_date=d, exit_date=d + timedelta(days=3), holding_days=3, symbol="A")
        p2 = make_pos(entry_date=d + timedelta(days=4), symbol="B")  # gap = 1 day
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "REVENGE" not in tags

    def test_not_revenge_when_position_not_increased(self):
        """Prior loss + gap + significant loss but position not increased -> no REVENGE."""
        d = date(2024, 1, 2)
        p1 = make_pos(pnl_pct=-0.01, entry_date=d, exit_date=d + timedelta(days=3), holding_days=3, symbol="A")
        p2 = make_pos(pnl_pct=-0.10, entry_date=d + timedelta(days=4), exit_date=d + timedelta(days=7), holding_days=3, symbol="B")
        p3 = make_pos(entry_date=d + timedelta(days=8), symbol="C")
        # p3.total_quantity stays at 100, same as p2.total_quantity
        tags = tag_names(p3, all_positions=[p1, p2, p3])
        assert "REVENGE" not in tags

    def test_revenge_confidence(self):
        d = date(2024, 1, 2)
        p1 = make_pos(pnl_pct=-0.01, entry_date=d, exit_date=d + timedelta(days=3), holding_days=3, symbol="A")
        p2 = make_pos(pnl_pct=-0.10, entry_date=d + timedelta(days=4), exit_date=d + timedelta(days=7), holding_days=3, symbol="B")
        p3 = make_pos(entry_date=d + timedelta(days=8), symbol="C")
        p3.total_quantity = 200
        results = PatternEngine.tag_position(p3, [p1, p2, p3])
        for r in results:
            if r.pattern_name == "REVENGE":
                assert r.confidence == 0.7


class TestOverTradingTag:
    """OVERTRADING: daily frequency at 95th percentile."""

    def test_overtrading_detected(self):
        """Day with many positions vs mostly 1/day gets tagged (95th percentile)."""
        base_date = date(2024, 1, 2)
        positions = []
        # 20 days with 1 position each
        for i in range(20):
            d = base_date + timedelta(days=i)
            positions.append(make_pos(symbol=f"A{i}", entry_date=d))
        # 1 day with 8 positions (to exceed 95th percentile)
        heavy_day = base_date + timedelta(days=21)
        for i in range(8):
            positions.append(make_pos(symbol=f"B{i}", entry_date=heavy_day))

        tags = tag_names(positions[20], all_positions=positions)  # first position on heavy day
        assert "OVERTRADING" in tags

    def test_not_overtrading_when_normal(self):
        """Normal frequency (1/day for 20+ days) does not trigger OVERTRADING."""
        base_date = date(2024, 1, 2)
        positions = []
        for i in range(21):
            d = base_date + timedelta(days=i)
            positions.append(make_pos(symbol=f"A{i}", entry_date=d))
        tags = tag_names(positions[0], all_positions=positions)
        assert "OVERTRADING" not in tags

    def test_not_overtrading_when_few_trading_days(self):
        """With fewer than 20 unique trading days, don't tag."""
        positions = [
            make_pos(symbol="A", entry_date=date(2024, 1, 2)),
            make_pos(symbol="B", entry_date=date(2024, 1, 2)),
        ]
        tags = tag_names(positions[0], all_positions=positions)
        assert "OVERTRADING" not in tags

    def test_all_positions_on_day_get_tagged(self):
        """All positions sharing the high-frequency day get tagged; others don't."""
        base_date = date(2024, 1, 2)
        positions = []
        for i in range(20):
            d = base_date + timedelta(days=i)
            positions.append(make_pos(symbol=f"A{i}", entry_date=d))
        heavy_day = base_date + timedelta(days=21)
        for i in range(8):
            positions.append(make_pos(symbol=f"B{i}", entry_date=heavy_day))

        assert "OVERTRADING" in tag_names(positions[20], all_positions=positions)
        assert "OVERTRADING" in tag_names(positions[25], all_positions=positions)
        assert "OVERTRADING" not in tag_names(positions[0], all_positions=positions)

    def test_overtrading_confidence(self):
        base_date = date(2024, 1, 2)
        positions = []
        for i in range(20):
            d = base_date + timedelta(days=i)
            positions.append(make_pos(symbol=f"A{i}", entry_date=d))
        heavy_day = base_date + timedelta(days=21)
        for i in range(8):
            positions.append(make_pos(symbol=f"B{i}", entry_date=heavy_day))

        results = PatternEngine.tag_position(positions[20], positions)
        for r in results:
            if r.pattern_name == "OVERTRADING":
                assert r.confidence == 0.7


class TestHoldLoserTag:
    """HOLD_LOSER: holding losers much longer than winners (median-based, >=5 each)."""

    def test_hold_loser_detected(self):
        """Loser held longer than winner median * 1.5 and above median loser hold."""
        positions = [
            # 5 winners: short holding
            make_pos(pnl_pct=0.05, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=4, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 6), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W5"),
            # 5 losers: long holding
            make_pos(pnl_pct=-0.03, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=15, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 17), symbol="L5"),
        ]
        # Winners median: sorted [2, 2, 3, 3, 4] -> median = 3
        # Losers median: sorted [8, 9, 10, 12, 15] -> median = 10
        # 10 > 3 * 1.5 = 4.5 ✓
        # Target L5: pnl<0 ✓, 15 > 10 ✓
        tags = tag_names(positions[9], all_positions=positions)
        assert "HOLD_LOSER" in tags

    def test_not_hold_loser_when_no_losers(self):
        all_winners = [
            make_pos(pnl_pct=0.05, holding_days=3),
            make_pos(pnl_pct=0.10, holding_days=5),
        ]
        tags = tag_names(all_winners[0], all_positions=all_winners)
        assert "HOLD_LOSER" not in tags

    def test_not_hold_loser_when_no_winners(self):
        all_losers = [
            make_pos(pnl_pct=-0.05, holding_days=8),
            make_pos(pnl_pct=-0.03, holding_days=5),
        ]
        tags = tag_names(all_losers[0], all_positions=all_losers)
        assert "HOLD_LOSER" not in tags

    def test_not_hold_loser_when_ratio_below_threshold(self):
        """Ratio below 1.5 doesn't trigger."""
        positions = [
            # 5 winners: moderate holding
            make_pos(pnl_pct=0.05, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="W5"),
            # 5 losers: similar holding
            make_pos(pnl_pct=-0.03, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=11, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 13), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L5"),
        ]
        # Winners median: sorted [8, 8, 9, 9, 10] -> median = 9
        # Losers median: sorted [9, 10, 10, 11, 12] -> median = 10
        # 10 > 9 * 1.5 = 13.5? No -> no tag
        tags = tag_names(positions[9], all_positions=positions)
        assert "HOLD_LOSER" not in tags

    def test_hold_loser_confidence(self):
        positions = [
            make_pos(pnl_pct=0.05, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=4, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 6), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W5"),
            make_pos(pnl_pct=-0.03, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=15, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 17), symbol="L5"),
        ]
        results = PatternEngine.tag_position(positions[9], positions)
        for r in results:
            if r.pattern_name == "HOLD_LOSER":
                assert r.confidence == 0.7


class TestCutWinnerTag:
    """CUT_WINNER: cutting winners short while letting losers run (median-based, >=5 each)."""

    def test_cut_winner_detected(self):
        """Winner cut shorter than loser median * 0.5 and below median winner hold."""
        positions = [
            # 5 winners: short holding
            make_pos(pnl_pct=0.05, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=4, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 6), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W5"),
            # 5 losers: long holding
            make_pos(pnl_pct=-0.03, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=15, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 17), symbol="L5"),
        ]
        # Winners median: sorted [2, 2, 3, 3, 4] -> median = 3
        # Losers median: sorted [8, 9, 10, 12, 15] -> median = 10
        # 3 < 10 * 0.5 = 5 ✓
        # Target W1: pnl>0 ✓, 2 < 3 ✓
        tags = tag_names(positions[0], all_positions=positions)
        assert "CUT_WINNER" in tags

    def test_not_cut_winner_when_no_winners(self):
        all_losers = [
            make_pos(pnl_pct=-0.05, holding_days=8),
            make_pos(pnl_pct=-0.03, holding_days=5),
        ]
        tags = tag_names(all_losers[0], all_positions=all_losers)
        assert "CUT_WINNER" not in tags

    def test_not_cut_winner_when_no_losers(self):
        all_winners = [
            make_pos(pnl_pct=0.05, holding_days=3),
            make_pos(pnl_pct=0.10, holding_days=5),
        ]
        tags = tag_names(all_winners[0], all_positions=all_winners)
        assert "CUT_WINNER" not in tags

    def test_not_cut_winner_when_ratio_above_threshold(self):
        """Ratio above 0.5 doesn't trigger."""
        positions = [
            make_pos(pnl_pct=0.05, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="W5"),
            make_pos(pnl_pct=-0.03, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=11, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 13), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L5"),
        ]
        # Winners median: sorted [8, 8, 9, 9, 10] -> median = 9
        # Losers median: sorted [9, 10, 10, 11, 12] -> median = 10
        # 9 < 10 * 0.5 = 5? No -> no tag
        tags = tag_names(positions[0], all_positions=positions)
        assert "CUT_WINNER" not in tags

    def test_cut_winner_confidence(self):
        positions = [
            make_pos(pnl_pct=0.05, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=4, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 6), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W5"),
            make_pos(pnl_pct=-0.03, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=15, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 17), symbol="L5"),
        ]
        results = PatternEngine.tag_position(positions[0], positions)
        for r in results:
            if r.pattern_name == "CUT_WINNER":
                assert r.confidence == 0.7


class TestFomoTag:
    """FOMO: entry near day's high after streak of up days."""

    def test_fomo_detected(self):
        """3+ up days in last 5 and entry near high."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]  # 25 days
        closes = [10.0] * 19 + [10.3, 10.5, 10.8, 11.0, 11.3] + [12.0]
        # 5 up days before entry ✓, entry_close=12.0
        highs = [c * 1.03 for c in closes]
        highs[-1] = 12.1  # 12.0 >= 12.1*0.98=11.858 ✓
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes, highs=highs)
        assert "FOMO" in _market_tags(pos, md)

    def test_not_fomo_when_no_up_days(self):
        """Flat before entry -> no FOMO."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 24 + [12.0]
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes)
        assert "FOMO" not in _market_tags(pos, md)

    def test_not_fomo_when_not_near_high(self):
        """Entry not close to day's high -> no FOMO."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 19 + [10.3, 10.5, 10.8, 11.0, 11.3] + [11.5]
        highs = [c * 1.03 for c in closes]
        # entry high = 11.5*1.03=11.845, 11.5 >= 11.845*0.98=11.608? No!
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes, highs=highs)
        assert "FOMO" not in _market_tags(pos, md)

    def test_not_fomo_when_insufficient_data(self):
        """Less than 5 days of data -> no FOMO."""
        dates = [f"2024-01-{d:02d}" for d in range(2, 7)]  # 5 days
        closes = [10.0, 10.3, 10.5, 10.8, 11.0]
        pos = make_pos(entry_date=date(2024, 1, 6))
        md = _make_market_data(dates, closes)
        assert "FOMO" not in _market_tags(pos, md)

    def test_fomo_confidence(self):
        dates = [f"2024-01-{d:02d}" for d in range(2, 27)]
        closes = [10.0] * 19 + [10.3, 10.5, 10.8, 11.0, 11.3] + [12.0]
        highs = [c * 1.03 for c in closes]
        highs[-1] = 12.1
        pos = make_pos(entry_date=date(2024, 1, 26))
        md = _make_market_data(dates, closes, highs=highs)
        results = PatternEngine.tag_market_patterns(pos, md)
        for r in results:
            if r.pattern_name == "FOMO":
                assert r.confidence == 0.7


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
        """A same-day trade with multiple siblings can be both SCALP and TURN."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=0, entry_date=d, exit_date=d, pnl_pct=0.01)
        p2 = make_pos(holding_days=0, entry_date=d, exit_date=d, pnl_pct=0.02)
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "SCALP" in tags
        assert "TURN" in tags

    def test_scalp_and_turn_via_trades(self):
        """A trade can be SCALP and TURN via trades parameter even with single position."""
        d = date(2024, 1, 2)
        pos = make_pos(holding_days=0, entry_date=d, exit_date=d)
        trades = [
            _Trade(symbol="000001", side="BUY", date=d),
            _Trade(symbol="000001", side="SELL", date=d),
        ]
        tags = tag_names(pos, all_positions=[pos], trades=trades)
        assert "SCALP" in tags
        assert "TURN" in tags

    def test_small_loss_exit_and_average_down_can_coexist(self):
        """A losing position in a multi-entry day is both."""
        d = date(2024, 1, 2)
        p1 = make_pos(holding_days=3, pnl_pct=0.1, entry_date=d, exit_date=date(2024, 1, 5))
        p2 = make_pos(holding_days=6, pnl_pct=-0.05, entry_date=d, exit_date=date(2024, 1, 8))
        p2.avg_entry_price = 9.5  # lower than first position's 10.0
        tags = tag_names(p2, all_positions=[p1, p2])
        assert "AVERAGE_DOWN" in tags
        assert "SMALL_LOSS_EXIT" in tags


# ============================================================================
# Tag Priority System
# ============================================================================


class TestTagPriority:
    """Overlapping tag resolution: CUT_WINNER > QUICK_PROFIT, HOLD_LOSER > SMALL_LOSS_EXIT."""

    def test_cut_winner_removes_quick_profit(self):
        """When CUT_WINNER is present, QUICK_PROFIT should be removed."""
        # A winner with holding_days=2, pnl_pct=0.03 would get both
        # CUT_WINNER (if median check passes) and QUICK_PROFIT
        positions = [
            make_pos(pnl_pct=0.05, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=4, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 6), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W5"),
            make_pos(pnl_pct=-0.03, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=12, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 14), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=15, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 17), symbol="L5"),
        ]
        # Check W3 (pnl_pct=0.03, holding_days=2) — would get both QUICK_PROFIT and CUT_WINNER
        tags = tag_names(positions[2], all_positions=positions)
        assert "CUT_WINNER" in tags
        assert "QUICK_PROFIT" not in tags

    def test_hold_loser_removes_small_loss_exit(self):
        """When HOLD_LOSER is present, SMALL_LOSS_EXIT should be removed."""
        # Winners: [2, 2, 3, 3, 4] -> median = 3
        # Losers: [8, 8, 9, 9, 10] -> median = 9
        # 9 > 3 * 1.5 = 4.5 ✓
        positions = [
            make_pos(pnl_pct=0.05, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W1"),
            make_pos(pnl_pct=0.10, holding_days=2, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 4), symbol="W2"),
            make_pos(pnl_pct=0.03, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W3"),
            make_pos(pnl_pct=0.08, holding_days=3, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 5), symbol="W4"),
            make_pos(pnl_pct=0.06, holding_days=4, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 6), symbol="W5"),
            make_pos(pnl_pct=-0.03, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L1"),
            make_pos(pnl_pct=-0.05, holding_days=8, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 10), symbol="L2"),
            make_pos(pnl_pct=-0.02, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L3"),
            make_pos(pnl_pct=-0.04, holding_days=9, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 11), symbol="L4"),
            make_pos(pnl_pct=-0.06, holding_days=10, entry_date=date(2024, 1, 2), exit_date=date(2024, 1, 12), symbol="L5"),
        ]
        # L5: pnl_pct=-0.06, holding_days=10
        # HOLD_LOSER: pnl<0 ✓, 10 > 9 ✓
        # SMALL_LOSS_EXIT: -0.08 <= -0.06 < 0 ✓, 10 <= 10 ✓
        # HOLD_LOSER should remove SMALL_LOSS_EXIT via priority
        tags = tag_names(positions[9], all_positions=positions)
        assert "HOLD_LOSER" in tags
        assert "SMALL_LOSS_EXIT" not in tags


# ============================================================================
# Phase 4 -- Tag Hierarchy (resolve_hierarchy)
# ============================================================================


class TestResolveHierarchy:
    """Tag hierarchy: L1->L2 via context.sub_pattern."""

    def test_trend_with_breakout_sets_sub_pattern(self):
        tags = [
            PatternResult("TREND", 0.7, {"ma20": 11, "ma60": 10}),
            PatternResult("BREAKOUT", 0.7, {}),
            PatternResult("SWING", 1.0, {"holding_days": 8}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        trend = next(t for t in result if t.pattern_name == "TREND")
        assert trend.context.get("sub_pattern") == "BREAKOUT"

    def test_trend_with_chase_sets_sub_pattern(self):
        tags = [
            PatternResult("TREND", 0.7, {}),
            PatternResult("CHASE", 0.7, {}),
            PatternResult("SWING", 1.0, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        trend = next(t for t in result if t.pattern_name == "TREND")
        assert trend.context.get("sub_pattern") == "CHASE"

    def test_trend_breakout_preferred_over_chase(self):
        """BREAKOUT appears first in the hierarchy check, so it wins."""
        tags = [
            PatternResult("TREND", 0.7, {}),
            PatternResult("BREAKOUT", 0.7, {}),
            PatternResult("CHASE", 0.7, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        trend = next(t for t in result if t.pattern_name == "TREND")
        assert trend.context.get("sub_pattern") == "BREAKOUT"

    def test_counter_trend_with_bottom(self):
        tags = [
            PatternResult("COUNTER_TREND", 0.7, {}),
            PatternResult("BOTTOM", 0.7, {}),
            PatternResult("SWING", 1.0, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        ct = next(t for t in result if t.pattern_name == "COUNTER_TREND")
        assert ct.context.get("sub_pattern") == "BOTTOM"

    def test_counter_trend_with_breakdown(self):
        tags = [
            PatternResult("COUNTER_TREND", 0.7, {}),
            PatternResult("BREAKDOWN", 0.7, {}),
            PatternResult("POSITION", 1.0, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        ct = next(t for t in result if t.pattern_name == "COUNTER_TREND")
        assert ct.context.get("sub_pattern") == "BREAKDOWN"

    def test_no_hierarchy_change_when_no_related_tags(self):
        tags = [
            PatternResult("TREND", 0.7, {}),
            PatternResult("SWING", 1.0, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        trend = next(t for t in result if t.pattern_name == "TREND")
        assert "sub_pattern" not in trend.context

    def test_no_hierarchy_for_unrelated_tags(self):
        tags = [
            PatternResult("SCALP", 1.0, {}),
            PatternResult("SWING", 1.0, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        assert all("sub_pattern" not in t.context for t in result)

    def test_multiple_trend_tags_all_get_sub_pattern(self):
        """If multiple positions have TREND, all should get sub_pattern."""
        tags = [
            PatternResult("TREND", 0.7, {}),
            PatternResult("TREND", 0.7, {}),
            PatternResult("BREAKOUT", 0.7, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        for t in result:
            if t.pattern_name == "TREND":
                assert t.context.get("sub_pattern") == "BREAKOUT"

    def test_double_hierarchy(self):
        """TREND+COUNTER_TREND both get their sub_patterns independently."""
        tags = [
            PatternResult("TREND", 0.7, {}),
            PatternResult("COUNTER_TREND", 0.7, {}),
            PatternResult("BREAKOUT", 0.7, {}),
            PatternResult("BOTTOM", 0.7, {}),
        ]
        result = PatternEngine.resolve_hierarchy(tags)
        for t in result:
            if t.pattern_name == "TREND":
                assert t.context.get("sub_pattern") == "BREAKOUT"
            if t.pattern_name == "COUNTER_TREND":
                assert t.context.get("sub_pattern") == "BOTTOM"
