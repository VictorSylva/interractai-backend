
import asyncio
import json
import logging
from services.prompt_service import prompt_service
from services.ai_service import generate_response
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution, ExecutionStep
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reproduce():
    business_id = "eb89cc6e-49fb-46b5-b5f6-11cced548172" # UUID for groupcopac@gmail.com
    user_message = "yes i will love to proceed. Favor James, 0990123455, favorj@gmail.com"
    
    # 1. Build profile
    async with AsyncSessionLocal() as session:
        stmt = select(BusinessSettings).where(BusinessSettings.business_id == business_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        profile = {c.name: getattr(settings, c.name) for c in settings.__table__.columns} if settings else {}
    
    system_instruction = prompt_service.build_system_prompt(profile)
    
    print("\n--- SYSTEM PROMPT ---")
    # print(system_instruction)
    print("--- END SYSTEM PROMPT ---\n")
    
    # 2. Generate response
    ai_reply = await generate_response(
        user_message, 
        [], 
        "repro_user", 
        system_instruction=system_instruction,
        business_id=business_id
    )
    
    print(f"USER: {user_message}")
    print(f"AI RAW REPLY: {ai_reply}")
    
    if "[ACTION: LEAD_CAPTURE" in ai_reply:
        print("SUCCESS: Lead Capture tag detected.")
    else:
        print("FAILURE: Lead Capture tag NOT detected.")

if __name__ == "__main__":
    asyncio.run(reproduce())
