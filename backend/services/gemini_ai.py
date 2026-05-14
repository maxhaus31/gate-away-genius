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


def _log_tokens(call_name: str, model: str, usage: dict) -> None:
    prompt = usage.get("promptTokenCount", "?")
    output = usage.get("candidatesTokenCount", "?")
    total = usage.get("totalTokenCount", "?")
    print(f"[TOKENS] {call_name} ({model}) — prompt: {prompt}, output: {output}, total: {total}")

# Simple in-memory prompt cache — avoids re-hitting the API for identical prompts
# Entries expire after 10 minutes (600s), which covers rapid repeated test submissions
_CACHE: dict = {}
_CACHE_TTL = 600

# Fallback persona places for when Gemini is rate-limited or unavailable
FALLBACK_PERSONA_PLACES = {
    "Lisbon": {
        "food_lover": [
            {
                "name": "Time Out Market Lisbon",
                "description": "A vibrant food hall showcasing the best of Lisbon's culinary scene with gourmet bites and local flavours.",
                "address": "Avenida 24 de Julho, Lisbon",
                "types": ["market", "food_court"],
                "coordinates": "38.7068,-9.1453",
                "search_query": "lisbon market food"
            },
            {
                "name": "Pastéis de Belém",
                "description": "The iconic custard tart bakery that defines Portuguese pastry tradition since 1837.",
                "address": "Belem, Lisbon",
                "types": ["bakery", "restaurant"],
                "coordinates": "38.6988,-9.2065",
                "search_query": "lisbon pastry bakery"
            },
            {
                "name": "Mercado da Ribeira",
                "description": "Historic riverside market buzzing with fresh produce, seafood, and authentic local energy.",
                "address": "Avenida 24 de Julho, Lisbon",
                "types": ["market", "food_market"],
                "coordinates": "38.7066,-9.1455",
                "search_query": "lisbon ribeira market"
            },
            {
                "name": "Manteigaria",
                "description": "A beloved neighborhood café and pastry shop perfect for a quick Portuguese coffee moment.",
                "address": "Baixa Pombalina, Lisbon",
                "types": ["café", "bakery"],
                "coordinates": "38.7147,-9.1397",
                "search_query": "lisbon cafe pastry"
            },
            {
                "name": "Afonso e Café",
                "description": "Cozy vintage café in Chiado serving excellent coffee and local sweets in a charming setting.",
                "address": "Chiado, Lisbon",
                "types": ["café", "restaurant"],
                "coordinates": "38.7143,-9.1448",
                "search_query": "lisbon vintage cafe"
            }
        ],
        "culture_seeker": [
            {
                "name": "Mosteiro dos Jerónimos",
                "description": "A UNESCO World Heritage monastery with stunning Manueline architecture and centuries of history.",
                "address": "Belém, Lisbon",
                "types": ["museum", "historic_site"],
                "coordinates": "38.6983,-9.2067",
                "search_query": "lisbon monastery architecture"
            },
            {
                "name": "Azulejo Museum",
                "description": "World's finest collection of Portuguese tiles showcasing centuries of azulejo artistry.",
                "address": "Convento da Madre de Deus, Lisbon",
                "types": ["museum", "art_gallery"],
                "coordinates": "38.7197,-9.1114",
                "search_query": "lisbon azulejo tiles museum"
            },
            {
                "name": "Praça do Comércio",
                "description": "Lisbon's grandest waterfront square with neoclassical architecture and iconic riverside views.",
                "address": "Ribeira, Lisbon",
                "types": ["tourist_attraction", "historical_landmark"],
                "coordinates": "38.7072,-9.1366",
                "search_query": "lisbon praca commerce square"
            },
            {
                "name": "Miradouro de Santa Catarina",
                "description": "A cherished viewpoint overlooking the Tejo River and city rooftops with classic Lisbon views.",
                "address": "Bairro Alto, Lisbon",
                "types": ["viewpoint", "tourist_attraction"],
                "coordinates": "38.7089,-9.1482",
                "search_query": "lisbon viewpoint river"
            },
            {
                "name": "Alfama Old Town",
                "description": "The oldest neighbourhood with winding tiled streets, fado music soul, and authentic local character.",
                "address": "Alfama, Lisbon",
                "types": ["neighborhood", "tourist_attraction"],
                "coordinates": "38.7124,-9.1306",
                "search_query": "lisbon alfama neighborhood"
            }
        ],
        "nature_wanderer": [
            {
                "name": "Jerónimos Park",
                "description": "Lush waterfront park with manicured gardens and serene riverside walking paths.",
                "address": "Belém, Lisbon",
                "types": ["park", "garden"],
                "coordinates": "38.6970,-9.2085",
                "search_query": "lisbon park gardens"
            },
            {
                "name": "Miradouro da Senhora do Monte",
                "description": "One of Lisbon's highest viewpoints offering panoramic vistas of the entire city and Tejo.",
                "address": "Graça, Lisbon",
                "types": ["viewpoint", "natural_landmark"],
                "coordinates": "38.7225,-9.1308",
                "search_query": "lisbon viewpoint panorama"
            },
            {
                "name": "Tapada das Necessidades",
                "description": "A hidden historic garden oasis with exotic plants, quiet pathways, and peaceful riverside views.",
                "address": "Lapa, Lisbon",
                "types": ["park", "garden"],
                "coordinates": "38.7005,-9.1606",
                "search_query": "lisbon secret garden nature"
            },
            {
                "name": "Parque da Malagueira",
                "description": "Contemporary urban park blending nature with sculpture and riverside walks along the Tejo.",
                "address": "Oriente, Lisbon",
                "types": ["park", "art_park"],
                "coordinates": "38.7610,-9.1005",
                "search_query": "lisbon modern park"
            },
            {
                "name": "Cristo Rei Viewpoint",
                "description": "Iconic landmark with sweeping 360-degree views of Lisbon and the bridge from across the river.",
                "address": "Caparica, Lisbon",
                "types": ["viewpoint", "landmark"],
                "coordinates": "38.6805,-9.1654",
                "search_query": "lisbon cristo rei statue"
            }
        ],
        "checklist_traveler": [
            {
                "name": "Cristo Rei Statue",
                "description": "Lisbon's most iconic monument—a massive statue overlooking the city like a guardian.",
                "address": "Caparica, Lisbon",
                "types": ["landmark", "monument"],
                "coordinates": "38.6805,-9.1654",
                "search_query": "lisbon cristo rei statue"
            },
            {
                "name": "25 de Abril Bridge",
                "description": "The famous red suspension bridge instantly recognizable as Lisbon's symbol.",
                "address": "Ribeira, Lisbon",
                "types": ["landmark", "engineering"],
                "coordinates": "38.7095,-9.1641",
                "search_query": "lisbon red bridge suspension"
            },
            {
                "name": "Torre de Belém",
                "description": "A UNESCO fortress tower from 1515 guarding the Tejo mouth—Lisbon's most photographed monument.",
                "address": "Belém, Lisbon",
                "types": ["historic_site", "monument"],
                "coordinates": "38.6920,-9.2162",
                "search_query": "lisbon torre belem tower"
            },
            {
                "name": "Praça do Comércio",
                "description": "Lisbon's most photographed square—a vast neoclassical waterfront plaza that defines the city.",
                "address": "Ribeira, Lisbon",
                "types": ["historic_site", "landmark"],
                "coordinates": "38.7072,-9.1366",
                "search_query": "lisbon praca commerce palace"
            },
            {
                "name": "Castelo de São Jorge",
                "description": "A hilltop castle with 11 centuries of history offering panoramic city views.",
                "address": "Castelo, Lisbon",
                "types": ["historic_site", "castle"],
                "coordinates": "38.7141,-9.1338",
                "search_query": "lisbon castle sao jorge"
            }
        ]
    },
    "Amsterdam": {
        "food_lover": [
            {
                "name": "Albert Cuyp Market",
                "description": "Amsterdam's largest and most vibrant street market with food stalls, local snacks, and authentic Dutch energy.",
                "address": "Albert Cuyp Straat, Amsterdam",
                "types": ["market", "food_market"],
                "coordinates": "52.3644,4.8910",
                "search_query": "amsterdam market food stalls"
            },
            {
                "name": "Stroopwafels Stand",
                "description": "Street vendor serving Amsterdam's signature sweet waffle treat fresh and warm.",
                "address": "Dam Square, Amsterdam",
                "types": ["street_food", "bakery"],
                "coordinates": "52.3730,4.8925",
                "search_query": "amsterdam stroopwafel sweet treat"
            },
            {
                "name": "Café de Jaren",
                "description": "A iconic riverside café perfect for Dutch pancakes and local pastries with waterway views.",
                "address": "Prins Hendrikkade 20, Amsterdam",
                "types": ["café", "restaurant"],
                "coordinates": "52.3758,4.9034",
                "search_query": "amsterdam cafe pancakes"
            },
            {
                "name": "Cheese Museum",
                "description": "Experience authentic Dutch cheese culture with tastings of world-famous varieties.",
                "address": "Prinsengracht 440, Amsterdam",
                "types": ["museum", "food"],
                "coordinates": "52.3716,4.8813",
                "search_query": "amsterdam cheese tasting"
            },
            {
                "name": "Bloemenmarkt Floating Market",
                "description": "Unique floating flower and plant market selling tulips, bulbs, and Dutch botanical treasures.",
                "address": "Singel Canal, Amsterdam",
                "types": ["market", "flower_market"],
                "coordinates": "52.3643,4.8960",
                "search_query": "amsterdam flower market floating"
            }
        ],
        "culture_seeker": [
            {
                "name": "Anne Frank House",
                "description": "The poignant historical museum preserving the diary and hiding place of Anne Frank.",
                "address": "Prinsengracht 263, Amsterdam",
                "types": ["museum", "historic_site"],
                "coordinates": "52.3750,4.8840",
                "search_query": "amsterdam anne frank house"
            },
            {
                "name": "Rijksmuseum",
                "description": "Netherlands' most famous art museum showcasing Rembrandt, Vermeer, and Dutch golden age masterpieces.",
                "address": "Museumplein 1, Amsterdam",
                "types": ["museum", "art_gallery"],
                "coordinates": "52.3603,4.8852",
                "search_query": "amsterdam rijks museum art"
            },
            {
                "name": "Van Gogh Museum",
                "description": "The world's finest collection of Vincent van Gogh paintings and letters in a converted theatre.",
                "address": "Museumplein 6, Amsterdam",
                "types": ["museum", "art_gallery"],
                "coordinates": "52.3585,4.8810",
                "search_query": "amsterdam van gogh museum"
            },
            {
                "name": "Canal Ring",
                "description": "UNESCO World Heritage canal system with 17th-century architecture forming Amsterdam's romantic heart.",
                "address": "Grachten, Amsterdam",
                "types": ["historic_site", "neighborhood"],
                "coordinates": "52.3640,4.8860",
                "search_query": "amsterdam canal architecture historic"
            },
            {
                "name": "Amsterdam Museum",
                "description": "Comprehensive museum telling the story of Amsterdam from medieval times to present day.",
                "address": "Kalverstraat 92, Amsterdam",
                "types": ["museum", "history"],
                "coordinates": "52.3707,4.8935",
                "search_query": "amsterdam history museum"
            }
        ],
        "nature_wanderer": [
            {
                "name": "Vondelpark",
                "description": "Amsterdam's most popular park with tree-lined paths, ponds, and open green spaces perfect for wandering.",
                "address": "Vondelpark, Amsterdam",
                "types": ["park", "garden"],
                "coordinates": "52.3584,4.8704",
                "search_query": "amsterdam vondelpark nature"
            },
            {
                "name": "Waterland Countryside",
                "description": "Rural landscape just north of Amsterdam with windmills, farmland, and serene waterway scenery.",
                "address": "Waterland, Amsterdam",
                "types": ["park", "natural_landscape"],
                "coordinates": "52.4000,4.9000",
                "search_query": "amsterdam waterland countryside"
            },
            {
                "name": "Oost Park",
                "description": "East-side park with lakes, wildlife, and peaceful walking paths away from city crowds.",
                "address": "Oost Park, Amsterdam",
                "types": ["park", "nature_reserve"],
                "coordinates": "52.3596,4.8947",
                "search_query": "amsterdam east park nature"
            },
            {
                "name": "Botanical Gardens",
                "description": "Historic gardens with exotic plants, glasshouses, and rare botanical specimens from around the world.",
                "address": "Plantage Middenlaan 2, Amsterdam",
                "types": ["garden", "botanical"],
                "coordinates": "52.3663,4.9134",
                "search_query": "amsterdam botanical garden plants"
            },
            {
                "name": "Zaanse Schans",
                "description": "Living museum with working windmills, traditional houses, and pastoral Dutch countryside atmosphere.",
                "address": "Zaanse Schans, near Amsterdam",
                "types": ["museum", "historic_village"],
                "coordinates": "52.4347,4.7863",
                "search_query": "amsterdam windmills historic village"
            }
        ],
        "checklist_traveler": [
            {
                "name": "Windmills of Kinderdijk",
                "description": "UNESCO World Heritage site with 19 iconic windmills—the most famous Dutch symbol.",
                "address": "Kinderdijk, near Amsterdam",
                "types": ["landmark", "historic_site"],
                "coordinates": "51.8743,4.6456",
                "search_query": "amsterdam kinderdijk windmills"
            },
            {
                "name": "Dam Square",
                "description": "Amsterdam's most iconic square surrounded by historic buildings and the Royal Palace.",
                "address": "Dam Square, Amsterdam",
                "types": ["landmark", "historic_site"],
                "coordinates": "52.3730,4.8925",
                "search_query": "amsterdam dam square palace"
            },
            {
                "name": "Canal Boat Tour",
                "description": "The quintessential Amsterdam experience—gliding through UNESCO canals seeing the city from the water.",
                "address": "Various docks, Amsterdam",
                "types": ["tour", "experience"],
                "coordinates": "52.3640,4.8860",
                "search_query": "amsterdam canal boat tour"
            },
            {
                "name": "Begijnhof",
                "description": "A hidden historic courtyard in the city centre dating back to the 14th century with charming architecture.",
                "address": "Begijnhof, Amsterdam",
                "types": ["historic_site", "courtyard"],
                "coordinates": "52.3690,4.8935",
                "search_query": "amsterdam begijnhof courtyard historic"
            },
            {
                "name": "St. Nicholas Basilica",
                "description": "A magnificent neo-Renaissance church overlooking Central Station—iconic Amsterdam landmark.",
                "address": "Prins Hendrikkade 73, Amsterdam",
                "types": ["landmark", "church"],
                "coordinates": "52.3747,4.9024",
                "search_query": "amsterdam church basilica architecture"
            }
        ]
    },
    "Singapore": {
        "food_lover": [
            {
                "name": "Hawker Chan's",
                "description": "The world's cheapest Michelin-star restaurant—authentic Singaporean chicken rice at its finest.",
                "address": "Chinatown Food Complex, Singapore",
                "types": ["restaurant", "street_food"],
                "coordinates": "1.4455,103.8425",
                "search_query": "singapore hawker food stall"
            },
            {
                "name": "Maxwell Food Centre",
                "description": "Legendary hawker market where locals queue for iconic dishes and authentic street food.",
                "address": "Maxwell Road, Singapore",
                "types": ["market", "food_court"],
                "coordinates": "1.4442,103.8374",
                "search_query": "singapore maxwell market food"
            },
            {
                "name": "Jalan Alor Street Food",
                "description": "A vibrant alley of food stalls serving grilled satay, noodles, and Malaysian-influenced Singaporean cuisine.",
                "address": "Kuala Lumpur - nearby equivalent in Singapore",
                "types": ["street_food", "market"],
                "coordinates": "1.4388,103.8517",
                "search_query": "singapore street food stalls"
            },
            {
                "name": "Peranakan Museum & Tea House",
                "description": "Experience traditional Peranakan culture with local delicacies and cultural immersion.",
                "address": "Peranakan Museum, Singapore",
                "types": ["museum", "restaurant"],
                "coordinates": "1.3948,103.8392",
                "search_query": "singapore peranakan culture food"
            },
            {
                "name": "Satay by the Bay",
                "description": "Beachfront dining with grilled satay, local seafood, and sunset views over Marina Bay.",
                "address": "Marina Bay, Singapore",
                "types": ["restaurant", "food_court"],
                "coordinates": "1.3544,103.8597",
                "search_query": "singapore satay bay marina"
            }
        ],
        "culture_seeker": [
            {
                "name": "National Museum of Singapore",
                "description": "Comprehensive museum presenting Singapore's rich history from colonial times to modern nation.",
                "address": "National Museum Road, Singapore",
                "types": ["museum", "history"],
                "coordinates": "1.2955,103.8173",
                "search_query": "singapore national museum history"
            },
            {
                "name": "Thian Hock Keng Temple",
                "description": "Singapore's oldest Chinese temple with intricate architecture and spiritual significance.",
                "address": "Telok Ayer Street, Singapore",
                "types": ["temple", "historic_site"],
                "coordinates": "1.4388,103.8432",
                "search_query": "singapore temple architecture historic"
            },
            {
                "name": "Singapore Art Museum",
                "description": "World-class contemporary and classical Asian art in a converted Catholic mission building.",
                "address": "National Library Building, Singapore",
                "types": ["museum", "art_gallery"],
                "coordinates": "1.3527,103.8547",
                "search_query": "singapore art museum contemporary"
            },
            {
                "name": "Chinatown Heritage Centre",
                "description": "Museum preserving the stories and experiences of Chinese immigrants who built Singapore.",
                "address": "Chinatown, Singapore",
                "types": ["museum", "cultural_center"],
                "coordinates": "1.4436,103.8434",
                "search_query": "singapore chinatown heritage"
            },
            {
                "name": "Sri Mariamman Temple",
                "description": "Singapore's oldest Hindu temple with stunning gopuram tower and vibrant Hindu culture.",
                "address": "South Bridge Road, Singapore",
                "types": ["temple", "historic_site"],
                "coordinates": "1.4400,103.8444",
                "search_query": "singapore temple hindu"
            }
        ],
        "nature_wanderer": [
            {
                "name": "Singapore Botanic Gardens",
                "description": "UNESCO World Heritage gardens with lush landscapes, orchid collections, and serene pathways.",
                "address": "Napier Road, Singapore",
                "types": ["garden", "botanical"],
                "coordinates": "1.3136,103.8159",
                "search_query": "singapore botanic gardens nature"
            },
            {
                "name": "Gardens by the Bay",
                "description": "Futuristic gardens with iconic Supertrees, light shows, and botanical wonders.",
                "address": "Marina Bay, Singapore",
                "types": ["garden", "park"],
                "coordinates": "1.3644,103.8641",
                "search_query": "singapore gardens bay nature"
            },
            {
                "name": "MacRitchie Reservoir",
                "description": "Nature reserve with rainforest walks, tree canopy bridges, and freshwater views.",
                "address": "MacRitchie Reservoir, Singapore",
                "types": ["nature_reserve", "park"],
                "coordinates": "1.3453,103.8324",
                "search_query": "singapore macritchie forest nature"
            },
            {
                "name": "East Coast Park",
                "description": "Beachfront park with sandy stretches, cycle paths, and seaside serenity.",
                "address": "East Coast Park, Singapore",
                "types": ["park", "beach"],
                "coordinates": "1.3012,103.9603",
                "search_query": "singapore beach park coastal"
            },
            {
                "name": "Pulau Ubin Island",
                "description": "An off-the-beaten-path island with coastal cliffs, forested paths, and tranquil getaway vibes.",
                "address": "Pulau Ubin, Singapore",
                "types": ["island", "nature_reserve"],
                "coordinates": "1.4024,103.9603",
                "search_query": "singapore island nature forest"
            }
        ],
        "checklist_traveler": [
            {
                "name": "Merlion Statue",
                "description": "Singapore's most iconic monument—a mythical lion-fish hybrid overlooking Marina Bay.",
                "address": "Merlion Park, Singapore",
                "types": ["landmark", "monument"],
                "coordinates": "1.3456,103.8542",
                "search_query": "singapore merlion statue icon"
            },
            {
                "name": "Marina Bay Sands",
                "description": "Singapore's most recognizable hotel with sky-high rooftop infinity pool and city views.",
                "address": "Marina Bay Sands, Singapore",
                "types": ["landmark", "hotel"],
                "coordinates": "1.2858,103.8581",
                "search_query": "singapore marina bay sands"
            },
            {
                "name": "Singapore Flyer",
                "description": "World's tallest observation wheel offering 360-degree views of the city and surroundings.",
                "address": "Marina Bay, Singapore",
                "types": ["landmark", "observation_wheel"],
                "coordinates": "1.3715,103.8554",
                "search_query": "singapore flyer observation wheel"
            },
            {
                "name": "Sentosa Island",
                "description": "A major resort island with beaches, attractions, and iconic Singapore experiences.",
                "address": "Sentosa Island, Singapore",
                "types": ["island", "resort"],
                "coordinates": "1.2495,103.8310",
                "search_query": "singapore sentosa island resort"
            },
            {
                "name": "Raffles Hotel",
                "description": "Historic iconic hotel in Singapore's colonial district where the Singapore Sling cocktail was invented.",
                "address": "Beach Road, Singapore",
                "types": ["landmark", "historic_hotel"],
                "coordinates": "1.3553,103.8567",
                "search_query": "singapore raffles hotel historic"
            }
        ]
    }
}

