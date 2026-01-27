import asyncio
from database.session import AsyncSessionLocal
from database.models.crm import Lead
from database.models.chat import Conversation, Message
from sqlalchemy import select, desc

async def check_leads_and_conversations():
    async with AsyncSessionLocal() as session:
        # Check leads
        lead_stmt = select(Lead).order_by(desc(Lead.created_at)).limit(10)
        lead_result = await session.execute(lead_stmt)
        leads = lead_result.scalars().all()
        
        print(f"\n=== LEADS ({len(leads)}) ===")
        for lead in leads:
            print(f"ID: {lead.id} | Name: {lead.name} | Contact: {lead.contact} | Email: {lead.email} | Phone: {lead.phone} | Business: {lead.business_id}")
        
        # Check conversations
        conv_stmt = select(Conversation).order_by(desc(Conversation.last_timestamp)).limit(10)
        conv_result = await session.execute(conv_stmt)
        convs = conv_result.scalars().all()
        
        print(f"\n=== CONVERSATIONS ({len(convs)}) ===")
        for conv in convs:
            print(f"ID: {conv.id} | Name: {conv.customer_name} | Platform: {conv.platform} | Business: {conv.business_id}")
            
            # Get messages for this conversation
            msg_stmt = select(Message).where(Message.conversation_id == conv.id).order_by(Message.timestamp).limit(5)
            msg_result = await session.execute(msg_stmt)
            messages = msg_result.scalars().all()
            
            print(f"  Messages ({len(messages)}):")
            for msg in messages:
                print(f"    [{msg.sender}]: {msg.text[:50]}...")

if __name__ == "__main__":
    asyncio.run(check_leads_and_conversations())
