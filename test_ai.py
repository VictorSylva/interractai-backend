import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, '/app')

async def test_ai():
    print("=" * 50)
    print("Testing AI Service Configuration")
    print("=" * 50)
    
    # Check environment variables
    print(f"\nOPENROUTER_API_KEY: {os.getenv('OPENROUTER_API_KEY')[:20]}..." if os.getenv('OPENROUTER_API_KEY') else "None")
    print(f"OPENROUTER_MODEL: {os.getenv('OPENROUTER_MODEL')}")
    print(f"GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY')}")
    
    # Import and test
    from services.ai_service import generate_response
    
    print("\n" + "=" * 50)
    print("Calling AI Service...")
    print("=" * 50)
    
    try:
        response = await generate_response("Hello, how are you?", user_id="test_user", business_id="test_business")
        print(f"\n✅ SUCCESS!")
        print(f"Response: {response}")
    except Exception as e:
        print(f"\n❌ ERROR!")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai())
