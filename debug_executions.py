
import asyncio
import json
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowExecution, ExecutionStep, WorkflowEdge
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from sqlalchemy import select

async def debug_latest_executions(email='groupcopac@gmail.com'):
    async with AsyncSessionLocal() as session:
        # Resolve BID
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        if not user:
            print(f"User {email} not found")
            return
        bid = user.business_id
        print(f"Business UUID: {bid}")

        # Get latest 5 executions
        res = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.business_id == bid)
            .order_by(WorkflowExecution.started_at.desc())
            .limit(5)
        )
        executions = res.scalars().all()
        
        if not executions:
            print("No executions found.")
            return

        for ex in executions:
            print(f"\n{'='*80}")
            print(f"EXECUTION: {ex.id}")
            print(f"Status: {ex.status}")
            print(f"Started: {ex.started_at}")
            print(f"Trigger Message: {ex.trigger_event.get('message')}")
            # print(f"Full Context: {json.dumps(ex.context_data, indent=2, default=str)}")
            
            res_steps = await session.execute(
                select(ExecutionStep)
                .where(ExecutionStep.execution_id == ex.id)
                .order_by(ExecutionStep.started_at.asc())
            )
            steps = res_steps.scalars().all()
            print("--- STEPS ---")
            for i, s in enumerate(steps):
                print(f"[{i}] Node: {s.node_id} | Status: {s.status}")
                print(f"    Input Keys: {list(s.input_data.keys())}")
                print(f"    Output: {json.dumps(s.output_data, default=str)}")
                if s.error:
                    print(f"    ERROR: {s.error}")
            print(f"{'='*80}\n")

if __name__ == '__main__':
    asyncio.run(debug_latest_executions())
