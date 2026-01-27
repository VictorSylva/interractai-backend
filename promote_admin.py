import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

async def promote_user(email):
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found.")
        return

    print(f"Promoting user {email} to super_admin...")
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # Using raw SQL for simplicity and speed
        result = await conn.execute(
            text("UPDATE users SET role = 'super_admin' WHERE email = :email"),
            {"email": email}
        )
        await conn.commit()
        
        if result.rowcount > 0:
            print(f"✅ User {email} is now a super_admin.")
        else:
            print(f"❌ User {email} not found.")
            
    await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py <email>")
    else:
        asyncio.run(promote_user(sys.argv[1]))
