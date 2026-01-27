from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"))
    
    name = Column(String)
    contact = Column(String) # Email or Phone (Legacy)
    email = Column(String)
    phone = Column(String)
    source = Column(String)
    notes = Column(Text)
    status = Column(String, default="new")
    
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)
    conversation_id = Column(String)
    last_interaction_at = Column(DateTime)
    value = Column(Integer) # Estimated value/budget

    source_rule = Column(String) # Which workflow captured this?
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="leads")
    activities = relationship("LeadActivity", back_populates="lead")

class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    business_id = Column(String, ForeignKey("businesses.id"), index=True)
    
    type = Column(String) # status_change, note, message_sent, system
    content = Column(JSON) # e.g. {"old_status": "new", "new_status": "contacted"} or {"text": "Called client"}
    created_by = Column(String) # user_id or 'system'
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="activities")
    business = relationship("Business", back_populates="activities")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"))
    
    subject = Column(String)
    description = Column(Text)
    priority = Column(String, default="medium")
    status = Column(String, default="open")
    
    created_at = Column(DateTime, default=datetime.utcnow)

