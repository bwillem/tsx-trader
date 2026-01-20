from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Boolean,
    Index,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base, TimestampMixin


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TradeOrder(Base, TimestampMixin):
    __tablename__ = "trade_orders"
    __table_args__ = (Index("ix_orders_user_status", "user_id", "status"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    # Order details
    order_type = Column(SQLEnum(OrderType), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    limit_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)

    # Status
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    broker_order_id = Column(String, nullable=True, unique=True)

    # Risk management
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    position_size_pct = Column(Float, nullable=True)
    risk_amount = Column(Float, nullable=True)

    # Execution
    filled_quantity = Column(Integer, default=0)
    average_fill_price = Column(Float, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)

    # Context
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    reasoning = Column(Text, nullable=True)  # Claude's reasoning for the trade
    is_paper_trade = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    stock = relationship("Stock", back_populates="orders")
    executions = relationship("TradeExecution", back_populates="order")
    conversation = relationship("Conversation")


class TradeExecution(Base, TimestampMixin):
    __tablename__ = "trade_executions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("trade_orders.id"), nullable=False)

    # Execution details
    broker_execution_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    executed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("TradeOrder", back_populates="executions")


class Position(Base, TimestampMixin):
    __tablename__ = "positions"
    __table_args__ = (
        Index("ix_positions_user_stock", "user_id", "stock_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    # Position details
    quantity = Column(Integer, nullable=False)
    average_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    market_value = Column(Float, nullable=True)

    # P&L
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)

    # Risk management
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)

    # Status
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="positions")
    stock = relationship("Stock", back_populates="positions")
