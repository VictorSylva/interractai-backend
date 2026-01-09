
import asyncio
import os
import json
import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat"

async def test_extract():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("MISSING API KEY")
        return

    text_to_analyze = """
    Latest Message: FINAL_FINAL: I am from Netflix and my budget is $1,000,000
    
    Chat History:
    
    Previous AI Output: 
    """
    
    target_fields = [
        {"name": "company", "type": "string", "description": "The name of the user's company"},
        {"name": "budget", "type": "number", "description": "The user's budget"}
    ]
    
    fields_str = ""
    for f in target_fields:
        fields_str += f"- {f.get('name')}: {f.get('description')} (Type: {f.get('type')})\n"

    system_instruction = f"""
    You are an elite Data Extraction Specialist. 
    Your task is to extract specific attributes from the provided chat snippet and return a RAW JSON object.

    FIELDS TO EXTRACT:
    {fields_str}

    CRITICAL RULES:
    1. return ONLY valid JSON.
    2. No markdown blocks. No conversational text.
    3. If you can't find a value, set it to null.
    4. Be precise. If the user says 'I am from Apple', company is 'Apple'.
    5. For numbers (budget, etc.), return only the numeric value (no $ or commas).

    EXAMPLE RESPONSE:
    {{ "company": "Tesla", "budget": 50000 }}
    """
    
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": text_to_analyze}
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.0,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        print(f"STATUS: {res.status_code}")
        print(f"RESPONSE: {res.text}")

if __name__ == "__main__":
    asyncio.run(test_extract())
