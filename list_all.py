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

async def dump_data():
    if not DATABASE_URL:
        print("No DATABASE_URL found.")
        return
        
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        print("--- USERS ---")
        res_users = await conn.execute(text("SELECT id, email, role, business_id FROM users"))
        for row in res_users.fetchall():
            print(row)
            
        print("\n--- BUSINESSES ---")
        res_biz = await conn.execute(text("SELECT id, name FROM businesses"))
        for row in res_biz.fetchall():
            print(row)
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(dump_data())
