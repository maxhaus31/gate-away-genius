from pydantic import BaseModel
from typing import Optional, List

# Request model
class PlannerInput(BaseModel):
    arrival_time: str  # ISO format: "2024-05-01T10:00:00"
    departure_time: str  # ISO format: "2024-05-01T14:00:00"
    airport_code: str  # "LIS", "AMS", "SIN"
    passport_region: str  # "EU", "US", "OTHER"


# Response models
class TimelineSegment(BaseModel):
    label: str
    duration_minutes: int
    color: str


class Activity(BaseModel):
    emoji: str
    name: str
    description: str
    duration_minutes: int


class PlannerOutput(BaseModel):
    verdict: str  # "safe", "tight", or "stay"
    verdict_description: str
    timeline: List[TimelineSegment]
    available_time_minutes: int
    suggestions: List[Activity]
    safety_buffer_breakdown: dict