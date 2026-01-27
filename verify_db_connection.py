import os
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    print("--- Verifying DEV DB Connection ---")
    
    # Load DEV config forced
    if os.path.exists(".env.dev"):
        load_dotenv(".env.dev", override=True)
    
    url = os.getenv("DATABASE_URL")
    print(f"Connecting to: {url}")
    
    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Query Result: {result.scalar()}")
        print("SUCCESS: Connected to database.")
    except Exception as e:
        print(f"FAILURE: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
