"""What-If engine: counterfactual backtest removing selected behavior patterns."""
from dataclasses import dataclass


@dataclass
class WhatIfItem:
    """Result of removing a single behavioral pattern from the portfolio."""

    removed_pattern: str
    original_return: float
    what_if_return: float
    delta: float
    damage_score: float


class WhatIfEngine:
    """Simulate portfolio return after removing positions tagged with a pattern."""

    @staticmethod
    def analyze(positions, patterns_map: dict[int, list[str]]) -> list[WhatIfItem]:
        """Run what-if analysis for each unique pattern.

        For each pattern, removes all positions tagged with it and
        recomputes the portfolio return. The damage_score quantifies
        how much the pattern affected the overall result (0 = no effect,
        1 = most harmful/helpful).

        Args:
            positions: List of position-like objects with .pnl, .avg_entry_price,
                       .total_quantity.
            patterns_map: {position_index: [pattern_name, ...]}.

        Returns:
            List of WhatIfItem sorted by damage_score descending.
        """
        total_invested = sum(
            p.avg_entry_price * p.total_quantity for p in positions
        )
        total_pnl = sum(p.pnl for p in positions)
        original_return = (
            total_pnl / total_invested if total_invested > 0 else 0.0
        )

        all_patterns: set[str] = set()
        for pats in patterns_map.values():
            all_patterns.update(pats)

        results: list[WhatIfItem] = []
        for pattern_name in all_patterns:
            filtered = [
                p
                for i, p in enumerate(positions)
                if pattern_name not in patterns_map.get(i, [])
            ]
            if not filtered:
                continue

            filtered_invested = sum(
                p.avg_entry_price * p.total_quantity for p in filtered
            )
            filtered_pnl = sum(p.pnl for p in filtered)
            what_if_return = (
                filtered_pnl / filtered_invested
                if filtered_invested > 0
                else 0.0
            )

            results.append(
                WhatIfItem(
                    removed_pattern=pattern_name,
                    original_return=round(original_return, 4),
                    what_if_return=round(what_if_return, 4),
                    delta=round(what_if_return - original_return, 4),
                    damage_score=0.0,
                )
            )

        # Normalize damage scores
        if results:
            max_delta = max(abs(r.delta) for r in results)
            for r in results:
                r.damage_score = (
                    round(abs(r.delta) / max_delta, 4) if max_delta > 0 else 0.0
                )

        results.sort(key=lambda x: x.damage_score, reverse=True)
        return results
