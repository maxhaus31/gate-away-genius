from pydantic import BaseModel
from typing import Optional, List


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
    checkin_cutoff_min: int     # Schengen/non-Schengen based on passport_type
    total_buffer_min: int


class Persona(BaseModel):
    key: str
    label: str
    description: str


class PlannerOutput(BaseModel):
    flight_overview: FlightOverview
    buffer_breakdown: BufferBreakdown
    usable_minutes: int
    verdict: str        # "safe" | "tight" | "not_possible"
    personas: List[Persona]


# ---------------------------------------------------------------------------
# ACTIVITY PLANNING — models below are not needed until Step 3
# ---------------------------------------------------------------------------

class TimelineSegment(BaseModel):  # ACTIVITY PLANNING — not needed until Step 3
    label: str
    duration_minutes: int
    color: str


class ActivityStep(BaseModel):  # ACTIVITY PLANNING — not needed until Step 3
    type: str
    emoji: str
    title: str
    duration_minutes: int
    coordinates: Optional[str] = None


class ActivityItinerary(BaseModel):  # ACTIVITY PLANNING — not needed until Step 3
    steps: List[ActivityStep]


class Suggestion(BaseModel):  # ACTIVITY PLANNING — not needed until Step 3
    emoji: str
    title: str
    blurb: str
    minTimeNeeded: int


class PlaceOption(BaseModel):  # ACTIVITY PLANNING — not needed until Step 3
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


class AirportInfo(BaseModel):  # ACTIVITY PLANNING — not needed until Step 3
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
