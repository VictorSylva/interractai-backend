import asyncio
import json
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from sqlalchemy import select

async def dump_workflows():
    async with AsyncSessionLocal() as session:
        stmt = select(Workflow).where(Workflow.business_id == 'groupcopac@gmail.com')
        result = await session.execute(stmt)
        workflows = result.scalars().all()
        for wf in workflows:
            print(f"--- WORKFLOW: {wf.name} ---")
            print(f"ID: {wf.id}")
            print(f"Status: {'Active' if wf.is_active else 'Inactive'}")
            print(f"Trigger: {wf.trigger_type} (Config: {wf.trigger_config})")
            
            nodes = wf.definition.get('nodes', [])
            print(f"Logic Steps ({len(nodes)}):")
            for i, node in enumerate(nodes):
                ntype = node.get('type')
                nlabel = node.get('data', {}).get('label', ntype)
                nconfig = node.get('data', {}).get('config', {})
                print(f"  {i+1}. {nlabel} ({ntype})")
                if nconfig:
                    print(f"     Config: {nconfig}")
            print("\n")

if __name__ == "__main__":
    asyncio.run(dump_workflows())
