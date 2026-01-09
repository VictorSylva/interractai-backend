
import json
import re

def get_context_value(context: dict, key: str):
    if not key: return None
    parts = key.split('.')
    val = context
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            val = None
            break
    if val is None and len(parts) == 1:
        val = context.get(key)
    return val

context = {
  "trigger": {
    "message": "Type: \"I am from Chimp and our budget is $10,000\"",
    "message_body": "Type: \"I am from Chimp and our budget is $10,000\"",
    "intent": "pricing",
    "user_id": "web_user_yyzzvzagg",
    "business_id": "groupcopac@gmail.com"
  },
  "business_id": "eb89cc6e-49fb-46b5-b5f6-11cced548172",
  "status": "started",
  "budget": 10000,
  "company": "Chimp",
  "condition_eval": "true",
  "lead_id": 34,
  "lead_status": "captured"
}

def hydrate(text):
    def replace_var(match):
        key = match.group(1).strip()
        val = get_context_value(context, key)
        return str(val) if val is not None else match.group(0)
    return re.sub(r'\{\{(.*?)\}\}', replace_var, text)

print(f"Test 1: {{company}} -> {hydrate('{{company}}')}")
print(f"Test 2: {{company}} VIP -> {hydrate('{{company}} VIP')}")
print(f"Test 3: {{trigger.intent}} -> {hydrate('{{trigger.intent}}')}")
