import asyncio
import json
import logging
import uuid
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowExecution, ExecutionStep, WorkflowEdge
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from services.workflow_engine import workflow_engine, execute_node_logic, get_next_nodes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_lead_qualification():
    business_id = "eb89cc6e-49fb-46b5-b5f6-11cced548172"
    
    async with AsyncSessionLocal() as session:
        # 1. Create a Test Workflow
        wf = Workflow(
            business_id=business_id,
            name="Lead Qual Test",
            trigger_type="message_created",
            trigger_config={"intent": "pricing"},
            is_active=True
        )
        session.add(wf)
        await session.flush()

        # Nodes
        n1_id, n2_id, n3_id, n4_id, n5_id = [str(uuid.uuid4()) for _ in range(5)]
        
        start = WorkflowNode(id=n1_id, workflow_id=wf.id, type="start", label="Start")
        extract = WorkflowNode(id=n2_id, workflow_id=wf.id, type="ai_extract", label="Extract", config={
            "fields": [
                {"name": "budget", "type": "number"},
                {"name": "company", "type": "string"}
            ]
        })
        cond = WorkflowNode(id=n3_id, workflow_id=wf.id, type="condition", label="Check Budget", config={
            "variable": "budget",
            "operator": "greater_than",
            "value": "5000"
        })
        capture = WorkflowNode(id=n4_id, workflow_id=wf.id, type="lead_capture", label="VIP Capture", config={
            "name": "{{company}} VIP",
            "status": "vip",
            "notes": "Qualified with budget {{budget}}"
        })
        agent = WorkflowNode(id=n5_id, workflow_id=wf.id, type="action", label="Standard Reply", config={
            "action_type": "send_message",
            "template": "Thanks for your interest! We have plans for your company {{company}}."
        })

        session.add_all([start, extract, cond, capture, agent])

        # Edges
        e1 = WorkflowEdge(workflow_id=wf.id, source_id=n1_id, target_id=n2_id)
        e2 = WorkflowEdge(workflow_id=wf.id, source_id=n2_id, target_id=n3_id)
        e3 = WorkflowEdge(workflow_id=wf.id, source_id=n3_id, target_id=n4_id, condition_value="true")
        e4 = WorkflowEdge(workflow_id=wf.id, source_id=n3_id, target_id=n5_id, condition_value="false")
        session.add_all([e1, e2, e3, e4])
        
        await session.commit()

        # 2. Simulate Trigger
        trigger_data = {
            "message_body": "I am from Google and our budget is $10,000",
            "user_id": "test_user_qual",
            "intent": "pricing"
        }
        
        print("\n--- Testing High Budget Case ---")
        context = {"trigger": trigger_data, "business_id": business_id}
        
        # Manually run nodes to verify logic
        # Start -> Extract
        print("Executing AI Extract...")
        out_extract = await execute_node_logic(extract, context)
        print(f"Extract Output: {out_extract}")
        context.update(out_extract)

        # Extract -> Condition
        print("Executing Condition Check...")
        out_cond = await execute_node_logic(cond, context)
        print(f"Condition Output: {out_cond}")
        context.update(out_cond)

        # Check path
        next_nodes = await get_next_nodes(session, cond, out_cond)
        print(f"Next Nodes: {[n.label for n in next_nodes]}")
        
        if next_nodes and next_nodes[0].id == n4_id:
            print("SUCCESS: Routed to VIP Capture")
            # Execute Capture
            out_capture = await execute_node_logic(capture, context)
            print(f"Capture Output: {out_capture}")
        else:
            print("FAILURE: Did not route to VIP Capture")

        # Clean up
        await session.delete(wf)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(test_lead_qualification())
