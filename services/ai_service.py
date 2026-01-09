import os
import httpx
import logging
from services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

# API Key fetched at runtime
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat" # or deepseek/deepseek-r1

from services.db_service import log_prompt_execution

async def generate_response(user_message: str, conversation_history: list = None, user_id: str = "unknown", system_instruction: str = None, business_id: str = None):
    """
    Generates a response from DeepSeek via OpenRouter.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    # ... check key ...
    if not api_key:
         # Lazy load
         from dotenv import load_dotenv
         load_dotenv()
         api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set.")
        return "Error: AI service not configured."
    
    print(f"DEBUG: Using API Key with length {len(api_key)}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://interact.com", 
        "X-Title": "Interact AI Platform",
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
            response = await client.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30.0)
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
        logger.error(f"Error calling OpenRouter: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to Mock AI for Demo Mode if API fails
        return f"I'm in Demo Mode! Error: {e}"
