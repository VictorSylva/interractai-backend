import os
import httpx
import logging
from services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

# Multi-Provider Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# Determine which provider to use
if GEMINI_API_KEY:
    PROVIDER = "gemini"
    API_KEY = GEMINI_API_KEY
    MODEL_NAME = GEMINI_MODEL
    logger.info(f"Using Provider: Google Gemini ({MODEL_NAME})")
elif OPENROUTER_API_KEY:
    PROVIDER = "openrouter"
    API_KEY = OPENROUTER_API_KEY
    MODEL_NAME = OPENROUTER_MODEL
    logger.info(f"Using Provider: OpenRouter ({MODEL_NAME})")
else:
    PROVIDER = None
    API_KEY = None
    MODEL_NAME = None
    logger.error("No AI provider configured. Set either GEMINI_API_KEY or OPENROUTER_API_KEY.")

from services.db_service import log_prompt_execution

async def generate_response(user_message: str, conversation_history: list = None, user_id: str = "unknown", system_instruction: str = None, business_id: str = None):
    """
    Generates a response from the configured AI provider (Gemini or OpenRouter).
    """
    if not API_KEY:
        return "Error: AI Service not configured. Please set GEMINI_API_KEY or OPENROUTER_API_KEY."
    
    messages = prompt_service.construct_messages(user_message, conversation_history, system_instruction)
    
    # Safety Check
    if not prompt_service.check_safety(user_message):
        return "I cannot answer that question as it violates our safety guidelines."

    try:
        logger.info(f"[AI] Calling {PROVIDER.upper()} ({MODEL_NAME}) for user {user_id}...")
        
        if PROVIDER == "gemini":
            ai_content = await _call_gemini(messages)
        elif PROVIDER == "openrouter":
            ai_content = await _call_openrouter(messages)
        else:
            return "Error: No AI provider configured."
        
        logger.info(f"[AI] Response received ({len(ai_content)} chars)")
        
        # Log execution (non-blocking)
        if business_id:
            try:
                await log_prompt_execution(business_id, user_id, messages, ai_content, meta={"model": MODEL_NAME, "provider": PROVIDER})
            except Exception as log_err:
                logger.error(f"Error logging prompt execution: {log_err}")
        
        return ai_content
                
    except httpx.TimeoutException:
        logger.error(f"AI Service timeout after 20s")
        return "The AI service is taking too long to respond. Please try again."
    except httpx.HTTPStatusError as e:
        logger.error(f"AI Service HTTP Error: {e}")
        logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        return "I'm having trouble connecting to the AI provider. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error calling AI Provider: {type(e).__name__}: {e}")
        logger.exception("Full traceback:")
        return f"I'm having trouble connecting to my AI service. Please try again in a moment."


async def _call_gemini(messages: list) -> str:
    """Call Google Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    # Convert OpenAI-style messages to Gemini format
    gemini_contents = []
    system_instruction = None
    
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            gemini_contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            gemini_contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
    
    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000,
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    
    logger.info(f"[Gemini] Calling API with URL: {url[:80]}...")
    logger.info(f"[Gemini] Payload keys: {list(payload.keys())}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=20.0)
        
        if response.status_code != 200:
            logger.error(f"Gemini API Error ({response.status_code}): {response.text}")
            if response.status_code == 400:
                return "AI Service Error: Invalid request to Gemini."
            if response.status_code == 401 or response.status_code == 403:
                return "AI Service Error: Unauthorized. Please check your GEMINI_API_KEY."
            if response.status_code == 429:
                return "AI Service is busy. Please try again in a few seconds."
            response.raise_for_status()
        
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            logger.error(f"Unexpected Gemini response format: {data}")
            return "I'm having trouble processing that right now."


async def _call_openrouter(messages: list) -> str:
    """Call OpenRouter API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://interact.com",
        "X-Title": "Interact AI Platform",
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=20.0)
        
        if response.status_code != 200:
            logger.error(f"OpenRouter API Error ({response.status_code}): {response.text}")
            if response.status_code == 401:
                return "AI Service Error: Unauthorized. Please check your OPENROUTER_API_KEY."
            if response.status_code == 402:
                return "AI Service Error: Insufficient credits on OpenRouter."
            if response.status_code == 429:
                return "AI Service is busy. Please try again in a few seconds."
            response.raise_for_status()
        
        data = response.json()
        
        if 'choices' in data and len(data['choices']) > 0:
            return data['choices'][0]['message']['content']
        else:
            logger.error(f"Unexpected OpenRouter response format: {data}")
            return "I'm having trouble processing that right now."
