import asyncio
from datetime import time
from database.session import AsyncSessionLocal
from database.models.scheduling import AppointmentType, AvailabilityRule
from services.db_service import resolve_business_id

async def seed_scheduling(business_id: str = "demo"):
    bid = await resolve_business_id(business_id)
    async with AsyncSessionLocal() as session:
        # 1. Clear Existing
        from sqlalchemy import delete
        await session.execute(delete(AppointmentType).where(AppointmentType.business_id == bid))
        await session.execute(delete(AvailabilityRule).where(AvailabilityRule.business_id == bid))
        
        # 2. Add Appointment Types
        types = [
            AppointmentType(business_id=bid, name="Consultation", duration_minutes=30),
            AppointmentType(business_id=bid, name="Demo", duration_minutes=45),
            AppointmentType(business_id=bid, name="Site Visit", duration_minutes=60, color_code="#10b981")
        ]
        session.add_all(types)
        
        # 3. Add Availability (Mon-Fri, 9-5)
        for i in range(5):
            rule = AvailabilityRule(
                business_id=bid,
                day_of_week=i,
                start_time=time(9, 0),
                end_time=time(17, 0)
            )
            session.add(rule)
            
        await session.commit()
        print(f"Seeded scheduling data for business: {bid}")

if __name__ == "__main__":
    asyncio.run(seed_scheduling())
