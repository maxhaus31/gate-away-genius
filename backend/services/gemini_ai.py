"""
Gemini AI Service: Generate activity recommendations with coordinates using httpx REST
"""

import hashlib
import time
import httpx
import json
from pydantic import BaseModel, Field
from config import GOOGLE_GEMINI_API_KEY
from typing import List

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.0-flash-lite"

# Simple in-memory prompt cache — avoids re-hitting the API for identical prompts
# Entries expire after 10 minutes (600s), which covers rapid repeated test submissions
_CACHE: dict = {}
_CACHE_TTL = 600


def _cache_get(prompt: str):
    key = hashlib.md5(prompt.encode()).hexdigest()
    entry = _CACHE.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["value"]
    return None


def _cache_set(prompt: str, value: str):
    key = hashlib.md5(prompt.encode()).hexdigest()
    _CACHE[key] = {"value": value, "ts": time.time()}


class Activity(BaseModel):
    """Pydantic model for activity structure"""
    emoji: str = Field(..., description="Single emoji representing the activity")
    title: str = Field(..., description="Activity name")
    description: str = Field(..., description="What you'll do and why it's worth seeing")
    minTimeNeeded: int = Field(..., description="Time needed in minutes")
    latitude: float = Field(..., description="GPS latitude (-90 to 90)")
    longitude: float = Field(..., description="GPS longitude (-180 to 180)")


