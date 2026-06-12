"""Pydantic schemas for analysis endpoints."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class AnalysisRunRequest(BaseModel):
    date_start: date
    date_end: date


class AnalysisRunResponse(BaseModel):
    analysis_id: str


class PositionItem(BaseModel):
    symbol: str
    asset_type: str
    entry_date: date
    exit_date: date
    holding_days: int
    total_quantity: float
    avg_entry_price: float
    avg_exit_price: float
    pnl: float
    pnl_pct: float
    trade_ids: list[str]


class OutcomeItem(BaseModel):
    label: str
    count: int


class StatsResponse(BaseModel):
    total_trades: int
    total_positions: int
    unknown_cost_count: int = 0
    win_count: int
    win_rate: float
    total_pnl: float
    avg_holding_days: float
    max_win: float
    max_loss: float
    consecutive_losses: int
    outcome_distribution: list[OutcomeItem] = []
    positions: list[PositionItem]


class InsightPatternItem(BaseModel):
    pattern_name: str
    count: int
    win_count: int
    win_rate: float
    total_pnl: float
    avg_pnl_pct: float
    expectancy: float = 0.0


class InsightResponse(BaseModel):
    patterns: list[InsightPatternItem]  # all patterns (backward compat)
    entry_patterns: list[InsightPatternItem] = []
    holding_patterns: list[InsightPatternItem] = []
    risk_patterns: list[InsightPatternItem] = []
    exit_patterns: list[InsightPatternItem] = []
    categories: dict[str, list[InsightPatternItem]] = {}
    best_pattern: Optional[InsightPatternItem] = None
    worst_pattern: Optional[InsightPatternItem] = None


class AttributionItem(BaseModel):
    removed_pattern: str
    original_return: float
    what_if_return: float
    delta: float
    contribution_pct: float


class WhatIfResponse(BaseModel):
    items: list[AttributionItem]
