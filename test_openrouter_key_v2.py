import os
import requests
from dotenv import load_dotenv

def test_key():
    # Try loading .env.dev first
    if os.path.exists(".env.dev"):
        print("Found .env.dev, loading...")
        load_dotenv(".env.dev")
    else:
        print(".env.dev not found, loading .env...")
        load_dotenv(".env")
        
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    if not api_key:
        print("Error: OPENROUTER_API_KEY is None")
        return

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
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_key()
