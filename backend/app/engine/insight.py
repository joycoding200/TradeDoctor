"""Insight engine: aggregate positions by behavior pattern and compute statistics."""
from dataclasses import dataclass


@dataclass
class InsightItem:
    """Aggregated statistics for a single behavioral pattern."""

    pattern_name: str
    count: int
    win_count: int
    win_rate: float
    total_pnl: float
    avg_pnl_pct: float


class InsightEngine:
    """Group positions by pattern and compute performance metrics per pattern."""

    @staticmethod
    def analyze(positions, patterns_map: dict[int, list[str]]) -> list[InsightItem]:
        """Analyze positions grouped by behavioral pattern.

        Args:
            positions: List of position-like objects with .pnl and .pnl_pct.
            patterns_map: {position_index: [pattern_name, ...]}.

        Returns:
            List of InsightItem sorted by total_pnl descending.
        """
        by_pattern: dict[str, dict] = {}
        for i, pos in enumerate(positions):
            for pat_name in patterns_map.get(i, []):
                if pat_name not in by_pattern:
                    by_pattern[pat_name] = {
                        "positions": [],
                        "wins": 0,
                        "total_pnl": 0.0,
                    }
                by_pattern[pat_name]["positions"].append(pos)
                by_pattern[pat_name]["total_pnl"] += pos.pnl
                if pos.pnl > 0:
                    by_pattern[pat_name]["wins"] += 1

        results: list[InsightItem] = []
        for pat_name, data in by_pattern.items():
            count = len(data["positions"])
            total_pnl_all = sum(p.pnl for p in data["positions"])
            results.append(
                InsightItem(
                    pattern_name=pat_name,
                    count=count,
                    win_count=data["wins"],
                    win_rate=data["wins"] / count if count > 0 else 0.0,
                    total_pnl=round(total_pnl_all, 2),
                    avg_pnl_pct=(
                        round(sum(p.pnl_pct for p in data["positions"]) / count, 4)
                        if count > 0
                        else 0.0
                    ),
                )
            )

        results.sort(key=lambda x: x.total_pnl, reverse=True)
        return results
