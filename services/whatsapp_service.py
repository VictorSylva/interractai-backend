from fastapi import APIRouter, Request, HTTPException, Depends
import os
import logging
import re
import json
from .ai_service import generate_response
from .ai_service import generate_response
# from .db_service import db # Deprecated
import httpx

logger = logging.getLogger(__name__)
router = APIRouter()

from .db_service import get_whatsapp_config, get_business_id_by_phone_id

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "interact_secret_token")
# Global fallbacks for backward compatibility or system-level messages
DEFAULT_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
DEFAULT_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verifies the webhook for WhatsApp (Meta).
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        # We can support either a global verify token or business-specific ones.
        # For simplicity in the Meta developer portal, we'll keep one global verify token.
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            logger.info("Webhook verified successfully.")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    return {"status": "error", "message": "Missing parameters"}

@router.post("/webhook")
async def receive_message(request: Request):
    """
    Receives messages from WhatsApp.
    """
    try:
        data = await request.json()
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            msg_body = message.get("text", {}).get("body", "")
            
            if msg_body:
                logger.info(f"Received message from {from_number}: {msg_body}")
                
                # 1. Resolve Business ID from Phone Number ID (Tenancy Resolver)
                metadata = value.get("metadata", {})
                phone_id = metadata.get("phone_number_id")
                
                business_id = await get_business_id_by_phone_id(phone_id)
                
                if not business_id:
                    # Fallback to system-level if not found or configured per-business
                    business_id_input = os.getenv("PRIMARY_BUSINESS_ID", "groupcopac@gmail.com")
                    from .db_service import resolve_business_id
                    business_id = await resolve_business_id(business_id_input)
                else:
                    logger.info(f"Resolved Business ID {business_id} for Phone ID {phone_id}")

                # Check Subscription
                from services.subscription_service import check_subscription_access
                if not await check_subscription_access(business_id):
                    logger.warning(f"[WhatsApp] Blocked access for {business_id} (status: expired/suspended)")
                    # Optional: Notify user once.
                    await send_whatsapp_message(from_number, "Your InteracAI trial has ended. Please log in to your dashboard to upgrade.", business_id=business_id)
                    return {"status": "blocked"}

                from .db_service import store_message, get_chat_history
                await store_message(business_id, from_number, msg_body, "customer", platform="whatsapp")
                
                # 1.5. Trigger Workflow Automation ( Arbitration Check )
                # If a workflow is triggered or resumed, it OWNS the response.
                from .workflow_engine import workflow_engine
                from .prompt_service import prompt_service
                
                detected_intent = prompt_service.detect_intent(msg_body)
                detected_sentiment = prompt_service.analyze_sentiment(msg_body)
                
                trigger_cmd = {
                    "from_number": from_number,
                    "message_body": msg_body,
                    "platform": "whatsapp",
                    "business_id": business_id,
                    "intent": detected_intent,
                    "sentiment": detected_sentiment
                }
                logger.info(f"Triggering workflow for WhatsApp from {from_number} | BID: {business_id} | Intent: {detected_intent}")
                executions = await workflow_engine.trigger_workflow(business_id, "message_created", trigger_cmd)
                
                if executions:
                    logger.info(f"Workflow(s) {executions} handled the message. Suppressing default AI response (Arbitration Success).")
                    return {"status": "workflow_processing", "executions": executions}

                # 2. Fetch Context (Fall-through if no workflow matched)
                from services.db_service import get_business_profile, get_knowledge_documents
                from services.prompt_service import prompt_service
                
                # Retrieve profile matching the business_id
                profile = await get_business_profile(business_id) # Using email or UUID
                knowledge_docs = await get_knowledge_documents(business_id)
                if knowledge_docs:
                    profile['knowledge_docs'] = knowledge_docs

                system_instruction = prompt_service.build_system_prompt(profile)

                # Fetch history for context
                raw_history = await get_chat_history(business_id, from_number, limit=5)
                formatted_history = []
                for msg in raw_history:
                    role = "user" if msg['sender'] == 'customer' else "assistant"
                    formatted_history.append({"role": role, "content": msg['text']})

                # 3. Generate AI response (Standard Chatbot)
                logger.info(f"Response Arbitration: No workflow matched for WhatsApp. Falling back to Business AI.")
                ai_reply = await generate_response(msg_body, formatted_history, system_instruction=system_instruction)
                
                # 4. Post-Processing (Action Parsers)
                from .db_service import save_lead
                lead_pattern = r'\[ACTION: LEAD_CAPTURE \| (?P<json>.*?)\]'
                lead_match = re.search(lead_pattern, ai_reply)
                if lead_match:
                    try:
                        lead_data = json.loads(lead_match.group('json'))
                        logger.info(f"[Whatsapp] Capturing lead: {lead_data}")
                        await save_lead(business_id, lead_data)
                        ai_reply = ai_reply.replace(lead_match.group(0), "").strip()
                    except Exception as e:
                        logger.error(f"Error parsing lead capture in WhatsApp: {e}")

                # 4.1 Parse ANALYSIS tag
                analysis_match = re.search(r'\[ANALYSIS:\s*(?P<intent>.*?)\s*\|\s*(?P<sentiment>.*?)\s*\]', ai_reply, re.IGNORECASE)
                final_intent = detected_intent
                final_sentiment = detected_sentiment
                if analysis_match:
                    ai_intent = analysis_match.group('intent').strip().lower()
                    if ai_intent in ["booking", "enquiry", "pricing", "support", "greeting", "features", "integration", "complaint", "feedback", "human"]:
                        final_intent = ai_intent
                        final_sentiment = analysis_match.group('sentiment').strip()
                    
                    # Remove internal [ANALYSIS: ...] tag
                    ai_reply = ai_reply.replace(analysis_match.group(0), "").strip()

                # Final cleanup
                ai_reply = re.sub(r'\[ACTION:.*?\]', '', ai_reply).strip()
                ai_reply = re.sub(r'\[ANALYSIS:.*?\]', '', ai_reply).strip()

                # 5. Store & Send AI response
                await store_message(business_id, from_number, ai_reply, "agent", platform="whatsapp", intent=final_intent, sentiment=final_sentiment)
                await send_whatsapp_message(from_number, ai_reply, business_id=business_id)

        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error"}

async def send_whatsapp_message(to_number: str, text: str, business_id: str = None):
    # Determine credentials
    api_token = DEFAULT_API_TOKEN
    phone_id = DEFAULT_PHONE_ID
    
    if business_id:
        config = await get_whatsapp_config(business_id)
        if config and config.get("is_active"):
            api_token = config.get("access_token")
            phone_id = config.get("phone_number_id")
            logger.info(f"Using business-specific WhatsApp credentials for {business_id}")
    
    if not api_token or not phone_id:
        logger.error(f"WhatsApp credentials missing for business {business_id or 'System'}")
        return

    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": text}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error(f"WhatsApp Send Failed: {response.text}")
