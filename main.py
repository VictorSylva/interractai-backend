from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
from pydantic import BaseModel
from services.ai_service import generate_response
from services.db_service import store_message, get_chat_history, get_recent_conversations, get_conversation_messages, \
    add_knowledge_document, get_knowledge_documents, delete_knowledge_document, save_lead, \
    get_business_profile, update_business_profile, get_learned_insights, update_conversation_stats, log_prompt_execution
from services.whatsapp_service import router as whatsapp_router
from services.workflow_engine import workflow_engine
from services.file_service import extract_text_from_file, scrape_url
from celery_app import celery_app # Ensure Celery is loaded for task dispatch

load_dotenv()

app = FastAPI(title="Interact API", description="Backend for Interact AI Automation Platform (SQL + Workflow Engine)")

# CORS Setup
origins = [
    "http://localhost:3000",
    "https://interact-demo.web.app", 
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='.*', # Allow all origins for dev
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
    from database.models import general, chat, crm, workflow
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    return await get_conversation_messages(business_id, user_id)

from services.db_service import get_leads, get_analytics_summary

@app.get("/api/leads")
async def read_leads(business_id: str):
    from services.db_service import resolve_business_id, get_leads
    bid = await resolve_business_id(business_id)
    return await get_leads(bid)

@app.get("/api/analytics")
async def read_analytics(business_id: str):
    from services.db_service import resolve_business_id, get_analytics_summary
    bid = await resolve_business_id(business_id)
    return await get_analytics_summary(bid)

# --- Authentication ---
from services.auth_service import register_business, authenticate_user
from database.session import get_db

class RegisterRequest(BaseModel):
    email: str
    password: str
    business_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register_endpoint(body: RegisterRequest):
    session = await get_db().__anext__()
    try:
        result = await register_business(session, body.email, body.password, body.business_name)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login")
async def login_endpoint(body: LoginRequest):
    session = await get_db().__anext__()
    user = await authenticate_user(session, body.email, body.password)
    
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

@app.get("/api/business-profile")
async def get_profile(business_id: str):
    return await get_business_profile(business_id)

@app.post("/api/business-profile")
async def update_profile(profile: BusinessProfile):
    data = profile.dict(exclude_unset=True)
    bid = data.pop('business_id')
    await update_business_profile(bid, data)
    return {"status": "updated", "data": data}

@app.post("/api/train/{business_id}")
async def train_business_ai(business_id: str):
    # Retrieve current profile and knowledge to "simulate" training or fine-tune
    # For now, we just ensure knowledge is indexed (if using vector db later)
    return {"status": "trained", "message": "Business AI updated with latest knowledge."}

@app.post("/api/web-chat")
async def web_chat(body: WebMessage):
    from services.db_service import resolve_business_id
    profile_id = await resolve_business_id(body.business_id)
    # real_business_id is now consistently the UUID if user found
    real_business_id = profile_id 
    
    if "@" in body.business_id and profile_id == body.business_id:
        # Fallback for when resolve_business_id didn't find a user but it IS an email
        logger.warning(f"Could not resolve business_id from email {body.business_id}")
    else:
        logger.info(f"Resolved BID: {body.business_id} -> {profile_id}")

    # 1. Store User Message
    await store_message(real_business_id, body.user_id, body.message, "customer", platform="web")
    
    # 2. Detect Intent & Sentiment (Prompt Service)
    from services.prompt_service import prompt_service
    detected_intent = prompt_service.detect_intent(body.message)
    sentiment = prompt_service.analyze_sentiment(body.message) # Assume this exists or mock it
    
    # 3. Check Workflow Automations
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
    
    # 4. Dynamic AI Response (Standard Chatbot)
    profile = await get_business_profile(profile_id)
    # insights = await get_learned_insights(profile_id) 
    # profile['learned_insights'] = insights 
    
    knowledge_docs = await get_knowledge_documents(profile_id)
    if knowledge_docs:
        profile['knowledge_docs'] = knowledge_docs

    system_instruction = prompt_service.build_system_prompt(profile)

    raw_history = await get_chat_history(real_business_id, body.user_id, limit=5)
    formatted_history = []
    for msg in raw_history:
        role = "user" if msg['sender'] == 'customer' else "assistant"
        formatted_history.append({"role": role, "content": msg['text']})
    
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
    lead_match = re.search(r'\[ACTION: LEAD_CAPTURE\s*\|\s*(?P<json>\{.*?\})\]', ai_reply, re.IGNORECASE)
    if lead_match:
        try:
            lead_json_str = lead_match.group('json')
            lead_data = json.loads(lead_json_str)
            logger.info(f"[LeadCapture] Saving lead for BID {real_business_id}: {lead_data}")
            await save_lead(real_business_id, lead_data)
            ai_reply = ai_reply.replace(lead_match.group(0), "").strip()
        except Exception as e:
            print(f"Error parsing lead capture: {e}")

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
    return await get_knowledge_documents(business_id)

@app.delete("/api/knowledge/{doc_id}")
async def delete_knowledge(doc_id: str, business_id: str):
    success = await delete_knowledge_document(business_id, doc_id)
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
