"""Tests for WhatIfEngine -- counterfactual backtest simulation."""
from dataclasses import dataclass, field
from datetime import date

from app.engine.whatif import WhatIfEngine


# -- helpers ----------------------------------------------------------------


@dataclass
class _Position:
    """Minimal position-like object for testing what-if."""
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
    trade_ids: list[str] = field(default_factory=lambda: ["t1"])


def make_pos(
    pnl: float = 0.0,
    avg_entry: float = 10.0,
    qty: float = 100,
) -> _Position:
    """Create a test position."""
    avg_exit = avg_entry + pnl / qty if qty else avg_entry
    pnl_pct = (avg_exit - avg_entry) / avg_entry if avg_entry else 0.0
    return _Position(
        pnl=pnl,
        pnl_pct=pnl_pct,
        avg_entry_price=avg_entry,
        total_quantity=qty,
        avg_exit_price=avg_exit,
    )


# ============================================================================
# Tests
# ============================================================================


class TestWhatIfEngineBasic:
    """Basic what-if scenarios."""

    def test_returns_one_item_per_pattern(self):
        positions = [
            make_pos(pnl=100.0),
            make_pos(pnl=-50.0),
        ]
        patterns_map = {0: ["SWING"], 1: ["SCALP"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        assert len(results) == 2
        assert {r.removed_pattern for r in results} == {"SWING", "SCALP"}

    def test_original_return_same_for_all_items(self):
        positions = [
            make_pos(pnl=100.0),
            make_pos(pnl=-50.0),
        ]
        patterns_map = {0: ["SWING"], 1: ["SCALP"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        # total_invested = 1000 + 1000 = 2000, total_pnl = 50, return = 0.025
        for r in results:
            assert r.original_return == 0.025

    def test_removing_loss_pattern_improves_return(self):
        positions = [
            make_pos(pnl=200.0),
            make_pos(pnl=100.0),
            make_pos(pnl=-500.0),
        ]
        patterns_map = {0: ["A"], 1: ["A"], 2: ["TERRIBLE"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        terrible = next(r for r in results if r.removed_pattern == "TERRIBLE")
        assert terrible.what_if_return > terrible.original_return
        assert terrible.delta > 0

    def test_removing_profit_pattern_decreases_return(self):
        positions = [
            make_pos(pnl=500.0),
            make_pos(pnl=-50.0),
        ]
        patterns_map = {0: ["STAR"], 1: ["MEH"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        star = next(r for r in results if r.removed_pattern == "STAR")
        assert star.what_if_return < star.original_return
        assert star.delta < 0


class TestWhatIfEngineDamageScore:
    """Damage score calculation and sorting."""

    def test_damage_score_sorted_descending(self):
        positions = [
            make_pos(pnl=500.0),
            make_pos(pnl=-200.0),
            make_pos(pnl=-50.0),
        ]
        patterns_map = {0: ["A"], 1: ["B"], 2: ["C"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        damage_scores = [r.damage_score for r in results]
        assert damage_scores == sorted(damage_scores, reverse=True)

    def test_damage_score_between_zero_and_one(self):
        positions = [
            make_pos(pnl=500.0),
            make_pos(pnl=-200.0),
            make_pos(pnl=-50.0),
        ]
        patterns_map = {0: ["A"], 1: ["B"], 2: ["C"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        for r in results:
            assert 0.0 <= r.damage_score <= 1.0

    def test_damage_score_one_for_most_harmful(self):
        """The most harmful pattern should have damage_score=1.0."""
        positions = [
            make_pos(pnl=500.0),
            make_pos(pnl=-500.0),
            make_pos(pnl=50.0),
        ]
        patterns_map = {0: ["GOOD"], 1: ["BAD"], 2: ["MEH"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        # The pattern with largest |delta| should have damage_score 1.0
        assert results[0].damage_score == 1.0


class TestWhatIfEngineEdgeCases:
    """Edge cases: empty inputs, zero values."""

    def test_empty_positions(self):
        results = WhatIfEngine.analyze([], {})
        assert results == []

    def test_empty_patterns_map(self):
        positions = [make_pos(pnl=100.0)]
        results = WhatIfEngine.analyze(positions, {})
        assert results == []

    def test_zero_invested_does_not_crash(self):
        """Positions with avg_entry_price=0 should not cause division by zero."""
        pos = _Position(
            pnl=0.0, pnl_pct=0.0, avg_entry_price=0.0, total_quantity=0
        )
        results = WhatIfEngine.analyze([pos], {0: ["SCALP"]})
        assert results == []

    def test_all_positions_have_same_pattern(self):
        """Removing the only pattern should produce empty filtered list -> skipped."""
        positions = [
            make_pos(pnl=100.0),
            make_pos(pnl=50.0),
        ]
        patterns_map = {0: ["A"], 1: ["A"]}
        results = WhatIfEngine.analyze(positions, patterns_map)
        # When we remove "A", no positions remain -> skipped
        assert results == []


# ============================================================================
# Phase 4 — WhatIf Level 2: analyze_replace()
# ============================================================================


class TestWhatIfAnalyzeReplace:
    """Level 2: Replace one behavior with another."""

    def test_replace_removes_from_pattern_and_adds_to_pattern(self):
        """Positions tagged with from_pattern are removed UNLESS also tagged with to_pattern."""
        positions = [
            make_pos(pnl=200.0, avg_entry=10.0, qty=100),  # 0: BAD only
            make_pos(pnl=-50.0, avg_entry=10.0, qty=100),  # 1: IGNORE only
            make_pos(pnl=-100.0, avg_entry=10.0, qty=100), # 2: both BAD and GOOD
        ]
        patterns_map = {0: ["BAD"], 1: ["IGNORE"], 2: ["BAD", "GOOD"]}
        result = WhatIfEngine.analyze_replace(positions, patterns_map, "BAD", "GOOD")
        assert result is not None
        assert result["from_pattern"] == "BAD"
        assert result["to_pattern"] == "GOOD"
        # Positions: 0 removed (BAD only), 1 kept (IGNORE), 2 kept (BAD+GOOD)
        # filtered = positions 1 + 2 => total_pnl = -50 + -100 = -150
        # total_invested = 1000 + 1000 = 2000
        # what_if_return = -150 / 2000 = -0.075
        assert result["what_if_return"] == -0.075

    def test_replace_returns_original_and_delta(self):
        positions = [
            make_pos(pnl=200.0),
            make_pos(pnl=-500.0),
        ]
        patterns_map = {0: ["GOOD"], 1: ["BAD"]}
        result = WhatIfEngine.analyze_replace(positions, patterns_map, "BAD", "GOOD")
        assert result is not None
        assert "original_return" in result
        assert "delta" in result
        # original: total_pnl = -300 / 2000 = -0.15
        assert result["original_return"] == -0.15
        # filtered: only position 0 (GOOD) => pnl=200, invested=1000 => 0.2
        # delta = 0.2 - (-0.15) = 0.35
        assert result["delta"] == 0.35

    def test_replace_returns_none_when_no_positions_remain(self):
        positions = [make_pos(pnl=100.0)]
        patterns_map = {0: ["BAD"]}
        result = WhatIfEngine.analyze_replace(positions, patterns_map, "BAD", "GOOD")
        assert result is None

    def test_replace_with_no_pattern_match(self):
        """When no position has from_pattern, all positions remain."""
        positions = [make_pos(pnl=100.0), make_pos(pnl=-50.0)]
        patterns_map = {0: ["A"], 1: ["B"]}
        result = WhatIfEngine.analyze_replace(positions, patterns_map, "NONEXISTENT", "A")
        assert result is not None
        # all positions remain, result = original return
        assert result["delta"] == 0.0

    def test_replace_zero_invested_does_not_crash(self):
        pos = _Position(pnl=0.0, avg_entry_price=0.0, total_quantity=0)
        result = WhatIfEngine.analyze_replace([pos], {0: ["BAD"]}, "BAD", "GOOD")
        assert result is None


# ============================================================================
# Phase 4 — WhatIf Level 3: analyze_rule()
# ============================================================================


class TestWhatIfAnalyzeRule:
    """Level 3: Rule simulation."""

    def test_stop_loss_caps_losses(self):
        """Positions with pnl_pct < -5% get capped at -5%."""
        positions = [
            make_pos(pnl=200.0, avg_entry=10.0, qty=100),   # pnl_pct = 20%
            make_pos(pnl=-100.0, avg_entry=10.0, qty=100),  # pnl_pct = -10%
            make_pos(pnl=-30.0, avg_entry=10.0, qty=100),   # pnl_pct = -3%
        ]
        # pos 1 has pnl_pct=-10% < -5%, cap at -5% = -10.0*100*-0.05 = -50.0
        # total_pnl_original = 70, total_invested = 3000, original_return = 0.02333...
        # simulated: 200 + (-50) + (-30) = 120, what_if_return = 120/3000 = 0.04
        result = WhatIfEngine.analyze_rule(positions, "stop_loss", {"loss_pct": 0.05})
        assert result is not None
        assert result["rule"] == "stop_loss_0.05"
        assert result["affected_positions"] == 1
        assert result["delta"] > 0  # should improve return
        assert result["what_if_return"] == 0.04

    def test_stop_loss_no_affected(self):
        """When no positions exceed loss_pct, delta is 0."""
        positions = [
            make_pos(pnl=200.0, avg_entry=10.0, qty=100),   # pnl_pct = 20%
            make_pos(pnl=-30.0, avg_entry=10.0, qty=100),   # pnl_pct = -3%
        ]
        result = WhatIfEngine.analyze_rule(positions, "stop_loss", {"loss_pct": 0.05})
        assert result is not None
        assert result["affected_positions"] == 0
        assert result["delta"] == 0.0

    def test_stop_loss_all_capped(self):
        """All positions exceed loss_pct."""
        positions = [
            make_pos(pnl=-200.0, avg_entry=10.0, qty=100),   # pnl_pct = -20%
            make_pos(pnl=-100.0, avg_entry=10.0, qty=100),   # pnl_pct = -10%
        ]
        # Both capped at -5%: each contributes -50 pnl
        # simulated_pnl = -100, original_pnl = -300
        result = WhatIfEngine.analyze_rule(positions, "stop_loss", {"loss_pct": 0.05})
        assert result is not None
        assert result["affected_positions"] == 2

    def test_stop_loss_zero_invested_does_not_crash(self):
        pos = _Position(pnl=-100.0, pnl_pct=-0.10, avg_entry_price=0.0, total_quantity=0)
        result = WhatIfEngine.analyze_rule([pos], "stop_loss", {"loss_pct": 0.05})
        assert result is not None
        assert result["original_return"] == 0.0
        assert result["what_if_return"] == 0.0

    def test_unknown_rule_type_returns_none(self):
        positions = [make_pos(pnl=100.0)]
        result = WhatIfEngine.analyze_rule(positions, "unknown_rule", {})
        assert result is None
