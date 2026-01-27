from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True) # User ID (e.g. phone number or cookie ID)
    business_id = Column(String, ForeignKey("businesses.id"), index=True)
    
    customer_name = Column(String)
    platform = Column(String) # whatsapp, web
    last_message = Column(Text)
    last_timestamp = Column(DateTime, index=True)
    unread_count = Column(Integer, default=0)
    
    # Analytics Snapshot
    last_intent = Column(String)
    last_sentiment = Column(String)

    business = relationship("Business", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"), index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), index=True)
    
    text = Column(Text)
    sender = Column(String) # customer, agent
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    platform = Column(String)
    status = Column(String, default="sent") # pending, sent, failed
    
    intent = Column(String)
    sentiment = Column(String)

    conversation = relationship("Conversation", back_populates="messages")
