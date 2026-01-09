
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

async def test_support_and_booking():
    business_id = "eb89cc6e-49fb-46b5-b5f6-11cced548172"
    
    async with AsyncSessionLocal() as session:
        # --- SUPPORT ESCALATION TEST ---
        wf_s = Workflow(business_id=business_id, name="Support Test", trigger_type="message_created", trigger_config={"intent": "complaint"}, is_active=True)
        session.add(wf_s)
        await session.flush()
        
        n_s1, n_s2, n_s3 = [str(uuid.uuid4()) for _ in range(3)]
        node_s1 = WorkflowNode(id=n_s1, workflow_id=wf_s.id, type="start", label="Start")
        node_s2 = WorkflowNode(id=n_s2, workflow_id=wf_s.id, type="action", label="Create Ticket", config={"action_type": "create_ticket", "subject": "High Priority Complaint", "priority": "high"})
        node_s3 = WorkflowNode(id=n_s3, workflow_id=wf_s.id, type="action", label="Send Apology", config={"action_type": "send_message", "template": "We are sorry for the issue. Ticket #{{ticket_id}} created."})
        session.add_all([node_s1, node_s2, node_s3])
        session.add(WorkflowEdge(workflow_id=wf_s.id, source_id=n_s1, target_id=n_s2))
        session.add(WorkflowEdge(workflow_id=wf_s.id, source_id=n_s2, target_id=n_s3))
        
        await session.commit()
        
        print("\n--- Testing Support Escalation ---")
        context_s = {"trigger": {"message_body": "My delivery is missing", "intent": "complaint", "user_id": "test_support_user"}, "business_id": business_id}
        out_s2 = await execute_node_logic(node_s2, context_s)
        print(f"Ticket Output: {out_s2}")
        context_s.update(out_s2)
        out_s3 = await execute_node_logic(node_s3, context_s)
        print(f"Message Output: {out_s3}")
        if "Ticket #" in out_s3.get("message_body", ""): print("SUCCESS: Ticket ID hydrated in message")
        
        # --- BOOKING & DELAY TEST ---
        wf_b = Workflow(business_id=business_id, name="Booking Test", trigger_type="message_created", trigger_config={"intent": "booking"}, is_active=True)
        session.add(wf_b)
        await session.flush()
        
        n_b1, n_b2, n_b3 = [str(uuid.uuid4()) for _ in range(3)]
        node_b1 = WorkflowNode(id=n_b1, workflow_id=wf_b.id, type="start", label="Start")
        node_b2 = WorkflowNode(id=n_b2, workflow_id=wf_b.id, type="time_delay", label="1hr Delay", config={"seconds": 3600})
        node_b3 = WorkflowNode(id=n_b3, workflow_id=wf_b.id, type="action", label="Reminder", config={"action_type": "send_message", "template": "Don't forget your appointment!"})
        session.add_all([node_b1, node_b2, node_b3])
        session.add(WorkflowEdge(workflow_id=wf_b.id, source_id=n_b1, target_id=n_b2))
        session.add(WorkflowEdge(workflow_id=wf_b.id, source_id=n_b2, target_id=n_b3))
        
        await session.commit()
        
        print("\n--- Testing Booking Delay ---")
        context_b = {"trigger": {"message_body": "I want to book for tomorrow"}, "business_id": business_id}
        out_b2 = await execute_node_logic(node_b2, context_b)
        print(f"Delay Output: {out_b2}")
        if out_b2.get("orchestration_signal") == "delay" and out_b2.get("seconds") == 3600:
            print("SUCCESS: Delay signal correctly generated")

        # Cleanup
        await session.delete(wf_s)
        await session.delete(wf_b)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(test_support_and_booking())
