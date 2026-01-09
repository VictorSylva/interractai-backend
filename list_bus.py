import asyncio
from database.session import AsyncSessionLocal
from database.models.general import Business
from sqlalchemy import select

async def list_businesses():
    async with AsyncSessionLocal() as session:
        stmt = select(Business)
        result = await session.execute(stmt)
        businesses = result.scalars().all()
        for b in businesses:
            print(f"Business ID: '{b.id}' | Name: '{b.name}'")

if __name__ == "__main__":
    asyncio.run(list_businesses())
