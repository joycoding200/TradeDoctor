"""TokenBlacklist model for JWT revocation (logout)."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, String

from app.database import Base


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    jti = Column(String(36), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