def _call_gemini(prompt: str, model: str = PRIMARY_MODEL) -> str:
    """Make a single REST call to Gemini and return the text response."""
    url = GEMINI_API_URL.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7},
    }
    response = httpx.post(url, params={"key": GOOGLE_GEMINI_API_KEY}, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_gemini_with_fallback(prompt: str) -> str:
    """Try primary model, fall back to lite on failure. Caches results to avoid repeat hits."""
    cached = _cache_get(prompt)
    if cached is not None:
        return cached
    try:
        result = _call_gemini(prompt, PRIMARY_MODEL)
    except Exception as e:
        print(f"WARNING: Primary model failed ({e}), trying fallback")
        result = _call_gemini(prompt, FALLBACK_MODEL)
    _cache_set(prompt, result)
    return result


class GeminiActivityService:
    """Service to generate AI-powered activity recommendations via Gemini REST API"""

    def generate_activities(
        self,
        airport_city: str,
        available_minutes: int,
        passport_region: str,
        airport_iata: str,
    ) -> List[dict]:
        """
        Ask Gemini for activity recommendations in the city.

        Returns:
            List of activities, each with emoji, title, description, minTimeNeeded, latitude, longitude
        """
        prompt_text = f"""You are a travel expert. Suggest exactly 3 quick activities someone can do during a {available_minutes}-minute layover in {airport_city}.

Requirements:
- Include ONLY the most iconic, unmissable experiences for this city
- For each activity, provide: name, brief description, realistic time needed (in minutes), and exact GPS coordinates
- Make sure coordinates are PRECISE (verified, real locations)
- Focus on realistic activities — a quick coffee is better than a full museum if time is short
- Consider passport region "{passport_region}" (EU citizens have easier re-entry at EU airports)
- Each activity should be doable within the {available_minutes} available minutes

Return exactly 3 activities as a JSON array. Each activity must have these exact fields:
- emoji: single emoji character
- title: activity name
- description: what to do and why it's worth it
- minTimeNeeded: time in minutes
- latitude: GPS latitude (number between -90 and 90)
- longitude: GPS longitude (number between -180 and 180)

Format: Return ONLY valid JSON array, nothing else."""

        try:
            text = _call_gemini_with_fallback(prompt_text)

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            activities = json.loads(text)

            validated = []
            for activity in activities:
                try:
                    validated.append(Activity(**activity).model_dump())
                except Exception as e:
                    print(f"WARNING: Activity validation failed: {e}")
            return validated[:3]

        except Exception as e:
            print(f"WARNING: Gemini activity generation failed: {e}")
            return self._fallback_activities(airport_city)

    def generate_verdict_copy(
        self,
        verdict: str,
        available_minutes: int,
        airport_city: str,
        activities: List[dict],
    ) -> str:
        """Generate witty, personalized copy for the verdict."""
        activity_names = [a.get("title", "activity") for a in activities[:2]]
        activity_str = " + ".join(activity_names) if activity_names else "exploration"

        if verdict == "safe":
            prompt_text = f"Write ONE witty, encouraging sentence telling someone they can absolutely do {activity_str} in {airport_city} with {available_minutes} minutes to spare. Be confident. Max 15 words. No markdown."
        elif verdict == "tight":
            prompt_text = f"Write ONE witty sentence about how someone can *squeeze in* {activity_str} in {airport_city} with {available_minutes} minutes, but they'll need to move. Max 15 words. No markdown."
        else:
            prompt_text = f"Write ONE witty sentence telling someone they should probably just stay in the airport and relax with a coffee. {airport_city} will still be there another time. Max 15 words. No markdown."

        try:
            return _call_gemini_with_fallback(prompt_text)[:100]
        except Exception as e:
            print(f"WARNING: Gemini verdict generation failed: {e}")
            return self._fallback_copy(verdict, available_minutes, airport_city)

    def generate_place_descriptions_batch(
        self,
        places: List[dict],
    ) -> dict:
        """
        Generate witty descriptions for multiple places in a single Gemini call.

        Args:
            places: list of dicts with keys name, types, rating, user_ratings_total

        Returns:
            dict mapping place name → description string
        """
        if not places:
            return {}

        lines = []
        for i, p in enumerate(places):
            place_type = p["types"][0] if p.get("types") else "attraction"
            lines.append(
                f'{i+1}. "{p["name"]}" — {place_type}, {p["rating"]}/5 stars, {p["user_ratings_total"]} reviews'
            )

        prompt_text = (
            "For each place below, write ONE short witty description (max 10 words). "
            "Return a JSON object where each key is the place name and the value is the description. "
            "Return ONLY valid JSON, nothing else.\n\n"
            + "\n".join(lines)
        )

        try:
            text = _call_gemini_with_fallback(prompt_text)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"WARNING: Batch description generation failed: {e}")
            return {
                p["name"]: f"{p['name']} — {p['rating']}/5 ({p['user_ratings_total']} reviews)"
                for p in places
            }

    def generate_persona_places(
        self,
        airport_city: str,
        persona_key: str,
        persona_label: str,
        persona_description: str,
        available_minutes: int,
    ) -> List[dict]:
        """
        Ask Gemini for 5 places in airport_city tailored to the traveller persona.
        Returns list of dicts with: name, description, address, types, coordinates, search_query
        """
        persona_guidelines = {
            "food_lover": (
                "Focus on iconic local food markets, celebrated local restaurants, "
                "historic cafés, street food scenes, and neighbourhood spots known for "
                "authentic regional cuisine. NO chains, fast food, or generic coffee shops."
            ),
            "culture_seeker": (
                "Focus on world-class museums, UNESCO heritage sites, famous historic "
                "landmarks, architectural icons, and neighbourhoods with deep cultural "
                "character. Prioritise places with strong storytelling and local identity."
            ),
            "nature_wanderer": (
                "Focus on iconic parks, scenic viewpoints, waterfronts, botanical gardens, "
                "nature reserves, and outdoor escapes with memorable landscapes. "
                "Prioritise places known for their beauty and peaceful atmosphere."
            ),
            "checklist_traveler": (
                "Focus on the city's most famous and universally recognised landmarks, "
                "must-see squares, iconic monuments, and top-rated attractions that "
                "every visitor talks about. These should be the 'I was there' moments."
            ),
        }

        persona_hint = persona_guidelines.get(
            persona_key,
            "Focus on places that are genuinely special, well-known, and memorable."
        )

        prompt_text = f"""You are an expert local travel guide recommending layover stops in {airport_city}.

Traveller persona: "{persona_label}" — {persona_description}
Available city time: {available_minutes} minutes

Your goal: Suggest exactly 5 real, specific, well-known places in {airport_city} that this traveller will remember.

Persona focus: {persona_hint}

Hard rules — a place MUST be excluded if it is any of the following:
- A supermarket, grocery store, or convenience store
- A fast food chain (McDonald's, KFC, Burger King, Subway, etc.)
- A global coffee chain (Starbucks, Costa, etc.)
- A shopping mall or generic retail chain
- A place chosen purely for high ratings but with no special local character

A great recommendation is:
- Famous or iconic within the city (locals and tourists alike know it)
- Genuinely tied to the city's identity, history, culture, food scene, or landscape
- Realistic to visit in {available_minutes} minutes from the city centre
- Something that feels special and memorable, not interchangeable with any other city

Return a JSON array. Each element must have exactly these fields:
- name: the place name (string)
- description: one vivid sentence capturing why this place is unmissable (string)
- address: street address or neighbourhood (string)
- types: list of 1-2 category strings, e.g. ["restaurant"], ["museum", "historic_site"]
- coordinates: "lat,lng" as a string with real GPS coordinates for this specific place
- search_query: 2-3 word Unsplash photo search query for this place (e.g. "lisbon market", "amsterdam canal")

Return ONLY a valid JSON array, nothing else."""

        try:
            text = _call_gemini_with_fallback(prompt_text)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            places = json.loads(text)
            return places[:5]
        except Exception as e:
            print(f"WARNING: Gemini persona places generation failed: {e}")
            return []

    def _fallback_activities(self, airport_city: str) -> List[dict]:
        return [
            {
                "emoji": "☕",
                "title": "Airport Café",
                "description": "Grab a coffee and relax before your next flight",
                "minTimeNeeded": 20,
                "latitude": 0.0,
                "longitude": 0.0,
            }
        ]

    def _fallback_copy(self, verdict: str, minutes: int, city: str) -> str:
        if verdict == "safe":
            return f"You've got time! Quick {city} adventure incoming INFO:"
        elif verdict == "tight":
            return f"Tight timeline but doable—move fast! ⏰"
        else:
            return f"Stay cozy in the airport, {city} can wait 😊"