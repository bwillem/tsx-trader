from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.trade import OrderType, OrderSide, OrderStatus


class TradeOrderCreate(BaseModel):
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    reasoning: Optional[str] = None


class TradeOrderResponse(BaseModel):
    id: int
    stock_id: int
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    limit_price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    broker_order_id: Optional[str]
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    filled_quantity: int
    average_fill_price: Optional[float]
    created_at: datetime
    submitted_at: Optional[datetime]
    filled_at: Optional[datetime]
    is_paper_trade: bool

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    id: int
    stock_id: int
    symbol: str
    quantity: int
    average_cost: float
    current_price: Optional[float]
    market_value: Optional[float]
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    is_open: bool
    opened_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True
