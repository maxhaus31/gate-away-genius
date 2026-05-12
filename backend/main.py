from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import config
from models import PlannerInput, PlannerOutput, RouteResponse, PlaceOption
from services.planner_service import generate_plan
from services.schiphol_api import SchipholService
from services.route_service import RouteService
from pydantic import BaseModel
from typing import List

app = FastAPI(title="GateAway Genius Backend", version="0.1.0")

# CORS: Allow frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173", "http://localhost:8080", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request model for route calculation
class CalculateRouteRequest(BaseModel):
    airport_code: str
    place_ids: List[str]  # IDs of selected places
    place_names: List[str]  # Names of selected places
    place_coordinates: List[str]  # ["lat,lng", "lat,lng", "lat,lng"]
    transport_mode: str = "transit"  # "transit" or "driving"
    available_minutes: int  # Total available time for activities
    time_per_place: int = 45  # Minutes to spend at each place


@app.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {"status": "ok"}


@app.post("/api/calculate-route")
async def calculate_route(request: CalculateRouteRequest) -> dict:
    """
    Calculate multi-place route with detailed itinerary
    
    Takes selected places and returns:
    - Route legs with travel times
    - Detailed itinerary showing time at each place
    - Total remaining time
    - Polyline for map visualization
    """
    try:
        # Calculate route using Google Maps
        route_data = await RouteService.calculate_multi_waypoint_route(
            airport_code=request.airport_code,
            place_coordinates=request.place_coordinates,
            place_names=request.place_names,
            mode=request.transport_mode,
        )
        
        if not route_data:
            raise HTTPException(status_code=500, detail="Failed to calculate route")
        
        # Build detailed itinerary with timing
        itinerary = []
        cumulative_minutes = 0
        
        legs = route_data["legs"]
        
        for i, leg in enumerate(legs):
            # Travel leg
            travel_duration = leg["duration_minutes"]
            itinerary.append({
                "sequence": len(itinerary),
                "type": "travel",
                "from": leg["from_place"],
                "to": leg["to_place"],
                "duration_minutes": travel_duration,
                "cumulative_minutes": cumulative_minutes + travel_duration,
                "distance_meters": leg["distance_meters"],
            })
            cumulative_minutes += travel_duration
            
            # Activity leg (45 min at the place, if not at airport)
            if "Airport" not in leg["to_place"] and i < len(legs) - 1:  # Not the return leg
                itinerary.append({
                    "sequence": len(itinerary),
                    "type": "activity",
                    "place": leg["to_place"],
                    "duration_minutes": request.time_per_place,
                    "cumulative_minutes": cumulative_minutes + request.time_per_place,
                })
                cumulative_minutes += request.time_per_place
        
        # Calculate remaining time
        total_used_minutes = cumulative_minutes
        remaining_minutes = request.available_minutes - total_used_minutes
        
        return {
            "route": route_data,
            "itinerary": itinerary,
            "timing_summary": {
                "total_travel_minutes": sum(leg["duration_minutes"] for leg in legs),
                "total_activity_minutes": request.time_per_place * 3,  # 3 places
                "total_used_minutes": total_used_minutes,
                "available_minutes": request.available_minutes,
                "remaining_minutes": max(0, remaining_minutes),
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route calculation error: {str(e)}")



@app.post("/api/plan")
async def create_plan(input_data: PlannerInput) -> PlannerOutput:
    """
    Main endpoint: receives flight info, returns layover verdict + suggestions
    
    Uses planner_service to calculate verdict based on flight times and airport rules.
    Integrates with Google Maps for real transit times and Gemini for activity suggestions.
    """
    try:
        result = await generate_plan(input_data)
        if result is None:
            raise HTTPException(status_code=400, detail="Invalid input data")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/api/airports")
async def get_airports():
    """Returns list of supported airports"""
    return {
        "airports": [
            {"code": "LIS", "name": "Lisbon Humberto Delgado", "country": "Portugal"},
            {"code": "AMS", "name": "Amsterdam Schiphol", "country": "Netherlands"},
            {"code": "SIN", "name": "Singapore Changi", "country": "Singapore"},
        ]
    }


@app.get("/api/airports/{airport_code}")
async def get_airport_details(airport_code: str):
    """Returns details for a specific airport"""
    # Placeholder
    return {
        "code": airport_code,
        "name": "Airport Name",
        "terminals": ["T1", "T2"],
        "security_buffer_minutes": 15,
    }


@app.get("/api/flights/lookup")
async def lookup_flight(flight_number: str, date: str = None):
    """
    Look up a Schiphol flight by IATA name (e.g. "KL1234").

    Query params:
    - flight_number: IATA flight name (e.g., "KL1234")
    - date: Schedule date YYYY-MM-DD (defaults to today)

    Returns flight details including scheduled times, terminal, gate, and delay.
    """
    if not flight_number:
        raise HTTPException(status_code=400, detail="flight_number is required")

    try:
        result = await SchipholService.get_flight(flight_number, date)
        if result.get("is_mock"):
            raise HTTPException(
                status_code=404,
                detail=f"Flight {flight_number} not found. Check the flight number and date."
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up flight: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)