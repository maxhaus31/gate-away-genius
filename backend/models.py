from pydantic import BaseModel
from typing import Optional, List

# Request model
class PlannerInput(BaseModel):
    arrival_time: str  # ISO format: "2024-05-01T10:00:00"
    departure_time: str  # ISO format: "2024-05-01T14:00:00"
    airport_code: str  # "LIS", "AMS", "SIN"
    passport_region: str  # "EU", "US", "OTHER"
    flight_number: Optional[str] = None  # e.g., "BA 284" for real flight lookup
    transport_mode: str = "transit"  # "transit" for public transport, "driving" for car/taxi


# Response models
class TimelineSegment(BaseModel):
    label: str
    duration_minutes: int
    color: str


class ActivityStep(BaseModel):
    """Single activity in the itinerary"""
    type: str  # "airport", "travel", "activity"
    emoji: str  # Icon representation
    title: str  # "Lisbon Airport", "Travel to Pastel de Nata", etc.
    duration_minutes: int
    coordinates: Optional[str] = None  # For activities: "lat,lng"


class ActivityItinerary(BaseModel):
    """Detailed step-by-step itinerary for the layover"""
    steps: List[ActivityStep]  # Ordered journey from airport -> activities -> airport


class Suggestion(BaseModel):
    """Activity suggestion for a layover"""
    emoji: str
    title: str
    blurb: str
    minTimeNeeded: int


class PlaceOption(BaseModel):
    """Suggested place that user can select and add to plan"""
    place_id: str
    name: str
    description: str  # Witty Gemini-generated description
    rating: float
    user_ratings_total: int
    coordinates: str  # "lat,lng"
    address: str
    types: List[str]
    photo_url: Optional[str] = None  # URL to place photo (hotlinked from Unsplash or Google Maps)
    photographer_name: Optional[str] = None  # Photographer name (for Unsplash attribution)
    photographer_url: Optional[str] = None  # Link to photographer profile (with UTM params)
    unsplash_url: Optional[str] = None  # Link back to Unsplash (with UTM params)
    download_location: Optional[str] = None  # Unsplash download tracking endpoint


class AirportInfo(BaseModel):
    """Airport configuration and metadata"""
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


class BufferBreakdown(BaseModel):
    """Breakdown of buffer time requirements"""
    label: str
    minutes: int


class PlannerOutput(BaseModel):
    """Complete layover plan response"""
    # Verdict and messaging
    verdict: str  # "safe", "tight", or "stay"
    verdict_description: str  # Detailed message about the verdict
    headline: str  # Short headline version
    
    # Timeline data
    timeline: List[TimelineSegment]
    activity_itinerary: ActivityItinerary  # Detailed step-by-step breakdown for visualization
    
    # Time breakdown
    total_minutes: int  # Total layover time
    buffer_minutes: int  # Total buffer required
    usable_minutes: int  # Total minus buffer
    available_time_minutes: int  # City time available (usable minus transport)
    city_time_minutes: int  # Pure city time (available minus round-trip)
    
    # Airport and suggestions
    airport: AirportInfo
    suggestions: List[Suggestion]
    place_options: List[PlaceOption]  # Suggested places user can select
    immigration_buffer: int  # Immigration buffer based on passport region
    safety_buffer_breakdown: dict  # Detailed breakdown of buffers
    buffer_breakdown: List[BufferBreakdown]  # List of buffer items