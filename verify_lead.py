
import asyncio
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution, ExecutionStep
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from sqlalchemy import select, desc

async def verify():
    bid = 'eb89cc6e-49fb-46b5-b5f6-11cced548172'
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.business_id == bid).order_by(desc(Lead.created_at)).limit(3)
        result = await session.execute(stmt)
        leads = result.scalars().all()
        
        print(f"Recent leads for {bid}:")
        for l in leads:
            print(f"  - ID: {l.id} | Name: {l.name} | Created: {l.created_at} | BID: {l.business_id}")

if __name__ == "__main__":
    asyncio.run(verify())
