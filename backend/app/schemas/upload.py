"""Pydantic schemas for upload endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DetectResult(BaseModel):
    source_type: str
    asset_type: str
    score: float


class UploadResponse(BaseModel):
    raw_file_id: str
    detected_formats: list[DetectResult]


class ConfirmRequest(BaseModel):
    raw_file_id: str
    source_type: str


class TradeDataResponse(BaseModel):
    datetime: datetime
    symbol: str
    exchange: str
    side: str
    quantity: float
    price: float
    commission: float = 0.0
    margin: Optional[float] = None
    multiplier: Optional[int] = None


class ConfirmResponse(BaseModel):
    trades: list[TradeDataResponse]
    count: int


class ImportRequest(BaseModel):
    raw_file_id: str


class ImportResponse(BaseModel):
    imported_count: int
    skipped_count: int = 0
