import os
import httpx
import logging
import json
from services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

# --- CONFIGURATION & ENV LOADING ---
# Provider Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
# OpenRouter strictly requires Referer and Title headers to prevent key invalidation.
OPENROUTER_REFERER = os.getenv("OPENROUTER_REFERER", "https://interact-ai.com")
OPENROUTER_TITLE = os.getenv("OPENROUTER_TITLE", "Interact AI Platform")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# Structured Logging Config
class AIServiceLogger:
    @staticmethod
    def log_request(provider, model, user_id):
        logger.info(f"[AI REQUEST] Provider: {provider} | Model: {model} | User: {user_id}")

    @staticmethod
    def log_response(provider, status_code, char_count):
        logger.info(f"[AI RESPONSE] Provider: {provider} | Status: {status_code} | Chars: {char_count}")

    @staticmethod
    def log_error(provider, category, message, status_code=None):
        error_msg = f"[AI ERROR] Provider: {provider} | Category: {category} | Msg: {message}"
        if status_code:
            error_msg += f" | Status: {status_code}"
        logger.error(error_msg)

# Determine primary provider at startup
if GEMINI_API_KEY:
    PRIMARY_PROVIDER = "gemini"
    logger.info(f"AI Service Initialized with Provider: Google Gemini ({GEMINI_MODEL})")
elif OPENROUTER_API_KEY:
    PRIMARY_PROVIDER = "openrouter"
    logger.info(f"AI Service Initialized with Provider: OpenRouter ({OPENROUTER_MODEL})")
else:
    PRIMARY_PROVIDER = None
    logger.warning("No AI provider (GEMINI_API_KEY or OPENROUTER_API_KEY) found in environment.")

from services.db_service import log_prompt_execution

async def generate_response(user_message: str, conversation_history: list = None, user_id: str = "unknown", system_instruction: str = None, business_id: str = None):
    """
    Main entry point for generating AI responses. 
    Routes to the configured provider and handles common errors.
    """
    if not PRIMARY_PROVIDER:
        return "AI Service Error: No provider configured. Please check your API keys."
    
    # Safety Check (Prompt Injection / Harmful Content)
    if not prompt_service.check_safety(user_message):
        AIServiceLogger.log_error(PRIMARY_PROVIDER, "safety_violation", f"Blocked message from user {user_id}")
        return "I cannot answer that question as it violates our safety guidelines."

    messages = prompt_service.construct_messages(user_message, conversation_history, system_instruction)

    try:
        AIServiceLogger.log_request(PRIMARY_PROVIDER, 
                                   GEMINI_MODEL if PRIMARY_PROVIDER == "gemini" else OPENROUTER_MODEL, 
                                   user_id)
        
        if PRIMARY_PROVIDER == "gemini":
            ai_content = await _call_gemini(messages)
        else:
            ai_content = await _call_openrouter(messages)
        
        # Log to DB (non-blocking)
        if business_id:
            try:
                model_used = GEMINI_MODEL if PRIMARY_PROVIDER == "gemini" else OPENROUTER_MODEL
                await log_prompt_execution(business_id, user_id, messages, ai_content, 
                                         meta={"model": model_used, "provider": PRIMARY_PROVIDER})
            except Exception as log_err:
                logger.error(f"Error logging prompt execution: {log_err}")
        
        return ai_content
                
    except httpx.TimeoutException:
        AIServiceLogger.log_error(PRIMARY_PROVIDER, "timeout", "Request timed out after 20s")
        return "The AI service is taking too long to respond. Please try again in a moment."
    
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_body = e.response.text
        
        # Determine Error Category
        if status_code == 401:
            category = "authentication"
            user_msg = "AI Service Error: Unauthorized. Please check your API key."
        elif status_code == 403:
            category = "validation"
            user_msg = "AI Service Error: The request was rejected by the provider. Ensure required headers are sent."
        elif status_code == 429:
            category = "rate_limit"
            user_msg = "The AI service is currently busy. Please wait a few seconds and try again."
        elif status_code >= 500:
            category = "provider_down"
            user_msg = "The AI provider is currently offline or overloaded. Please try again later."
        else:
            category = "unknown_http"
            user_msg = "I'm having trouble connecting to the AI provider right now."

        AIServiceLogger.log_error(PRIMARY_PROVIDER, category, f"HTTP {status_code}: {error_body}", status_code)
        return user_msg

    except Exception as e:
        AIServiceLogger.log_error(PRIMARY_PROVIDER, "unexpected", f"{type(e).__name__}: {e}")
        logger.exception("Full traceback for unexpected AI error:")
        return "I encountered an internal error while talking to my AI brain. Please try again."

async def _call_gemini(messages: list) -> str:
    """Internal helper to call Google Gemini API"""
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
            # Gemini uses 'model' role for AI responses
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
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=20.0)
        response.raise_for_status()
        
        data = response.json()
        if 'candidates' in data and data['candidates']:
            content = data['candidates'][0]['content']['parts'][0]['text']
            AIServiceLogger.log_response("gemini", response.status_code, len(content))
            return content
        
        raise ValueError(f"Empty or malformed Gemini response: {data}")

async def _call_openrouter(messages: list) -> str:
    """Internal helper to call OpenRouter API with mandatory headers"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # FAIL FAST if mandatory headers are missing or improperly configured
    # OpenRouter strictly requires these to prevent key invalidation.
    valid_referer = OPENROUTER_REFERER and str(OPENROUTER_REFERER).strip() not in ["", "None", "undefined", "https://interact-ai.com"] # Force real referer in prod
    # Actually, let's just ensure it's not empty or "undefined"
    clean_referer = str(OPENROUTER_REFERER).strip()
    clean_title = str(OPENROUTER_TITLE).strip()

    if not clean_referer or clean_referer in ["None", "undefined"]:
        AIServiceLogger.log_error("openrouter", "config_error", f"Invalid OPENROUTER_REFERER: '{OPENROUTER_REFERER}'")
        raise ValueError("OpenRouter requires a valid HTTP-Referer header. Check your environment variables.")

    if not clean_title or clean_title in ["None", "undefined"]:
        AIServiceLogger.log_error("openrouter", "config_error", f"Invalid OPENROUTER_TITLE: '{OPENROUTER_TITLE}'")
        raise ValueError("OpenRouter requires a valid X-Title header. Check your environment variables.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_REFERER,
        "X-Title": OPENROUTER_TITLE,
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=20.0)
        
        # Explicitly handle 401/403 before raise_for_status to avoid keys being disabled if possible
        if response.status_code in [401, 403]:
            AIServiceLogger.log_error("openrouter", "authentication", response.text, response.status_code)
            # We raise so generate_response can catch and categorize
            response.raise_for_status()

        response.raise_for_status()
        
        data = response.json()
        if 'choices' in data and data['choices']:
            content = data['choices'][0]['message']['content']
            AIServiceLogger.log_response("openrouter", response.status_code, len(content))
            return content
        
        raise ValueError(f"Empty or malformed OpenRouter response: {data}")
