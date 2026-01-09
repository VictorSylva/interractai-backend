# DEPRECATED
# This service is replaced by services/workflow_engine.py
# Reference: Implementation Plan "Full PostgreSQL Migration"

class AutomationService:
    async def get_rules(self, business_id):
        return []
    
    async def check_triggers(self, *args, **kwargs):
        return None

automation_service = AutomationService()
