"""
Planner Service: Core logic for layover verdict calculation

Migrated from src/lib/gateaway-data.ts
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from models import PlannerInput, PlannerOutput, TimelineSegment, Suggestion, AirportInfo, BufferBreakdown, ActivityStep, ActivityItinerary, PlaceOption
from services.gemini_ai import GeminiActivityService
from services.google_maps import GoogleMapsService
from services.places_service import PlacesService
from services.schiphol_api import SchipholService
from services.unsplash import UnsplashService
from services import cache_service

# Security limit: Max Google Maps API calls per plan generation
# Each activity can use 1 call, set this to prevent budget overruns
MAX_GOOGLE_MAPS_CALLS = 10


# Airport configuration (migrated from frontend)
AIRPORTS_CONFIG = {
    "LIS": {
        "city": "Lisbon",
        "name": "Humberto Delgado",
        "country": "Portugal",
        "flag": "🇵🇹",
        "transport_to_city_min": 35,
        "transport_label": "Metro Red Line → Baixa-Chiado",
        "reentry_security_min": 20,
        "walk_to_gate_min": 10,
        "checkin_cutoff_min": 45,
        "vibe": "tile-lined alleys, pastéis de nata, golden-hour viewpoints",
    },
    "AMS": {
        "city": "Amsterdam",
        "name": "Schiphol",
        "country": "Netherlands",
        "flag": "🇳🇱",
        "transport_to_city_min": 20,
        "transport_label": "Direct train → Centraal (every 10 min)",
        "reentry_security_min": 30,
        "walk_to_gate_min": 10,
        "checkin_cutoff_min": 45,
        "vibe": "canal rings, brown cafés, bikes everywhere",
    },
    "SIN": {
        "city": "Singapore",
        "name": "Changi",
        "country": "Singapore",
        "flag": "🇸🇬",
        "transport_to_city_min": 30,
        "transport_label": "MRT East-West → Marina Bay",
        "reentry_security_min": 25,
        "walk_to_gate_min": 10,
        "checkin_cutoff_min": 45,
        "vibe": "hawker centres, skyline gardens, late-night neon",
    },
}

# Suggestions per airport (migrated from frontend)
SUGGESTIONS_CONFIG = {
    "LIS": [
        {
            "emoji": "🥐",
            "title": "Pastel de Nata at Manteigaria",
            "blurb": "Quick metro hop, one perfect custard tart, back before your gate even opens.",
            "min_time_needed": 60,
        },
        {
            "emoji": "🌅",
            "title": "Miradouro de Santa Catarina",
            "blurb": "Tiled streets, a glass of vinho verde and the best Tagus view in the city.",
            "min_time_needed": 120,
        },
        {
            "emoji": "🚋",
            "title": "Tram 28 + Alfama wander",
            "blurb": "Ride the iconic yellow tram, get lost in Alfama, taste a real bifana.",
            "min_time_needed": 180,
        },
    ],
    "AMS": [
        {
            "emoji": "☕",
            "title": "Coffee on the Singel canal",
            "blurb": "Direct train to Centraal, a flat white by the water, easy turnaround.",
            "min_time_needed": 60,
        },
        {
            "emoji": "🚲",
            "title": "Jordaan stroll + bitterballen",
            "blurb": "Wander the prettiest neighbourhood, snack on something fried and Dutch.",
            "min_time_needed": 120,
        },
        {
            "emoji": "🖼️",
            "title": "Rijksmuseum highlights tour",
            "blurb": "Skip-the-line, see the Vermeer and the Rembrandt, you've earned it.",
            "min_time_needed": 180,
        },
    ],
    "SIN": [
        {
            "emoji": "🌳",
            "title": "Jewel Changi rainforest",
            "blurb": "Don't even leave — the world's tallest indoor waterfall is right here.",
            "min_time_needed": 45,
        },
        {
            "emoji": "🍜",
            "title": "Hawker lunch at Lau Pa Sat",
            "blurb": "MRT downtown, satay and laksa under colonial iron, back in a flash.",
            "min_time_needed": 120,
        },
        {
            "emoji": "🌃",
            "title": "Marina Bay + Gardens skyline",
            "blurb": "Supertrees, the light show, a cocktail 57 floors up. Singapore in one bite.",
            "min_time_needed": 180,
        },
    ],
}


def parse_iso_time(iso_str: str) -> int:
    """Parse ISO 8601 datetime and return minutes since midnight"""
    dt = datetime.fromisoformat(iso_str)
    return dt.hour * 60 + dt.minute


def calculate_minutes_between(arrival_iso: str, departure_iso: str) -> int:
    """Calculate total minutes between arrival and departure"""
    arrival_dt = datetime.fromisoformat(arrival_iso)
    departure_dt = datetime.fromisoformat(departure_iso)
    
    # If departure is before arrival (overnight), add 24 hours
    total_minutes = int((departure_dt - arrival_dt).total_seconds() / 60)
    if total_minutes <= 0:
        total_minutes += 24 * 60
    
    return total_minutes


def get_immigration_buffer(passport_region: str, airport_code: str) -> int:
    """Calculate immigration buffer based on passport and airport"""
    if passport_region == "EU" and airport_code in ["LIS", "AMS"]:
        return 0
    elif passport_region == "OTHER":
        return 15
    else:  # US
        return 5


def format_duration(minutes: int) -> str:
    """Format minutes as human-readable duration"""
    if minutes <= 0:
        return "0 min"
    h = minutes // 60
    m = minutes % 60
    if h == 0:
        return f"{m} min"
    if m == 0:
        return f"{h}h"
    return f"{h}h {m}min"


def get_suggestions_for_city_time(airport_code: str, city_time_minutes: int) -> List[Suggestion]:
    """Get suggestions that fit within available city time"""
    suggestions = SUGGESTIONS_CONFIG.get(airport_code, [])
    
    # Filter suggestions that fit in available time (with 15 min buffer)
    fitting = [s for s in suggestions if s["min_time_needed"] <= city_time_minutes + 15]
    
    # Return up to 3, or if none fit, return first suggestion
    if fitting:
        candidates = fitting[-3:] if len(fitting) >= 3 else fitting
    else:
        candidates = suggestions[0:1]
    
    return [
        Suggestion(
            emoji=s["emoji"],
            title=s["title"],
            blurb=s["blurb"],
            minTimeNeeded=s["min_time_needed"],
        )
        for s in candidates
    ]


async def get_place_options_with_photos(airport_code: str, city_time_minutes: int) -> List[PlaceOption]:
    """
    Get fallback place options with photos from Unsplash API
    Follows Unsplash API guidelines for attribution and download tracking
    """
    place_options_data = {
        "LIS": [
            {"name": "Praça do Comércio", "description": "Historic riverside plaza with stunning views.", "search_query": "lisbon plaza"},
            {"name": "Pastéis de Nata at Manteigaria", "description": "Famous pastry shop - don't miss the original custard tart.", "search_query": "portuguese pastry"},
            {"name": "Miradouro de Santa Catarina", "description": "Best viewpoint for sunset and the Tagus river.", "search_query": "lisbon viewpoint"},
            {"name": "Tram 28", "description": "Iconic yellow tram through the historic Alfama district.", "search_query": "lisbon tram"},
            {"name": "Café Majestic", "description": "Historic café with Belle Époque elegance and great coffee.", "search_query": "portuguese cafe"},
        ],
        "AMS": [
            {"name": "Amsterdam Canals", "description": "UNESCO-listed canal ring - quintessential Amsterdam.", "search_query": "amsterdam canal"},
            {"name": "Rijksmuseum", "description": "World-class art museum - home to masterpieces.", "search_query": "museum art"},
            {"name": "Jordaan District", "description": "Charming neighborhood with galleries, cafés, and antique shops.", "search_query": "amsterdam neighborhood"},
            {"name": "Anne Frank House", "description": "Moving historical museum - book ahead online.", "search_query": "amsterdam history"},
            {"name": "Bitterballen & Brown Café", "description": "Traditional Dutch snack in a cozy local pub.", "search_query": "dutch food"},
        ],
        "SIN": [
            {"name": "Gardens by the Bay", "description": "Futuristic supertrees and enchanting light show.", "search_query": "singapore gardens"},
            {"name": "Jewel Changi - Waterfall", "description": "World's tallest indoor waterfall - don't miss it!", "search_query": "waterfall"},
            {"name": "Hawker Chan - Chicken Rice", "description": "Michelin-starred street food - legend in a stall.", "search_query": "singapore food"},
            {"name": "Marina Bay Sands Observation Deck", "description": "57th floor views over the entire skyline.", "search_query": "singapore skyline"},
            {"name": "Orchard Road Shopping", "description": "Luxury and local brands on Singapore's main drag.", "search_query": "shopping"},
        ],
    }
    
    places = place_options_data.get(airport_code, [])
    
    # Filter places that fit in available time
    fitting_places = [
        p for p in places 
        if city_time_minutes >= 75  # Most activities need at least 75 min
    ]
    
    if not fitting_places:
        fitting_places = places
    
    # Fetch photos from Unsplash for each place
    result = []
    for place in fitting_places[:5]:
        # Search Unsplash for photos of this place
        photos = await UnsplashService.search_photos(
            query=place["search_query"],
            per_page=1  # Get the top photo
        )
        
        if photos:
            photo = photos[0]
            result.append(PlaceOption(
                place_id=f"fallback_{place['name'].replace(' ', '_').lower()}",
                name=place["name"],
                description=place["description"],
                rating=4.5,  # Fallback rating
                user_ratings_total=0,
                coordinates="0,0",
                address="",
                types=["point_of_interest"],
                photo_url=photo["url"],  # Hotlinked Unsplash photo
                photographer_name=photo["photographer"],
                photographer_url=photo["photographer_url"],
                unsplash_url=photo["unsplash_url"],
                download_location=photo["download_location"],
            ))
        else:
            # Fallback without photo if Unsplash fails
            result.append(PlaceOption(
                place_id=f"fallback_{place['name'].replace(' ', '_').lower()}",
                name=place["name"],
                description=place["description"],
                rating=4.5,
                user_ratings_total=0,
                coordinates="0,0",
                address="",
                types=["point_of_interest"],
            ))
    
    return result


async def generate_plan(input_data: PlannerInput) -> Optional[PlannerOutput]:
    """
    Generate layover plan based on flight info and passport
    
    Args:
        input_data: PlannerInput with inbound/outbound flight numbers, airport, passport

    Returns:
        PlannerOutput with verdict, timeline, suggestions, etc.
    """

    # Support all airports now
    airport_config = AIRPORTS_CONFIG.get(input_data.airport_code)
    if not airport_config:
        raise ValueError(f"Airport {input_data.airport_code} not supported")

    # Resolve full ISO datetimes from Schiphol — flight_date is only used for the
    # API query (defaults to today inside SchipholService); all downstream calculations
    # use the complete datetime strings returned here, not just the time component.
    inbound = await SchipholService.get_flight(input_data.inbound_flight, input_data.flight_date)
    arrival_time = inbound.get("scheduled_arrival")

    outbound = await SchipholService.get_flight(input_data.outbound_flight, input_data.flight_date)
    departure_time = outbound.get("scheduled_departure")

    if not arrival_time or not departure_time:
        raise ValueError("Could not resolve flight times — check flight numbers and date")

    # Cache check — skip all API calls if we have a recent result for this window
    cache_key = cache_service.make_key(
        input_data.airport_code,
        input_data.passport_region,
        input_data.transport_mode,
        arrival_time,
        departure_time,
    )
    cached = cache_service.get(cache_key)
    if cached:
        print(f"OK: Cache hit [{cache_key}]")
        return PlannerOutput(**cached)

    # Calculate total available time
    total_minutes = calculate_minutes_between(arrival_time, departure_time)
    if total_minutes <= 0:
        raise ValueError("Departure time must be after arrival time")
    
    # Calculate immigration buffer
    immigration_buffer = get_immigration_buffer(input_data.passport_region, input_data.airport_code)
    
    # Build buffer breakdown
    buffer_breakdown = [
        {"label": "Disembark + immigration", "minutes": 25 + immigration_buffer},
        {"label": f"Re-entry security ({airport_config['city']})", "minutes": airport_config["reentry_security_min"]},
        {"label": "Walk to gate", "minutes": airport_config["walk_to_gate_min"]},
        {"label": "Check-in / boarding cutoff", "minutes": airport_config["checkin_cutoff_min"]},
    ]
    
    buffer_total = sum(b["minutes"] for b in buffer_breakdown)
    usable_minutes = max(0, total_minutes - buffer_total)
    
    # Calculate city time (usable minus round-trip transport)
    round_trip_transport = airport_config["transport_to_city_min"] * 2
    city_time_minutes = max(0, usable_minutes - round_trip_transport)
    available_time_minutes = usable_minutes
    
    # Determine base verdict based on time available
    if usable_minutes < round_trip_transport + 30:
        verdict = "stay"
    elif city_time_minutes < 75:
        verdict = "tight"
    else:
        verdict = "safe"
    
    # Get activity recommendations
    place_options: List[PlaceOption] = []
    suggestions_list: List[Suggestion] = []
    
    # Try Places API first, fall back to Gemini if not available
    try:
        # Get popular attractions using Places API
        places = await PlacesService.find_attractions(
            airport_code=input_data.airport_code,
            available_minutes=city_time_minutes,
            transport_mode=input_data.transport_mode,
            max_places=5
        )
        
        if places:
            print(f"INFO: Found {len(places)} top places to visit")
            
            # Check if we can reach these places within available time
            maps_call_count = 0
            for place in places:
                # Check if we can reach this place within available time
                if maps_call_count < MAX_GOOGLE_MAPS_CALLS:
                    round_trip_minutes = await GoogleMapsService.get_round_trip_duration(
                        input_data.airport_code,
                        place["coordinates"],
                        mode=input_data.transport_mode
                    )
                    maps_call_count += 1
                else:
                    print(f"WARNING: Google Maps API limit reached")
                    round_trip_minutes = None
                
                # If we can't calculate real time, estimate it
                if round_trip_minutes is None:
                    round_trip_minutes = 60  # Fallback estimate
                
                # Only add if reachable (at least 15 min to spend there)
                if city_time_minutes - round_trip_minutes >= 15:
                    place_options.append(PlaceOption(
                        place_id=place.get("place_id", "unknown"),
                        name=place["name"],
                        description=place.get("description", f"{place['name']} - {place['rating']}/5 stars"),
                        rating=place["rating"],
                        user_ratings_total=place["user_ratings_total"],
                        coordinates=place["coordinates"],
                        address=place["address"],
                        types=place["types"],
                        photo_url=place.get("photo_url"),
                    ))
            
            print(f"OK: {len(place_options)} places are reachable")
            
            # Build suggestions from top places
            if place_options:
                suggestions_list = [
                    Suggestion(
                        emoji="⭐",
                        title=p.name,
                        blurb=p.description,
                        minTimeNeeded=45,
                    )
                    for p in place_options[:3]
                ]
        else:
            print("WARNING: No places found via Places API, using Gemini fallback")
            raise Exception("Places API returned no results")
    
    except Exception as e:
        print(f"WARNING: Places API unavailable: {e}. Using Gemini activity generation.")
        place_options = []
        
        # Fallback to Gemini-based activity generation
        try:
            gemini_service = GeminiActivityService()
            gemini_activities = gemini_service.generate_activities(
                airport_city=airport_config["city"],
                available_minutes=city_time_minutes,
                passport_region=input_data.passport_region,
                airport_iata=input_data.airport_code,
            )
            
            print(f"INFO: Got {len(gemini_activities)} activity suggestions from Gemini")
            
            # Validate activities with Google Maps - get real transit times
            maps_call_count = 0
            reachable_activities = []
            
            for activity in gemini_activities:
                coords = f"{activity['latitude']},{activity['longitude']}"
                round_trip_minutes = None
                
                # Only call Google Maps if we haven't hit the limit
                if maps_call_count < MAX_GOOGLE_MAPS_CALLS:
                    round_trip_minutes = await GoogleMapsService.get_round_trip_duration(
                        input_data.airport_code,
                        coords,
                        mode=input_data.transport_mode
                    )
                    maps_call_count += 1
                else:
                    print(f"WARNING: Google Maps API limit ({MAX_GOOGLE_MAPS_CALLS}) reached")
                
                # If Google Maps call failed or skipped, use Gemini's time estimate
                if round_trip_minutes is None:
                    print(f"WARNING: Could not verify travel time for {activity['title']}, using Gemini estimate")
                    round_trip_minutes = activity.get("minTimeNeeded", 60)
                
                # Check if activity is reachable
                actual_activity_time = city_time_minutes - round_trip_minutes
                if actual_activity_time >= 15:  # At least 15 minutes to do the activity
                    reachable_activities.append({
                        "emoji": activity["emoji"],
                        "title": activity["title"],
                        "blurb": activity["description"],
                        "minTimeNeeded": activity.get("minTimeNeeded", round_trip_minutes - 20),
                        "roundTripMinutes": round_trip_minutes,
                        "coordinates": coords,
                    })
            
            print(f"OK: {len(reachable_activities)} activities are reachable")
            
            # Build suggestions from reachable activities
            if reachable_activities:
                suggestions_list = [
                    Suggestion(
                        emoji=a["emoji"],
                        title=a["title"],
                        blurb=a["blurb"],
                        minTimeNeeded=a["minTimeNeeded"],
                    )
                    for a in reachable_activities[:3]
                ]
            else:
                suggestions_list = get_suggestions_for_city_time(input_data.airport_code, city_time_minutes)
        
        except Exception as gemini_error:
            print(f"WARNING: Gemini also failed: {gemini_error}")
            suggestions_list = get_suggestions_for_city_time(input_data.airport_code, city_time_minutes)
    
    # If place_options is still empty, use fallback with photos
    if not place_options:
        print(f"INFO: Using fallback places with photos from Unsplash")
        place_options = await get_place_options_with_photos(input_data.airport_code, city_time_minutes)
    
    # Generate witty verdict copy from Gemini
    headline = ""
    try:
        gemini_service = GeminiActivityService()
        # Convert place options to activity format for verdict generation
        activities_for_verdict = [
            {"title": p.name, "description": p.description}
            for p in place_options[:2]
        ] if place_options else []
        headline = gemini_service.generate_verdict_copy(
            verdict=verdict,
            available_minutes=city_time_minutes,
            airport_city=airport_config["city"],
            activities=activities_for_verdict,
        )
    except Exception as e:
        print(f"WARNING: Gemini copy generation failed: {e}")
        headline = _fallback_headline(verdict, city_time_minutes, airport_config["city"])
    
    # Create verdict message
    if verdict == "stay":
        message = f"By the time you cleared immigration and rode into {airport_config['city']}, you'd be turning right back around. Grab a proper meal in the terminal — {airport_config['name']} is genuinely nice — and save the city for the next layover."
    elif verdict == "tight":
        message = f"You've got about {format_duration(city_time_minutes)} on the ground. Enough for one good thing, not three. Set an alarm for the turnaround and keep it tight."
    else:  # safe
        vibe_first_part = airport_config["vibe"].split(",")[0].strip()
        message = f"Plenty of room to {vibe_first_part} and still be back at your gate without a sprint. Go."
    
    # Build timeline segments
    timeline_segments = []
    
    timeline_segments.append(
        TimelineSegment(
            label="Disembark + immigration",
            duration_minutes=25 + immigration_buffer,
            color="red",
        )
    )
    
    if verdict != "stay":
        timeline_segments.append(
            TimelineSegment(
                label=f"Travel to city ({format_duration(airport_config['transport_to_city_min'])})",
                duration_minutes=airport_config["transport_to_city_min"],
                color="blue",
            )
        )
        
        timeline_segments.append(
            TimelineSegment(
                label="Activity time",
                duration_minutes=city_time_minutes,
                color="green",
            )
        )
        
        timeline_segments.append(
            TimelineSegment(
                label=f"Travel back ({format_duration(airport_config['transport_to_city_min'])})",
                duration_minutes=airport_config["transport_to_city_min"],
                color="blue",
            )
        )
    
    timeline_segments.append(
        TimelineSegment(
            label="Re-entry security + buffer",
            duration_minutes=airport_config["reentry_security_min"] + airport_config["walk_to_gate_min"] + airport_config["checkin_cutoff_min"],
            color="orange",
        )
    )
    
    # Build safety buffer breakdown dict
    safety_buffer_dict = {}
    for item in buffer_breakdown:
        key = item["label"].lower().replace(" ", "_").replace("+", "and").replace("(", "").replace(")", "")
        safety_buffer_dict[key] = item["minutes"]
    
    # Create airport info object
    airport_info = AirportInfo(
        code=input_data.airport_code,
        city=airport_config["city"],
        name=airport_config["name"],
        country=airport_config["country"],
        flag=airport_config["flag"],
        transportToCityMin=airport_config["transport_to_city_min"],
        transportLabel=airport_config["transport_label"],
        reentrySecurityMin=airport_config["reentry_security_min"],
        walkToGateMin=airport_config["walk_to_gate_min"],
        checkinCutoffMin=airport_config["checkin_cutoff_min"],
        vibe=airport_config["vibe"],
    )
    
    # Convert buffer breakdown list
    buffer_breakdown_list = [
        BufferBreakdown(label=b["label"], minutes=b["minutes"])
        for b in buffer_breakdown
    ]
    
    # Build detailed activity itinerary for visualization
    itinerary_steps = []
    
    # Step 1: Start at airport (disembark + immigration)
    itinerary_steps.append(
        ActivityStep(
            type="airport",
            emoji="✈️",
            title=f"{airport_config['name']} (Arrive)",
            duration_minutes=25 + immigration_buffer,
        )
    )
    
    if verdict != "stay" and suggestions_list:
        # Step 2: Travel to first activity
        first_activity_travel = airport_config["transport_to_city_min"]
        itinerary_steps.append(
            ActivityStep(
                type="travel",
                emoji="🚌",
                title=airport_config["transport_label"],
                duration_minutes=first_activity_travel,
            )
        )
        
        # Step 3+: Each activity with travel time between them
        for i, activity in enumerate(suggestions_list[:3]):
            itinerary_steps.append(
                ActivityStep(
                    type="activity",
                    emoji=activity.emoji,
                    title=activity.title,
                    duration_minutes=activity.minTimeNeeded,
                    coordinates=None,  # Could add coordinates if we have them
                )
            )
            
            # Add travel time to next activity or back to airport (except for last one)
            if i < len(suggestions_list) - 1:
                itinerary_steps.append(
                    ActivityStep(
                        type="travel",
                        emoji="🚶",
                        title="Travel between activities",
                        duration_minutes=15,  # Estimated inter-city travel
                    )
                )
        
        # Step N: Travel back to airport
        itinerary_steps.append(
            ActivityStep(
                type="travel",
                emoji="🚌",
                title=f"Return to {airport_config['name']}",
                duration_minutes=airport_config["transport_to_city_min"],
            )
        )
    
    # Step N+1: Final airport buffer (security + boarding)
    itinerary_steps.append(
        ActivityStep(
            type="airport",
            emoji="🛂",
            title="Security + Gate",
            duration_minutes=airport_config["reentry_security_min"] + airport_config["walk_to_gate_min"] + airport_config["checkin_cutoff_min"],
        )
    )
    
    activity_itinerary = ActivityItinerary(steps=itinerary_steps)
    
    result = PlannerOutput(
        verdict=verdict,
        verdict_description=message,
        headline=headline,
        timeline=timeline_segments,
        activity_itinerary=activity_itinerary,
        total_minutes=total_minutes,
        buffer_minutes=buffer_total,
        usable_minutes=usable_minutes,
        available_time_minutes=available_time_minutes,
        city_time_minutes=city_time_minutes,
        airport=airport_info,
        suggestions=suggestions_list,
        place_options=place_options,
        immigration_buffer=immigration_buffer,
        safety_buffer_breakdown=safety_buffer_dict,
        buffer_breakdown=buffer_breakdown_list,
    )

    cache_service.set(cache_key, result.model_dump())
    print(f"CACHE: Cached result [{cache_key}]")
    return result


def _fallback_headline(verdict: str, minutes: int, city: str) -> str:
    """Fallback headline if Gemini fails"""
    if verdict == "safe":
        return f"You've got {minutes} solid minutes in {city}. Time to explore!"
    elif verdict == "tight":
        return f"Possible, but you'll need to move fast in {city}."
    else:
        return f"Play it safe and stay at the airport."
