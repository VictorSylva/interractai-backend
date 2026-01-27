from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text, Time
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base
import uuid

class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"))
    
    name = Column(String, nullable=False) # Demo, Consultation, etc.
    description = Column(Text)
    duration_minutes = Column(Integer, default=30)
    color_code = Column(String, default="#3b82f6") # Default blue
    is_active = Column(Boolean, default=True)
    
    business = relationship("Business", back_populates="appointment_types")
    appointments = relationship("Appointment", back_populates="appointment_type")

class AvailabilityRule(Base):
    __tablename__ = "availability_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"))
    
    day_of_week = Column(Integer) # 0 = Monday, 6 = Sunday
    start_time = Column(Time) # e.g., 09:00:00
    end_time = Column(Time)   # e.g., 17:00:00
    is_active = Column(Boolean, default=True)
    
    business = relationship("Business", back_populates="availability_rules")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    conversation_id = Column(String, nullable=True) # For anonymous/web chat links
    appointment_type_id = Column(String, ForeignKey("appointment_types.id"))
    
    start_at = Column(DateTime, index=True)
    end_at = Column(DateTime)
    status = Column(String, default="scheduled") # scheduled, confirmed, completed, cancelled, no_show
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="appointments")
    lead = relationship("Lead") # No back_populates needed on Lead for now, or add it if helpful
    appointment_type = relationship("AppointmentType", back_populates="appointments")
