from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class PortfolioSnapshot(Base, TimestampMixin):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False, index=True)

    # Values
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)

    # P&L
    daily_pnl = Column(Float, default=0.0)
    daily_pnl_pct = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)

    # Trading metrics
    num_positions = Column(Integer, default=0)
    num_trades_today = Column(Integer, default=0)
    win_rate = Column(Float, nullable=True)

    # Risk metrics
    largest_position_pct = Column(Float, nullable=True)
    cash_reserve_pct = Column(Float, nullable=True)
    daily_loss_from_high = Column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="portfolio_snapshots")
