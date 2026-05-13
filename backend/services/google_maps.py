"""
Google Maps Service: Get real transit times between airport and locations
"""

import httpx
from config import GOOGLE_MAPS_API_KEY
from typing import Optional, Dict
import asyncio


class GoogleMapsService:
    """Service to fetch transit times using Routes API"""
    
    BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    TIMEOUT = 10.0
    
    # Airport coordinates for major hubs
    AIRPORT_COORDS = {
        "AMS": "52.3086,4.7639",      # Amsterdam Schiphol
        "LIS": "38.7813,-9.1359",     # Lisbon Humberto Delgado
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
        Get distance and duration between two points using Routes API
        
        Args:
            from_coords: "52.3086,4.7639" (airport)
            to_coords: "52.3600,4.8852" (destination)
            departure_time: Unix timestamp for real-time traffic
            mode: "transit" for public transport, "driving" for car/taxi
        
        Returns:
            {"distance_m": 5000, "duration_min": 25} or None if API fails
        """
        if not GOOGLE_MAPS_API_KEY:
            print("WARNING: GOOGLE_MAPS_API_KEY not configured")
            return None
        
        try:
            # Parse coordinates
            from_lat, from_lng = map(float, from_coords.split(","))
            to_lat, to_lng = map(float, to_coords.split(","))
            
            # Map mode to Routes API travelMode
            travel_mode = "TRANSIT" if mode == "transit" else "DRIVE"
            
            # Routes API request body
            body = {
                "origin": {"location": {"latLng": {"latitude": from_lat, "longitude": from_lng}}},
                "destination": {"location": {"latLng": {"latitude": to_lat, "longitude": to_lng}}},
                "travelMode": travel_mode,
            }

            # routingPreference is only valid for DRIVE, not TRANSIT
            if travel_mode == "DRIVE":
                body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"

            if departure_time:
                body["departureTime"] = f"2024-01-01T{departure_time:02d}:00:00Z"

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "routes.legs.duration,routes.legs.distanceMeters",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GoogleMapsService.BASE_URL,
                    json=body,
                    headers=headers,
                    timeout=GoogleMapsService.TIMEOUT
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Check for valid response
                if not data.get("routes") or len(data["routes"]) == 0:
                    print(f"WARNING: Google Maps Routes API: No routes found")
                    return None
                
                route = data["routes"][0]
                
                # Sum up legs to get total distance and duration
                total_distance = 0
                total_duration = 0
                
                if route.get("legs"):
                    for leg in route["legs"]:
                        if "distanceMeters" in leg:
                            total_distance += leg["distanceMeters"]
                        if "duration" in leg:
                            # Parse duration string like "1234s"
                            duration_str = leg["duration"]
                            total_duration += int(duration_str.rstrip('s'))
                
                return {
                    "distance_m": total_distance,
                    "duration_min": total_duration // 60,
                }
                
        except Exception as e:
            print(f"ERROR: Google Maps Routes API error: {e}")
            return None
    
    @staticmethod
    async def get_round_trip_duration(
        airport_code: str,
        to_coords: str,
        mode: str = "transit",
    ) -> Optional[int]:
        """
        Get round-trip duration from airport to location and back
        
        Args:
            airport_code: IATA code (e.g., "AMS")
            to_coords: destination coordinates "52.3600,4.8852"
            mode: "transit" for public transport, "driving" for car/taxi
        
        Returns:
            total minutes for round trip, or None if API fails
        """
        airport_coords = GoogleMapsService.AIRPORT_COORDS.get(airport_code)
        if not airport_coords:
            print(f"WARNING: Airport {airport_code} coordinates not found")
            return None
        
        # Get duration there
        result = await GoogleMapsService.get_distance_and_duration(
            from_coords=airport_coords,
            to_coords=to_coords,
            mode=mode
        )
        
        if not result:
            return None
        
        # Assume return trip is similar duration (add 10% buffer for return trip)
        return int(result["duration_min"] * 2.1)
    

