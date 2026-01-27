import logging
from datetime import datetime
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models.general import Business

logger = logging.getLogger(__name__)

async def check_subscription_access(business_id: str) -> bool:
    """
    Checks if the business has a valid subscription or active trial.
    Updates status to 'expired' if trial has ended.
    Returns True if access is allowed, False otherwise.
    """
    if not business_id:
        return False

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Business).where(Business.id == business_id)
            result = await session.execute(stmt)
            business = result.scalar_one_or_none()

            if not business:
                logger.warning(f"Subscription Check: Business {business_id} not found.")
                # If business not found, maybe allow? No, strict.
                return False

            # 1. Check if already marked as expired or suspended
            if business.status in ["expired", "suspended"]:
                logger.info(f"Subscription Check: Business {business_id} is {business.status}.")
                return False

            # 2. Check Trial Expiry Logic
            if business.status == "trial" and business.trial_end_at:
                if datetime.utcnow() > business.trial_end_at:
                    logger.info(f"Subscription Check: Trial expired for {business_id}. Updating status.")
                    business.status = "expired"
                    await session.commit()
                    return False
            
            # 3. Allow Access (Active or Trial within date)
            return True

        except Exception as e:
            logger.error(f"Error checking subscription for {business_id}: {e}")
            return False
