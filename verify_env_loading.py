import os
from dotenv import load_dotenv

# Simulate the logic I added to main.py
def check_env_loading(simulated_env_var):
    print(f"--- Simulating ENV={simulated_env_var} ---")
    env_file = f".env.{simulated_env_var}"
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True) # Override for test purposes
        print(f"Success: Found {env_file}")
        print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
        print(f"PRIMARY_BUSINESS_ID: {os.getenv('PRIMARY_BUSINESS_ID')}")
    else:
        print(f"Fallback: {env_file} not found")

if __name__ == "__main__":
    # Test DEV
    check_env_loading("dev")

    # Test STAGING
    check_env_loading("staging")
    
    # Test PROD (Default/Missing file)
    check_env_loading("production")
