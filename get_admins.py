import asyncio
import os
from dotenv import load_dotenv

# Load dev env
if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
    print("Loaded .env.dev")

from database.session import AsyncSessionLocal
from database.models.general import User
from sqlalchemy import select

async def get_users():
    import os
    print(f"DEBUG: DATABASE_URL={os.getenv('DATABASE_URL')}")
    async with AsyncSessionLocal() as session:
        print("DEBUG: Session opened")
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"UID: {u.id} | Email: {u.email} | Role: {u.role} | BID: {u.business_id}")

if __name__ == "__main__":
    asyncio.run(get_users())
