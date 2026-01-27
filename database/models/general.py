from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base

class Business(Base):
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, index=True) # Manually assigned ID (e.g. 'demo')
    name = Column(String)
    status = Column(String, default="active") # active, suspended, trial, expired
    plan_name = Column(String, default="starter")
    trial_start_at = Column(DateTime, nullable=True)
    trial_end_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="business")
    settings = relationship("BusinessSettings", back_populates="business", uselist=False)
    knowledge_docs = relationship("KnowledgeDoc", back_populates="business")
    conversations = relationship("Conversation", back_populates="business")
    workflows = relationship("Workflow", back_populates="business")
    leads = relationship("Lead", back_populates="business")
    whatsapp_config = relationship("BusinessWhatsAppConfig", back_populates="business", uselist=False)
    activities = relationship("LeadActivity", back_populates="business")
    
    # Scheduling Relationships
    appointment_types = relationship("AppointmentType", back_populates="business")
    availability_rules = relationship("AvailabilityRule", back_populates="business")
    appointments = relationship("Appointment", back_populates="business")

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    business_id = Column(String, ForeignKey("businesses.id"))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String) # For SQL Auth
    role = Column(String, default="agent") # owner, agent
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="users")

class BusinessSettings(Base):
    """Stores profile, tone, etc."""
    __tablename__ = "business_settings"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"), unique=True)
    
    industry = Column(String)
    description = Column(Text)
    services = Column(Text)
    tone = Column(String)
    faq = Column(Text)
    custom_instructions = Column(Text)
    location = Column(String)
    hours = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="settings")

class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    
    id = Column(String, primary_key=True) # UUID
    business_id = Column(String, ForeignKey("businesses.id"))
    type = Column(String) # file, url
    title = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="knowledge_docs")

class BusinessWhatsAppConfig(Base):
    """Stores business-specific WhatsApp API credentials."""
    __tablename__ = "business_whatsapp_configs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"), unique=True)
    
    phone_number_id = Column(String)
    business_account_id = Column(String)
    app_id = Column(String)
    app_secret = Column(Text) # Encrypted
    access_token = Column(Text) # Encrypted
    
    webhook_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="whatsapp_config")
