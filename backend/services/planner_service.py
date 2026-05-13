"""
Planner Service: Step 1 — layover verdict from flight numbers and passport type.

Step 1 returns: flight overview, buffer breakdown, usable minutes, verdict, persona list.
Step 3 (activity planning) functions are preserved below but flagged.
"""

from typing import Optional, List
from datetime import datetime
from models import (
    PlannerInput, PlannerOutput,
    FlightOverview, InboundFlightInfo, OutboundFlightInfo,
    BufferBreakdown, Persona,
    # ACTIVITY PLANNING — imports below not needed until Step 3
    Suggestion, PlaceOption, TimelineSegment, ActivityStep, ActivityItinerary, AirportInfo,
)
from services.airport_data import (
    AMS_EXIT_TIME_BY_PIER, EXIT_TIME_FALLBACK_MIN,
    AIRPORT_CONFIG, CHECKIN_CUTOFF_BY_PASSPORT,
)
from services.schiphol_api import SchipholService
from services.aerodatabox_api import AeroDataBoxService
from services import cache_service  # ACTIVITY PLANNING — cache not called in Step 1; re-enable in Step 3

# ACTIVITY PLANNING — imports below not needed until Step 3
from services.gemini_ai import GeminiActivityService
from services.google_maps import GoogleMapsService
from services.places_service import PlacesService
from services.unsplash import UnsplashService

# ACTIVITY PLANNING — not needed until Step 3
MAX_GOOGLE_MAPS_CALLS = 10

# ACTIVITY PLANNING — city/transport/vibe fields below are needed for Step 3 activity
# planning. The Step 1 buffer fields (reentry_security_min, walk_to_gate_min,
# checkin_cutoff_min) have been extracted to airport_data.py to avoid duplication.
AIRPORTS_CONFIG = {
    "LIS": {
        "city": "Lisbon",
        "name": "Humberto Delgado",
        "country": "Portugal",
        "flag": "🇵🇹",
        "transport_to_city_min": 35,
        "transport_label": "Metro Red Line → Baixa-Chiado",
        "vibe": "tile-lined alleys, pastéis de nata, golden-hour viewpoints",
        # reentry_security_min, walk_to_gate_min, checkin_cutoff_min → see airport_data.py
    },
    "AMS": {
        "city": "Amsterdam",
        "name": "Schiphol",
        "country": "Netherlands",
        "flag": "🇳🇱",
        "transport_to_city_min": 20,
        "transport_label": "Direct train → Centraal (every 10 min)",
        "vibe": "canal rings, brown cafés, bikes everywhere",
        # reentry_security_min, walk_to_gate_min, checkin_cutoff_min → see airport_data.py
    },
    "SIN": {
        "city": "Singapore",
        "name": "Changi",
        "country": "Singapore",
        "flag": "🇸🇬",
        "transport_to_city_min": 30,
        "transport_label": "MRT East-West → Marina Bay",
        "vibe": "hawker centres, skyline gardens, late-night neon",
        # reentry_security_min, walk_to_gate_min, checkin_cutoff_min → see airport_data.py
    },
}

# ACTIVITY PLANNING — not needed until Step 3
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

# Personas returned with every verdict — user selects one before Step 3
PERSONAS: List[Persona] = [
    Persona(
        key="food_lover",
        label="Food Lover",
        description="Travels to discover local cuisine, cafés, markets, and memorable dining experiences.",
    ),
    Persona(
        key="culture_seeker",
        label="Culture Seeker",
        description="Enjoys museums, history, traditions, architecture, and authentic local experiences.",
    ),
    Persona(
        key="nature_wanderer",
        label="Nature Wanderer",
        description="Prefers outdoor adventures, scenic landscapes, and peaceful escapes in nature.",
    ),
    Persona(
        key="checklist_traveler",
        label="Checklist Traveler",
        description="Focuses on visiting iconic landmarks and must-see attractions efficiently.",
    ),
]


