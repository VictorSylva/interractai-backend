
import asyncio
import json
import logging
import re
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

async def verify_intelligent_flow():
    business_id = "eb89cc6e-49fb-46b5-b5f6-11cced548172"
    
    # Test Case 1: Complaint + Lead
    message_1 = "favor 0813445646. the finishing was not up to your standard"
    
    # Test Case 2: Enquiry
    message_2 = "also, i want to enquire about your construction"
    
    async with AsyncSessionLocal() as session:
        stmt = select(BusinessSettings).where(BusinessSettings.business_id == business_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        profile = {c.name: getattr(settings, c.name) for c in settings.__table__.columns} if settings else {}
    
    system_instruction = prompt_service.build_system_prompt(profile)

    print("\n--- TEST 1: Complaint + Lead ---")
    ai_reply_1 = await generate_response(message_1, [], system_instruction=system_instruction, business_id=business_id)
    print(f"USER: {message_1}")
    print(f"AI RAW REPLY: {ai_reply_1}")
    
    if "[ACTION: LEAD_CAPTURE" in ai_reply_1:
        print("SUCCESS: Lead Capture tag detected in complaint!")
    else:
        print("FAILURE: Lead Capture tag NOT detected in complaint.")

    print("\n--- TEST 2: Enquiry ---")
    ai_reply_2 = await generate_response(message_2, [], system_instruction=system_instruction, business_id=business_id)
    print(f"USER: {message_2}")
    print(f"AI RAW REPLY: {ai_reply_2}")
    
    analysis_match = re.search(r'\[ANALYSIS:\s*(?P<intent>.*?)\s*\|', ai_reply_2, re.IGNORECASE)
    if analysis_match:
        detected = analysis_match.group('intent').strip().lower()
        print(f"DETECTED INTENT: {detected}")
        if detected == "enquiry":
            print("SUCCESS: Enquiry intent detected correctly!")
        else:
            print(f"FAILURE: Expected enquiry, got {detected}")
    else:
        print("FAILURE: ANALYSIS tag missing in enquiry reply.")

if __name__ == "__main__":
    asyncio.run(verify_intelligent_flow())
