import asyncio
from database.session import AsyncSessionLocal
from database.models.crm import Lead
from database.models.general import User, Business
from sqlalchemy import select

async def debug_leads():
    async with AsyncSessionLocal() as session:
        # 1. Check User/Business mapping
        print("--- User Mapping ---")
        stmt = select(User).where(User.email == 'groupcopac@gmail.com')
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            print(f"User: {user.email} | Business ID: {user.business_id}")
            
            # Check Business name
            stmt = select(Business).where(Business.id == user.business_id)
            res = await session.execute(stmt)
            bid = res.scalar_one_or_none()
            if bid:
                print(f"Business Record: {bid.name} ({bid.id})")
        else:
            print("User groupcopac@gmail.com not found")

        # 2. Check all leads and their business IDs
        print("\n--- Recent Leads ---")
        stmt = select(Lead).order_by(Lead.created_at.desc()).limit(10)
        res = await session.execute(stmt)
        leads = res.scalars().all()
        for l in leads:
            print(f"Lead: {l.id} | Name: {l.name} | BID: {l.business_id} | Created: {l.created_at}")

        # 3. Check for specific BID 9c2c60f2-32bf-4855-ad66-8a38c75ce938 from logs
        print("\n--- Leads for 9c2c60f2-32bf-4855-ad66-8a38c75ce938 ---")
        stmt = select(Lead).where(Lead.business_id == '9c2c60f2-32bf-4855-ad66-8a38c75ce938')
        res = await session.execute(stmt)
        leads_9c = res.scalars().all()
        for l in leads_9c:
            print(f"Lead: {l.id} | Name: {l.name}")

if __name__ == "__main__":
    asyncio.run(debug_leads())