def calculate_minutes_between(arrival_iso: str, departure_iso: str) -> int:
    """Calculate total minutes between two ISO 8601 datetimes."""
    arrival_dt   = datetime.fromisoformat(arrival_iso)
    departure_dt = datetime.fromisoformat(departure_iso)
    total_minutes = int((departure_dt - arrival_dt).total_seconds() / 60)
    if total_minutes <= 0:
        total_minutes += 24 * 60  # handle overnight layovers
    return total_minutes


async def _get_flight(
    flight_number: str,
    date: Optional[str],
    airport_code: str,
    direction: str,
) -> dict:
    """Route flight lookup to Schiphol (AMS) or AeroDataBox (LIS/SIN)."""
    if airport_code == "AMS":
        return await SchipholService.get_flight(flight_number, date)
    else:
        return await AeroDataBoxService.get_flight(flight_number, date, airport_code, direction)


async def generate_plan(input_data: PlannerInput) -> Optional[PlannerOutput]:
    """
    Step 1: Build flight overview and layover verdict.

    Routes to Schiphol (AMS) or AeroDataBox (LIS/SIN), computes buffer from
    airport_data constants and live security queue (AMS only), returns verdict
    + persona list.
    """
    airport_cfg = AIRPORT_CONFIG.get(input_data.layover_airport)
    if not airport_cfg:
        raise ValueError(f"Airport {input_data.layover_airport} not supported")

    # ── Flight data ────────────────────────────────────────────────────────────
    inbound_raw  = await _get_flight(
        input_data.inbound_flight, input_data.inbound_date,
        input_data.layover_airport, "inbound",
    )
    outbound_raw = await _get_flight(
        input_data.outbound_flight, input_data.outbound_date,
        input_data.layover_airport, "outbound",
    )

    scheduled_arrival   = inbound_raw.get("scheduled_arrival")
    actual_arrival      = inbound_raw.get("actual_arrival")
    effective_arrival   = actual_arrival or scheduled_arrival  # use actual if available
    scheduled_departure = outbound_raw.get("scheduled_departure")

    if not scheduled_arrival or not scheduled_departure:
        raise ValueError("Could not resolve flight times — check flight numbers and dates")

    # Layover uses actual/estimated arrival to account for inbound delay
    layover_duration_minutes = calculate_minutes_between(effective_arrival, scheduled_departure)
    if layover_duration_minutes <= 0:
        raise ValueError("Departure time must be after arrival time")

    # ── Buffer calculation ─────────────────────────────────────────────────────
    pier = inbound_raw.get("pier", "")
    if input_data.layover_airport == "AMS":
        exit_time_min = AMS_EXIT_TIME_BY_PIER.get(pier.upper(), EXIT_TIME_FALLBACK_MIN)
    else:
        exit_time_min = EXIT_TIME_FALLBACK_MIN

    # Live Schiphol queue for AMS; hardcoded fallback for LIS/SIN
    if input_data.layover_airport == "AMS":
        # Schiphol queue areas map to piers (e.g. "D"), not terminal numbers (e.g. "2")
        outbound_pier = outbound_raw.get("pier") or outbound_raw.get("terminal")
        queue_data = await SchipholService.get_security_queue(outbound_pier)
        security_reentry_min = queue_data.get("queue_minutes", airport_cfg["security_reentry_min_fallback"])
    else:
        security_reentry_min = airport_cfg["security_reentry_min_fallback"]

    walk_to_gate_min   = airport_cfg["walk_to_gate_min"]
    checkin_cutoff_min = CHECKIN_CUTOFF_BY_PASSPORT.get(input_data.passport_type, 75)
    total_buffer_min   = exit_time_min + security_reentry_min + walk_to_gate_min + checkin_cutoff_min

    usable_minutes = max(0, layover_duration_minutes - total_buffer_min)

    transport_to_city_min = airport_cfg.get("transport_to_city_min", 30)
    city_time_preview = max(0, usable_minutes - (transport_to_city_min * 2))
    print(
        f"\n── Layover calculation ──────────────────────────\n"
        f"  Effective arrival:    {effective_arrival}\n"
        f"  Scheduled departure:  {scheduled_departure}\n"
        f"  Total layover:        {layover_duration_minutes} min\n"
        f"  Exit time (pier {pier or '?'}):   {exit_time_min} min\n"
        f"  Security re-entry:    {security_reentry_min} min\n"
        f"  Walk to gate:         {walk_to_gate_min} min\n"
        f"  Check-in cutoff:      {checkin_cutoff_min} min\n"
        f"  Total buffer:         {total_buffer_min} min\n"
        f"  Usable:               {usable_minutes} min\n"
        f"  Transport (×2):       {transport_to_city_min * 2} min\n"
        f"  Yours in the city:    {city_time_preview} min\n"
        f"────────────────────────────────────────────────\n"
    )

    # ── Verdict ────────────────────────────────────────────────────────────────
    if usable_minutes <= 0:
        verdict = "not_possible"
    elif usable_minutes < 75:
        verdict = "tight"
    else:
        verdict = "safe"

    # ── Build response ─────────────────────────────────────────────────────────
    inbound_info = InboundFlightInfo(
        flight_number=inbound_raw.get("flight_number", input_data.inbound_flight),
        date=inbound_raw.get("date", ""),
        scheduled_arrival=scheduled_arrival,
        actual_arrival=actual_arrival,
        delay_minutes=inbound_raw.get("delay_minutes", 0),
        status=inbound_raw.get("status", "unknown"),
        terminal=inbound_raw.get("terminal", ""),
        pier=pier,
    )

    outbound_info = OutboundFlightInfo(
        flight_number=outbound_raw.get("flight_number", input_data.outbound_flight),
        date=outbound_raw.get("date", ""),
        scheduled_departure=scheduled_departure,
        status=outbound_raw.get("status", "unknown"),
        terminal=outbound_raw.get("terminal", ""),
        pier=outbound_raw.get("pier", ""),
    )

    # ── City time (transport_to_city × 2 subtracted from usable minutes) ──────
    transport_to_city_min = airport_cfg.get("transport_to_city_min", 30)
    city_time_minutes = max(0, usable_minutes - (transport_to_city_min * 2))

    # ── Place options ──────────────────────────────────────────────────────────
    place_options = await get_place_options_with_photos(input_data.layover_airport, city_time_minutes)

    return PlannerOutput(
        flight_overview=FlightOverview(
            inbound=inbound_info,
            outbound=outbound_info,
            total_layover_minutes=layover_duration_minutes,
            airport_buffer_minutes=total_buffer_min,
            security_reentry_minutes=security_reentry_min,
            transport_minutes=transport_to_city_min * 2,
            city_time_minutes=city_time_minutes,
        ),
        buffer_breakdown=BufferBreakdown(
            exit_time_min=exit_time_min,
            security_reentry_min=security_reentry_min,
            walk_to_gate_min=walk_to_gate_min,
            checkin_cutoff_min=checkin_cutoff_min,
            total_buffer_min=total_buffer_min,
        ),
        usable_minutes=usable_minutes,
        verdict=verdict,
        personas=PERSONAS,
        place_options=place_options,
        available_time_minutes=usable_minutes,
    )


