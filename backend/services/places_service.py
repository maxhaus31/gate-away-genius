"""
Places Service: Find popular attractions using Places API + LLM descriptions
"""

from typing import List, Optional, Dict
from services.google_maps import GoogleMapsService
from services.gemini_ai import GeminiActivityService


class PlacesService:
    """Service to find nearby attractions and get LLM descriptions"""
    
    # City center coordinates for major airports
    CITY_CENTERS = {
        "LIS": "38.7223,-9.1393",      # Lisbon city center
        "AMS": "52.3676,4.9041",       # Amsterdam city center
        "SIN": "1.3521,103.8198",      # Singapore city center
    }
    
    # Keywords to search for (limited to reduce API calls)
    # Each keyword = 1 Places API call, so we keep this minimal
    SEARCH_KEYWORDS = [
        "tourist_attraction",  # Museums, monuments, landmarks
        "restaurant",          # Food & dining
    ]
    
    @staticmethod
    async def find_attractions(
        airport_code: str,
        available_minutes: int,
        transport_mode: str = "transit",
        max_places: int = 5,
    ) -> List[Dict]:
        """
        Find top attractions near city center based on available time
        
        Args:
            airport_code: IATA code (e.g., "LIS")
            available_minutes: minutes available for activities
            transport_mode: "transit" or "driving"
            max_places: max attractions to return
        
        Returns:
            List of ranked attractions with name, rating, description
        """
        city_center = PlacesService.CITY_CENTERS.get(airport_code)
        if not city_center:
            print(f"⚠️ City center for {airport_code} not found")
            return []
        
        # Calculate radius based on available time
        # Approximate: 30 min available = 5km radius, 60 min = 10km, etc.
        radius_m = min(int((available_minutes / 30) * 5000), 15000)  # Cap at 15km
        
        print(f"🔍 Searching for attractions within {radius_m}m radius")
        
        # Search for attractions
        all_places = []
        for keyword in PlacesService.SEARCH_KEYWORDS:
            places = await GoogleMapsService.nearby_search(
                location=city_center,
                radius_m=radius_m,
                keyword=keyword,
                max_results=10
            )
            
            if places:
                all_places.extend(places)
        
        # Remove duplicates and sort by rating
        unique_places = {}
        for place in all_places:
            if place["place_id"] not in unique_places:
                unique_places[place["place_id"]] = place
        
        sorted_places = sorted(
            unique_places.values(),
            key=lambda p: (p["user_ratings_total"], p["rating"]),
            reverse=True
        )[:max_places]
        
        print(f"📍 Found {len(sorted_places)} top attractions")
        
        # Get descriptions from Gemini for each place
        gemini_service = GeminiActivityService()
        
        for place in sorted_places:
            try:
                # Use Gemini to create a witty description
                description = gemini_service.generate_place_description(
                    place_name=place["name"],
                    place_types=place["types"],
                    rating=place["rating"],
                    user_ratings_total=place["user_ratings_total"],
                )
                place["description"] = description
            except Exception as e:
                print(f"⚠️ Could not generate description for {place['name']}: {e}")
                place["description"] = f"{place['name']} - Highly rated by {place['user_ratings_total']} visitors"
        
        return sorted_places
