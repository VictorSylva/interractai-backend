"""
Manual test to add a lead directly and verify it appears in the UI
"""
import requests

# Your backend URL
BASE_URL = "http://localhost:8002"

# Your business ID (check your login - it's either your email or a UUID)
BUSINESS_ID = "groupcopac@gmail.com"  # Change this to your actual business_id

# Test lead data
lead_data = {
    "name": "Test User",
    "email": "test@example.com",
    "phone": "+1234567890",
    "source": "manual_test",
    "status": "new",
    "notes": "This is a manual test lead"
}

# This would normally be done via the save_lead function, but we'll use the API
# Since there's no direct POST /api/leads endpoint, we need to add one or use the database directly

print(f"To manually test, you can:")
print(f"1. Open the browser console on the Leads page")
print(f"2. Run this JavaScript:")
print(f"""
fetch('{BASE_URL}/api/leads?business_id={BUSINESS_ID}')
  .then(r => r.json())
  .then(data => console.log('Current leads:', data))
""")
print(f"\n3. Check the backend logs for '[LeadCapture]' messages during your conversation")
print(f"\n4. Verify your business_id matches: {BUSINESS_ID}")
