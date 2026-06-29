"""Trade model."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String

from app.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_file_id = Column(
        String(36), ForeignKey("raw_files.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    asset_type = Column(String(10), nullable=False)
    datetime = Column(DateTime, nullable=False)
    symbol = Column(String(20), nullable=False)
    # Chinese security name extracted from the broker export
    # (column 证券名称 / 股票名称). Nullable because not every broker/file
    # carries the name column, and historical imports pre-date this column.
    symbol_name = Column(String(50), nullable=True)
    exchange = Column(String(10), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    margin = Column(Float, nullable=True)
    multiplier = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_trades_user_datetime", "user_id", "datetime"),
        Index("ix_trades_raw_file_id", "raw_file_id"),
        Index(
            "ix_trades_user_symbol_datetime",
            "user_id",
            "symbol",
            "datetime",
        ),
    )
