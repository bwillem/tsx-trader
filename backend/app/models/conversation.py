from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation", "conversation_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)

    # Tool execution tracking
    tool_calls = Column(Text, nullable=True)  # JSON string of tool calls
    tool_results = Column(Text, nullable=True)  # JSON string of tool results

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
