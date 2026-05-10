from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import config
from models import PlannerInput, PlannerOutput
from services.planner_service import generate_plan
from services.flight_data import get_flight_times

app = FastAPI(title="GateAway Genius Backend", version="0.1.0")

# CORS: Allow frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173", "http://localhost:8080", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {"status": "ok"}


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
async def lookup_flight(flight_number: str, airport_code: str):
    """
    Look up a flight by number and arrival airport
    
    Query params:
    - flight_number: IATA code (e.g., "LH780")
    - airport_code: IATA code (e.g., "SIN")
    
    Returns arrival time and date, or error if not found
    """
    if not flight_number or not airport_code:
        raise HTTPException(status_code=400, detail="flight_number and airport_code required")
    
    try:
        result = await get_flight_times(flight_number, airport_code)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Flight {flight_number} arriving at {airport_code} not found. Check the flight number and airport code."
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up flight: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)