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
        key="coffee_lover",
        label="Coffee Lover",
        description="Great coffee shops and a comfortable spot to recharge between flights.",
    ),
    Persona(
        key="culture_seeker",
        label="Culture Seeker",
        description="Museums, landmarks, and a taste of local history in the time available.",
    ),
    Persona(
        key="fast_traveler",
        label="Fast Traveler",
        description="Maximum sights in minimum time — efficient routes, no detours.",
    ),
    Persona(
        key="relaxed_discoverer",
        label="Relaxed Discoverer",
        description="A slower pace: markets, parks, and whatever looks interesting along the way.",
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


async def generate_plan(input_data: PlannerInput) -> Optional[PlannerOutput]:
    """
    Step 1: Build flight overview and layover verdict.

    Calls Schiphol for both flights, computes buffer from airport_data constants
    and live security queue (AMS only), and returns verdict + persona list.
    """
    airport_cfg = AIRPORT_CONFIG.get(input_data.airport_code)
    if not airport_cfg:
        raise ValueError(f"Airport {input_data.airport_code} not supported")

    # ── Flight data ────────────────────────────────────────────────────────────
    inbound_raw  = await SchipholService.get_flight(input_data.inbound_flight,  input_data.flight_date)
    outbound_raw = await SchipholService.get_flight(input_data.outbound_flight, input_data.flight_date)

    scheduled_arrival  = inbound_raw.get("scheduled_arrival")
    actual_arrival     = inbound_raw.get("actual_arrival")
    effective_arrival  = actual_arrival or scheduled_arrival  # use actual if available
    scheduled_departure = outbound_raw.get("scheduled_departure")

    if not scheduled_arrival or not scheduled_departure:
        raise ValueError("Could not resolve flight times — check flight numbers and date")

    # Layover uses actual/estimated arrival to account for inbound delay
    layover_duration_minutes = calculate_minutes_between(effective_arrival, scheduled_departure)
    if layover_duration_minutes <= 0:
        raise ValueError("Departure time must be after arrival time")

    # ── Buffer calculation ─────────────────────────────────────────────────────
    pier = inbound_raw.get("pier", "")
    if input_data.airport_code == "AMS":
        exit_time_min = AMS_EXIT_TIME_BY_PIER.get(pier.upper(), EXIT_TIME_FALLBACK_MIN)
    else:
        exit_time_min = EXIT_TIME_FALLBACK_MIN

    # Live Schiphol queue for AMS; hardcoded fallback for LIS/SIN
    if input_data.airport_code == "AMS":
        outbound_terminal = outbound_raw.get("terminal")
        queue_data = await SchipholService.get_security_queue(outbound_terminal)
        security_reentry_min = queue_data.get("queue_minutes", airport_cfg["security_reentry_min_fallback"])
    else:
        security_reentry_min = airport_cfg["security_reentry_min_fallback"]

    walk_to_gate_min  = airport_cfg["walk_to_gate_min"]
    checkin_cutoff_min = CHECKIN_CUTOFF_BY_PASSPORT.get(input_data.passport_region, 75)
    total_buffer_min  = exit_time_min + security_reentry_min + walk_to_gate_min + checkin_cutoff_min

    usable_minutes = max(0, layover_duration_minutes - total_buffer_min)

    # ── Verdict ────────────────────────────────────────────────────────────────
    # ACTIVITY PLANNING — in Step 3 these thresholds will be refined by subtracting
    # round-trip transport time (transport_to_city_min × 2) before the 75-min check
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

    return PlannerOutput(
        flight_overview=FlightOverview(
            inbound=inbound_info,
            outbound=outbound_info,
            layover_duration_minutes=layover_duration_minutes,
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
    """Get fallback place options with photos from Unsplash API."""
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
    fitting_places = [p for p in places if city_time_minutes >= 75]
    if not fitting_places:
        fitting_places = places

    result = []
    for place in fitting_places[:5]:
        photos = await UnsplashService.search_photos(query=place["search_query"], per_page=1)
        if photos:
            photo = photos[0]
            result.append(PlaceOption(
                place_id=f"fallback_{place['name'].replace(' ', '_').lower()}",
                name=place["name"],
                description=place["description"],
                rating=4.5,
                user_ratings_total=0,
                coordinates="0,0",
                address="",
                types=["point_of_interest"],
                photo_url=photo["url"],
                photographer_name=photo["photographer"],
                photographer_url=photo["photographer_url"],
                unsplash_url=photo["unsplash_url"],
                download_location=photo["download_location"],
            ))
        else:
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


def _fallback_headline(verdict: str, minutes: int, city: str) -> str:
    # ACTIVITY PLANNING — not needed until Step 3
    """Fallback headline if Gemini fails."""
    if verdict == "safe":
        return f"You've got {minutes} solid minutes in {city}. Time to explore!"
    elif verdict == "tight":
        return f"Possible, but you'll need to move fast in {city}."
    else:
        return "Play it safe and stay at the airport."
