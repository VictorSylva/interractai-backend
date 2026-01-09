import asyncio
import httpx
import uuid
import json
from database.session import AsyncSessionLocal
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc
from database.models.chat import Message, Conversation
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution, ExecutionStep
from database.models.crm import Lead, Ticket
from sqlalchemy import select, delete

class EndToEndAuditor:
    def __init__(self, base_url="http://localhost:8000", business_email="groupcopac@gmail.com"):
        self.base_url = base_url
        self.business_email = business_email
        self.test_user_id = f"audit_http_{uuid.uuid4().hex[:8]}"

    async def test_web_chat(self, message_text):
        print(f"\n[Audit] Testing Web Chat API: '{message_text}'")
        url = f"{self.base_url}/api/web-chat"
        payload = {
            "business_id": self.business_email,
            "user_id": self.test_user_id,
            "message": message_text
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=20.0)
            data = response.json()
            print(f"[Audit] API Response ({response.status_code}): {json.dumps(data, indent=2)}")
            
            # Check for Arbitration
            if data.get("status") == "workflow_processing":
                print("[Audit] SUCCESS: Workflow triggered and Standard AI suppressed.")
            elif data.get("reply"):
                print(f"[Audit] FALLBACK: Standard AI replied: {data.get('reply')[:50]}...")
            else:
                print("[Audit] WARNING: No reply and no workflow status.")

    async def test_whatsapp_webhook(self, message_text, from_number="123456789"):
        print(f"\n[Audit] Testing WhatsApp Webhook: '{message_text}'")
        url = f"{self.base_url}/whatsapp/webhook"
        # Mocking Meta/WhatsApp JSON structure
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "888",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "16505551111", "phone_number_id": "123456"},
                        "contacts": [{"profile": {"name": "Audit User"}, "wa_id": from_number}],
                        "messages": [{
                            "from": from_number,
                            "id": f"wamid.{uuid.uuid4().hex}",
                            "timestamp": "1674555555",
                            "text": {"body": message_text},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=20.0)
            data = response.json()
            print(f"[Audit] Webhook Response ({response.status_code}): {data}")
            
            # The webhook returns immediately. We need to check the DB for bot replies.
            await asyncio.sleep(3)
            async with AsyncSessionLocal() as session:
                stmt = select(Message).where(
                    Message.conversation_id == from_number,
                    Message.sender == 'agent' # Webhook uses 'agent' for bot replies
                ).order_by(Message.timestamp.desc()).limit(2)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                print(f"[Audit] Database Verification (WhatsApp): Found {len(messages)} agent replies.")
                for msg in messages:
                    print(f"  -> {msg.text[:100]}...")
                
                if len(messages) > 1:
                    print("[Audit] !!! FAILURE !!! Double response detected in WhatsApp channel.")
                elif len(messages) == 1:
                    print("[Audit] SUCCESS: Single response preserved in WhatsApp channel.")

    async def run_audit(self):
        print("=== STANDARDIZED RUNTIME ARBITRATION AUDIT ===")
        
        # 1. Test Web Chat (Workflow Match)
        await self.test_web_chat("test") 
        
        # 2. Test Web Chat (No Match -> Fallback)
        await self.test_web_chat("hello there")
        
        # 3. Test WhatsApp (Workflow Match)
        WhatsApp_Num = f"wa_{uuid.uuid4().hex[:6]}"
        await self.test_whatsapp_webhook("pricing", from_number=WhatsApp_Num)
        
        # 4. Test WhatsApp (No Match -> Fallback)
        WhatsApp_Num_2 = f"wa_{uuid.uuid4().hex[:6]}"
        await self.test_whatsapp_webhook("what is your address?", from_number=WhatsApp_Num_2)

if __name__ == "__main__":
    auditor = EndToEndAuditor()
    asyncio.run(auditor.run_audit())
