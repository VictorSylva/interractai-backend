import asyncio
import os
from dotenv import load_dotenv

if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
else:
    load_dotenv()

from database.session import AsyncSessionLocal
from services.db_service import save_lead, send_lead_message, get_lead_activities
from database.models.crm import Lead
from database.models.chat import Message
from database.models.general import Business
from database.models.workflow import Workflow
from sqlalchemy import select
import uuid

async def test_message_reliability():
    business_id = str(uuid.uuid4())
    
    # 0. Create Business
    async with AsyncSessionLocal() as session:
        business = Business(id=business_id, name="Test Corp", status="active")
        session.add(business)
        await session.commit()
        print("[OK] Created Business")

    # 1. Create Lead with phone
    lead_data = {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "+1234567890",
        "status": "new"
    }
    
    lead_id = await save_lead(business_id, lead_data)
    print(f"[OK] Created Lead ID: {lead_id}")
    
    # 2. Send Message (will fail since no real WhatsApp config, but should persist)
    result = await send_lead_message(
        business_id, 
        lead_id, 
        "Hello! This is a test message from CRM.",
        user_id="agent_test"
    )
    
    print(f"\n[OK] Message Send Result:")
    print(f"  Success: {result['success']}")
    print(f"  Message ID: {result.get('message_id')}")
    print(f"  Status: {result.get('status')}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    
    # 3. Verify Message Persistence
    async with AsyncSessionLocal() as session:
        stmt = select(Message).where(Message.business_id == business_id)
        result_db = await session.execute(stmt)
        messages = result_db.scalars().all()
        
        print(f"\n[OK] Messages in DB: {len(messages)}")
        for msg in messages:
            print(f"  - [{msg.status}] {msg.text[:50]}... (sender: {msg.sender})")
    
    # 4. Verify Activity Log
    activities = await get_lead_activities(business_id, lead_id)
    print(f"\n[OK] Activity Log ({len(activities)} entries):")
    for activity in activities:
        print(f"  - [{activity['type']}] {activity['content']}")
    
    # 5. Assertions
    assert len(messages) == 1, "Message not persisted!"
    assert messages[0].status in ["sent", "failed", "pending"], f"Invalid status: {messages[0].status}"
    assert len(activities) >= 1, "Activity not logged!"
    
    print("\n[SUCCESS] CRM Messaging Reliability Test PASSED")
    print(f"  - Message persisted: YES")
    print(f"  - Status tracked: {messages[0].status}")
    print(f"  - Activity logged: YES")

if __name__ == "__main__":
    asyncio.run(test_message_reliability())
