import os
from dotenv import load_dotenv

# Load Environment Variables BEFORE any other local imports
ENV = os.getenv("ENV", "production") 
if ENV == "dev":
    env_file = ".env.dev"
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded configuration from {env_file}")
    else:
        print(f"Warning: ENV=dev but {env_file} not found")
else:
    load_dotenv() # Production fallbacks

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from pydantic import BaseModel
from services.ai_service import generate_response
from services.db_service import store_message, get_chat_history, get_recent_conversations, get_conversation_messages, \
    add_knowledge_document, get_knowledge_documents, delete_knowledge_document, save_lead, \
    get_business_profile, update_business_profile, get_learned_insights, update_conversation_stats, log_prompt_execution, \
    get_whatsapp_config, update_whatsapp_config, update_lead, get_lead_activities, send_lead_message
from services.whatsapp_service import router as whatsapp_router
from services.workflow_engine import workflow_engine
from services.file_service import extract_text_from_file, scrape_url
from celery_app import celery_app # Ensure Celery is loaded for task dispatch

# Load Environment Variables Dynamically
ENV = os.getenv("ENV", "production") # Default to production for safety if not set
if ENV == "dev":
    env_file = ".env.dev"
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded configuration from {env_file}")
    else:
        print(f"Warning: ENV=dev but {env_file} not found")
else:
    # Production or other environments: Use system env vars (Render)
    # We can still check for .env as a convenient fallback for local prod-like testing if needed
    if os.path.exists(".env"):
        load_dotenv(".env")
        print("Loaded configuration from default .env")
    else:
        print("Using system environment variables")

app = FastAPI(title="Interact API", description="Backend for Interact AI Automation Platform (SQL + Workflow Engine)")

# CORS Setup
origins = [
    "http://localhost:3000",
    "https://interac-ai.web.app",
    "https://interac-ai.firebaseapp.com",
    "https://interact-demo.web.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Interact API is running (PostgreSQL + Celery)"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    # Auto-create tables for MVP (replaces manually running alembic revision for now)
    from database.session import engine
    from database.base import Base
    from database.models import general, chat, crm, workflow, scheduling
    import asyncio
    
    max_retries = 20
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                # One-time patches for existing tables (PostgreSQL specific)
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP"))
                await conn.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active'"))
                await conn.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS plan_name VARCHAR DEFAULT 'starter'"))
                await conn.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS trial_start_at TIMESTAMP"))
                await conn.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS trial_end_at TIMESTAMP"))
                
            logger.info("Database connection established and tables updated.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (Attempt {attempt + 1}/{max_retries}). Retrying in 3s... Error: {e}")
                await asyncio.sleep(3)
            else:
                logger.error("Could not connect to database after multiple attempts.")
                raise e

app.include_router(whatsapp_router, prefix="/whatsapp")

@app.get("/api/conversations")
async def read_conversations(business_id: str):
    """Get list of conversations for a business"""
    from services.db_service import resolve_business_id, get_recent_conversations
    bid = await resolve_business_id(business_id)
    return await get_recent_conversations(business_id=bid)

@app.get("/api/conversations/{user_id}/messages")
async def read_messages(user_id: str, business_id: str):
    """Get messages for a specific conversation in a business"""
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    return await get_conversation_messages(bid, user_id)

from services.db_service import get_leads, get_analytics_summary

# leads is defined again below with more features, removing duplicate

@app.get("/api/analytics")
async def read_analytics(business_id: str, days: int = 30):
    from services.db_service import resolve_business_id, get_analytics_summary
    bid = await resolve_business_id(business_id)
    return await get_analytics_summary(bid, days=days)

@app.get("/api/analytics/insights")
async def get_analytics_insights(business_id: str):
    from services.db_service import resolve_business_id
    from services.sales_intelligence_service import sales_intelligence_service
    bid = await resolve_business_id(business_id)
    return await sales_intelligence_service.get_ai_insights(bid)

# --- Authentication ---
from services.auth_service import register_business, authenticate_user, create_reset_token, reset_password
from database.session import get_db

class RegisterRequest(BaseModel):
    email: str
    password: str
    business_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@app.post("/api/auth/register")
async def register_endpoint(body: RegisterRequest):
    from database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            result = await register_business(session, body.email, body.password, body.business_name)
            return {"status": "success", "data": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login")
async def login_endpoint(body: LoginRequest):
    from database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            user = await authenticate_user(session, body.email, body.password)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(status_code=500, detail="Database connection error. Please check backend logs.")
        
        if not user:
             raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "email": user.email,
            "business_id": user.business_id,
            "role": user.role
        },
        "token": "dummy-jwt-token-for-mvp" 
    }

