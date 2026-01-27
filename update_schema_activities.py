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
    print("Updating schema for Lead Activities...")
    async with engine.begin() as conn:
        commands = [
            """
            CREATE TABLE IF NOT EXISTS lead_activities (
                id SERIAL PRIMARY KEY,
                lead_id INTEGER REFERENCES leads(id),
                business_id VARCHAR REFERENCES businesses(id),
                type VARCHAR,
                content JSON,
                created_by VARCHAR,
                created_at TIMESTAMP DEFAULT (now() at time zone 'utc')
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_lead_activities_lead_id ON lead_activities (lead_id)",
            "CREATE INDEX IF NOT EXISTS ix_lead_activities_business_id ON lead_activities (business_id)"
        ]
        
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                await conn.execute(text(cmd))
            except Exception as e:
                print(f"Error: {e}")

    print("Lead Activities Schema update completed.")

if __name__ == "__main__":
    asyncio.run(update_schema())
