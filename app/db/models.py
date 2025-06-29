"""Database models for the Jedi Agent application."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class MarketResearchData(Base):
    """Store the market research statements."""
    __tablename__ = "market_research_data"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """User model for multi-user support."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to conversations
    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    """Conversation model to persist chat sessions."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """Message model for storing individual messages in conversations."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column(Text, nullable=True)  # JSON string for tool calls, citations, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages")


class ToolInvocation(Base):
    """Track tool usage for analytics."""
    __tablename__ = "tool_invocations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)  # Link to specific message
    tool_name = Column(String(100), nullable=False)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    execution_time = Column(Integer, nullable=True)  # milliseconds
    error_message = Column(Text, nullable=True)  # Store error details if failed
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    """Store user feedback on agent responses."""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    feedback_type = Column(String(20), nullable=False)  # 'thumbs_up', 'thumbs_down'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EvaluationScore(Base):
    """Store automated evaluation scores for responses."""
    __tablename__ = "evaluation_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    relevance_score = Column(Integer, nullable=True)  # 1-5 scale
    accuracy_score = Column(Integer, nullable=True)   # 1-5 scale
    completeness_score = Column(Integer, nullable=True)  # 1-5 scale
    overall_score = Column(Integer, nullable=True)    # 1-5 scale
    evaluation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