def _get_fallback_persona_places(airport_city: str, persona_key: str) -> List[dict]:
    """Get fallback places for when Gemini is unavailable."""
    city_places = FALLBACK_PERSONA_PLACES.get(airport_city, {})
    return city_places.get(persona_key, [])


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


def _call_gemini(prompt: str, model: str = PRIMARY_MODEL, call_name: str = "gemini") -> str:
    """Make a single REST call to Gemini and return the text response."""
    url = GEMINI_API_URL.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7},
    }
    response = httpx.post(url, params={"key": GOOGLE_GEMINI_API_KEY}, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    _log_tokens(call_name, model, data.get("usageMetadata", {}))
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_gemini_with_fallback(prompt: str, call_name: str = "gemini") -> str:
    """Try primary model, fall back to lite on failure. Caches results to avoid repeat hits."""
    cached = _cache_get(prompt)
    if cached is not None:
        return cached
    try:
        result = _call_gemini(prompt, PRIMARY_MODEL, call_name=call_name)
    except Exception as e:
        print(f"WARNING: Primary model failed ({e}), trying fallback")
        result = _call_gemini(prompt, FALLBACK_MODEL, call_name=call_name)
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
            text = _call_gemini_with_fallback(prompt_text, call_name="generate_activities")

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
            return _call_gemini_with_fallback(prompt_text, call_name="generate_verdict_copy")[:100]
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
            text = _call_gemini_with_fallback(prompt_text, call_name="generate_place_descriptions_batch")
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
            text = _call_gemini_with_fallback(prompt_text, call_name="generate_persona_places")
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            places = json.loads(text)
            return places[:5]
        except Exception as e:
            print(f"WARNING: Gemini persona places generation failed: {e}, using fallback places")
            fallback = _get_fallback_persona_places(airport_city, persona_key)
            return fallback if fallback else []

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