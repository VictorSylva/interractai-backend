import asyncio
import os
import httpx
from dotenv import load_dotenv

# Test against deepseek-chat specifically
load_dotenv(".env.dev")

async def test():
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = "deepseek/deepseek-chat"
    print(f"Testing Key: {api_key[:15]}...")
    print(f"Testing Model: {model}")
    
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
        "max_tokens": 10
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