@app.post("/api/auth/forgot-password")
async def forgot_password_endpoint(body: ForgotPasswordRequest):
    from database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        # Note: For security, usually return success even if email doesn't exist
        # to prevent user enumeration. But for MVP let's be explicit.
        success = await create_reset_token(session, body.email)
        if not success:
            # We'll still say success for security if desired, but for now:
            raise HTTPException(status_code=404, detail="Email not found")
        return {"status": "success", "message": "Reset link sent"}

@app.post("/api/auth/reset-password")
async def reset_password_endpoint(body: ResetPasswordRequest):
    from database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        success = await reset_password(session, body.token, body.new_password)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        return {"status": "success", "message": "Password updated"}

# --- Web Chat & Automation ---

class WebMessage(BaseModel):
    user_id: str
    message: str
    business_id: str = "default"

class BusinessProfile(BaseModel):
    business_id: str
    name: str = None
    industry: str = None
    description: str = None
    services: str = None
    tone: str = None
    faq: str = None
    custom_instructions: str = None
    location: str = None
    hours: str = None

class WhatsAppConfigRequest(BaseModel):
    business_id: str
    phone_number_id: str = None
    business_account_id: str = None
    app_id: str = None
    app_secret: str = None
    access_token: str = None
    is_active: bool = None

class AppointmentTypeRequest(BaseModel):
    name: str
    description: str = None
    duration_minutes: int = 30
    color_code: str = "#3b82f6"

class AvailabilityRuleRequest(BaseModel):
    day_of_week: int # 0-6
    start_time: str # "HH:MM"
    end_time: str   # "HH:MM"
    is_active: bool = True

@app.get("/api/business-status")
async def read_business_status(business_id: str):
    from services.db_service import resolve_business_id, get_business_status
    bid = await resolve_business_id(business_id)
    status = await get_business_status(bid)
    if not status:
        raise HTTPException(status_code=404, detail="Business not found")
    return status

@app.get("/api/business-profile")
async def get_profile(business_id: str):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    return await get_business_profile(bid)

@app.post("/api/business-profile")
async def update_profile(profile: BusinessProfile):
    from services.db_service import resolve_business_id
    data = profile.dict(exclude_unset=True)
    bid = data.pop('business_id')
    real_bid = await resolve_business_id(bid)
    await update_business_profile(real_bid, data)
    return {"status": "updated", "data": data}

@app.get("/api/whatsapp/config")
async def get_whatsapp_config_endpoint(business_id: str):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    config = await get_whatsapp_config(bid)
    if not config:
        return {"status": "not_configured"}
    return {"status": "success", "config": config}

@app.post("/api/whatsapp/config")
async def update_whatsapp_config_endpoint(req: WhatsAppConfigRequest):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(req.business_id)
    data = req.dict(exclude_unset=True)
    data.pop('business_id')
    success = await update_whatsapp_config(bid, data)
    return {"status": "success" if success else "failed"}

@app.post("/api/whatsapp/test-message")
async def test_whatsapp_message(business_id: str, phone: str):
    from services.whatsapp_service import send_whatsapp_message
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    
    try:
        await send_whatsapp_message(phone, "Hello! This is a test message from your InterractAI dashboard.", business_id=bid)
        return {"status": "success", "message": "Test message sent!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/train/{business_id}")
