from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Questrade tokens
    questrade_access_token = Column(String, nullable=True)
    questrade_refresh_token = Column(String, nullable=True)
    questrade_api_server = Column(String, nullable=True)
    questrade_token_expires_at = Column(String, nullable=True)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    positions = relationship("Position", back_populates="user")
    orders = relationship("TradeOrder", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="user")


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Trading parameters
    position_size_pct = Column(Float, default=20.0)
    stop_loss_pct = Column(Float, default=5.0)
    daily_loss_limit_pct = Column(Float, default=5.0)
    max_open_positions = Column(Integer, default=10)
    min_cash_reserve_pct = Column(Float, default=10.0)
    min_risk_reward_ratio = Column(Float, default=2.0)

    # Trading mode
    paper_trading_enabled = Column(Boolean, default=True)
    auto_trading_enabled = Column(Boolean, default=False)

    # Risk management
    require_stop_loss = Column(Boolean, default=True)
    circuit_breaker_enabled = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="settings")
