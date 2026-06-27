"""Parser helpers."""


def _get_exchange(symbol: str) -> str:
    """Get exchange code from stock/futures symbol."""
    sym = symbol.zfill(6)
    if sym[0] in ("6", "5", "9"):
        return "SH"
    if sym[0] in ("0", "3", "2"):
        return "SZ"
    # Futures exchanges
    upper = symbol.upper()
    if any(upper.startswith(p) for p in ("IF", "IC", "IH", "IM", "T", "TF", "TS")):
        return "CFFEX"
    if any(upper.startswith(p) for p in ("CU", "AL", "ZN", "PB", "NI", "SN", "AO",
                                          "AU", "AG", "RB", "HC", "BU", "RU", "SP", "FU", "WR",
                                          "SS", "BR")):
        return "SHFE"
    return "DCE"  # Default for futures


def _find_col(col_map: dict[str, str], candidates: list[str]) -> str | None:
    """Find first matching column from candidates in the column map.

    Args:
        col_map: Mapping from lowercase column name to actual column name.
        candidates: List of possible column names to find.

    Returns:
        Actual column name if found, None otherwise.
    """
    for c in candidates:
        c_lower = c.strip().lower()
        if c_lower in col_map:
            return col_map[c_lower]
    return None