# ---------------------------------------------------------------------------
# ACTIVITY PLANNING — everything below is not needed until Step 3
# ---------------------------------------------------------------------------

def parse_iso_time(iso_str: str) -> int:  # ACTIVITY PLANNING — not needed until Step 3
    """Parse ISO 8601 datetime and return minutes since midnight."""
    dt = datetime.fromisoformat(iso_str)
    return dt.hour * 60 + dt.minute


def format_duration(minutes: int) -> str:  # ACTIVITY PLANNING — not needed until Step 3
    """Format minutes as human-readable duration."""
    if minutes <= 0:
        return "0 min"
    h = minutes // 60
    m = minutes % 60
    if h == 0:
        return f"{m} min"
    if m == 0:
        return f"{h}h"
    return f"{h}h {m}min"


def get_immigration_buffer(passport_region: str, airport_code: str) -> int:
    # ACTIVITY PLANNING — not needed until Step 3
    """Calculate immigration buffer based on passport and airport."""
    if passport_region == "EU" and airport_code in ["LIS", "AMS"]:
        return 0
    elif passport_region == "OTHER":
        return 15
    else:  # US
        return 5


def get_suggestions_for_city_time(airport_code: str, city_time_minutes: int) -> List[Suggestion]:
    # ACTIVITY PLANNING — not needed until Step 3
    """Get suggestions that fit within available city time."""
    suggestions = SUGGESTIONS_CONFIG.get(airport_code, [])
    fitting = [s for s in suggestions if s["min_time_needed"] <= city_time_minutes + 15]
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
    # ACTIVITY PLANNING — not needed until Step 3
    """Get place options from Places API (with fallback to hardcoded) with photos from Unsplash API."""
    try:
        # Try to fetch real places from Places API (with fallback built in)
        places = await PlacesService.find_attractions(
            airport_code=airport_code,
            available_minutes=city_time_minutes,
            max_places=5,
        )
        
        # Fetch photos in parallel for better performance
        import asyncio
        async def fetch_photo(place_name: str) -> Optional[str]:
            """Fetch a single Unsplash photo, return URL or None"""
            try:
                photos = await UnsplashService.search_photos(query=place_name, per_page=1)
                return photos[0]["url"] if photos else None
            except Exception as e:
                print(f"WARNING: Failed to fetch photo for {place_name}: {e}")
                return None
        
        # Get all photo URLs in parallel
        photo_tasks = [
            fetch_photo(place.get("name", ""))
            for place in places
        ]
        photo_urls = await asyncio.gather(*photo_tasks)
        
        result = []
        for place, photo_url in zip(places, photo_urls):
            # Convert place dict to PlaceOption object
            place_id = place.get("name", "").replace(" ", "_").lower()
            
            result.append(PlaceOption(
                place_id=place_id,
                name=place.get("name", ""),
                description=place.get("description", ""),
                rating=place.get("rating", 4.5),
                user_ratings_total=place.get("user_ratings_total", 0),
                coordinates=place.get("coordinates", ""),
                address=place.get("address", ""),
                types=["point_of_interest"],
                photo_url=photo_url,
            ))
        
        return result
    except Exception as e:
        print(f"ERROR: Failed to get place options: {e}")
        return []


