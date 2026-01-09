import asyncio
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow
from sqlalchemy import select

async def list_wfs():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Workflow))
        wfs = result.scalars().all()
        print(f"Total Workflows in DB: {len(wfs)}")
        for w in wfs:
            print(f"ID: {w.id} | BID: {w.business_id} | Name: {w.name}")

if __name__ == "__main__":
    asyncio.run(list_wfs())
