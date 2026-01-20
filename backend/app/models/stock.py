from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)  # e.g., "TD.TO"
    name = Column(String, nullable=False)
    exchange = Column(String, default="TSX")
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    is_active = Column(String, default=True)

    # Relationships
    market_data = relationship("MarketDataDaily", back_populates="stock")
    sentiment_mentions = relationship("SentimentStockMention", back_populates="stock")
    positions = relationship("Position", back_populates="stock")
    orders = relationship("TradeOrder", back_populates="stock")


class MarketDataDaily(Base, TimestampMixin):
    __tablename__ = "market_data_daily"
    __table_args__ = (Index("ix_market_data_symbol_date", "stock_id", "date"),)

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)

    # Technical Indicators
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    ema_12 = Column(Float, nullable=True)
    ema_26 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_middle = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)

    # Relationships
    stock = relationship("Stock", back_populates="market_data")
