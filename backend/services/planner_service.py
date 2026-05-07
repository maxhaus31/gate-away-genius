"""
Planner Service: Core logic for layover verdict calculation

Migrated from src/lib/gateaway-data.ts
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from models import PlannerInput, PlannerOutput, TimelineSegment, Suggestion, AirportInfo, BufferBreakdown
from services.gemini_ai import GeminiActivityService
from services.google_maps import GoogleMapsService


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


async def generate_plan(input_data: PlannerInput) -> Optional[PlannerOutput]:
    """
    Generate layover plan based on flight info and passport
    
    Args:
        input_data: PlannerInput with arrival/departure times, airport, passport, optional flight number
    
    Returns:
        PlannerOutput with verdict, timeline, suggestions, etc.
    """
    
    # Support all airports now
    airport_config = AIRPORTS_CONFIG.get(input_data.airport_code)
    if not airport_config:
        raise ValueError(f"Airport {input_data.airport_code} not supported")
    
    # Calculate total available time
    total_minutes = calculate_minutes_between(input_data.arrival_time, input_data.departure_time)
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
    
    # Get activity recommendations from Gemini
    gemini_activities = []
    reachable_activities = []
    
    try:
        gemini_service = GeminiActivityService()
        gemini_activities = gemini_service.generate_activities(
            airport_city=airport_config["city"],
            available_minutes=city_time_minutes,
            passport_region=input_data.passport_region,
            airport_iata=input_data.airport_code,
        )
        
        print(f"✈️ Got {len(gemini_activities)} activity suggestions from Gemini")
        
        # Validate activities with Google Maps - get real transit times
        for activity in gemini_activities:
            coords = f"{activity['latitude']},{activity['longitude']}"
            round_trip_minutes = await GoogleMapsService.get_round_trip_duration(
                input_data.airport_code,
                coords
            )
            
            # If Google Maps call failed, use Gemini's time estimate
            if round_trip_minutes is None:
                print(f"⚠️ Could not verify travel time for {activity['title']}, using Gemini estimate")
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
        
        print(f"✅ {len(reachable_activities)} activities are reachable")
        
    except Exception as e:
        print(f"⚠️ Gemini activity generation failed: {e}. Using fallback.")
        gemini_activities = []
    
    # Build suggestions from reachable activities or fallback
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
    
    # Generate witty verdict copy from Gemini
    headline = ""
    try:
        gemini_service = GeminiActivityService()
        headline = gemini_service.generate_verdict_copy(
            verdict=verdict,
            available_minutes=city_time_minutes,
            airport_city=airport_config["city"],
            activities=gemini_activities[:2] if gemini_activities else [],
        )
    except Exception as e:
        print(f"⚠️ Gemini copy generation failed: {e}")
        headline = self._fallback_headline(verdict, city_time_minutes, airport_config["city"])
    
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
    
    return PlannerOutput(
        verdict=verdict,
        verdict_description=message,
        headline=headline,
        timeline=timeline_segments,
        total_minutes=total_minutes,
        buffer_minutes=buffer_total,
        usable_minutes=usable_minutes,
        available_time_minutes=available_time_minutes,
        city_time_minutes=city_time_minutes,
        airport=airport_info,
        suggestions=suggestions_list,
        immigration_buffer=immigration_buffer,
        safety_buffer_breakdown=safety_buffer_dict,
        buffer_breakdown=buffer_breakdown_list,
    )


def _fallback_headline(verdict: str, minutes: int, city: str) -> str:
    """Fallback headline if Gemini fails"""
    if verdict == "safe":
        return f"You've got {minutes} solid minutes in {city}. Time to explore!"
    elif verdict == "tight":
        return f"Possible, but you'll need to move fast in {city}."
    else:
        return f"Play it safe and stay at the airport."
