
import asyncio
import json
from datetime import datetime, timedelta
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow, WorkflowNode, WorkflowExecution, ExecutionStep, WorkflowEdge
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Conversation, Message
from database.models.crm import Lead, Ticket
from sqlalchemy import select

async def debug_all_recent():
    async with AsyncSessionLocal() as session:
        # Get executions in last 30 mins
        since = datetime.utcnow() - timedelta(minutes=30)
        res = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.started_at >= since)
            .order_by(WorkflowExecution.started_at.desc())
        )
        executions = res.scalars().all()
        
        print(f"Found {len(executions)} executions since {since}")

        for ex in executions:
            print(f"\n{'='*80}")
            print(f"EXECUTION: {ex.id} | BID: {ex.business_id}")
            print(f"Status: {ex.status}")
            print(f"Msg: {ex.trigger_event.get('message')}")
            
            res_steps = await session.execute(
                select(ExecutionStep)
                .where(ExecutionStep.execution_id == ex.id)
                .order_by(ExecutionStep.started_at.asc())
            )
            steps = res_steps.scalars().all()
            for i, s in enumerate(steps):
                print(f"  [{i}] Node: {s.node_id} | Status: {s.status} | Output: {json.dumps(s.output_data, default=str)} | Error: {s.error}")

if __name__ == '__main__':
    asyncio.run(debug_all_recent())
