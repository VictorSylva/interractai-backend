import asyncio
import logging
from database.session import AsyncSessionLocal
from database.models.crm import Lead
from database.models.general import User
from sqlalchemy import select, update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_leads():
    """
    Migrates all leads that are currently saved with an Email business_id 
     to their proper internal UUID business_id.
    """
    async with AsyncSessionLocal() as session:
        try:
            # 1. Get all unique business_ids from the leads table
            stmt = select(Lead.business_id).distinct()
            res = await session.execute(stmt)
            bids = res.scalars().all()
            
            email_bids = [b for b in bids if b and "@" in b]
            
            if not email_bids:
                logger.info("No email-based business_ids found in leads table.")
                return

            logger.info(f"Found {len(email_bids)} email-based business_ids to migrate: {email_bids}")
            
            for email in email_bids:
                # Resolve internal UUID
                stmt = select(User.business_id).where(User.email == email)
                res = await session.execute(stmt)
                uuid = res.scalar_one_or_none()
                
                if uuid:
                    logger.info(f"Migrating leads for {email} -> {uuid}")
                    # Update all leads for this email
                    upd = update(Lead).where(Lead.business_id == email).values(business_id=uuid)
                    await session.execute(upd)
                else:
                    logger.warning(f"Could not find internal UUID for email: {email}")
            
            await session.commit()
            logger.info("Migration complete!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate_leads())
