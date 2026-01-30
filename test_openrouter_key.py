import os
import httpx
import asyncio
from dotenv import load_dotenv

async def test_key():
    load_dotenv(".env.dev")
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    print(f"Testing Key: {api_key[:10]}...{api_key[-5:]}")
    print(f"Model: {model}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://interact.com",
        "X-Title": "Interact AI Platform",
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_key())
