import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

# The "Grand Master" Demo Payload
DEMO_PAYLOAD = {
  "name": "Grand Master Demo: Sales",
  "trigger_type": "keyword",
  "trigger_config": { "keyword": "demo_sales" },
  "nodes": [
    { "id": "n1", "type": "start", "label": "Start", "position": { "x": 0, "y": 0 } },
    { "id": "n2", "type": "action", "label": "Greet", "config": { "action_type": "send_message", "template": "Hi! What is your monthly budget for automation?" }, "position": { "x": 0, "y": 100 } },
    { "id": "n3", "type": "wait_for_reply", "label": "Wait for Budget", "position": { "x": 0, "y": 200 } },
    { "id": "n4", "type": "ai_extract", "label": "Extract Budget", "config": { "fields": [{ "name": "budget", "type": "number" }, { "name": "email", "type": "email" }] }, "position": { "x": 0, "y": 300 } },
    { "id": "n5", "type": "condition", "label": "Check Value", "config": { "variable": "budget", "operator": "greater_than", "value": 1000 }, "position": { "x": 0, "y": 400 } },
    { "id": "n6", "type": "action", "label": "VIP Route", "config": { "action_type": "send_message", "template": "You qualify for our VIP plan! A manager will email you at {email}." }, "position": { "x": -200, "y": 550 } },
    { "id": "n6_lead", "type": "lead_capture", "label": "Save Lead", "config": { "tags": ["vip"] }, "position": { "x": -200, "y": 650 } },
    { "id": "n7", "type": "action", "label": "Standard Route", "config": { "action_type": "send_message", "template": "Thanks! You can check our standard pricing page." }, "position": { "x": 200, "y": 550 } }
  ],
  "edges": [
    { "source": "n1", "target": "n2" },
    { "source": "n2", "target": "n3" },
    { "source": "n3", "target": "n4" },
    { "source": "n4", "target": "n5" },
    { "source": "n5", "target": "n6", "condition": "true", "label": "High Budget" },
    { "source": "n6", "target": "n6_lead" },
    { "source": "n5", "target": "n7", "condition": "false", "label": "Low Budget" }
  ]
}

async def create_demo():
    print("--- Setting up 'Grand Master' Demo Workflow ---")
    
    async with httpx.AsyncClient() as client:
        # 0. Register/Get Business (Reuse existing logic or assume 'demo_biz')
        # specific to your verifying setup, let's use the one from verification
        # or just register a new one to be clean.
        business_name = "Demo Corp"
        email = "demo@interact.ai"
        
        print(f"1. Ensuring Business '{business_name}' exists...")
        reg_resp = await client.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "demo_password",
            "business_name": business_name
        })
        
        if reg_resp.status_code == 200:
             # Registration success
             print("   -> Registered new business.")
             # Login to get ID
        
        # Login
        login_resp = await client.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": "demo_password"
        })
        
        if login_resp.status_code != 200:
            print(f"FAILED to login: {login_resp.text}")
            return
            
        token = login_resp.json()["access_token"]
        user_data = login_resp.json()["user"]
        business_id = user_data["business_id"]
        print(f"   -> Logged in. Business ID: {business_id}")

        # 2. Create Workflow
        print("\n2. Uploading Workflow Definition...")
        DEMO_PAYLOAD["business_id"] = business_id
        
        resp = await client.post(f"{BASE_URL}/api/workflows", json=DEMO_PAYLOAD)
        
        if resp.status_code == 200:
            wf = resp.json()
            print(f"\n✅ SUCCESS! Workflow '{wf['name']}' created (ID: {wf['id']})")
            print("\nHOW TO TEST:")
            print(f"1. Go to the Chat Interface (or use API).")
            print(f"2. Send message: 'demo_sales'")
            print(f"3. See the AI greet you.")
        else:
            print(f"❌ FAILED to create workflow: {resp.text}")

if __name__ == "__main__":
    asyncio.run(create_demo())
