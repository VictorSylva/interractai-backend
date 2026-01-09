import logging
from .db_service import get_recent_conversations, get_conversation_messages, save_learned_insights
from .ai_service import generate_response

logger = logging.getLogger(__name__)

class LearningService:
    async def train_model(self, business_id: str):
        """
        Analyzes past conversations to extract common patterns and FAQs.
        """
        logger.info(f"Starting training for {business_id}...")
        
        # 1. Fetch recent conversations (Last 50)
        conversations = await get_recent_conversations(business_id, limit=50)
        
        if not conversations:
            return {"status": "no_data", "message": "Not enough conversations to train."}

        # 2. Aggregate text
        aggregated_text = ""
        count = 0
        
        for conv in conversations:
            # Skip empty or short convs
            user_id = conv['id']
            msgs = await get_conversation_messages(business_id, user_id, limit=10)
            
            if len(msgs) < 2: 
                continue
                
            aggregated_text += f"\n--- Conversation with {user_id} ---\n"
            for m in msgs:
                role = "Customer" if m['sender'] == 'customer' else "Agent"
                aggregated_text += f"{role}: {m['text']}\n"
            
            count += 1
            if count >= 10: break # Limit to analysis of 10 solid convs for speed MVP
            
        if not aggregated_text:
             return {"status": "no_data", "message": "No meaningful conversations found."}
             
        # 3. Analyze with AI
        analyst_prompt = (
            "You are an expert Data Analyst.\n"
            "Analyze the following customer service logs.\n"
            "Extract 2 things:\n"
            "1. A list of 3-5 Common Frequently Asked Questions (FAQs) and their answers based on how the Agent replied.\n"
            "2. A list of 2-3 common Customer Intents or problems.\n\n"
            "Output formatted as a concise summary for an AI System Prompt. Do not use Markdown formatting like ** or ##.\n"
            "Format:\n"
            "COMMON PATTERNS:\n"
            "- [Pattern 1]\n"
            "- [Pattern 2]\n\n"
            "SUGGESTED RESPONSES:\n"
            "- Q: [Question] -> A: [Answer]\n"
        )
        
        log_content = f"{analyst_prompt}\n\nLOGS:\n{aggregated_text}"
        
        # We use the same generate_response function but with a specialized prompt
        # We pass user_id="system_training" for logging
        analysis_result = await generate_response(log_content, user_id="system_training")
        
        # 4. Save Result
        data = {
            "insights_text": analysis_result,
            "source_conversations_count": count
        }
        
        await save_learned_insights(business_id, data)
        
        logger.info(f"Training complete for {business_id}")
        return {"status": "success", "insights": analysis_result}

learning_service = LearningService()
