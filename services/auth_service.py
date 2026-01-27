from passlib.context import CryptContext
import os
from sqlalchemy.orm import Session
from sqlalchemy import select
from database.models.general import User, Business, BusinessSettings
import uuid
import logging
import secrets
from datetime import datetime, timedelta
from services.email_service import email_service

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
logger = logging.getLogger(__name__)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # PBKDF2 has no 72-byte limit, so we don't need manual truncation
    return pwd_context.hash(password)

async def authenticate_user(session, email, password):
    from sqlalchemy.orm import joinedload
    stmt = select(User).options(joinedload(User.business)).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        return False
    
    if user.business and user.business.status == "suspended":
        raise ValueError("This account has been suspended by the platform administrator.")
        
    if not verify_password(password, user.password_hash):
        return False
    return user

async def register_business(session, email, password, business_name):
    # Check if user exists
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise ValueError("User with this email already exists")

    # 1. Create Business
    # Simple ID generation: using sanitized name or uuid
    # Let's use User Email as business ID for simplicity in this MVP migration 
    # OR better, generate a simple ID.
    # The 'business_id' in previous code was often the email.
    # Let's keep business_id = email for compatibility with current logic if safe,
    # BUT user wants "create business knowledge".
    # Let's use a unique string ID.
    
    # Actually, using email as business_id is fragile if multiple users per business.
    # Let's create a proper UUID business_id.
    
    business_id = str(uuid.uuid4())
    
    new_business = Business(
        id=business_id,
        name=business_name,
        status="trial",
        plan_name="starter",
        trial_start_at=datetime.utcnow(),
        trial_end_at=datetime.utcnow() + timedelta(days=14)
    )
    session.add(new_business)
    
    # 2. Create User (Owner)
    hashed_pwd = get_password_hash(password)
    user_id = str(uuid.uuid4())
    
    new_user = User(
        id=user_id,
        business_id=business_id,
        email=email,
        password_hash=hashed_pwd,
        role="owner"
    )
    session.add(new_user)
    
    # 3. Default Settings
    settings = BusinessSettings(
        business_id=business_id,
        description=f"Business profile for {business_name}",
        tone="professional"
    )
    session.add(settings)
    
    await session.commit()
    
    return {"business_id": business_id, "user_id": user_id, "email": email}

async def create_reset_token(session, email: str):
    """Generates a reset token, saves it, and sends it via email."""
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        return False
        
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    # Token valid for 15 minutes as per requirements
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
    
    await session.commit()
    
    # Send real email
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    
    # Send via email service
    await email_service.send_reset_email(email, reset_link)
    
    logger.info(f"PASSWORD RESET REQUEST: User {email} requested reset. Link sent to email.")
    
    return True

async def reset_password(session, token: str, new_password: str):
    """Verifies the token and updates the password if valid."""
    stmt = select(User).where(User.reset_token == token)
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user or not user.reset_token_expiry:
        return False
        
    if user.reset_token_expiry < datetime.utcnow():
        # Token expired
        user.reset_token = None
        user.reset_token_expiry = None
        await session.commit()
        return False
        
    # Valid token
    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    
    await session.commit()
    return True