async def train_business_ai(business_id: str):
    # Retrieve current profile and knowledge to "simulate" training or fine-tune
    # For now, we just ensure knowledge is indexed (if using vector db later)
    return {"status": "trained", "message": "Business AI updated with latest knowledge."}

@app.post("/api/web-chat")
async def web_chat(body: WebMessage):
    from services.db_service import resolve_business_id, get_chat_history
    profile_id = await resolve_business_id(body.business_id)
    # real_business_id is now consistently the UUID if user found
    real_business_id = profile_id 
    
    if "@" in body.business_id and profile_id == body.business_id:
        # Fallback for when resolve_business_id didn't find a user but it IS an email
        logger.warning(f"Could not resolve business_id from email {body.business_id}")
    else:
        logger.info(f"Resolved BID: {body.business_id} -> {profile_id}")

    # Check Subscription Access
    from services.subscription_service import check_subscription_access
    if not await check_subscription_access(real_business_id):
        logger.warning(f"[WebChat] Blocked access for {real_business_id} (expired/suspended)")
        return {"reply": "Your trial has ended. Please upgrade your plan to continue using InteracAI.", "status": "blocked"}

    # 1. Fetch Chat History BEFORE storing new message (Clean Context)
    raw_history = await get_chat_history(real_business_id, body.user_id, limit=5)
    formatted_history = []
    for msg in raw_history:
        role = "user" if msg['sender'] == 'customer' else "assistant"
        formatted_history.append({"role": role, "content": msg['text']})

    # 2. Store User Message
    await store_message(real_business_id, body.user_id, body.message, "customer", platform="web")
    
    # 3. Detect Intent & Sentiment (Prompt Service)
    from services.prompt_service import prompt_service
    detected_intent = prompt_service.detect_intent(body.message)
    sentiment = prompt_service.analyze_sentiment(body.message) # Assume this exists or mock it
    
    # 4. Check Workflow Automations
    # Trigger event data
    trigger_data = {
        "message": body.message,
        "message_body": body.message, # ALIAS for engine compatibility
        "intent": detected_intent,
        "user_id": body.user_id,
        "business_id": body.business_id # CRITICAL: Include in context for nodes
    }
    
    # 3.1 Fire and Forget Workflow Trigger
    logger.info(f"[Chat] Message Received: '{body.message}' | User: {body.user_id} | BID: {real_business_id}")
    executions = await workflow_engine.trigger_workflow(real_business_id, "message_created", trigger_data)
    
    if executions:
        logger.info(f"[Chat] Workflow Action: Started/Resumed {len(executions)} execution(s) {executions}")
        logger.info(f"[Chat] Response Arbitration: Default AI Suppressed for BID {body.business_id} (Workflow Handled)")
        return {"reply": None, "status": "workflow_processing", "executions": executions}
    
    logger.info(f"[Chat] Response Arbitration: No workflow matched. Proceeding with Default AI.")
    
    profile = await get_business_profile(profile_id)
    knowledge_docs = await get_knowledge_documents(profile_id)
    if knowledge_docs:
        profile['knowledge_docs'] = knowledge_docs

    system_instruction = prompt_service.build_system_prompt(profile)
    
    ai_reply = await generate_response(
        body.message, 
        formatted_history, 
        body.user_id, 
        system_instruction=system_instruction,
        business_id=real_business_id
    )

    logger.debug(f"[Chat] Raw AI Reply for BID {real_business_id}: {ai_reply}")

    # 5. Post-Processing (Action Parsers)
    import re
    import json
    
    # [ACTION: LEAD_CAPTURE | JSON]
    lead_match = re.search(r'\[ACTION: LEAD_CAPTURE\s*\|\s*(?P<json>\{.*?\})\]', ai_reply, re.IGNORECASE | re.DOTALL)
    if lead_match:
        try:
            lead_json_str = lead_match.group('json')
            # Clean up potential markdown formatting from AI
            lead_json_str = lead_json_str.strip()
            if lead_json_str.startswith("```json"):
                lead_json_str = lead_json_str.replace("```json", "", 1)
            if lead_json_str.endswith("```"):
                lead_json_str = lead_json_str.rsplit("```", 1)[0]
            
            lead_data = json.loads(lead_json_str)
            logger.info(f"[LeadCapture] Parsed JSON for BID {real_business_id}: {lead_data}")
            
            # Field Mapping (AI might use 'contact' instead of 'email'/'phone')
            if "contact" in lead_data and not lead_data.get("email") and not lead_data.get("phone"):
                contact = str(lead_data["contact"])
                if "@" in contact:
                    lead_data["email"] = contact
                else:
                    lead_data["phone"] = contact
                del lead_data["contact"]

            # Inject matching conversation_id for CRM linking (Composite ID)
            lead_data["conversation_id"] = f"{real_business_id}:{body.user_id}"
            
            await save_lead(real_business_id, lead_data)
            ai_reply = ai_reply.replace(lead_match.group(0), "").strip()
        except Exception as e:
            logger.error(f"Error parsing lead capture JSON: {e} | Raw: {lead_match.group('json')}")

    # 5.1 Parse ANALYSIS tag for better Intent/Sentiment
    analysis_match = re.search(r'\[ANALYSIS:\s*(?P<intent>.*?)\s*\|\s*(?P<sentiment>.*?)\s*\]', ai_reply, re.IGNORECASE)
    if analysis_match:
        ai_intent = analysis_match.group('intent').strip().lower()
        ai_sentiment = analysis_match.group('sentiment').strip()
        if ai_intent in ["booking", "enquiry", "pricing", "support", "greeting", "features", "integration", "complaint", "feedback", "human"]:
            detected_intent = ai_intent
            sentiment = ai_sentiment
            logger.info(f"[Chat] AI Refined Intent: {detected_intent} | Sentiment: {sentiment}")
        
        # Remove internal [ANALYSIS: ...] tag
        ai_reply = ai_reply.replace(analysis_match.group(0), "").strip()

    # Final cleanup of any remaining internal markers
    ai_reply = re.sub(r'\[ACTION:.*?\]', '', ai_reply).strip()
    ai_reply = re.sub(r'\[ANALYSIS:.*?\]', '', ai_reply).strip()

    await store_message(real_business_id, body.user_id, ai_reply, "agent", platform="web", intent=detected_intent, sentiment=sentiment)
    
    return {"reply": ai_reply}

