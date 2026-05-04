"""
Test script to explore AviationStack API response structure
Run this to see what data you get back
"""

import httpx
import json
from dotenv import load_dotenv
import os

load_dotenv()

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

if not AVIATIONSTACK_API_KEY:
    print("❌ AVIATIONSTACK_API_KEY not found in .env")
    exit(1)


async def test_flight_lookup():
    """Test fetching a real flight with multiple approaches"""
    
    url = "https://api.aviationstack.com/v1/flights"
    
    # Your real flights: Frankfurt → Singapore (May 10, LH780) → Sydney (SQ221)
    test_flights = [
        "LH780",  # Lufthansa Frankfurt to Singapore
        "SQ221",  # Singapore Airlines Singapore to Sydney
        "AA100",  # Fallback test (known working)
    ]
    
    async with httpx.AsyncClient() as client:
        for flight_code in test_flights:
            print(f"\n{'='*60}")
            print(f"🔍 Trying flight: {flight_code}")
            print(f"{'='*60}")
            
            params = {
                "access_key": AVIATIONSTACK_API_KEY,
                "flight_iata": flight_code,
            }
            
            try:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                
                data = response.json()
                
                # Check pagination info
                pagination = data.get("pagination", {})
                total = pagination.get("total", 0)
                
                print(f"✅ API Response Status: {response.status_code}")
                print(f"📊 Total flights found: {total}")
                
                if total > 0:
                    print(f"\n✨ SUCCESS! Found {total} flight(s)")
                    print("\nFull Response:")
                    print(json.dumps(data, indent=2))
                    return  # Stop after first success
                else:
                    print(f"⚠️  No flights found for {flight_code}")
                    
            except httpx.HTTPError as e:
                print(f"❌ HTTP Error: {e}")
            except json.JSONDecodeError:
                print(f"❌ Failed to parse JSON response")
        
        print(f"\n{'='*60}")
        print("⚠️  FREE TIER LIMITATION")
        print(f"{'='*60}")
        print("""
The free tier of AviationStack has limited data access:
- Only 100 requests/month
- Limited historical flight data
- May not have all flights available

SOLUTIONS:
1. Upgrade to a paid plan for full access
2. Use a mock response for development (we'll do this)
3. Test with archived flight data if available

For MVP, we'll use MOCK data and Google Maps for transit times.
This is actually better for development - we control the data.
        """)


# Run the test
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_flight_lookup())
