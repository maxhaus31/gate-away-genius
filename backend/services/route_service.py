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
        "LIS": {"lat": 38.7813, "lng": -9.1359},
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
            
            # Build waypoints for ALL stops (airport + places + return airport)
            # This is done FIRST so markers show on map even if route calculation fails
            waypoints = []
            for i, (name, lat, lng) in enumerate(all_stops):
                waypoints.append({"lat": lat, "lng": lng, "name": name})
            
            # Calculate legs between consecutive stops
            total_distance = 0
            total_duration = 0
            legs = []
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
                    "X-Goog-FieldMask": "routes.legs.duration,routes.legs.distanceMeters,routes.legs.steps.navigationInstruction,routes.legs.steps.transitDetails,routes.legs.steps.transitDetails.arrivalStop,routes.legs.steps.transitDetails.departureStop,routes.legs.steps.transitDetails.transitLine,routes.polyline",
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

                            transit_details = RouteService._extract_transit_details(leg.get("steps", []))
                            
                            legs.append({
                                "from_place": from_name,
                                "to_place": to_name,
                                "distance_meters": distance,
                                "duration_minutes": duration_minutes,
                                "transit_details": transit_details,
                            })
                    
                    # Collect polyline if available
                    if route.get("polyline"):
                        polyline_str = route["polyline"].get("encodedPolyline", "")
                        if polyline_str:
                            all_polylines.append(polyline_str)
            
            return {
                "total_distance_meters": total_distance,
                "total_duration_minutes": total_duration,
                "legs": legs,
                "polyline": all_polylines[0] if all_polylines else None,
                "polyline_segments": all_polylines,
                "waypoints": waypoints,
            }
        
        except Exception as e:
            print(f"⚠️ Route calculation error: {e}")
            return None

    @staticmethod
    def _extract_transit_details(steps: List[Dict]) -> Optional[Dict]:
        """Extract transit line and stop details from a Google Routes leg."""
        if not steps:
            return None

        segments = []
        for step in steps:
            transit_details = step.get("transitDetails") or step.get("transit_details")
            if not transit_details:
                continue

            transit_line = transit_details.get("transitLine", {})
            departure_stop = (
                transit_details.get("departureStop")
                or step.get("departureStop")
                or {}
            )
            arrival_stop = (
                transit_details.get("arrivalStop")
                or step.get("arrivalStop")
                or {}
            )
            vehicle = transit_line.get("vehicle", {})

            line_name = (
                transit_line.get("nameShort")
                or transit_line.get("name")
                or transit_line.get("shortName")
                or transit_line.get("nameShortText")
                or vehicle.get("name")
                or "Transit"
            )

            departure_stop_name = departure_stop.get("name") if isinstance(departure_stop, dict) else str(departure_stop)
            arrival_stop_name = arrival_stop.get("name") if isinstance(arrival_stop, dict) else str(arrival_stop)

            segments.append({
                "line_name": line_name,
                "line_color": transit_line.get("color", "#ef4444"),
                "line_text_color": transit_line.get("textColor", "#ffffff"),
                "vehicle_name": vehicle.get("name", "Transit"),
                "vehicle_type": vehicle.get("type", ""),
                "departure_stop": departure_stop_name,
                "arrival_stop": arrival_stop_name,
                "headsign": transit_details.get("headsign", ""),
            })

        if not segments:
            return None

        first_segment = segments[0]
        last_segment = segments[-1]
        return {
            "summary": first_segment["line_name"],
            "line_color": first_segment["line_color"],
            "line_text_color": first_segment["line_text_color"],
            "segments": segments,
            "departure_stop": first_segment.get("departure_stop", ""),
            "arrival_stop": last_segment.get("arrival_stop", ""),
        }
