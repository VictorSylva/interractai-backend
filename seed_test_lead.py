import asyncio
from database.session import AsyncSessionLocal
from sqlalchemy import select
from database.models.general import User
from services.db_service import save_lead

async def seed_lead():
    email = "groupcopac@gmail.com"
    async with AsyncSessionLocal() as session:
        # 1. Find the business ID
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User {email} not found!")
            return

        print(f"Found Business ID: {user.business_id}")
        
        # 2. Insert Lead
        lead_data = {
            "name": "Test Customer",
            "email": "customer@example.com", 
            "phone": "555-0199",
            "status": "new",
            "type": "lead",
            "contact": "customer@example.com"
        }
        
        lead_id = await save_lead(user.business_id, lead_data)
        if lead_id:
            print(f"Successfully created test lead with ID: {lead_id}")
        else:
            print("Failed to save lead.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(seed_lead())
