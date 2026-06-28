"""TDD red tests for best/worst pattern selection (缺陷2).

Investment researcher found the diagnostic conclusion labelled a positive-
contribution pattern ("害怕错过(心理)" +2893) as "最大问题" — self-contradictory.
Root cause: `best = significant[0]`, `worst = significant[-1]` operate on the
flat `all_items` list which is NOT sorted across pattern-dimensions, so the
"last" significant item may be a positive-contribution pattern.

These tests drive extraction of a pure selector `_select_best_worst_patterns`
so the rule becomes explicit and testable:
  - best  = significant item with the MAX total_pnl (most positive)
  - worst = significant item with the MIN total_pnl (most negative)
"""
from app.engine.compute import _select_best_worst_patterns
from app.schemas.analysis import InsightPatternItem


def _item(name: str, count: int, total_pnl: float) -> InsightPatternItem:
    return InsightPatternItem(
        pattern_name=name,
        count=count,
        win_count=count // 2,
        win_rate=0.5,
        total_pnl=total_pnl,
        avg_pnl_pct=0.0,
        expectancy=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
    )


class TestSelectBestWorst:
    def test_best_is_max_positive_worst_is_min_negative(self):
        """best = 最大正贡献，worst = 最负贡献。"""
        items = [
            _item("SWING", 5, 1660.0),            # 正
            _item("LARGE_LOSS_EXIT", 5, -16000.0), # 负最负
            _item("FOMO", 6, 2893.0),              # 正最大
            _item("SCALP", 5, -2915.0),            # 负
        ]
        best, worst = _select_best_worst_patterns(items)
        assert best is not None
        assert worst is not None
        assert best.pattern_name == "FOMO"
        assert best.total_pnl == 2893.0
        assert worst.pattern_name == "LARGE_LOSS_EXIT"
        assert worst.total_pnl == -16000.0

    def test_all_positive_worst_is_least_positive(self):
        """全正贡献时 worst 应是正贡献最小者（降级合理），而非最后一个。"""
        items = [
            _item("A", 5, 500.0),
            _item("B", 5, 3000.0),
            _item("C", 5, 1000.0),
        ]
        best, worst = _select_best_worst_patterns(items)
        assert best.pattern_name == "B"   # 最大正
        assert worst.pattern_name == "A"  # 最小正（最接近0）

    def test_all_negative_best_is_least_negative(self):
        """全负贡献时 best 应是负贡献最小者（最接近0），worst 是最负。"""
        items = [
            _item("X", 5, -500.0),
            _item("Y", 5, -3000.0),
            _item("Z", 5, -1000.0),
        ]
        best, worst = _select_best_worst_patterns(items)
        assert best.pattern_name == "X"   # 最接近0
        assert worst.pattern_name == "Y"  # 最负

    def test_insufficient_samples_returns_none(self):
        """count<5 的标签不参与 best/worst 选择。"""
        items = [
            _item("SMALL", 4, 9999.0),
            _item("ALSO_SMALL", 3, -9999.0),
        ]
        best, worst = _select_best_worst_patterns(items)
        assert best is None
        assert worst is None

    def test_single_significant_returns_best_only(self):
        """只有一个显著标签时，best 有值，worst 为 None。"""
        items = [_item("ONLY", 5, 1000.0)]
        best, worst = _select_best_worst_patterns(items)
        assert best is not None and best.pattern_name == "ONLY"
        assert worst is None
