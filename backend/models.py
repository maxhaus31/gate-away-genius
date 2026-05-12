from pydantic import BaseModel
from typing import Optional, List, Dict


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class PlannerInput(BaseModel):
    # Step 1 — three fields sent by the frontend
    inbound_flight: str    # e.g. "KL1234"
    outbound_flight: str   # e.g. "KL5678"
    passport_region: str   # "EU", "US", or "OTHER"

    # Not user-facing in Step 1; defaults to today inside SchipholService
    flight_date: Optional[str] = None  # "YYYY-MM-DD"

    # Not user-facing in Step 1; needed internally for buffer lookup.
    # Will become a required user field when multi-airport support is introduced.
    airport_code: str = "AMS"  # "AMS", "LIS", "SIN"

    # ACTIVITY PLANNING — transport_mode is not part of Step 1 user input.
    # It may be needed in Step 3 for Google Maps distance calculations.
    transport_mode: str = "transit"  # "transit" or "driving"


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
    inbound: InboundFlightInfo
    outbound: OutboundFlightInfo
    layover_duration_minutes: int      # outbound departure − inbound actual/estimated arrival


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
    # Step 1 — required fields (always present)
    flight_overview: FlightOverview
    buffer_breakdown: BufferBreakdown
    usable_minutes: int
    verdict: str        # "safe" | "tight" | "not_possible"
    personas: List[Persona]
    
    # Step 3 — optional fields (populated after place selection)
    verdict_description: Optional[str] = None
    headline: Optional[str] = None
    timeline: Optional[List[TimelineSegment]] = None
    activity_itinerary: Optional[ActivityItinerary] = None
    total_minutes: Optional[int] = None
    buffer_minutes: Optional[int] = None
    available_time_minutes: Optional[int] = None
    city_time_minutes: Optional[int] = None
    airport: Optional[AirportInfo] = None
    suggestions: Optional[List[Suggestion]] = None
    place_options: Optional[List[PlaceOption]] = None
    immigration_buffer: Optional[int] = None
    safety_buffer_breakdown: Optional[List[Dict]] = None


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