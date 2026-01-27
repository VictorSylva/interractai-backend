import asyncio
import os
import sys

# Add the current directory to sys.path so we can import from database and services
sys.path.append(os.getcwd())

from sqlalchemy import select, func
from database.session import AsyncSessionLocal
from database.models.chat import Conversation, Message
from database.models.general import User, Business

async def debug_db():
    print("--- Database Debug Summary ---")
    async with AsyncSessionLocal() as session:
        try:
            # 1. Counts
            user_count = await session.execute(select(func.count()).select_from(User))
            bus_count = await session.execute(select(func.count()).select_from(Business))
            convo_count = await session.execute(select(func.count()).select_from(Conversation))
            msg_count = await session.execute(select(func.count()).select_from(Message))

            print(f"Users: {user_count.scalar()}")
            print(f"Businesses: {bus_count.scalar()}")
            print(f"Conversations: {convo_count.scalar()}")
            print(f"Messages: {msg_count.scalar()}")

            # 2. Recent Conversations
            print("\n--- Recent 5 Conversations ---")
            stmt = select(Conversation).order_by(Conversation.last_timestamp.desc()).limit(5)
            result = await session.execute(stmt)
            convos = result.scalars().all()
            for c in convos:
                print(f"ID: {c.id} | BID: {c.business_id} | Name: {c.customer_name} | Last: {c.last_message[:30] if c.last_message else ''}")

            # 3. Recent Messages
            print("\n--- Recent 10 Messages ---")
            stmt = select(Message).order_by(Message.timestamp.desc()).limit(10)
            result = await session.execute(stmt)
            msgs = result.scalars().all()
            for m in msgs:
                print(f"ID: {m.id} | BID: {m.business_id} | CID: {m.conversation_id} | Sender: {m.sender} | Text: {m.text[:30]}")

            # 4. Check for groupcopac user
            print("\n--- User Resolution Check ---")
            stmt = select(User).where(User.email == "groupcopac@gmail.com")
            user = (await session.execute(stmt)).scalar_one_or_none()
            if user:
                print(f"Found user: {user.email} | BID: {user.business_id}")
            else:
                print("User groupcopac@gmail.com NOT found in database.")

        except Exception as e:
            print(f"Error during debug: {e}")

if __name__ == "__main__":
    asyncio.run(debug_db())
