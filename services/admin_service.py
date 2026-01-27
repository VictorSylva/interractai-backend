from sqlalchemy import select, func
from database.session import AsyncSessionLocal
from database.models.general import Business, User, BusinessSettings, KnowledgeDoc, BusinessWhatsAppConfig
from database.models.chat import Message, Conversation
from database.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution, ExecutionStep
from database.models.crm import Lead, Ticket
import logging

logger = logging.getLogger(__name__)

class AdminService:
    async def check_is_super_admin(self, user_id: str):
        """Checks if a user has the super_admin role in SQL."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                return user and user.role in ["super_admin", "admin"]
            except Exception as e:
                logger.error(f"Error checking admin status: {e}")
                return False

    async def get_all_businesses(self):
        """Fetches all businesses from the SQL database."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Business)
                result = await session.execute(stmt)
                businesses = result.scalars().all()
                
                return [{
                    "business_id": b.id,
                    "name": b.name,
                    "created_at": b.created_at,
                    "status": b.status,
                    "plan_name": b.plan_name or "starter" # Default to starter if null
                } for b in businesses]
            except Exception as e:
                logger.error(f"Error fetching all businesses: {e}")
                return []

    async def update_business_status(self, business_id: str, status: str):
        """Updates the status of a business (active, suspended, etc)."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Business).where(Business.id == business_id)
                result = await session.execute(stmt)
                business = result.scalar_one_or_none()
                if not business:
                    return False
                
                business.status = status
                await session.commit()
                return True
            except Exception as e:
                logger.error(f"Error updating business status: {e}")
                await session.rollback()
                return False

    async def delete_business(self, business_id: str):
        """Permanently deletes a business and all its associated data."""
        async with AsyncSessionLocal() as session:
            try:
                from sqlalchemy import delete
                
                # Deletion sequence to satisfy foreign key constraints
                
                # 1. Chat related
                await session.execute(delete(Message).where(Message.business_id == business_id))
                await session.execute(delete(Conversation).where(Conversation.business_id == business_id))
                
                # 2. Workflow related
                # Execution steps depend on executions
                # We need to find executions for this business
                exec_ids_stmt = select(WorkflowExecution.id).where(WorkflowExecution.business_id == business_id)
                exec_ids_res = await session.execute(exec_ids_stmt)
                exec_ids = exec_ids_res.scalars().all()
                if exec_ids:
                    await session.execute(delete(ExecutionStep).where(ExecutionStep.execution_id.in_(exec_ids)))
                
                await session.execute(delete(WorkflowExecution).where(WorkflowExecution.business_id == business_id))
                
                # Nodes and edges depend on workflows
                work_ids_stmt = select(Workflow.id).where(Workflow.business_id == business_id)
                work_ids_res = await session.execute(work_ids_stmt)
                work_ids = work_ids_res.scalars().all()
                if work_ids:
                    await session.execute(delete(WorkflowEdge).where(WorkflowEdge.workflow_id.in_(work_ids)))
                    await session.execute(delete(WorkflowNode).where(WorkflowNode.workflow_id.in_(work_ids)))
                
                await session.execute(delete(Workflow).where(Workflow.business_id == business_id))
                
                # 3. CRM related
                await session.execute(delete(Lead).where(Lead.business_id == business_id))
                await session.execute(delete(Ticket).where(Ticket.business_id == business_id))
                
                # 4. General related
                await session.execute(delete(User).where(User.business_id == business_id))
                await session.execute(delete(BusinessSettings).where(BusinessSettings.business_id == business_id))
                await session.execute(delete(KnowledgeDoc).where(KnowledgeDoc.business_id == business_id))
                await session.execute(delete(BusinessWhatsAppConfig).where(BusinessWhatsAppConfig.business_id == business_id))
                
                # 5. Final target
                stmt = delete(Business).where(Business.id == business_id)
                result = await session.execute(stmt)
                
                await session.commit()
                return result.rowcount > 0
            except Exception as e:
                logger.error(f"Error deleting business {business_id}: {e}")
                await session.rollback()
                return False

    async def get_platform_stats(self):
        """Aggregates platform-wide stats from SQL."""
        async with AsyncSessionLocal() as session:
            try:
                # 1. Total Businesses
                stmt_biz = select(func.count(Business.id))
                res_biz = await session.execute(stmt_biz)
                total_businesses = res_biz.scalar() or 0

                # 2. Total Users
                stmt_users = select(func.count(User.id))
                res_users = await session.execute(stmt_users)
                total_users = res_users.scalar() or 0

                # 3. Total Messages
                stmt_msgs = select(func.count(Message.id))
                res_msgs = await session.execute(stmt_msgs)
                total_messages = res_msgs.scalar() or 0

                return {
                    "total_businesses": total_businesses,
                    "total_users": total_users,
                    "total_messages_processed": total_messages,
                    "active_subscriptions": total_businesses # Placeholder
                }
            except Exception as e:
                logger.error(f"Error getting platform stats: {e}")
                return {
                    "total_businesses": 0,
                    "total_users": 0,
                    "total_messages_processed": 0,
                    "active_subscriptions": 0
                }

admin_service = AdminService()
