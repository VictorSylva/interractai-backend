import os
import asyncio
import httpx

KEYS = {
    ".env": "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",
    ".env.dev": "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"
}

API_URL = "https://openrouter.ai/api/v1/chat/completions"

async def test_key(name, key):
    print(f"Testing key from {name}...")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://test.com", 
    }
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=headers, json=payload, timeout=10.0)
            if response.status_code == 200:
                print(f"PASS: Key from {name} is VALID.")
                return key
            else:
                print(f"FAIL: Key from {name} failed: {response.status_code}")
                return None
    except Exception as e:
        print(f"FAIL: Error testing {name}: {e}")
        return None

async def main():
    print("Starting Key Verification...")
    valid_key = None
    
    for name, key in KEYS.items():
        result = await test_key(name, key)
        if result:
            valid_key = result
            
    if valid_key:
        print(f"Found Valid Key: {valid_key[:10]}...")
    else:
        print("All keys failed.")

if __name__ == "__main__":
    asyncio.run(main())
