import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import re
import base64
import json
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import config
from models import PlannerInput, PlannerOutput, RouteResponse, PlaceOption, PersonaPlacesRequest
from services.planner_service import generate_plan, get_persona_place_options
from services.schiphol_api import SchipholService
from services.aerodatabox_api import AeroDataBoxService
from services.route_service import RouteService
from pydantic import BaseModel
from typing import List, Optional
import database

app = FastAPI(title="GateAway Genius Backend", version="0.1.0")

database.init_db()

# CORS: Allow frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173", "http://localhost:8080", "http://localhost:8081", 'https://gate-away-genius.vercel.app'],
    allow_origin_regex=r"https://.*\.vercel\.app",
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
    total_layover_minutes: int = 0  # Total layover duration
    airport_buffer_minutes: int = 0  # Airport buffers (security, check-in, etc)


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
                "transit_details": leg.get("transit_details"),
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
        # remaining_minutes = total_layover - airport_buffers - total_used_minutes
        remaining_minutes = request.total_layover_minutes - request.airport_buffer_minutes - total_used_minutes
        
        return {
            "route": route_data,
            "itinerary": itinerary,
            "timing_summary": {
                "total_travel_minutes": sum(leg["duration_minutes"] for leg in legs),
                "total_activity_minutes": request.time_per_place * len(request.place_names),
                "total_used_minutes": total_used_minutes,
                "available_minutes": request.available_minutes,
                "remaining_minutes": request.total_layover_minutes - request.airport_buffer_minutes - total_used_minutes,
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


@app.post("/api/places-for-persona")
async def places_for_persona(request: PersonaPlacesRequest) -> dict:
    """Return Gemini-generated place suggestions tailored to a traveller persona."""
    try:
        places = await get_persona_place_options(
            airport_code=request.airport_code,
            persona_key=request.persona_key,
            persona_label=request.persona_label,
            persona_description=request.persona_description,
            available_minutes=request.available_minutes,
        )
        return {"place_options": [p.model_dump() for p in places]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona places error: {str(e)}")


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
async def lookup_flight(
    flight_number: str,
    date: str = None,
    airport_code: str = "AMS",
    direction: str = "inbound",
):
    """
    Look up a flight by IATA number.

    Routes to Schiphol (AMS) or AeroDataBox (LIS/SIN).

    Query params:
    - flight_number: IATA flight number (e.g., "KL1234")
    - date:          Schedule date YYYY-MM-DD (defaults to today)
    - airport_code:  Layover airport "AMS" | "LIS" | "SIN" (default "AMS")
    - direction:     "inbound" or "outbound"
    """
    if not flight_number:
        raise HTTPException(status_code=400, detail="flight_number is required")

    try:
        if airport_code == "AMS":
            result = await SchipholService.get_flight(flight_number, date)
        else:
            result = await AeroDataBoxService.get_flight(flight_number, date, airport_code, direction)

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


FLIGHT_RE = re.compile(r"\b([A-Z]{2}\d{3,4})\b")


@app.post("/api/extract-flights")
async def extract_flights(file: UploadFile = File(...)):
    """
    Extract inbound and outbound flight numbers from a boarding pass image or PDF.

    Step 1 (PDF only): PyMuPDF pulls plain text; regex finds [A-Z]{2}\\d{3,4} matches.
    Step 2 (fallback): If fewer than 2 matches, send the file to Gemini Vision and parse
                       its structured JSON response.

    Returns { inbound_flight, outbound_flight } — either value may be null.
    """
    contents = await file.read()
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    is_pdf = content_type == "application/pdf" or filename.endswith(".pdf")

    flight_numbers: list = []

    # ── Step 1: text extraction for PDFs ──────────────────────────────────────
    if is_pdf:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=contents, filetype="pdf")
            text = "".join(page.get_text() for page in doc)
            flight_numbers = list(dict.fromkeys(FLIGHT_RE.findall(text.upper())))
        except Exception as e:
            print(f"WARNING: PyMuPDF extraction failed: {e}")

    # ── Step 2: Gemini Vision fallback ────────────────────────────────────────
    if len(flight_numbers) < 2:
        try:
            if is_pdf:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=contents, filetype="pdf")
                pix = doc[0].get_pixmap(dpi=150)
                image_bytes = pix.tobytes("png")
                mime_type = "image/png"
            else:
                image_bytes = contents
                mime_type = content_type or "image/jpeg"

            b64_data = base64.b64encode(image_bytes).decode()
            prompt = (
                "This is a boarding pass or flight confirmation document. "
                "Find all flight numbers (2 uppercase letters followed by 3 or 4 digits, "
                "e.g. KL1234 or TP835). "
                'Return ONLY a JSON object: {"inbound_flight": "XX1234", "outbound_flight": "XX5678"}. '
                "Set a value to null if not visible."
            )
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            payload = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                        {"text": prompt},
                    ]
                }]
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    params={"key": config.GOOGLE_GEMINI_API_KEY},
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
            resp_data = resp.json()
            usage = resp_data.get("usageMetadata", {})
            print(
                f"[TOKENS] extract_boarding_pass (gemini-2.5-flash) — "
                f"prompt: {usage.get('promptTokenCount', '?')}, "
                f"output: {usage.get('candidatesTokenCount', '?')}, "
                f"total: {usage.get('totalTokenCount', '?')}"
            )
            raw = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw)
            return {
                "inbound_flight": parsed.get("inbound_flight"),
                "outbound_flight": parsed.get("outbound_flight"),
            }
        except Exception as e:
            print(f"WARNING: Gemini Vision extraction failed: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Could not extract flight numbers from file: {e}",
            )

    return {
        "inbound_flight": flight_numbers[0] if len(flight_numbers) > 0 else None,
        "outbound_flight": flight_numbers[1] if len(flight_numbers) > 1 else None,
    }


class FeedbackRequest(BaseModel):
    rating: Optional[int] = None
    email: Optional[str] = None
    message: Optional[str] = None


@app.post("/api/feedback")
async def submit_feedback(body: FeedbackRequest):
    """Save user feedback (star rating, email, free-text) to the local SQLite database."""
    try:
        row_id = database.insert_feedback(body.rating, body.email, body.message)
        return {"ok": True, "id": row_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)