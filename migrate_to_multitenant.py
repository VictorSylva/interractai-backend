import asyncio
import firebase_admin
from firebase_admin import firestore
from services.db_service import db

async def migrate():
    if not db:
        print("DB connection failed.")
        return

    print("--- Starting Migration ---")
    
    # 1. Get all root conversations
    root_convs = db.collection("conversations").stream()
    
    count = 0
    msg_count = 0
    
    for doc in root_convs:
        data = doc.to_dict()
        conv_id = doc.id
        
        # Determine Target Business ID
        # Use existing owner_id if present, otherwise 'default'
        business_id = data.get('owner_id')
        if not business_id or business_id == 'default_agent':
            business_id = 'default'
            
        print(f"Migrating {conv_id} -> businesses/{business_id}/conversations/{conv_id} ...")
        
        # 2. Copy Conversation Document
        target_ref = db.collection("businesses").document(business_id).collection("conversations").document(conv_id)
        target_ref.set(data)
        
        # 3. Copy Messages Subcollection
        messages = db.collection("conversations").document(conv_id).collection("messages").stream()
        for msg in messages:
            msg_data = msg.to_dict()
            target_ref.collection("messages").document(msg.id).set(msg_data)
            msg_count += 1
            
        count += 1

    print(f"--- Migration Complete ---")
    print(f"Conversations migrated: {count}")
    print(f"Messages migrated: {msg_count}")
    print("NOTE: Old data in root 'conversations' was NOT deleted for safety. You can delete it manually later.")

if __name__ == "__main__":
    # Fix for asyncio in some windows envs
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) 
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(migrate())
    finally:
        loop.close()
