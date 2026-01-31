import httpx
import asyncio
import sys

async def verify_diagnostic(business_id: str, api_url: str = "http://localhost:8000"):
    print(f"--- Diagnostic Verification for: {business_id} ---")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{api_url}/api/debug/business-id?business_id={business_id}"
            print(f"Calling: {url}")
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("\n[SUCCESS] Diagnostic Data Received:")
                print(f"  Input ID: {data.get('input_id')}")
                print(f"  Resolved UUID: {data.get('resolved_uuid')}")
                print(f"  All Mapped IDs: {data.get('all_mapped_ids')}")
                print("\n  Data Counts:")
                for bid, counts in data.get('counts', {}).items():
                    print(f"    - ID: {bid}")
                    print(f"      Leads: {counts.get('leads')}")
                    print(f"      Conversations: {counts.get('conversations')}")
                    print(f"      Knowledge Docs: {counts.get('knowledge_docs')}")
            else:
                print(f"\n[ERROR] Failed to fetch diagnostic data. Status: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"\n[ERROR] Request failed: {e}")

if __name__ == "__main__":
    bid = sys.argv[1] if len(sys.argv) > 1 else "victor@interact.ai" # Default for testing
    api = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    asyncio.run(verify_diagnostic(bid, api))
