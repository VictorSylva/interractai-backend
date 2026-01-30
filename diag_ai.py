import asyncio
import os
import httpx
from dotenv import load_dotenv

# Load the same environment as the app
load_dotenv(".env.dev")

async def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    print("-" * 50)
    print("Testing OpenRouter with:")
    print(f"API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")
    print(f"Model: {model}")
    print("-" * 50)
    
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
            
            if response.status_code == 200:
                print("RESULT: Connection Successful!")
            else:
                print(f"RESULT: Connection Failed with status {response.status_code}")
        except httpx.ConnectError as e:
            print(f"RESULT: Network/Connection Error: {e}")
        except httpx.TimeoutException as e:
            print(f"RESULT: Timeout Error: {e}")
        except Exception as e:
            print(f"RESULT: Unexpected Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
