from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class TradingDecision(Base, TimestampMixin):
    """Logs Claude's trading decisions and reasoning"""

    __tablename__ = "trading_decisions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)

    # Decision
    decision = Column(
        String, nullable=False
    )  # "buy", "sell", "hold", "close_position"
    confidence = Column(Float, nullable=True)  # 0-1 confidence score

    # Analysis
    technical_signal = Column(String, nullable=True)  # "bullish", "bearish", "neutral"
    sentiment_score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=False)
    market_conditions = Column(Text, nullable=True)

    # Suggested action (for manual review)
    suggested_action = Column(Text, nullable=True)  # JSON string with trade details

    # Action taken
    order_id = Column(Integer, ForeignKey("trade_orders.id"), nullable=True)
    action_taken = Column(Boolean, default=False)
    action_reason = Column(
        Text, nullable=True
    )  # Why action was or wasn't taken (e.g., validation failure)

    # Relationships
    user = relationship("User")
    stock = relationship("Stock")
    order = relationship("TradeOrder")
