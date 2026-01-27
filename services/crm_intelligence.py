"""
AI-Enhanced CRM Intelligence Service

Provides lead scoring and conversation insights with full transparency.
All AI outputs are logged as LeadActivity for auditability.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CRMIntelligenceService:
    """AI-powered CRM insights with transparency"""
    
    def calculate_lead_score(self, lead_data: dict) -> dict:
        """
        Simple rule-based lead scoring.
        Returns score and reasoning for transparency.
        """
        score = 0
        factors = []
        
        # Value/Budget scoring
        value = lead_data.get("value") or 0
        if value > 10000:
            score += 30
            factors.append(f"High budget (${value})")
        elif value > 5000:
            score += 20
            factors.append(f"Medium budget (${value})")
        elif value > 0:
            score += 10
            factors.append(f"Budget provided (${value})")
        
        # Contact completeness
        if lead_data.get("email") and lead_data.get("phone"):
            score += 15
            factors.append("Complete contact info")
        elif lead_data.get("email") or lead_data.get("phone"):
            score += 10
            factors.append("Partial contact info")
        
        # Tags (VIP, urgent, etc.)
        tags = lead_data.get("tags", [])
        if "vip" in [t.lower() for t in tags]:
            score += 25
            factors.append("VIP tag")
        if "urgent" in [t.lower() for t in tags]:
            score += 15
            factors.append("Urgent tag")
        
        # Status progression
        status = lead_data.get("status", "new").lower()
        if status == "qualified":
            score += 20
            factors.append("Qualified status")
        elif status == "contacted":
            score += 10
            factors.append("Contacted status")
        
        # Engagement (last interaction)
        if lead_data.get("last_interaction_at"):
            score += 10
            factors.append("Recent engagement")
        
        return {
            "score": min(score, 100),  # Cap at 100
            "factors": factors,
            "tier": "hot" if score >= 70 else "warm" if score >= 40 else "cold"
        }
    
    async def summarize_conversation(self, messages: list) -> str:
        """
        Generate conversation summary.
        For MVP: Simple extraction. Future: LLM-based.
        """
        if not messages:
            return "No conversation history"
        
        # Simple summary for MVP
        total = len(messages)
        customer_msgs = [m for m in messages if m.get("sender") == "customer"]
        agent_msgs = [m for m in messages if m.get("sender") == "agent"]
        
        summary = f"Conversation: {total} messages ({len(customer_msgs)} from customer, {len(agent_msgs)} from agent)"
        
        # Extract key topics (simple keyword detection)
        all_text = " ".join([m.get("text", "") for m in messages]).lower()
        topics = []
        if "price" in all_text or "cost" in all_text or "budget" in all_text:
            topics.append("pricing")
        if "demo" in all_text or "trial" in all_text:
            topics.append("demo request")
        if "feature" in all_text or "integration" in all_text:
            topics.append("features")
        
        if topics:
            summary += f". Topics: {', '.join(topics)}"
        
        return summary

crm_intelligence = CRMIntelligenceService()
