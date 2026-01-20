from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class SentimentPost(Base, TimestampMixin):
    __tablename__ = "sentiment_posts"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)  # "reddit", "news"
    source_id = Column(String, unique=True, nullable=False)  # Reddit post ID or article URL
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    author = Column(String, nullable=True)
    url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=False, index=True)

    # Sentiment scores
    sentiment_compound = Column(Float, nullable=True)  # -1 to 1
    sentiment_positive = Column(Float, nullable=True)
    sentiment_negative = Column(Float, nullable=True)
    sentiment_neutral = Column(Float, nullable=True)

    # Engagement metrics
    upvotes = Column(Integer, default=0)
    comments = Column(Integer, default=0)

    # Relationships
    stock_mentions = relationship("SentimentStockMention", back_populates="post")


class SentimentStockMention(Base, TimestampMixin):
    __tablename__ = "sentiment_stock_mentions"
    __table_args__ = (
        Index("ix_sentiment_stock_date", "stock_id", "created_at"),
        Index("ix_sentiment_post_stock", "post_id", "stock_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("sentiment_posts.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    # Mention context
    mention_count = Column(Integer, default=1)
    sentiment_score = Column(Float, nullable=True)  # Specific sentiment for this mention

    # Relationships
    post = relationship("SentimentPost", back_populates="stock_mentions")
    stock = relationship("Stock", back_populates="sentiment_mentions")
