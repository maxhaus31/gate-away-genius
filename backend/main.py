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
from models import PlannerInput, PlannerOutput
from services.planner_service import generate_plan
from services.schiphol_api import SchipholService

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
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)