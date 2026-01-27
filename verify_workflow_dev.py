import asyncio
import os
from dotenv import load_dotenv

# Force load DEV env
if os.path.exists(".env.dev"):
    load_dotenv(".env.dev", override=True)

# Patch main.py loading logic if needed (already handled by load_dotenv override)
# But we need imports AFTER env is loaded to ensure services get right config?
# Actually services/db_session.py reads os.getenv("DATABASE_URL").
# Since we loaded it above, it should work.

from services.workflow_engine import workflow_engine
from services.db_service import store_message

async def test_workflow():
    print("--- Verifying Workflow in DEV ---")
    print(f"DB: {os.getenv('DATABASE_URL')}")
    
    business_id = os.getenv("PRIMARY_BUSINESS_ID", "default_dev_bid")
    
    # Trigger data payload
    trigger_data = {
        "message": "test trigger",
        "message_body": "test trigger",
        "intent": "greeting",
        "user_id": "dev_tester",
        "business_id": business_id
    }

    print(f"Triggering workflow for BID: {business_id}")
    try:
        # We might not have any workflows actually created in the DB if it is fresh?
        # But we are using the 'interact_db' which is shared with the container (persisited volume).
        # So it should have existing workflows if any were created.
        executions = await workflow_engine.trigger_workflow(business_id, "message_created", trigger_data)
        print(f"Executions triggered: {len(executions)}")
        print("SUCCESS: Workflow engine triggered without error.")
    except Exception as e:
        import sys
        print(f"FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_workflow())
