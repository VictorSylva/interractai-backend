import asyncio
import os
import httpx
from dotenv import load_dotenv

async def test_key(api_key, model):
    print("-" * 50)
    print(f"Testing Key: {api_key[:15]}...")
    
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
        "temperature": 0.7,
        "max_tokens": 10
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False

async def main():
    model = "google/gemini-2.0-flash-exp:free"
    
    keys = [
        "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",
        "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",
        "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"
    ]
    
    for key in keys:
        if await test_key(key, model):
            print(f"\n✅ FOUND WORKING KEY: {key}")
            break
    else:
        print("\n❌ No working keys found in history.")

if __name__ == "__main__":
    asyncio.run(main())
