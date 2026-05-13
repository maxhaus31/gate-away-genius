"""
Route Service: Calculate multi-stop routes using Google Maps Directions API
"""

import httpx
from config import GOOGLE_MAPS_API_KEY
from typing import Optional, Dict, List
from datetime import datetime, timezone


class RouteService:
    """Service to calculate routes between multiple waypoints"""
    
    BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    DISTANCE_MATRIX_BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
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
                
                leg_result = await RouteService._fetch_routes_leg(
                    from_lat=from_lat,
                    from_lng=from_lng,
                    to_lat=to_lat,
                    to_lng=to_lng,
                    mode=mode,
                    leg_index=i,
                )

                if leg_result is None:
                    leg_result = await RouteService._fetch_distance_matrix_leg(
                        from_lat=from_lat,
                        from_lng=from_lng,
                        to_lat=to_lat,
                        to_lng=to_lng,
                        mode=mode,
                        leg_index=i,
                    )

                if leg_result is None:
                    print(f"⚠️ No live travel time found for leg {i}: {from_name} → {to_name}")
                    continue

                distance = leg_result.get("distance_meters", 0)
                duration_minutes = leg_result.get("duration_minutes", 0)
                transit_details = leg_result.get("transit_details")
                polyline_str = leg_result.get("polyline")

                total_distance += distance
                total_duration += duration_minutes

                legs.append({
                    "from_place": from_name,
                    "to_place": to_name,
                    "distance_meters": distance,
                    "duration_minutes": duration_minutes,
                    "transit_details": transit_details,
                    "source": leg_result.get("source", "routes"),
                })

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
    async def _fetch_routes_leg(
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        mode: str,
        leg_index: int,
    ) -> Optional[Dict]:
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
            "travelMode": "TRANSIT" if mode == "transit" else "DRIVE",
        }

        if mode == "transit":
            body["departureTime"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        else:
            body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.legs.duration,routes.legs.distanceMeters,routes.legs.steps.navigationInstruction,routes.legs.steps.transitDetails,routes.legs.steps.transitDetails.stopDetails,routes.legs.steps.transitDetails.stopDetails.arrivalStop,routes.legs.steps.transitDetails.stopDetails.departureStop,routes.legs.steps.transitDetails.stopDetails.arrivalTime,routes.legs.steps.transitDetails.stopDetails.departureTime,routes.legs.steps.transitDetails.transitLine,routes.legs.steps.transitDetails.headsign,routes.legs.steps.transitDetails.tripShortText,routes.polyline.encodedPolyline",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                RouteService.BASE_URL,
                json=body,
                headers=headers,
                timeout=RouteService.TIMEOUT,
            )

        if not response.is_success:
            print(
                f"⚠️ Google Routes error for leg {leg_index}: {response.status_code} "
                f"{response.text[:300]}"
            )
            return None

        data = response.json()
        routes = data.get("routes") or []
        if not routes:
            print(f"⚠️ Google Routes returned no routes for leg {leg_index}: keys={list(data.keys())}")
            return None

        route = routes[0]
        route_legs = route.get("legs") or []
        if not route_legs:
            print(f"⚠️ Google Routes returned no legs for leg {leg_index}")
            return None

        first_leg = route_legs[0]
        duration_seconds = RouteService._parse_duration_seconds(first_leg.get("duration"))
        distance_meters = int(first_leg.get("distanceMeters", 0) or 0)
        transit_details = RouteService._extract_transit_details(first_leg.get("steps", []))
        polyline_str = (route.get("polyline") or {}).get("encodedPolyline", "")

        return {
            "distance_meters": distance_meters,
            "duration_minutes": max(1, duration_seconds // 60) if duration_seconds else 0,
            "transit_details": transit_details,
            "polyline": polyline_str or None,
            "source": "routes",
        }

    @staticmethod
    async def _fetch_distance_matrix_leg(
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        mode: str,
        leg_index: int,
    ) -> Optional[Dict]:
        params = {
            "origins": f"{from_lat},{from_lng}",
            "destinations": f"{to_lat},{to_lng}",
            "mode": mode,
            "key": GOOGLE_MAPS_API_KEY,
            "units": "metric",
        }

        if mode == "transit":
            params["departure_time"] = "now"
            params["transit_routing_preference"] = "less_walking"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                RouteService.DISTANCE_MATRIX_BASE_URL,
                params=params,
                timeout=RouteService.TIMEOUT,
            )

        if not response.is_success:
            print(
                f"⚠️ Distance Matrix error for leg {leg_index}: {response.status_code} "
                f"{response.text[:300]}"
            )
            return None

        data = response.json()
        rows = data.get("rows") or []
        if not rows:
            print(f"⚠️ Distance Matrix returned no rows for leg {leg_index}")
            return None

        elements = rows[0].get("elements") or []
        if not elements:
            print(f"⚠️ Distance Matrix returned no elements for leg {leg_index}")
            return None

        element = elements[0]
        if element.get("status") != "OK":
            print(f"⚠️ Distance Matrix element status for leg {leg_index}: {element.get('status')}")
            return None

        duration = (element.get("duration") or {}).get("value", 0)
        distance = (element.get("distance") or {}).get("value", 0)

        return {
            "distance_meters": int(distance or 0),
            "duration_minutes": max(1, int(duration // 60)) if duration else 0,
            "transit_details": None,
            "polyline": None,
            "source": "distance_matrix",
        }

    @staticmethod
    def _parse_duration_seconds(duration_value: Optional[str]) -> int:
        if not duration_value:
            return 0
        if isinstance(duration_value, (int, float)):
            return int(duration_value)
        duration_text = str(duration_value).strip()
        if duration_text.endswith("s"):
            duration_text = duration_text[:-1]
        try:
            return int(float(duration_text))
        except ValueError:
            return 0

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
            stop_details = transit_details.get("stopDetails") or {}
            departure_stop = stop_details.get("departureStop") or step.get("departureStop") or {}
            arrival_stop = stop_details.get("arrivalStop") or step.get("arrivalStop") or {}
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
