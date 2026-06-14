"""Market data fetcher — pull A-share daily bars via akshare, cache to DailyBar.

Usage:
    from app.engine.market_fetcher import ensure_market_data

    # Fetch and cache bars, returns data dict for PatternEngine
    data = ensure_market_data(db, ["600036", "000858"], start, end)
"""

from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.engine.market_data import MarketDataCache


def _compute_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Add MA5, MA10, MA20, MA60, avg_volume_20d columns."""
    df = df.sort_values("date")
    df["ma5"] = df["close"].rolling(5, min_periods=1).mean().round(4)
    df["ma10"] = df["close"].rolling(10, min_periods=1).mean().round(4)
    df["ma20"] = df["close"].rolling(20, min_periods=1).mean().round(4)
    df["ma60"] = df["close"].rolling(60, min_periods=1).mean().round(4)
    df["avg_volume_20d"] = df["volume"].rolling(20, min_periods=1).mean().round(2)
    return df


def _symbol_ak(symbol: str) -> str:
    """Convert 6-digit code to akshare format ('sh600036' or 'sz000858')."""
    if symbol[0] in ("6", "5", "9"):
        return f"sh{symbol}"
    return f"sz{symbol}"


def _fetch_single_symbol(db: Session, symbol: str) -> int:
    """Fetch all history for one symbol. Returns count of new bars stored."""
    import akshare as ak

    try:
        raw = ak.stock_zh_a_hist(
            symbol=symbol, period="daily", adjust="qfq"
        )
    except Exception:
        return 0

    if raw.empty:
        return 0

    raw = raw.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        }
    )
    raw["date"] = pd.to_datetime(raw["date"]).dt.date
    raw["symbol"] = symbol

    if "volume" not in raw:
        raw["volume"] = 0.0

    # Compute MAs over full history for accuracy
    raw = _compute_moving_averages(raw)

    # Find dates not already cached
    existing_dates: set[date] = set()
    try:
        bars = MarketDataCache.get_bars(
            db, symbol, raw["date"].min(), raw["date"].max()
        )
        existing_dates = {date.fromisoformat(b["date"]) for b in bars}
    except Exception:
        pass

    new_rows = [
        r
        for _, r in raw.iterrows()
        if r["date"] not in existing_dates
    ]
    if not new_rows:
        return 0

    stored = MarketDataCache.store_bars(
        db,
        [
            {
                "symbol": symbol,
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r.get("volume", 0.0)),
                "ma5": float(r["ma5"]) if pd.notna(r.get("ma5")) else None,
                "ma10": float(r["ma10"]) if pd.notna(r.get("ma10")) else None,
                "ma20": float(r["ma20"]) if pd.notna(r.get("ma20")) else None,
                "ma60": float(r["ma60"]) if pd.notna(r.get("ma60")) else None,
                "avg_volume_20d": (
                    float(r["avg_volume_20d"])
                    if pd.notna(r.get("avg_volume_20d"))
                    else None
                ),
            }
        ],
    )
    return stored


def ensure_market_data(
    db: Session, symbols: list[str], start: date, end: date
) -> dict:
    """Fetch and cache daily bars for given symbols, then return market_data dict.

    Fetches from 60 trading days before `start` to ensure MAs are accurate.

    Returns dict in PatternEngine format:
        {symbol: {date_str: {open, high, low, close, volume, ma5, ...}}}
    """
    if not symbols:
        return {}

    lookback_start = start - timedelta(days=120)  # ~60 trading days

    for sym in set(symbols):
        _fetch_single_symbol(db, sym)

    return MarketDataCache.get_market_data(
        db, list(set(symbols)), lookback_start, end
    )
