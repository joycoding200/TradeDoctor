"""Test _build_category_map's precomputed fast path.

The precomputed path lets callers (report.py) reuse already-tagged PatternResult
lists instead of re-tagging the whole position set. Its output MUST be identical
to the non-precomputed path on the same inputs — otherwise report.py would
silently produce a different category map (and thus a different AI prompt) than
the /insight endpoint. This test locks that equivalence.
"""

import pytest

from app.engine.compute import _build_category_map
from app.engine.pattern import PatternEngine
from app.engine.position import PositionBuilder
from app.parsers.smart import SmartParser

CSV = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    "2024-01-05 09:30:00,000001,平安银行,买入,10.00,1000,5.00\n"
    "2024-01-12 14:00:00,000001,平安银行,卖出,11.20,1000,5.00\n"
    "2024-02-05 09:30:00,600001,包钢股份,买入,5.00,2000,3.00\n"
    "2024-02-12 14:00:00,600001,包钢股份,卖出,4.50,2000,3.00"
)


@pytest.fixture
def positions_and_trades():
    trades = SmartParser().parse(CSV.encode("utf-8"), filename="t.csv")
    positions = PositionBuilder.build(trades)
    return positions, trades


def test_precomputed_matches_non_precomputed(positions_and_trades):
    """precomputed=results must yield the same category_map as the default path."""
    positions, trades = positions_and_trades

    # Reference: the full internal tagging path (no precomputed).
    expected = _build_category_map(positions, trades=trades, market_data=None)

    # Reproduce the tagging report.py does, then hand the results in.
    psychology_results = PatternEngine.detect_psychological_patterns(
        positions, all_trades=trades
    )
    psyche_by_pos: dict[int, list] = {}
    for idx, psy_result in psychology_results:
        psyche_by_pos.setdefault(idx, []).append(psy_result)

    results_by_pos: dict[int, list] = {}
    for i, pos in enumerate(positions):
        results = PatternEngine.tag_position(
            pos, positions, trades=trades, all_trades=trades
        )
        results = PatternEngine.resolve_hierarchy(results)
        if i in psyche_by_pos:
            results.extend(psyche_by_pos[i])
        results_by_pos[i] = results

    actual = _build_category_map(
        positions, trades=trades, market_data=None, precomputed=results_by_pos
    )

    assert actual == expected, (
        "precomputed path diverged from the default path — report.py would "
        "build a different category_map than /insight"
    )


def test_precomputed_empty_when_no_results(positions_and_trades):
    """An index with no precomputed results resolves to an empty category dict,
    matching the non-precomputed path's behavior for the same (untagged) input."""
    positions, _ = positions_and_trades
    # precomputed=None would hit the default path; pass an explicit empty map so
    # every index gets [] → empty {} category. Compare against the default path
    # with no trades/market_data (which still tags holding+outcome patterns, so
    # NOT empty) only makes sense as "no tags survive resolve_per_category".
    # Here we only assert the precomputed branch doesn't crash and returns {}
    # per index when given no results.
    precomputed = {i: [] for i in range(len(positions))}
    actual = _build_category_map(
        positions, trades=None, market_data=None, precomputed=precomputed
    )
    assert all(v == {} for v in actual.values())
