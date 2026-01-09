
import asyncio
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowExecution, ExecutionStep, WorkflowEdge
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from sqlalchemy import select

async def migrate():
    async with AsyncSessionLocal() as session:
        # 1. Fetch all users for mapping email -> business_id
        res = await session.execute(select(User))
        users = res.scalars().all()
        email_to_id = {u.email: u.business_id for u in users}
        print(f'Mappings: {email_to_id}')
        
        # 2. Update Workflows
        stmt = select(Workflow)
        res = await session.execute(stmt)
        workflows = res.scalars().all()
        
        count = 0
        for wf in workflows:
            if '@' in str(wf.business_id) and wf.business_id in email_to_id:
                new_id = email_to_id[wf.business_id]
                print(f'Migrating Workflow {wf.id}: {wf.business_id} -> {new_id}')
                wf.business_id = new_id
                count += 1
        
        # 3. Update Executions
        stmt = select(WorkflowExecution)
        res = await session.execute(stmt)
        executions = res.scalars().all()
        
        for ex in executions:
            if '@' in str(ex.business_id) and ex.business_id in email_to_id:
                new_id = email_to_id[ex.business_id]
                print(f'Migrating Execution {ex.id}: {ex.business_id} -> {new_id}')
                ex.business_id = new_id
                count += 1
                
        await session.commit()
        print(f'Successfully migrated {count} records.')

if __name__ == '__main__':
    asyncio.run(migrate())