async def get_persona_place_options(
    airport_code: str,
    persona_key: str,
    persona_label: str,
    persona_description: str,
    available_minutes: int,
) -> List[PlaceOption]:
    """Fetch persona-tailored place suggestions via Gemini, with Unsplash photos."""
    airport_cfg = AIRPORTS_CONFIG.get(airport_code, {})
    airport_city = airport_cfg.get("city", airport_code)

    gemini = GeminiActivityService()
    raw_places = gemini.generate_persona_places(
        airport_city=airport_city,
        persona_key=persona_key,
        persona_label=persona_label,
        persona_description=persona_description,
        available_minutes=available_minutes,
    )

    result = []
    for place in raw_places:
        name = place.get("name", "")
        search_query = place.get("search_query", name)
        photos = await UnsplashService.search_photos(query=search_query, per_page=1)
        place_id = f"{persona_key}_{name.replace(' ', '_').lower()}"
        if photos:
            photo = photos[0]
            result.append(PlaceOption(
                place_id=place_id,
                name=name,
                description=place.get("description", ""),
                rating=4.5,
                user_ratings_total=0,
                coordinates=place.get("coordinates", ""),
                address=place.get("address", ""),
                types=place.get("types", ["point_of_interest"]),
                photo_url=photo["url"],
                photographer_name=photo["photographer"],
                photographer_url=photo["photographer_url"],
                unsplash_url=photo["unsplash_url"],
                download_location=photo["download_location"],
            ))
        else:
            result.append(PlaceOption(
                place_id=place_id,
                name=name,
                description=place.get("description", ""),
                rating=4.5,
                user_ratings_total=0,
                coordinates=place.get("coordinates", ""),
                address=place.get("address", ""),
                types=place.get("types", ["point_of_interest"]),
            ))
    return result


def _fallback_headline(verdict: str, minutes: int, city: str) -> str:
    # ACTIVITY PLANNING — not needed until Step 3
    """Fallback headline if Gemini fails."""
    if verdict == "safe":
        return f"You've got {minutes} solid minutes in {city}. Time to explore!"
    elif verdict == "tight":
        return f"Possible, but you'll need to move fast in {city}."
    else:
        return "Play it safe and stay at the airport."
