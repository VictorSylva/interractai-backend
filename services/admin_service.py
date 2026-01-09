from .db_service import db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AdminService:
    async def check_is_super_admin(self, user_id: str):
        # MVP: Hardcoded check or DB check.
        # For this demo, let's assume specific IDs or emails are super admin.
        # In production, this should check a 'is_super_admin' claim or field in a global 'users' collection.
        # ALLOWING ALL FOR DEMO if user_id starts with 'admin_'
        # if user_id and user_id.startswith('admin_'): return True
        return True # OPEN FOR DEV to ensure verified

    async def get_all_businesses(self):
        if not db:
            print("[DEBUG] DB is None in admin_service")
            return []
        try:
            businesses = []
            seen_ids = set()

            # 1. Try standard listing (for properly created docs)
            docs = db.collection("businesses").stream()
            for doc in docs:
                seen_ids.add(doc.id)
                d = doc.to_dict()
                d['business_id'] = doc.id
                d['status'] = 'Active' # Default
                businesses.append(d)
            
            # 2. Phantom Discovery via Conversations
            # Verify if we missed any (common in Firestore if only subcollections exist)
            # This is a bit expensive but necessary if parent docs aren't created.
            convs = db.collection_group("conversations").limit(50).stream() 
            for c in convs:
                # Path: businesses/{business_id}/conversations/{user_id}
                # parent = conversations collection
                # parent.parent = business document
                business_doc = c.reference.parent.parent
                if business_doc and business_doc.id not in seen_ids:
                    seen_ids.add(business_doc.id)
                    businesses.append({
                        "business_id": business_doc.id,
                        "name": f"Business {business_doc.id[:4]}...", # Fallback name
                        "industry": "Unknown",
                        "status": "Phantom (Auto-Detected)" 
                    })

            print(f"[DEBUG] Total businesses found: {len(businesses)}")
            return businesses
        except Exception as e:
            logger.error(f"Error fetching all businesses: {e}")
            print(f"[DEBUG] Error fetching businesses: {e}")
            return []

    async def get_platform_stats(self):
        if not db: return {}
        try:
            # Aggregate stats
            # 1. Total Businesses
            # Firestore count() queries are efficient
            total_businesses = 0 # Placeholder for exact count query if sdk supports
            businesses = await self.get_all_businesses()
            total_businesses = len(businesses)

            # 2. Total Messages (Estimate)
            # This is hard without a global counter. 
            # We will perform a simplified estimation or use a dedicated counters collection if it existed.
            # For MVP: Return 0 or sum from fetched businesses if small scale.
            
            return {
                "total_businesses": total_businesses,
                "total_users": total_businesses * 5, # Mock estimation
                "total_messages_processed": total_businesses * 124, # Mock estimation
                "active_subscriptions": total_businesses # Assuming all active for now
            }
        except Exception as e:
            logger.error(f"Error getting platform stats: {e}")
            return {}

admin_service = AdminService()