@app.get("/api/web-chat/history")
async def get_chat_history_endpoint(business_id: str, user_id: str):
    from services.db_service import resolve_business_id
    real_bid = await resolve_business_id(business_id)
    history = await get_chat_history(real_bid, user_id, limit=50)
    # Return in chronological order (Oldest -> Newest) which get_chat_history already does
    return {"messages": history}

# --- Knowledge Base endpoints ---

@app.post("/api/knowledge/upload")
async def upload_knowledge(business_id: str, file: UploadFile = File(...)):
    if not file.filename.endswith(('.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Only .docx and .txt files are supported")
    
    content = await file.read()
    text = await extract_text_from_file(content, file.filename)
    
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from file")
        
    doc_data = {
        "title": file.filename,
        "type": "file",
        "content": text
    }
    
    doc_id = await add_knowledge_document(business_id, doc_data)
    return {"status": "success", "id": doc_id, "text_preview": text[:200]}

class ScrapeRequest(BaseModel):
    url: str
    business_id: str

@app.post("/api/knowledge/scrape")
async def scrape_knowledge(req: ScrapeRequest):
    text = await scrape_url(req.url)
    
    if "Error" in text and len(text) < 100:
         raise HTTPException(status_code=400, detail=text)
         
    doc_data = {
        "title": req.url,
        "type": "url",
        "content": text
    }
    
    doc_id = await add_knowledge_document(req.business_id, doc_data)
    return {"status": "success", "id": doc_id, "text_preview": text[:200]}

@app.get("/api/knowledge")
async def list_knowledge(business_id: str):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    return await get_knowledge_documents(bid)

@app.delete("/api/knowledge/{doc_id}")
async def delete_knowledge(doc_id: str, business_id: str):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    success = await delete_knowledge_document(bid, doc_id)
    return {"status": "success" if success else "failed"}

# --- Workflow Management API ---

@app.post("/api/workflows")
async def create_workflow_endpoint(workflow_data: dict):
    from services.db_service import resolve_business_id
    bid = workflow_data.get("business_id", "default")
    real_bid = await resolve_business_id(bid)
    logger.info(f"[Workflows] Create Workflow for BID: {bid} (Resolved: {real_bid})")
    result = await workflow_engine.create_workflow(real_bid, workflow_data)
    return result

@app.get("/api/workflows")
async def list_workflows(business_id: str = "default"):
    from services.db_service import resolve_business_id
    real_bid = await resolve_business_id(business_id)
    wfs = await workflow_engine.get_workflows(real_bid)
    return wfs

@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow_endpoint(workflow_id: str, business_id: str = "default"):
    from services.db_service import resolve_business_id
    real_bid = await resolve_business_id(business_id)
    success = await workflow_engine.delete_workflow(real_bid, workflow_id)
    if success:
        return {"status": "deleted", "id": workflow_id}
    else:
        raise HTTPException(status_code=404, detail="Workflow not found or access denied")

@app.post("/api/workflows/{workflow_id}/trigger")
async def trigger_workflow_manual(workflow_id: str, payload: dict):
    from services.db_service import resolve_business_id
    bid = payload.get("business_id", "default")
    real_bid = await resolve_business_id(bid)
    execution_id = await workflow_engine.trigger_specific_workflow(real_bid, workflow_id, payload)
    if execution_id:
        return {"status": "triggered", "execution_id": execution_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to trigger workflow")

@app.get("/api/executions")
async def list_executions(business_id: str = "default", workflow_id: str = None):
    from services.db_service import resolve_business_id
    real_bid = await resolve_business_id(business_id)
    return await workflow_engine.get_executions(real_bid, workflow_id)

# --- Super Admin API ---
from services.admin_service import admin_service

@app.get("/api/super-admin/stats")
async def get_admin_stats(user_id: str = None):
    # In production, verify user_id role here
    return await admin_service.get_platform_stats()

@app.get("/api/super-admin/businesses")
async def get_admin_businesses(user_id: str = None):
    return await admin_service.get_all_businesses()

class StatusUpdate(BaseModel):
    status: str

@app.patch("/api/super-admin/businesses/{business_id}/status")
async def update_business_status(business_id: str, update: StatusUpdate):
    success = await admin_service.update_business_status(business_id, update.status)
    if not success:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"status": "success"}

@app.delete("/api/super-admin/businesses/{business_id}")
async def delete_business(business_id: str):
    success = await admin_service.delete_business(business_id)
    if not success:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"status": "success"}

# --- CRM API ---
from services.db_service import get_leads

@app.get("/api/leads")
async def list_leads(business_id: str):
    """Get all leads for a business"""
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    return await get_leads(bid)

class LeadUpdate(BaseModel):
    status: str = None
    value: int = None
    tags: list = None

@app.patch("/api/leads/{lead_id}")
async def update_lead_endpoint(lead_id: int, update: LeadUpdate, business_id: str, user_id: str = "system"):
    """Update lead and log activity"""
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    updates = {k: v for k, v in update.dict().items() if v is not None}
    result = await update_lead(bid, lead_id, updates, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result

@app.get("/api/leads/{lead_id}/activity")
async def get_lead_activity(lead_id: int, business_id: str):
    """Get activity timeline for a lead"""
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    return await get_lead_activities(bid, lead_id)

class MessageRequest(BaseModel):
    message: str
    user_id: str = "system"

@app.post("/api/leads/{lead_id}/message")
async def send_message_to_lead(lead_id: int, req: MessageRequest, business_id: str):
    """Send a message to a lead"""
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    result = await send_lead_message(bid, lead_id, req.message, req.user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))
    return result

@app.post("/api/leads/{lead_id}/insights")
async def generate_lead_insights(lead_id: int, business_id: str):
    """Generate AI insights for a lead and log as activity"""
    from services.crm_intelligence import crm_intelligence
    from services.db_service import get_lead_activities, resolve_business_id
    from database.session import AsyncSessionLocal
    from database.models.crm import Lead, LeadActivity
    from sqlalchemy import select
    
    bid = await resolve_business_id(business_id)
    
    async with AsyncSessionLocal() as session:
        # Get lead
        lead = await session.get(Lead, lead_id)
        if not lead or lead.business_id != bid:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Calculate score
        lead_dict = {
            "email": lead.email,
            "phone": lead.phone,
            "value": lead.value,
            "tags": lead.tags,
            "status": lead.status,
            "last_interaction_at": lead.last_interaction_at
        }
        score_data = crm_intelligence.calculate_lead_score(lead_dict)
        
        # Log as activity
        activity = LeadActivity(
            lead_id=lead.id,
            business_id=bid,
            type="ai_insight",
            content={
                "insight_type": "lead_score",
                "score": score_data["score"],
                "tier": score_data["tier"],
                "factors": score_data["factors"]
            },
            created_by="ai",
            created_at=datetime.utcnow()
        )
        session.add(activity)
        await session.commit()
        
        return {
            "success": True,
            "insights": score_data
        }

# --- Scheduling API ---
from services.scheduling_service import scheduling_service
from database.models.scheduling import AppointmentType, AvailabilityRule
from sqlalchemy import select, delete

@app.get("/api/scheduling/types")
async def get_appointment_types(business_id: str):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    async with AsyncSessionLocal() as session:
        stmt = select(AppointmentType).where(AppointmentType.business_id == bid)
        res = await session.execute(stmt)
        return res.scalars().all()

@app.post("/api/scheduling/types")
async def create_appointment_type(business_id: str, req: AppointmentTypeRequest):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    async with AsyncSessionLocal() as session:
        apt_type = AppointmentType(
            business_id=bid,
            name=req.name,
            description=req.description,
            duration_minutes=req.duration_minutes,
            color_code=req.color_code
        )
        session.add(apt_type)
        await session.commit()
        await session.refresh(apt_type)
        return apt_type

@app.get("/api/scheduling/availability")
async def get_availability(business_id: str):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    async with AsyncSessionLocal() as session:
        stmt = select(AvailabilityRule).where(AvailabilityRule.business_id == bid)
        res = await session.execute(stmt)
        return res.scalars().all()

@app.post("/api/scheduling/availability")
async def update_availability(business_id: str, rules: list[AvailabilityRuleRequest]):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    async with AsyncSessionLocal() as session:
        # Simple implementation: Clear and Replace
        await session.execute(delete(AvailabilityRule).where(AvailabilityRule.business_id == bid))
        
        for r in rules:
            from datetime import time as py_time
            sh, sm = map(int, r.start_time.split(':'))
            eh, em = map(int, r.end_time.split(':'))
            
            rule = AvailabilityRule(
                business_id=bid,
                day_of_week=r.day_of_week,
                start_time=py_time(sh, sm),
                end_time=py_time(eh, em),
                is_active=r.is_active
            )
            session.add(rule)
        
        await session.commit()
        return {"status": "success"}

@app.get("/api/scheduling/appointments")
async def get_appointments(business_id: str, start: str = None, end: str = None, lead_id: int = None):
    from services.db_service import resolve_business_id
    bid = await resolve_business_id(business_id)
    
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None
    
    apts = await scheduling_service.get_business_appointments(bid, start_dt, end_dt, lead_id)
    return apts

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
