import asyncio
from services.db_service import db

async def inspect_data():
    if not db:
        print("Database not connected.")
        return

    print("--- Inspecting Conversations ---")
    docs = db.collection("conversations").stream()
    count = 0
    for doc in docs:
        count += 1
        data = doc.to_dict()
        safe_msg = str(data.get('lastMessage', '')).encode('ascii', 'ignore').decode('ascii')
        print(f"ID: {doc.id} | Owner: {data.get('owner_id', 'MISSING')} | LastMsg: {safe_msg}")
    
    print(f"--- Total: {count} ---")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(inspect_data())
