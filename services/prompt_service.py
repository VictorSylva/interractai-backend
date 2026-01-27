import os
import json
import logging
import re

logger = logging.getLogger(__name__)

class PromptService:
    def __init__(self, prompts_dir="prompts"):
        self.prompts_dir = prompts_dir
        self.base_system = "You are InteractAI — a universal conversational AI built for ANY business. Your job is to intelligently understand what a customer wants, respond professionally, and convert inquiries into actionable leads."
        self.faq = self._load_file("faq.txt")
        self.safety = self._load_file("safety.txt")
        self.intents = self._load_json("intents.json")
        
        self.industry_templates = {
            "real_estate": "\nINDUSTRY: REAL ESTATE\n- Show available units.\n- Ask for budget, location, rooms.\n- Offer inspection.\n",
            "healthcare": "\nINDUSTRY: HEALTHCARE / CLINIC\n- Show service availability.\n- Offer appointment slots.\n- Collect patient details.\n",
            "restaurant": "\nINDUSTRY: RESTAURANT\n- Show menu if asked.\n- Confirm delivery areas.\n- Collect order & customer info.\n",
            "beauty": "\nINDUSTRY: BEAUTY SALON / SPA\n- Share prices.\n- Ask preferred style & date.\n- Book appointment.\n",
            "retail": "\nINDUSTRY: SUPERMARKET / RETAIL\n- Confirm stock availability.\n- Reserve items.\n- Collect customer info.\n",
            "logistics": "\nINDUSTRY: LOGISTICS / DELIVERY\n- Ask weight, pickup, destination.\n- Generate price estimate.\n- Book delivery.\n",
            "education": "\nINDUSTRY: SCHOOL / TRAINING\n- Share course details.\n- Ask preferred session.\n- Collect name & WhatsApp.\n",
            "consulting": "\nINDUSTRY: CONSULTING / SERVICES\n- Explain services.\n- Book consultation.\n",
            "ngo": "\nINDUSTRY: NGO / COMMUNITY\n- Explain mission.\n- Accept donations or volunteer signups.\n"
        }
    
    def _load_file(self, filename):
        try:
            path = os.path.join(self.prompts_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            return ""
        except Exception as e:
            logger.error(f"Error loading prompt file {filename}: {e}")
            return ""

    def _load_json(self, filename):
        try:
            path = os.path.join(self.prompts_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading json file {filename}: {e}")
            return {}

    def detect_intent(self, message: str) -> str:
        """
        Rule-based intent detection.
        Returns the intent name or 'general' if no match.
        """
        message_lower = message.lower()
        
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                # regex check for word boundary to avoid partial matches
                if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower):
                    return intent
        return "general"

    def analyze_sentiment(self, message: str) -> str:
        """
        Heuristic sentiment analysis.
        Returns 'Positive', 'Negative', or 'Neutral'.
        """
        message_lower = message.lower()
        
        pos_words = ["great", "thank", "love", "good", "amazing", "help", "cool", "nice", "awesome"]
        neg_words = ["bad", "terrible", "hate", "slow", "broken", "worst", "stupid", "useless", "fail"]
        
        pos_count = sum(1 for w in pos_words if w in message_lower)
        neg_count = sum(1 for w in neg_words if w in message_lower)
        
        if pos_count > neg_count:
            return "Positive"
        elif neg_count > pos_count:
            return "Negative"
        return "Neutral"

    def check_safety(self, message: str) -> bool:
        """
        Basic safety check using keywords.
        Returns True if safe, False if unsafe.
        """
        unsafe_keywords = ["suicide", "kill", "murder", "bomb", "terrorist", "hack"]
        message_lower = message.lower()
        for word in unsafe_keywords:
            if word in message_lower:
                 logger.warning(f"Safety violation detected: {word}")
                 return False
        return True

    def build_system_prompt(self, profile: dict) -> str:
        """
        Dynamically builds a system prompt based on the business profile.
        """
        business_name = profile.get('name') or profile.get('business_name') or 'this business'
        
        system_text = f"You are the AI assistant for {business_name}. Your primary goal is to represent them professionally and help customers with their specific inquiries.\n"
        
        if profile.get('industry'):
            ind = str(profile.get('industry')).lower()
            system_text += f"\nIndustry: {profile.get('industry')}.\n"
            
            # Inject Industry Logic
            for key, template in self.industry_templates.items():
                if key in ind:
                    system_text += template
                    break
            
            # Fallback if industry known but not in templates (General SME logic)
            if not any(key in ind for key in self.industry_templates):
                system_text += "\nINDUSTRY: GENERAL BUSINESS\n- Explain services/products.\n- Answer inquiries professionally.\n- Collect customer info if interested.\n"
        else:
            system_text += "\nINDUSTRY: GENERAL\n- Provide helpful information about products/services.\n- Answer questions based on the details provided below.\n"

        if profile.get('description'):
            system_text += f"\nAbout {business_name}: {profile.get('description')}.\n"
            
        if profile.get('services'):
            system_text += f"\nServices Offered by {business_name}:\n{profile.get('services')}\n"
            
        if profile.get('tone'):
            system_text += f"\nCommunication Tone: Use a {profile.get('tone')} tone in all messages.\n"
            
        if profile.get('hours'):
             system_text += f"\nOperating Hours: {profile.get('hours')}\n"
        
        if profile.get('location'):
             system_text += f"Location: {profile.get('location')}\n"
             
        if profile.get('faq'):
            system_text += f"\nFrequently Asked Questions (FAQ):\n{profile.get('faq')}\n"

        # Custom Rules (if any)
        if profile.get('custom_instructions'):
             system_text += f"\nSTRICT CUSTOM RULES:\n{profile.get('custom_instructions')}\n"

        # Learned Insights (from Training)
        if profile.get('learned_insights'):
             system_text += f"\nLEARNED KNOWLEDGE FROM PAST CHATS:\n{profile.get('learned_insights')}\n"

        # Knowledge Base Documents
        if profile.get('knowledge_docs'):
            system_text += "\n*** BUSINESS KNOWLEDGE BASE ***\n"
            for doc in profile.get('knowledge_docs'):
                # Truncate large docs to avoid token overflow (simplified)
                content = doc.get('content', '')[:3000] 
                system_text += f"SOURCE: {doc.get('title', 'Document')}\n{content}\n\n"
        
        # UNIVERSAL LEAD ENGINE & RESPONSE STYLE
        system_text += """
\n*** UNIVERSAL RESPONSE STYLE ***
- Friendly, professional, and concise.
- Simple explanations; do not overwhelm.
- STRICT RULE: Always end with a follow-up qualification question to move the conversation forward.
- Only provide info that is explicitly in the profile or FAQs. If unsure, ask for clarification.

*** UNIVERSAL LEAD ENGINE ***
1. Understand the Request -> Answer constraints/availability.
2. Qualify -> Ask for specifics (date, size, style, location).
3. Convert -> Propose the booking/order/visit.
4. Capture -> Ask for Name and Contact to confirm.
"""

        # Base instructions (Safety, etc) appended at the end or integrated
        system_text += f"\n{self.safety}\n"
        
        # ACTION PROTOCOLS
        system_text += """
*** ACTION PROTOCOLS (CRITICAL) ***
You have the ability to perform actions. Use the following tags at the END of your response if the condition is met.

1. LEAD CAPTURE (MAXIMUM PRIORITY):
   - CRITICAL: If the user provides a Name, Phone Number, or Email, you MUST capture it immediately.
   - Do NOT wait for all details. Capture whatever is provided (e.g., just a phone number).
   - If a user provides an address or specific request, include that in the "notes" field of the JSON if possible, but priorities Name and Contact.
   - Even if the user is confirming (e.g., "yes please" after you ask for details), if the details were provided previously in the chat history, capture them.
   - Format: [ACTION: LEAD_CAPTURE | {"name": "Name", "email": "email", "phone": "phone", "notes": "extra context"}]

2. SCHEDULING (HIGH CONVERSION):
   - If the user explicitly wants to book an appointment, schedule a call, visit, or asks about availability:
   - Identify the intent as "booking_request".
   - Append: [ACTION: SCHEDULE]

2. REQUIRED ANALYSIS (MANDATORY):
   - You MUST classify the User's message at the very end of every response. 
   - Use one of these intents: booking_request, enquiry, pricing, support, greeting, features, integration, complaint, feedback, human.
   - Format: [ANALYSIS: <Intent> | <Sentiment>]

*** IMPORTANT ***
- Output the LEAD_CAPTURE tag BEFORE the ANALYSIS tag.
- Ensure the ANALYSIS tag is on its own line at the very end.
"""
        
        # Append specific base instructions if needed, but the profile should be primary context
        system_text += "\nAlways be helpful, polite, and professional."
        
        return system_text

    def construct_messages(self, user_message: str, history: list = None, system_instruction: str = None) -> list:
        """
        Constructs the full list of messages for the API.
        If system_instruction is provided, it replaces the default base_system.
        """
        messages = []
        
        # 1. System Prompt
        # Use custom instruction if provided, else fallback to default logic
        if system_instruction:
            system_content = system_instruction
        else:
             system_content = f"{self.base_system}\n\n{self.safety}\n\n"
             # 2. Add relevant context (like FAQs) ONLY if using default (generic) system
             intent = self.detect_intent(user_message)
             if intent in ["pricing", "support", "features"]:
                  system_content += f"Relevant Knowledge:\n{self.faq}\n\n"
             system_content += f"Detected Intent: {intent}"
        
        messages.append({"role": "system", "content": system_content})
        
        # 3. History
        if history:
            # Add last 5 messages max to save tokens
            messages.extend(history[-5:])
            
        # 4. User Message
        messages.append({"role": "user", "content": user_message})
        
        return messages

# Singleton instance
prompt_service = PromptService()
