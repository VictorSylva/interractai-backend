from sqlalchemy import create_engine, select
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models.general import User

# Hardcode the DB URL for a quick check if needed, 
# but let's try to import from session if possible.
# Actually, let's just use the session directly.

from database.session import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        stmt = select(User.reset_token).where(User.email == "mbasitisylva@gmail.com")
        res = await session.execute(stmt)
        token = res.scalar()
        print(f"RESULT_TOKEN: {token}")

if __name__ == "__main__":
    asyncio.run(main())
