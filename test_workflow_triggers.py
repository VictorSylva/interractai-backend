import asyncio
import os
from dotenv import load_dotenv

if os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
else:
    load_dotenv()

from database.session import AsyncSessionLocal
from services.db_service import save_lead, update_lead
from database.models.crm import Lead
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge
from database.models.general import Business
import uuid

async def test_workflow_triggers():
    business_id = str(uuid.uuid4())
    
    # 0. Create Business
    async with AsyncSessionLocal() as session:
        business = Business(id=business_id, name="Test Corp", status="active")
        session.add(business)
        await session.commit()
        print("[OK] Created Business")

    # 1. Create Test Workflow (Trigger: lead_event, Condition: status=qualified)
    async with AsyncSessionLocal() as session:
        workflow = Workflow(
            id=str(uuid.uuid4()),
            business_id=business_id,
            name="Qualified Lead Automation",
            trigger_type="lead_event",
            trigger_config={"status": "qualified"},
            is_active=True
        )
        session.add(workflow)
        
        # Start Node
        start_node = WorkflowNode(
            id="start_1",
            workflow_id=workflow.id,
            type="start",
            label="Start"
        )
        session.add(start_node)
        
        # Action Node (Send Message)
        action_node = WorkflowNode(
            id="action_1",
            workflow_id=workflow.id,
            type="action",
            label="Send Brochure",
            config={
                "action_type": "send_message",
                "template": "Congratulations! You qualify for our premium plan. Here's the brochure: [link]"
            }
        )
        session.add(action_node)
        
        # Edge
        edge = WorkflowEdge(
            workflow_id=workflow.id,
            source_id="start_1",
            target_id="action_1"
        )
        session.add(edge)
        
        await session.commit()
        print(f"[OK] Created Workflow: {workflow.id}")

    # 2. Create Lead
    lead_data = {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "phone": "+1234567890",
        "status": "new"
    }
    
    lead_id = await save_lead(business_id, lead_data)
    print(f"[OK] Created Lead ID: {lead_id}")
    
    # 3. Update Lead Status to 'contacted' (should NOT trigger)
    print("\n[TEST] Updating status to 'contacted' (should NOT trigger workflow)...")
    result = await update_lead(business_id, lead_id, {"status": "contacted"}, user_id="agent_test")
    print(f"[OK] Updated to contacted: {result}")
    
    # 4. Update Lead Status to 'qualified' (SHOULD trigger)
    print("\n[TEST] Updating status to 'qualified' (SHOULD trigger workflow)...")
    result = await update_lead(business_id, lead_id, {"status": "qualified"}, user_id="agent_test")
    print(f"[OK] Updated to qualified: {result}")
    
    # Give workflow engine time to process (async task)
    await asyncio.sleep(2)
    
    # 5. Check Workflow Executions
    from database.models.workflow import WorkflowExecution
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        stmt = select(WorkflowExecution).where(WorkflowExecution.business_id == business_id)
        result_db = await session.execute(stmt)
        executions = result_db.scalars().all()
        
        print(f"\n[OK] Workflow Executions: {len(executions)}")
        for exe in executions:
            print(f"  - Execution {exe.id}: Status={exe.status}, Trigger={exe.trigger_event}")
    
    # 6. Assertions
    assert len(executions) == 1, f"Expected 1 execution, got {len(executions)}"
    assert executions[0].trigger_event.get("new_status") == "qualified", "Trigger event mismatch"
    
    print("\n[SUCCESS] CRM Workflow Trigger Test PASSED")
    print("  - Status change triggered automation: YES")
    print("  - Conditional matching worked: YES")
    print("  - No duplicate firing: YES")

if __name__ == "__main__":
    print("\n[NOTE] This test verifies workflow TRIGGERING, not execution completion.")
    print("[NOTE] Celery workers must be running for full workflow execution.")
    asyncio.run(test_workflow_triggers())
