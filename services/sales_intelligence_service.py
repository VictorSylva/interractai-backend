import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from database.session import AsyncSessionLocal
from database.models.crm import Lead, LeadActivity
from services.ai_service import generate_response
import json

logger = logging.getLogger(__name__)

class SalesIntelligenceService:
    async def get_ai_insights(self, business_id: str):
        """
        Generates sales intelligence insights: stalled leads and follow-up recs.
        """
        async with AsyncSessionLocal() as session:
            try:
                now = datetime.utcnow()
                stalled_threshold = now - timedelta(hours=48)
                
                # 1. Identify Stalled Leads
                # Leads in a "warm" or "qualified" status with no activity for 48h
                stmt = select(Lead).where(
                    Lead.business_id == business_id,
                    Lead.status.in_(["contacted", "qualified"]),
                    Lead.last_interaction_at < stalled_threshold
                ).limit(5) # Top 5 stalled leads
                
                res = await session.execute(stmt)
                stalled_leads = res.scalars().all()
                
                # 2. Generate Follow-up Recommendations
                insights = []
                for lead in stalled_leads:
                    recommendation = await self._generate_lead_recommendation(lead, business_id)
                    insights.append({
                        "lead_id": lead.id,
                        "lead_name": lead.name,
                        "status": lead.status,
                        "last_interaction": lead.last_interaction_at.isoformat() if lead.last_interaction_at else None,
                        "recommendation": recommendation
                    })
                
                return {
                    "stalled_leads_count": len(stalled_leads),
                    "insights": insights
                }
            except Exception as e:
                logger.error(f"Error generating AI insights: {e}")
                return {"stalled_leads_count": 0, "insights": []}

    async def _generate_lead_recommendation(self, lead: Lead, business_id: str):
        """
        Uses AI to suggest a specific follow-up based on lead context.
        """
        prompt = f"""
        Analyze this stalled lead and recommend a specific follow-up action.
        NAME: {lead.name}
        STATUS: {lead.status}
        NOTES: {lead.notes or 'No notes available'}
        VALUE: ${lead.value or 'Unknown'}
        
        Keep the recommendation concise (max 2 sentences). Focus on converting them to the next stage.
        """
        
        try:
            target_recommendation = await generate_response(
                prompt, 
                system_instruction="You are a senior sales strategist. Provide actionable, high-conversion follow-up advice.",
                business_id=business_id
            )
            return target_recommendation.strip()
        except:
            return "Re-engage with a personalized message to check if they have any remaining questions."

sales_intelligence_service = SalesIntelligenceService()
