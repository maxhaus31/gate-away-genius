from pydantic import BaseModel
from typing import Optional, List, Dict


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class PlannerInput(BaseModel):
    inbound_flight:  str              # e.g. "KL1234"
    outbound_flight: str              # e.g. "TP1835"
    inbound_date:    Optional[str] = None   # "YYYY-MM-DD"; defaults to today
    outbound_date:   Optional[str] = None   # "YYYY-MM-DD"; defaults to today
    layover_airport: str = "AMS"      # "AMS" | "LIS" | "SIN"
    passport_type:   str = "EU"       # "EU" | "US" | "OTHER"
    transport_mode:  str = "transit"  # kept for Step 3 route calculation


# ---------------------------------------------------------------------------
# Response models — Step 1 (flight overview + verdict)
# ---------------------------------------------------------------------------

class InboundFlightInfo(BaseModel):
    flight_number: str
    date: str                          # "YYYY-MM-DD"
    scheduled_arrival: str             # ISO 8601
    actual_arrival: Optional[str]      # None if not yet available
    delay_minutes: int
    status: str
    terminal: str
    pier: str


class OutboundFlightInfo(BaseModel):
    flight_number: str
    date: str                          # "YYYY-MM-DD"
    scheduled_departure: str           # ISO 8601
    status: str
    terminal: str
    pier: str


class FlightOverview(BaseModel):
    inbound:                   InboundFlightInfo
    outbound:                  OutboundFlightInfo
    total_layover_minutes:     int  # outbound departure − inbound actual/estimated arrival
    airport_buffer_minutes:    int  # exit + security + walk + check-in cutoff
    security_reentry_minutes:  int  # security queue component of the buffer
    transport_minutes:         int  # round-trip transport to city (transport_to_city × 2)
    city_time_minutes:         int  # total_layover − buffer − transport


class BufferBreakdown(BaseModel):
    exit_time_min: int          # pier-based (AMS) or flat fallback (LIS/SIN)
    security_reentry_min: int   # live Schiphol queue (AMS) or hardcoded (LIS/SIN)
    walk_to_gate_min: int       # hardcoded per airport
    checkin_cutoff_min: int     # Schengen/non-Schengen based on passport_region
    total_buffer_min: int


class Persona(BaseModel):
    key: str
    label: str
    description: str


# ---------------------------------------------------------------------------
# Step 3 (Activity Planning) models — used by PlannerOutput
# ---------------------------------------------------------------------------

class TimelineSegment(BaseModel):
    label: str
    duration_minutes: int
    color: str


class ActivityStep(BaseModel):
    type: str
    emoji: str
    title: str
    duration_minutes: int
    coordinates: Optional[str] = None


class ActivityItinerary(BaseModel):
    steps: List[ActivityStep]


class Suggestion(BaseModel):
    emoji: str
    title: str
    blurb: str
    minTimeNeeded: int


class PlaceOption(BaseModel):
    place_id: str
    name: str
    description: str
    rating: float
    user_ratings_total: int
    coordinates: str
    address: str
    types: List[str]
    photo_url: Optional[str] = None
    photographer_name: Optional[str] = None
    photographer_url: Optional[str] = None
    unsplash_url: Optional[str] = None
    download_location: Optional[str] = None


class AirportInfo(BaseModel):
    code: str
    city: str
    name: str
    country: str
    flag: str
    transportToCityMin: int
    transportLabel: str
    reentrySecurityMin: int
    walkToGateMin: int
    checkinCutoffMin: int
    vibe: str


# ---------------------------------------------------------------------------
# Main Response Models
# ---------------------------------------------------------------------------

class PlannerOutput(BaseModel):
    # Step 1 — always present
    flight_overview:  FlightOverview
    verdict:          str           # "safe" | "tight" | "not_possible"
    personas:         List[Persona]

    # Step 1 detail (buffer breakdown kept for tooltip display)
    buffer_breakdown:        Optional[BufferBreakdown] = None
    usable_minutes:          Optional[int] = None

    # Step 3 — optional fields
    verdict_description:     Optional[str] = None
    headline:                Optional[str] = None
    timeline:                Optional[List[TimelineSegment]] = None
    activity_itinerary:      Optional[ActivityItinerary] = None
    available_time_minutes:  Optional[int] = None
    airport:                 Optional[AirportInfo] = None
    suggestions:             Optional[List[Suggestion]] = None
    place_options:           Optional[List[PlaceOption]] = None
    safety_buffer_breakdown: Optional[List[Dict]] = None


class PersonaPlacesRequest(BaseModel):
    airport_code: str
    persona_key: str
    persona_label: str
    persona_description: str
    available_minutes: int


class RouteLeg(BaseModel):
    """Single leg of a route (from one place to next)"""
    from_place: str  # Place name or "Airport"
    to_place: str    # Destination place name or "Airport"
    distance_meters: int
    duration_minutes: int


class RouteResponse(BaseModel):
    """Response from route calculation endpoint"""
    total_distance_meters: int
    total_duration_minutes: int
    legs: List[RouteLeg]  # Individual legs of the journey
    polyline: Optional[str] = None  # Encoded polyline for map display
    waypoints: List[dict]  # List of waypoint coordinates


class ItineraryItem(BaseModel):
    """Single item in the detailed itinerary"""
    sequence: int
    activity: str  # "Travel to", "Visit", "Travel back"
    place_name: str
    duration_minutes: int
    cumulative_minutes: int
    coordinates: Optional[str] = None