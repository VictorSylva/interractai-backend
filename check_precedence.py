import os
from dotenv import load_dotenv

def check_precedence():
    key_name = "OPENROUTER_API_KEY"
    system_val = os.getenv(key_name)
    print(f"System value: {system_val[:10]}..." if system_val else "System value: None")
    
    if os.path.exists(".env.dev"):
        print("Loading .env.dev...")
        load_dotenv(".env.dev", override=False)
        after_load = os.getenv(key_name)
        print(f"Value after load_dotenv(override=False): {after_load[:10]}..." if after_load else "Value: None")
        
        load_dotenv(".env.dev", override=True)
        after_override = os.getenv(key_name)
        print(f"Value after load_dotenv(override=True): {after_override[:10]}..." if after_override else "Value: None")
        
        if system_val and system_val != after_override:
            print("WARNING: System environment variable is DIFFERENT from .env.dev value!")
            print(f"System: {system_val[:15]}...")
            print(f".env.dev: {after_override[:15]}...")
    else:
        print(".env.dev not found")

if __name__ == "__main__":
    check_precedence()
