"""Tests for MarketDataCache -- daily bar cache engine."""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.engine.market_data import MarketDataCache
from app.models.daily_bar import DailyBar


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


class TestMarketDataCacheStore:
    """Store daily bars."""

    def test_store_new_bars(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
        ]
        count = MarketDataCache.store_bars(db_session, bars)
        assert count == 1
        stored = db_session.query(DailyBar).all()
        assert len(stored) == 1
        assert stored[0].symbol == "000001"

    def test_store_skips_duplicates(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
        ]
        count1 = MarketDataCache.store_bars(db_session, bars)
        count2 = MarketDataCache.store_bars(db_session, bars)
        assert count1 == 1
        assert count2 == 0  # duplicate, not stored
        stored = db_session.query(DailyBar).all()
        assert len(stored) == 1

    def test_store_multiple_bars(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
            {"symbol": "000001", "date": date(2024, 1, 3), "open": 10.5, "high": 11.5,
             "low": 10.0, "close": 11.0, "volume": 150000},
            {"symbol": "000002", "date": date(2024, 1, 2), "open": 20.0, "high": 21.0,
             "low": 19.5, "close": 20.5, "volume": 200000},
        ]
        count = MarketDataCache.store_bars(db_session, bars)
        assert count == 3

    def test_store_with_optional_fields(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000,
             "ma5": 9.8, "ma10": 9.5, "ma20": 9.2, "ma60": 8.5,
             "avg_volume_20d": 80000},
        ]
        MarketDataCache.store_bars(db_session, bars)
        stored = db_session.query(DailyBar).first()
        assert stored.ma5 == 9.8
        assert stored.ma10 == 9.5
        assert stored.ma20 == 9.2
        assert stored.ma60 == 8.5
        assert stored.avg_volume_20d == 80000


class TestMarketDataCacheGetBars:
    """Retrieve daily bars."""

    def test_get_bars_returns_empty_when_no_data(self, db_session):
        result = MarketDataCache.get_bars(db_session, "000001", date(2024, 1, 1), date(2024, 1, 31))
        assert result == []

    def test_get_bars_in_date_range(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
            {"symbol": "000001", "date": date(2024, 1, 3), "open": 10.5, "high": 11.5,
             "low": 10.0, "close": 11.0, "volume": 150000},
            {"symbol": "000001", "date": date(2024, 1, 4), "open": 11.0, "high": 12.0,
             "low": 10.5, "close": 11.5, "volume": 200000},
        ]
        MarketDataCache.store_bars(db_session, bars)

        result = MarketDataCache.get_bars(db_session, "000001", date(2024, 1, 3), date(2024, 1, 3))
        assert len(result) == 1
        assert result[0]["date"] == "2024-01-03"

    def test_get_bars_excludes_other_symbols(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
            {"symbol": "000002", "date": date(2024, 1, 2), "open": 20.0, "high": 21.0,
             "low": 19.5, "close": 20.5, "volume": 200000},
        ]
        MarketDataCache.store_bars(db_session, bars)
        result = MarketDataCache.get_bars(db_session, "000001", date(2024, 1, 1), date(2024, 1, 31))
        assert len(result) == 1
        assert result[0]["close"] == 10.5

    def test_get_bars_ordered_by_date(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 3), "open": 11.0, "high": 12.0,
             "low": 10.5, "close": 11.5, "volume": 200000},
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
        ]
        MarketDataCache.store_bars(db_session, bars)
        result = MarketDataCache.get_bars(db_session, "000001", date(2024, 1, 1), date(2024, 1, 31))
        assert len(result) == 2
        assert result[0]["date"] == "2024-01-02"
        assert result[1]["date"] == "2024-01-03"


class TestMarketDataCacheGetMarketData:
    """get_market_data returns nested dict for PatternEngine."""

    def test_get_market_data_structure(self, db_session):
        bars = [
            {"symbol": "000001", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000, "ma5": 9.8},
        ]
        MarketDataCache.store_bars(db_session, bars)
        result = MarketDataCache.get_market_data(db_session, ["000001"], date(2024, 1, 1), date(2024, 1, 31))
        assert "000001" in result
        assert "2024-01-02" in result["000001"]
        assert result["000001"]["2024-01-02"]["close"] == 10.5
        assert result["000001"]["2024-01-02"]["ma5"] == 9.8

    def test_get_market_data_empty_for_missing_symbol(self, db_session):
        result = MarketDataCache.get_market_data(db_session, ["MISSING"], date(2024, 1, 1), date(2024, 1, 31))
        assert "MISSING" in result
        assert result["MISSING"] == {}

    def test_get_market_data_multiple_symbols(self, db_session):
        bars = [
            {"symbol": "A", "date": date(2024, 1, 2), "open": 10.0, "high": 11.0,
             "low": 9.5, "close": 10.5, "volume": 100000},
            {"symbol": "B", "date": date(2024, 1, 2), "open": 20.0, "high": 21.0,
             "low": 19.5, "close": 20.5, "volume": 200000},
        ]
        MarketDataCache.store_bars(db_session, bars)
        result = MarketDataCache.get_market_data(db_session, ["A", "B"], date(2024, 1, 1), date(2024, 1, 31))
        assert "A" in result
        assert "B" in result
        assert result["A"]["2024-01-02"]["close"] == 10.5
        assert result["B"]["2024-01-02"]["close"] == 20.5
