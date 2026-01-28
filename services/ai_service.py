import os
import httpx
import logging
from services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

# Provider Configuration: OpenRouter Only (DeepSeek)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
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
        logger.info(f"[AI] Calling {MODEL_NAME} for user {user_id}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=payload, timeout=20.0) # Increased timeout
            
            if response.status_code != 200:
                logger.error(f"AI Service Error ({response.status_code}): {response.text}")
                if response.status_code == 401:
                    return "AI Service Error: Unauthorized. Please check your OPENROUTER_API_KEY."
                if response.status_code == 402:
                    return "AI Service Error: Insufficient credits on OpenRouter."
                if response.status_code == 429:
                    return "AI Service is busy. Please try again in a few seconds."
                response.raise_for_status()

            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                ai_content = data['choices'][0]['message']['content']
                logger.info(f"[AI] Response received ({len(ai_content)} chars)")
                
                # Log execution (non-blocking)
                if business_id:
                    try:
                        await log_prompt_execution(business_id, user_id, messages, ai_content, meta={"model": MODEL_NAME})
                    except Exception as log_err:
                        logger.error(f"Error logging prompt execution: {log_err}")
                
                return ai_content
            else:
                logger.error(f"Unexpected response format: {data}")
                return "I'm having trouble processing that right now."
                
    except httpx.TimeoutException:
        logger.error(f"AI Service timeout after 20s")
        return "The AI service is taking too long to respond. DeepSeek might be overloaded. Please try again."
    except httpx.HTTPStatusError as e:
        logger.error(f"AI Service HTTP Error: {e}")
        return "I'm having trouble connecting to the AI provider. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error calling AI Provider: {type(e).__name__}: {e}")
        return f"I'm having trouble connecting to my AI service. Please try again in a moment."
