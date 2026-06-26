"""ConsentLog model — audit trail for case library consent decisions."""

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, String

from app.database import Base


class ConsentLog(Base):
    """Records every consent decision (agree/decline) as a compliance audit trail.

    One row per consent dialog interaction. Each row is immutable evidence of
    the user's choice at that point in time.
    """

    __tablename__ = "consent_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id = Column(
        String(36), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True
    )
    consented = Column(Boolean, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa.func.now(),
    )
