import asyncio
from database.session import AsyncSessionLocal
from database.models.workflow import Workflow
# Ensure ALL models are loaded for relationship resolution
from database.models import general, chat, workflow, crm
from services.workflow_engine import WorkflowEngine

async def test_trigger():
    async with AsyncSessionLocal() as session:
        # Get the first workflow
        from sqlalchemy import select
        result = await session.execute(select(Workflow))
        w = result.scalars().first()
        
        if not w:
            print("No workflow found!")
            return

        print(f"Triggering Workflow: {w.name} ({w.id})")
        
        # WorkflowEngine does not take session in __init__
        engine = WorkflowEngine() 
        # Mock trigger data
        trigger_data = {"message": "test trigger", "source": "manual_debug"}
        
        try:
            # Use specific trigger method
            exec_id = await engine.trigger_specific_workflow(w.business_id, w.id, trigger_data)
            print(f"Success! Execution ID: {exec_id}")
        except Exception as e:
            print(f"Error triggering workflow: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_trigger())
