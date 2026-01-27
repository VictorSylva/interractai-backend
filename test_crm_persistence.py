import asyncio
import os
from dotenv import load_dotenv

if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
else:
    load_dotenv()

from database.session import AsyncSessionLocal
from services.db_service import save_lead, update_lead, get_lead_activities, get_leads
from database.models.crm import Lead
from database.models.workflow import Workflow
from database.models.general import Business
from datetime import datetime
import uuid

async def test_crm_persistence():
    business_id = str(uuid.uuid4())
    
    # 0. Create Business
    async with AsyncSessionLocal() as session:
        business = Business(id=business_id, name="Test Corp", status="active")
        session.add(business)
        await session.commit()
        print("[OK] Created Business")

    # 1. Create Lead
    lead_data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+1234567890",
        "source": "workflow_automation",
        "notes": "Interested in enterprise plan",
        "status": "new",
        "tags": ["enterprise", "hot"],
        "value": 10000,
        "custom_fields": {"company": "Acme Corp", "employees": "50-100"}
    }
    
    lead_id = await save_lead(business_id, lead_data)
    print(f"[OK] Created Lead ID: {lead_id}")
    
    # 2. Update Lead Status
    result = await update_lead(business_id, lead_id, {"status": "contacted"}, user_id="agent_001")
    print(f"[OK] Updated Lead Status: {result}")
    
    # 3. Update Lead Value
    result = await update_lead(business_id, lead_id, {"value": 15000}, user_id="agent_001")
    print(f"[OK] Updated Lead Value: {result}")
    
    # 4. Fetch Activities
    activities = await get_lead_activities(business_id, lead_id)
    print(f"\n[OK] Activity Log ({len(activities)} entries):")
    for activity in activities:
        print(f"  - [{activity['type']}] {activity['content']} by {activity['created_by']}")
    
    # 5. Verify Persistence (Fetch Leads)
    leads = await get_leads(business_id)
    print(f"\n[OK] Fetched Leads: {len(leads)}")
    lead = leads[0]
    print(f"  Status: {lead['status']} (should be 'contacted')")
    print(f"  Value: {lead['value']} (should be 15000)")
    
    assert lead['status'] == 'contacted', "Status not persisted!"
    assert lead['value'] == 15000, "Value not persisted!"
    assert len(activities) == 2, "Activities not logged!"
    
    print("\n[SUCCESS] CRM Persistence Test PASSED")

if __name__ == "__main__":
    asyncio.run(test_crm_persistence())
