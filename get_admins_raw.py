import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

async def dump_users():
    if not DATABASE_URL:
        print("No DATABASE_URL found.")
        return
        
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, email, role, business_id FROM users"))
        rows = result.fetchall()
        print(f"Total Users Found: {len(rows)}")
        for row in rows:
            print(f"UID: {row[0]} | Email: {row[1]} | Role: {row[2]} | BID: {row[3]}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(dump_users())
