"""
Places Service: Fetch real attractions using Places API (New) with Unsplash photos
Falls back to hardcoded places if API fails
"""

from typing import List, Dict, Optional
import httpx
from config import GOOGLE_MAPS_API_KEY
from services.unsplash import UnsplashService


class PlacesService:
    """Service to find nearby attractions using Places API (New)"""
    
    # City center coordinates for major airports
    CITY_CENTERS = {
        "LIS": {"lat": 38.7138, "lng": -9.1394},      # Lisbon downtown (Baixa)
        "AMS": {"lat": 52.3676, "lng": 4.9041},       # Amsterdam city center
        "SIN": {"lat": 1.3521, "lng": 103.8198},      # Singapore city center
    }
    
    # Fallback hardcoded places (used if API fails)
    FALLBACK_PLACES = {
        "LIS": [
            {"name": "Praça do Comércio", "description": "Historic riverside plaza with stunning views.", "search_query": "lisbon plaza", "lat": 38.7072, "lng": -9.1370},
            {"name": "Pastéis de Nata at Manteigaria", "description": "Famous pastry shop - don't miss the original custard tart.", "search_query": "portuguese pastry", "lat": 38.7076, "lng": -9.1359},
            {"name": "Miradouro de Santa Catarina", "description": "Best viewpoint for sunset and the Tagus river.", "search_query": "lisbon viewpoint", "lat": 38.7097, "lng": -9.1477},
            {"name": "Tram 28", "description": "Iconic yellow tram through the historic Alfama district.", "search_query": "lisbon tram", "lat": 38.7126, "lng": -9.1310},
            {"name": "Café Majestic", "description": "Historic café with Belle Époque elegance and great coffee.", "search_query": "portuguese cafe", "lat": 38.7095, "lng": -9.1420},
        ],
        "AMS": [
            {"name": "Amsterdam Canals", "description": "UNESCO-listed canal ring - quintessential Amsterdam.", "search_query": "amsterdam canal", "lat": 52.3700, "lng": 4.8952},
            {"name": "Rijksmuseum", "description": "World-class art museum - home to masterpieces.", "search_query": "museum art", "lat": 52.3601, "lng": 4.8852},
            {"name": "Jordaan District", "description": "Charming neighborhood with galleries, cafés, and antique shops.", "search_query": "amsterdam neighborhood", "lat": 52.3750, "lng": 4.8770},
            {"name": "Anne Frank House", "description": "Moving historical museum - book ahead online.", "search_query": "amsterdam history", "lat": 52.3752, "lng": 4.8838},
            {"name": "Bitterballen & Brown Café", "description": "Traditional Dutch snack in a cozy local pub.", "search_query": "dutch food", "lat": 52.3689, "lng": 4.8981},
        ],
        "SIN": [
            {"name": "Gardens by the Bay", "description": "Futuristic supertrees and enchanting light show.", "search_query": "singapore gardens", "lat": 1.2816, "lng": 103.8636},
            {"name": "Jewel Changi - Waterfall", "description": "World's tallest indoor waterfall - don't miss it!", "search_query": "waterfall", "lat": 1.3581, "lng": 103.9868},
            {"name": "Hawker Chan - Chicken Rice", "description": "Michelin-starred street food - legend in a stall.", "search_query": "singapore food", "lat": 1.2870, "lng": 103.8462},
            {"name": "Marina Bay Sands Observation Deck", "description": "57th floor views over the entire skyline.", "search_query": "singapore skyline", "lat": 1.2858, "lng": 103.8607},
            {"name": "Orchard Road Shopping", "description": "Luxury and local brands on Singapore's main drag.", "search_query": "shopping", "lat": 1.3048, "lng": 103.8328},
        ],
    }
    
    @staticmethod
    async def find_attractions(
        airport_code: str,
        available_minutes: int,
        max_places: int = 5,
    ) -> List[Dict]:
        """
        Find top attractions near city center, with Unsplash photos.
        Falls back to hardcoded places if API fails.
        
        Args:
            airport_code: IATA code (e.g., "LIS")
            available_minutes: minutes available for activities
            max_places: max attractions to return
        
        Returns:
            List of attractions with name, description, photo_url, coordinates
        """
        if not GOOGLE_MAPS_API_KEY:
            print("WARNING: GOOGLE_MAPS_API_KEY not configured, using fallback places")
            return await PlacesService._get_fallback_places(airport_code, max_places)
        
        try:
            # Try to fetch from Places API (New)
            places = await PlacesService._search_places_api(airport_code, available_minutes, max_places)
            
            if places:
                print(f"INFO: Found {len(places)} places from Places API")
                return places
            else:
                print("WARNING: Places API returned no results, using fallback places")
                return await PlacesService._get_fallback_places(airport_code, max_places)
                
        except Exception as e:
            print(f"WARNING: Places API failed ({e}), using fallback places")
            return await PlacesService._get_fallback_places(airport_code, max_places)
    
    @staticmethod
    async def _search_places_api(
        airport_code: str,
        available_minutes: int,
        max_places: int,
    ) -> Optional[List[Dict]]:
        """Fetch places from Places API (New) v1/places:searchNearby endpoint"""
        
        city_center = PlacesService.CITY_CENTERS.get(airport_code)
        if not city_center:
            return None
        
        # Calculate search radius: more time = larger radius
        # 45 min = 5km, 90 min = 10km, capped at 15km
        radius_m = min(int((available_minutes / 45) * 5000), 15000)
        
        try:
            # Places API (New) endpoint
            url = "https://places.googleapis.com/v1/places:searchNearby"
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.formattedAddress,places.location,places.businessStatus",
            }
            
            body = {
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": city_center["lat"],
                            "longitude": city_center["lng"],
                        },
                        "radius": radius_m,
                    }
                },
                "includedTypes": ["tourist_attraction", "restaurant", "museum"],
                "maxResultCount": max_places + 5,  # Request extra in case some are filtered
                "rankPreference": "POPULARITY",  # Most popular/highly-rated first
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                
                data = response.json()
                places = data.get("places", [])
                
                if not places:
                    return None
                
                # Process results - don't fetch photos here to avoid timeout
                # Photos will be fetched in planner_service if needed
                result = []
                for place in places[:max_places]:
                    # Filter: only operational places
                    if place.get("businessStatus") != "OPERATIONAL":
                        continue
                    
                    name = place.get("displayName", {}).get("text", "Unknown")
                    rating = place.get("rating", 0)
                    user_ratings = place.get("userRatingCount", 0)
                    address = place.get("formattedAddress", "")
                    location = place.get("location", {})
                    
                    coordinates = f"{location.get('latitude', 0)},{location.get('longitude', 0)}"
                    
                    result.append({
                        "name": name,
                        "description": f"Rated {rating}/5.0 by {user_ratings} visitors",
                        "rating": rating,
                        "user_ratings_total": user_ratings,
                        "coordinates": coordinates,
                        "address": address,
                        "photo_url": None,  # Will be fetched in planner_service
                    })
                
                return result if result else None
                
        except Exception as e:
            print(f"ERROR: Places API request failed: {e}")
            return None
    
    @staticmethod
    async def _get_fallback_places(airport_code: str, max_places: int) -> List[Dict]:
        """Return hardcoded fallback places without photos to avoid timeout"""
        
        fallback_data = PlacesService.FALLBACK_PLACES.get(airport_code, [])
        result = []
        
        for place in fallback_data[:max_places]:
            result.append({
                "name": place["name"],
                "description": place["description"],
                "rating": 4.5,
                "user_ratings_total": 0,
                "coordinates": f"{place['lat']},{place['lng']}",
                "address": "",
                "photo_url": None,  # Will be fetched in planner_service
            })
        
        return result
