from pydantic import BaseModel
from typing import Optional, List

# Request model
class PlannerInput(BaseModel):
    arrival_time: str  # ISO format: "2024-05-01T10:00:00"
    departure_time: str  # ISO format: "2024-05-01T14:00:00"
    airport_code: str  # "LIS", "AMS", "SIN"
    passport_region: str  # "EU", "US", "OTHER"
    flight_number: Optional[str] = None  # e.g., "BA 284" for real flight lookup


# Response models
class TimelineSegment(BaseModel):
    label: str
    duration_minutes: int
    color: str


class Suggestion(BaseModel):
    """Activity suggestion for a layover"""
    emoji: str
    title: str
    blurb: str
    minTimeNeeded: int


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
    
    # Time breakdown
    total_minutes: int  # Total layover time
    buffer_minutes: int  # Total buffer required
    usable_minutes: int  # Total minus buffer
    available_time_minutes: int  # City time available (usable minus transport)
    city_time_minutes: int  # Pure city time (available minus round-trip)
    
    # Airport and suggestions
    airport: AirportInfo
    suggestions: List[Suggestion]
    immigration_buffer: int  # Immigration buffer based on passport region
    safety_buffer_breakdown: dict  # Detailed breakdown of buffers
    buffer_breakdown: List[BufferBreakdown]  # List of buffer items