import asyncio
import os
from dotenv import load_dotenv

if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
else:
    load_dotenv()

from database.session import engine
from sqlalchemy import text

async def update_schema():
    print("Adding status column to messages table...")
    async with engine.begin() as conn:
        commands = [
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'sent'"
        ]
        
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                await conn.execute(text(cmd))
            except Exception as e:
                print(f"Error: {e}")

    print("Message status column added.")

if __name__ == "__main__":
    asyncio.run(update_schema())
