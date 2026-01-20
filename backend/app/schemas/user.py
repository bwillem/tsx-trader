from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    position_size_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    daily_loss_limit_pct: Optional[float] = None
    max_open_positions: Optional[int] = None
    min_cash_reserve_pct: Optional[float] = None
    min_risk_reward_ratio: Optional[float] = None
    paper_trading_enabled: Optional[bool] = None
    auto_trading_enabled: Optional[bool] = None
    require_stop_loss: Optional[bool] = None
    circuit_breaker_enabled: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    id: int
    user_id: int
    position_size_pct: float
    stop_loss_pct: float
    daily_loss_limit_pct: float
    max_open_positions: int
    min_cash_reserve_pct: float
    min_risk_reward_ratio: float
    paper_trading_enabled: bool
    auto_trading_enabled: bool
    require_stop_loss: bool
    circuit_breaker_enabled: bool

    class Config:
        from_attributes = True
