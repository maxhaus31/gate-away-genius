"""
Route Service: Calculate multi-stop routes using Google Maps Directions API
"""

import httpx
from config import GOOGLE_MAPS_API_KEY
from typing import Optional, Dict, List
import polyline as pl


class RouteService:
    """Service to calculate routes between multiple waypoints"""
    
    BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    TIMEOUT = 10.0
    
    # Airport coordinates
    AIRPORT_COORDS = {
        "AMS": {"lat": 52.3086, "lng": 4.7639},
        "LIS": {"lat": 38.6813, "lng": -9.2267},
        "SIN": {"lat": 1.3644, "lng": 103.9915},
    }
    
    @staticmethod
    async def calculate_multi_waypoint_route(
        airport_code: str,
        place_coordinates: List[str],  # ["lat,lng", "lat,lng", "lat,lng"]
        place_names: List[str],  # ["Place 1", "Place 2", "Place 3"]
        mode: str = "transit"
    ) -> Optional[Dict]:
        """
        Calculate route from airport → place 1 → place 2 → place 3 → airport
        
        Args:
            airport_code: "AMS", "LIS", or "SIN"
            place_coordinates: List of "lat,lng" strings for waypoints
            place_names: List of place names corresponding to coordinates
            mode: "transit" for public transport, "driving" for car
        
        Returns:
            {
                "total_distance_meters": 5000,
                "total_duration_minutes": 45,
                "legs": [
                    {"from": "Airport", "to": "Place 1", "distance": 3000, "duration": 20},
                    {"from": "Place 1", "to": "Place 2", "distance": 2000, "duration": 15},
                    {"from": "Place 2", "to": "Place 3", "distance": 1000, "duration": 10},
                    {"from": "Place 3", "to": "Airport", "distance": 3000, "duration": 20},
                ],
                "polyline": "encoded_polyline_string",
                "waypoints": [airport_coords, place1_coords, place2_coords, place3_coords, airport_coords]
            }
        """
        if not GOOGLE_MAPS_API_KEY:
            print("⚠️ GOOGLE_MAPS_API_KEY not configured")
            return None
        
        if not place_coordinates or len(place_coordinates) == 0:
            return None
        
        try:
            airport_coords = RouteService.AIRPORT_COORDS.get(airport_code)
            if not airport_coords:
                return None
            
            # Build origin (airport)
            origin = {
                "location": {
                    "latLng": {
                        "latitude": airport_coords["lat"],
                        "longitude": airport_coords["lng"]
                    }
                }
            }
            
            # Build destination (last place, then back to airport)
            # For simplicity, we'll calculate pairwise routes and sum them
            # This is a limitation of the Directions API which doesn't support arbitrary waypoints
            
            # Create list of all stops: [airport, place1, place2, place3, airport]
            all_stops = []
            all_stops.append(("Airport", airport_coords["lat"], airport_coords["lng"]))
            
            for i, coords_str in enumerate(place_coordinates):
                lat_str, lng_str = coords_str.split(",")
                lat, lng = float(lat_str), float(lng_str)
                all_stops.append((place_names[i], lat, lng))
            
            # Add airport as final destination
            all_stops.append(("Airport (Return)", airport_coords["lat"], airport_coords["lng"]))
            
            # Calculate legs between consecutive stops
            total_distance = 0
            total_duration = 0
            legs = []
            waypoints = []
            all_polylines = []
            
            travel_mode = "TRANSIT" if mode == "transit" else "DRIVE"
            
            for i in range(len(all_stops) - 1):
                from_name, from_lat, from_lng = all_stops[i]
                to_name, to_lat, to_lng = all_stops[i + 1]
                
                # Build request for this leg
                body = {
                    "origin": {
                        "location": {
                            "latLng": {"latitude": from_lat, "longitude": from_lng}
                        }
                    },
                    "destination": {
                        "location": {
                            "latLng": {"latitude": to_lat, "longitude": to_lng}
                        }
                    },
                    "travelMode": travel_mode,
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "routes.legs.duration,routes.legs.distanceMeters,routes.polyline",
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        RouteService.BASE_URL,
                        json=body,
                        headers=headers,
                        timeout=RouteService.TIMEOUT
                    )
                    
                    if not response.is_success:
                        print(f"⚠️ Google Maps error for leg {i}: {response.status_code}")
                        continue
                    
                    data = response.json()
                    
                    if not data.get("routes") or len(data["routes"]) == 0:
                        print(f"⚠️ No routes found for leg {i}")
                        continue
                    
                    route = data["routes"][0]
                    
                    if route.get("legs"):
                        for leg in route["legs"]:
                            distance = leg.get("distanceMeters", 0)
                            duration_str = leg.get("duration", "0s")
                            
                            # Parse duration (format: "123s" for 123 seconds)
                            duration_seconds = int(duration_str.replace("s", "")) if duration_str else 0
                            duration_minutes = duration_seconds // 60
                            
                            total_distance += distance
                            total_duration += duration_minutes
                            
                            legs.append({
                                "from_place": from_name,
                                "to_place": to_name,
                                "distance_meters": distance,
                                "duration_minutes": duration_minutes,
                            })
                    
                    # Collect polyline if available
                    if route.get("polyline"):
                        polyline_str = route["polyline"].get("encodedPolyline", "")
                        if polyline_str:
                            all_polylines.append(polyline_str)
                
                # Add waypoint
                waypoints.append({"lat": from_lat, "lng": from_lng, "name": from_name})
            
            # Add final waypoint
            waypoints.append({
                "lat": all_stops[-1][1],
                "lng": all_stops[-1][2],
                "name": all_stops[-1][0]
            })
            
            return {
                "total_distance_meters": total_distance,
                "total_duration_minutes": total_duration,
                "legs": legs,
                "polyline": "|".join(all_polylines) if all_polylines else None,
                "waypoints": waypoints,
            }
        
        except Exception as e:
            print(f"⚠️ Route calculation error: {e}")
            return None
