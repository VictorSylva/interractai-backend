import asyncio
from database.session import AsyncSessionLocal
from database.models.general import Business
# Import other models to ensure Registry is populated for relationships
from database.models import chat, workflow, crm 
from sqlalchemy import select

async def fix():
    async with AsyncSessionLocal() as session:
        bid = "groupcopac@gmail.com"
        print(f"Checking for business: {bid}")
        
        stmt = select(Business).where(Business.id == bid)
        result = await session.execute(stmt)
        b = result.scalar_one_or_none()
        
        if not b:
            print(f"Business not found. Creating {bid}...")
            new_b = Business(id=bid, name="GroupCopac Auto-Created")
            session.add(new_b)
            await session.commit()
            print("Success! Business created.")
        else:
            print("Business already exists.")

if __name__ == "__main__":
    asyncio.run(fix())
