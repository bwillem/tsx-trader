from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
from .trade import PositionResponse


class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    positions_value: float
    daily_pnl: float
    daily_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    num_positions: int
    positions: List[PositionResponse]

    class Config:
        from_attributes = True


class PortfolioSnapshotResponse(BaseModel):
    id: int
    snapshot_date: date
    total_value: float
    cash_balance: float
    positions_value: float
    daily_pnl: float
    daily_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    num_positions: int
    num_trades_today: int
    win_rate: Optional[float]

    class Config:
        from_attributes = True
