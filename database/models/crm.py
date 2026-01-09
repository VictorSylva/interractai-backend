from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"))
    
    name = Column(String)
    contact = Column(String) # Email or Phone
    source = Column(String)
    notes = Column(Text)
    status = Column(String, default="new")
    
    source_rule = Column(String) # Which workflow captured this?
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="leads")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"))
    
    subject = Column(String)
    description = Column(Text)
    priority = Column(String, default="medium")
    status = Column(String, default="open")
    
    created_at = Column(DateTime, default=datetime.utcnow)

