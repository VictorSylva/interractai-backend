import asyncio
from database.session import AsyncSessionLocal
from database.models.crm import Lead
from sqlalchemy import select

async def check_leads():
    # UUID from logs: 9c2c60f2-32bf-4855-ad66-8a38c75ce938
    uuid = "9c2c60f2-32bf-4855-ad66-8a38c75ce938"
    email = "groupcopac@gmail.com"
    
    async with AsyncSessionLocal() as session:
        print(f"--- Checking Leads for UUID: {uuid} ---")
        stmt = select(Lead).where(Lead.business_id == uuid)
        res = await session.execute(stmt)
        leads = res.scalars().all()
        print(f"Count for UUID: {len(leads)}")
        for l in leads:
            print(f"  ID: {l.id} | Name: {l.name} | Contact: {l.contact}")
            
        print(f"\n--- Checking Leads for Email: {email} ---")
        stmt = select(Lead).where(Lead.business_id == email)
        res = await session.execute(stmt)
        leads_email = res.scalars().all()
        print(f"Count for Email: {len(leads_email)}")
        for l in leads_email:
            print(f"  ID: {l.id} | Name: {l.name} | Contact: {l.contact}")

if __name__ == "__main__":
    asyncio.run(check_leads())
