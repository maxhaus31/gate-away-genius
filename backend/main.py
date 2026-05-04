from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import config
from models import PlannerInput, PlannerOutput

app = FastAPI(title="GateAway Genius Backend", version="0.1.0")

# CORS: Allow frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173"],
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
    
    This is a placeholder. Will be replaced with real logic in Phase 2/3.
    """
    # For now, return mock data
    return PlannerOutput(
        verdict="safe",
        verdict_description="You have enough time to leave the airport safely.",
        timeline=[
            {"label": "Security", "duration_minutes": 15, "color": "red"},
            {"label": "Travel to city", "duration_minutes": 30, "color": "blue"},
            {"label": "Activity time", "duration_minutes": 90, "color": "green"},
            {"label": "Travel back", "duration_minutes": 30, "color": "blue"},
            {"label": "Buffer", "duration_minutes": 15, "color": "orange"},
        ],
        available_time_minutes=180,
        suggestions=[
            {
                "emoji": "🍷",
                "name": "Wine Tasting",
                "description": "Local Portuguese wine bar",
                "duration_minutes": 60,
            },
            {
                "emoji": "🎨",
                "name": "Pastéis de Nata Tour",
                "description": "Famous Lisbon pastry experience",
                "duration_minutes": 45,
            },
        ],
        safety_buffer_breakdown={
            "security_check": 15,
            "passport_control": 5,
            "buffer": 10,
        },
    )


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)