"""Tests for Shapley pct_of_total sign handling (compute_whatif).

Regression: when total_pnl is NEGATIVE, the old code computed
`pct_of_total = shapley_value / total_pnl * 100`, which flipped signs — a
positive-contribution pattern (shapley_value > 0) showed a NEGATIVE pct, and a
negative-contribution pattern showed a POSITIVE pct. This misled users into
thinking profitable patterns were losing money (e.g. "震荡市 +3999 (-47.2%)").

Fix: denom uses abs(total_pnl) so the percentage's sign follows shapley_value.
"""

from dataclasses import dataclass

from app.engine.compute import compute_whatif


@dataclass
class _Pos:
    """Minimal position stub for compute_whatif (only the fields it reads)."""
    pnl: float
    pnl_pct: float = 0.0
    cost_known: bool = True
    symbol: str = "000001"
    avg_entry_price: float = 10.0
    total_quantity: int = 100
    entry_date: object = None
    exit_date: object = None


def _run(positions, category_map):
    return compute_whatif(positions, category_map, market_data={})


def test_positive_shapley_has_positive_pct_when_total_is_negative():
    """When total_pnl < 0, a profit-contributing pattern must show pct >= 0.

    Red on old code: pct = +100 / (-50) * 100 = -200 (sign flipped).
    Green on fix:    pct = +100 / abs(-50) * 100 = +200 (sign kept).
    """
    # Two non-overlapping patterns: WINNER earns +100, LOSER loses -150.
    # total_pnl = -50 (negative), so the sign-flip bug would trigger.
    positions = [_Pos(pnl=100), _Pos(pnl=-150)]
    category_map = {0: {"behavior": "SWING"}, 1: {"behavior": "SCALP"}}
    whatif = _run(positions, category_map)

    shapley = {s.pattern_name: s for s in whatif.shapley}
    winner = shapley["SWING"]
    loser = shapley["SCALP"]

    # shapley_value itself is unaffected by the fix (always signed correctly)
    assert winner.shapley_value > 0, "WINNER should have positive shapley_value"
    assert loser.shapley_value < 0, "LOSER should have negative shapley_value"

    # The fix: pct sign must follow shapley_value, not be flipped by total_pnl
    assert winner.pct_of_total >= 0, (
        f"positive-contribution pattern must have pct >= 0, got {winner.pct_of_total} "
        f"(sign-flip bug: total_pnl is negative and divides into positive shapley)"
    )
    assert loser.pct_of_total <= 0, (
        f"negative-contribution pattern must have pct <= 0, got {loser.pct_of_total}"
    )


def test_pct_signs_match_shapley_when_total_is_positive():
    """Sanity: when total_pnl > 0 the fix must not change correct behavior."""
    positions = [_Pos(pnl=200), _Pos(pnl=-50)]
    category_map = {0: {"behavior": "SWING"}, 1: {"behavior": "SCALP"}}
    whatif = _run(positions, category_map)

    shapley = {s.pattern_name: s for s in whatif.shapley}
    assert shapley["SWING"].pct_of_total >= 0
    assert shapley["SCALP"].pct_of_total <= 0


def test_signed_pct_sums_to_100_when_total_negative():
    """Signed sum of pct_of_total should be -100% when total_pnl < 0, because
    sum(shapley) == total_pnl and denom = abs(total_pnl)."""
    positions = [_Pos(pnl=100), _Pos(pnl=-150), _Pos(pnl=40)]
    category_map = {
        0: {"behavior": "SWING"},
        1: {"behavior": "SCALP"},
        2: {"behavior": "POSITION"},
    }
    whatif = _run(positions, category_map)
    signed = sum(s.pct_of_total for s in whatif.shapley)
    # total_pnl = -10 → denom = 10 → sum(pct) = sum(shapley)/10*100 = -10/10*100 = -100
    assert abs(signed - (-100.0)) < 1.0, (
        f"signed pct sum should be ~-100, got {signed}"
    )
