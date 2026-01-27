import asyncio
import os
from dotenv import load_dotenv

# Load Environment Variables BEFORE any other local imports to match main.py behavior
# Try to load .env.dev specifically for local execution
if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
    print("Loaded .env.dev")
else:
    load_dotenv()

from database.session import engine
from sqlalchemy import text

async def update_schema():
    print("Updating schema for Trial System...")
    async with engine.begin() as conn:
        # Check if columns exist before adding (basic check or just try/except)
        # SQLite doesn't support IF NOT EXISTS in ALTER TABLE nicely for columns sometimes, 
        # but PostgreSQL does. The user is using PostgreSQL (implied by 'PostgreSQL' in main.py message).
        # We will wrap in try/except blocks to be safe or check information_schema (complex).
        # Easiest is to try adding; if it fails, it likely exists.
        
        commands = [
            "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS plan_name VARCHAR DEFAULT 'starter'",
            "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS trial_start_at TIMESTAMP",
            "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS trial_end_at TIMESTAMP"
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
