"""
Google Maps Service: Get real transit times between airport and locations
"""

import httpx
from config import GOOGLE_MAPS_API_KEY
from typing import Optional, Dict
import asyncio


class GoogleMapsService:
    """Service to fetch transit times using Distance Matrix API"""
    
    BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
    TIMEOUT = 10.0
    
    # Airport coordinates for major hubs
    AIRPORT_COORDS = {
        "AMS": "52.3086,4.7639",      # Amsterdam Schiphol
        "LIS": "38.6747,-9.2219",     # Lisbon
        "SIN": "1.3644,103.9915",     # Singapore Changi
    }
    
    @staticmethod
    async def get_distance_and_duration(
        from_coords: str,
        to_coords: str,
        departure_time: Optional[int] = None,
        mode: str = "transit"
    ) -> Optional[Dict]:
        """
        Get distance and duration between two points
        
        Args:
            from_coords: "52.3086,4.7639" (airport)
            to_coords: "52.3600,4.8852" (destination)
            departure_time: Unix timestamp for real-time traffic
            mode: "transit", "taxi", or "walking"
        
        Returns:
            {"distance_m": 5000, "duration_min": 25} or None if API fails
        """
        if not GOOGLE_MAPS_API_KEY:
            print("⚠️ GOOGLE_MAPS_API_KEY not configured")
            return None
        
        try:
            params = {
                "origins": from_coords,
                "destinations": to_coords,
                "key": GOOGLE_MAPS_API_KEY,
                "mode": mode,
                "units": "metric",
            }
            
            if departure_time:
                params["departure_time"] = departure_time
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    GoogleMapsService.BASE_URL,
                    params=params,
                    timeout=GoogleMapsService.TIMEOUT
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Check for valid response
                if data.get("status") != "OK" or not data.get("rows"):
                    print(f"⚠️ Google Maps API: {data.get('status')}")
                    return None
                
                element = data["rows"][0]["elements"][0]
                if element.get("status") != "OK":
                    return None
                
                return {
                    "distance_m": element["distance"]["value"],
                    "duration_min": element["duration"]["value"] // 60,
                }
                
        except Exception as e:
            print(f"❌ Google Maps error: {e}")
            return None
    
    @staticmethod
    async def get_round_trip_duration(
        airport_code: str,
        to_coords: str,
    ) -> Optional[int]:
        """
        Get round-trip duration from airport to location and back
        
        Args:
            airport_code: IATA code (e.g., "AMS")
            to_coords: destination coordinates "52.3600,4.8852"
        
        Returns:
            total minutes for round trip, or None if API fails
        """
        airport_coords = GoogleMapsService.AIRPORT_COORDS.get(airport_code)
        if not airport_coords:
            print(f"⚠️ Airport {airport_code} coordinates not found")
            return None
        
        # Get duration there
        result = await GoogleMapsService.get_distance_and_duration(
            from_coords=airport_coords,
            to_coords=to_coords,
            mode="transit"
        )
        
        if not result:
            return None
        
        # Assume return trip is similar duration (add 10% buffer for return trip)
        return int(result["duration_min"] * 2.1)
