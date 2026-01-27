import asyncio
import os
import sys
import uuid

# Add the current directory to sys.path
sys.path.append(os.getcwd())

# Import all models in correct order to ensure relationships are resolved
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc, BusinessWhatsAppConfig
from database.models.chat import Conversation, Message
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution
from database.models.crm import Lead, LeadActivity
from database.models.scheduling import AppointmentType, AvailabilityRule, Appointment

from database.session import AsyncSessionLocal

async def reproduce_collision():
    print("--- Reproducing Conversation ID Collision ---")
    async with AsyncSessionLocal() as session:
        try:
            # 1. Create two businesses
            bid1 = "bus_1_" + str(uuid.uuid4())[:8]
            bid2 = "bus_2_" + str(uuid.uuid4())[:8]
            
            session.add(Business(id=bid1, name="Business 1"))
            session.add(Business(id=bid2, name="Business 2"))
            await session.commit()
            print(f"Created Businesses: {bid1}, {bid2}")
            
            # 2. Create a conversation for Business 1
            shared_user_id = "shared_visitor_" + str(uuid.uuid4())[:8]
            convo1 = Conversation(id=shared_user_id, business_id=bid1, customer_name="Visitor")
            session.add(convo1)
            await session.commit()
            print(f"Created Conversation for {bid1} with user_id {shared_user_id}")
            
            # 3. Try to create conversation for Business 2 with SAME user_id
            print(f"Attempting to create Conversation for {bid2} with SAME user_id {shared_user_id}...")
            convo2 = Conversation(id=shared_user_id, business_id=bid2, customer_name="Visitor")
            session.add(convo2)
            await session.commit()
            print("SUCCESS: Somehow it worked? (This is unexpected if id is the only PK)")
            
        except Exception as e:
            print(f"FAILED as expected due to collision: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(reproduce_collision())
