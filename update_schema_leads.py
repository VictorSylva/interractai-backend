import asyncio
import os
from dotenv import load_dotenv

# Load Environment Variables
if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
    print("Loaded .env.dev")
else:
    load_dotenv()

from database.session import engine
from sqlalchemy import text

async def update_schema():
    print("Updating schema for Leads CRM...")
    async with engine.begin() as conn:
        commands = [
            # Email & Phone
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email VARCHAR",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone VARCHAR",
            
            # Metadata
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS custom_fields JSON DEFAULT '{}'",
            
            # Tracking
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS conversation_id VARCHAR",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_interaction_at TIMESTAMP",
            
            # Value/Budget
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS value INTEGER"
        ]
        
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                await conn.execute(text(cmd))
            except Exception as e:
                print(f"Error (may be ignored if exists): {e}")

    print("Leads Schema update completed.")

if __name__ == "__main__":
    asyncio.run(update_schema())
