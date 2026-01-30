import os
from dotenv import load_dotenv

def inspect_key():
    if os.path.exists(".env.dev"):
        load_dotenv(".env.dev")
    else:
        load_dotenv(".env")
        
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        print(f"Key: '{api_key}'")
        print(f"Length: {len(api_key)}")
        print(f"Starts with sk-or-v1-: {api_key.startswith('sk-or-v1-')}")
        print(f"Has trailing/leading whitespace: {api_key != api_key.strip()}")
        # Check for non-ascii characters
        non_ascii = [c for c in api_key if ord(c) > 127]
        if non_ascii:
            print(f"Non-ASCII characters found: {non_ascii}")
    else:
        print("Key not found!")

if __name__ == "__main__":
    inspect_key()
