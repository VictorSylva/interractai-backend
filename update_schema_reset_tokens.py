import asyncio
import os
from dotenv import load_dotenv

# Load Environment Variables BEFORE any other local imports
if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
    print("Loaded .env.dev")
else:
    load_dotenv()

from database.session import engine
from sqlalchemy import text

async def update_schema():
    print("Updating schema for Password Reset System...")
    async with engine.begin() as conn:
        commands = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP"
        ]
        
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                await conn.execute(text(cmd))
            except Exception as e:
                print(f"Error (ignoring if column exists): {e}")

    print("Schema update completed.")

if __name__ == "__main__":
    asyncio.run(update_schema())
