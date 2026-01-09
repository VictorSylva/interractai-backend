import asyncio
import httpx
import time
import json
import sys

BASE_URL = "http://localhost:8000"
BUSINESS_ID = "verify_biz_01"

async def run_verification():
    print(f"--- Starting Verification for Business: {BUSINESS_ID} ---")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 0. Register Business (Ensure it exists for Foreign Key)
        print("\n0. Registering Verification Business...")
        reg_payload = {
            "email": "verify_admin@example.com",
            "password": "password123",
            "business_name": BUSINESS_ID 
        }
        # Note: In our current auth service, business_id is usually UUID. But register_business accepts name.
        # However, for Foreign Key to match BUSINESS_ID constant, we might need to rely on what register returns
        # OR we can manually insert if we have a direct script. 
        # But let's try the API.
        
        # Wait, if I register via API:
        # POST /api/auth/register -> creates user & business. 
        # But business ID is generated (UUID).
        # My script uses "verify_biz_01" as a constant.
        # I should use the returned Business ID from registration!
        
        reg_resp = await client.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        
        # If already registered, login to get ID?
        # Simpler: Just try to get profile or assume success.
        # If using existing "verify_biz_01" string requires it to be inserted as ID.
        # But SQLAlchemy models imply UUID usually.
        # Let's check the response.
        
        if reg_resp.status_code == 200:
            data = reg_resp.json().get("data", {})
            # Our auth service registration returns info?
            # Let's hope it does. If not, we login.
            print(f"-> Registration Response: {reg_resp.json()}")
             # Actually, let's login to be sure what the business_id is.
        else:
            print(f"-> Registration failed (maybe exists): {reg_resp.json()}")

        # Login to get Business ID
        login_resp = await client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "verify_admin@example.com", 
            "password": "password123"
        })
        
        if login_resp.status_code == 200:
             user_data = login_resp.json()["user"]
             actual_business_id = user_data["business_id"]
             print(f"-> Using Business ID: {actual_business_id}")
        else:
             print("FAILED to login/get business ID.")
             return

        # 1. Create Workflow
        print("\n1. Creating Verification Workflow...")
        workflow_payload = {
            "business_id": actual_business_id, # Use dynamic ID
            "name": "E2E Verification Flow",
            "trigger_type": "keyword",
            "trigger_config": {"keyword": "verify_me"},
            "nodes": [
                {"id": "n1", "type": "start", "label": "Start", "position": {"x":0, "y":0}},
                {"id": "n2", "type": "action", "label": "Greet", "config": {"action_type": "send_message", "template": "Hello, please reply with your email."}, "position": {"x":100, "y":0}},
                {"id": "n3", "type": "wait_for_reply", "label": "Wait", "position": {"x":200, "y":0}},
                {"id": "n4", "type": "ai_extract", "label": "Extract Email", "config": {"fields": [{"name": "email", "type": "email"}]}, "position": {"x":300, "y":0}},
                {"id": "n5", "type": "condition", "label": "Check Email", "config": {"variable": "email", "operator": "exists"}, "position": {"x":400, "y":0}},
                {"id": "n6", "type": "action", "label": "Success", "config": {"action_type": "send_message", "template": "Got email: {email}"}, "position": {"x":500, "y":0}}
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
                {"source": "n3", "target": "n4"},
                {"source": "n4", "target": "n5"},
                {"source": "n5", "target": "n6", "condition": "true"}
            ]
        }
        
        resp = await client.post(f"{BASE_URL}/api/workflows", json=workflow_payload)
        resp_json = resp.json()
        print(f"DEBUG: Create Response: {resp_json}")
        if resp_json.get("status") != "success":
             print(f"FAILED to create workflow API Error: {resp_json}")
             return
        wf_id = resp_json["id"]
        print(f"-> Workflow Created (ID: {wf_id})")
        
        # 2. Trigger Workflow (Start)
        print("\n2. Triggering Workflow (via Chat Message 'verify_me')...")
        chat_payload = {
            "user_id": "tester_01",
            "message": "I want to verify_me please",
            "business_id": actual_business_id
        }
        resp = await client.post(f"{BASE_URL}/api/web-chat", json=chat_payload)
        # Note: This returns the AI reply immediately, but workflow runs in background.
        print(f"-> Chat Response: {resp.json()}")
        
        # 3. Poll for Suspension
        print("\n3. Waiting for Workflow to Suspend...")
        execution_id = None
        for i in range(10):
            await asyncio.sleep(2)
            resp = await client.get(f"{BASE_URL}/api/executions?business_id={actual_business_id}")
            executions = resp.json()
            if executions:
                latest = executions[0]
                print(f"   [Poll {i}] Status: {latest['status']}")
                if latest['status'] == 'suspended':
                    execution_id = latest['id']
                    # Verify suspension details?
                    break
        
        if not execution_id:
            print("FAILED: Workflow did not suspend in time.")
            return

        print(f"-> Workflow Suspended at Node (Execution ID: {execution_id})")
        
        # 4. Resume Workflow (Reply with Email)
        print("\n4. Resuming Workflow (Sending Reply with Email)...")
        resume_payload = {
            "user_id": "tester_01",
            "message": "My email is test_user@example.com",
            "business_id": actual_business_id
        }
        resp = await client.post(f"{BASE_URL}/api/web-chat", json=resume_payload)
        print(f"-> Chat Response: {resp.json()}")
        
        # 5. Poll for Completion
        print("\n5. Waiting for Completion and Extraction...")
        success = False
        for i in range(10):
            await asyncio.sleep(2)
            resp = await client.get(f"{BASE_URL}/api/executions?business_id={actual_business_id}")
            executions = resp.json()
            latest = next((e for e in executions if e['id'] == execution_id), None)
            
            if latest:
                print(f"   [Poll {i}] Status: {latest['status']}")
                if latest['status'] == 'completed':
                    # Check Context for Email
                    context = latest['context_data']
                    email = context.get('email')
                    print(f"   -> Extracted Email (Raw): {email}")
                    
                    # Sometimes extraction returns dict like {"email": "..."} inside context
                    # Current code merges output so context['email'] should exist.
                    
                    if email == "test_user@example.com":
                        success = True
                    break
        
        if success:
            print("\n✅ VERIFICATION PASSED: Full Flow (Start -> Suspend -> Resume -> Extract -> Complete)")
        else:
            print("\n❌ VERIFICATION FAILED: Workflow did not complete or extract email correctly.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_verification())
