import os
import httpx
import logging
from services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

# Provider Configuration: OpenRouter Only (DeepSeek)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat"
    
if not OPENROUTER_API_KEY:
    logger.error("OPENROUTER_API_KEY is not set. AI Service will fail.")
    API_KEY = None
else:
    API_KEY = OPENROUTER_API_KEY
    logger.info("Using Provider: OpenRouter (DeepSeek)")

HEADERS_EXTRA = {
    "HTTP-Referer": "https://interact.com", 
    "X-Title": "Interact AI Platform",
}

from services.db_service import log_prompt_execution

async def generate_response(user_message: str, conversation_history: list = None, user_id: str = "unknown", system_instruction: str = None, business_id: str = None):
    """
    Generates a response from DeepSeek via OpenRouter.
    """
    if not API_KEY:
        return "Error: AI Service not configured. Missing OPENROUTER_API_KEY."
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        **HEADERS_EXTRA
    }

    messages = prompt_service.construct_messages(user_message, conversation_history, system_instruction)
    
    # Safety Check
    if not prompt_service.check_safety(user_message):
        return "I cannot answer that question as it violates our safety guidelines."

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                ai_content = data['choices'][0]['message']['content']
                
                # Log execution
                if business_id:
                     await log_prompt_execution(business_id, user_id, messages, ai_content, meta={"model": MODEL_NAME})
                
                return ai_content
            else:
                logger.error(f"Unexpected response format: {data}")
                return "I'm having trouble processing that right now."
                
    except Exception as e:
        logger.error(f"Error calling AI Provider: {e}")
        # Fallback to Mock AI for Demo Mode if API fails
        return f"I'm in Demo Mode! Error: {e}"
