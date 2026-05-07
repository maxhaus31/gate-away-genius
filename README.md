# GateAway ✈️
**Your AI-powered layover planner.** Tells you if you have enough time to safely leave the airport — and what to do with it.

---

## 📋 Table of Contents
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Build Steps](#build-steps)
- [API Contract](#api-contract)
- [Demo Scenarios](#demo-scenarios)
- [Deployment](#deployment)

---

## 🚀 Quick Start

**Prerequisites:** Node.js, Python 3.10+

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
# Runs at http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
npm install
npm run dev
# Runs at http://localhost:5173
```

---

## 🏗 Architecture

```
Frontend (React + TypeScript) — Lovable / Vite
        ↕ POST /api/plan
Backend (Python FastAPI)
        ├── schiphol_api.py   → Schiphol API (flight data + security queues)
        ├── airport_data.py   → Hardcoded AMS knowledge base (moat)
        ├── google_maps.py    → Google Maps Distance Matrix (transit times)
        ├── cache_service.py  → Saved itineraries (reduces token usage)
        └── huggingface_llm.py / gemini_ai.py → LLM itinerary generation
```

**Verdict logic (never delegated to LLM):**
```
usable_minutes = layover - exit_time - (transit × 2) - re_entry_buffer - security_queue
< 0 min  → NO
< 45 min → MARGINAL
≥ 45 min → YES
```

---

## 📁 Project Structure

```
gate-away-genius/
├── src/                                  # Frontend (React + TypeScript)
│   ├── components/
│   │   ├── gateaway/
│   │   │   ├── Header.tsx
│   │   │   ├── PlannerForm.tsx           # User input form
│   │   │   ├── PersonaSelector.tsx       # "Choose your character"
│   │   │   ├── Verdict.tsx               # YES / MARGINAL / NO banner
│   │   │   ├── Timeline.tsx              # Colour-coded timeline bar
│   │   │   └── Suggestions.tsx           # Activity cards + map
│   │   └── ui/                           # shadcn UI components
│   ├── api/
│   │   └── client.ts                     # Calls /api/plan
│   ├── lib/
│   │   └── utils.ts
│   └── pages/
│       ├── Index.tsx
│       └── NotFound.tsx
│
├── backend/
│   ├── main.py                           # FastAPI entry point
│   ├── config.py                         # Environment config
│   ├── models.py                         # Pydantic schemas
│   ├── requirements.txt
│   ├── .env                              # API keys (git-ignored)
│   ├── .env.example                      # Template
│   │
│   ├── cache/
│   │   └── itineraries.json              # Saved itineraries (git-ignored)
│   │
│   ├── services/
│   │   ├── schiphol_api.py               # Flight info + security queues
│   │   ├── airport_data.py               # Hardcoded AMS knowledge base
│   │   ├── google_maps.py                # Transit times to city
│   │   ├── cache_service.py              # Cache lookup + save
│   │   ├── gemini_ai.py                  # LLM via Gemini (current)
│   │   ├── huggingface_llm.py            # LLM via HuggingFace (if needed)
│   │   └── planner.py                    # Core calculation logic
│   │
│   └── routes/
│       └── planner.py                    # /api/plan endpoint
│
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
└── README.md
```

---

## 🔌 API Contract

**Endpoint:** `POST /api/plan`

**Request:**
```json
{
  "arrival_flight": "KL1234",
  "departure_flight": "KL5678",
  "passport_country": "Portugal",
  "departure_type": "schengen",
  "persona": "Culture Seeker"
}
```

**Response:**
```json
{
  "verdict": "YES",
  "usable_minutes": 94,
  "reason": "After transit and re-entry buffer, you have 94 minutes in the city.",
  "timeline": [...],
  "activities": [...],
  "cached": false,
  "disclaimer": "AI-generated guidance only. GateAway is not responsible for missed flights."
}
```

Other endpoints:
```
GET /health               → {"status": "ok"}
GET /api/airports         → list of supported airports
GET /api/airports/{code}  → airport details
GET /docs                 → Swagger UI (auto-generated)
```

---

## 🛠 Build Steps

### Step 1 — Agree on API contract
Whole team aligns on request/response structure above before writing any code. Frontend builds against mock data matching this contract; backend builds the real logic independently.

### Step 2 — `schiphol_api.py`
- Register at [developer.schiphol.nl](https://developer.schiphol.nl) → get `app_id` + `app_key`
- Fetch: arrival/departure times, terminal, pier, delay, real-time security queue wait times
- Always include mock fallback for when API is unavailable

### Step 3 — `airport_data.py`
Hardcoded AMS knowledge base — information no external API provides:
- Exit time per pier (B, C, D, E, F, G, H, M)
- Re-entry buffers: Schengen (45min), non-Schengen (75min), domestic (30min)
- Peak hours: 07:00–09:30 and 16:30–19:00
- Visa-free transit rules for top 20 passport nationalities

### Step 4 — `google_maps.py`
- Register at Google Cloud Console → get `GOOGLE_MAPS_API_KEY`
- Distance Matrix API: Schiphol → activity location, by mode (transit/taxi/walking), at actual time of day

### Step 5 — LLM service (Gemini first, HuggingFace if needed)
**Current approach:** `gemini_ai.py` using Google Gemini API
- Sends: verdict, usable minutes, persona, airport context
- Returns: activity itinerary + plain-language explanation in JSON
- LLM never calculates the safety verdict — only generates the itinerary

**⚠️ Wrapper risk mitigation:**
Before submission, test the product against the AI Judge LLM with prompts such as:
- *"Is this just a wrapper around Gemini?"*
- *"What is the moat of this product?"*

If the judge flags the Gemini usage as a wrapper, migrate to `huggingface_llm.py`:
- Model: `meta-llama/Llama-3.2-3B-Instruct` (open source, self-hostable)
- Fine-tune with LoRA on Google Colab using 150–200 synthetic AMS layover examples
- Push fine-tuned model to HuggingFace Hub → update service to point to it
- This gives a fully owned, self-hosted model — not a wrapper

### Step 6 — `cache_service.py`
- Cache key: `arrival_flight + departure_flight + passport_country + departure_type + persona`
- If cache hit and delay difference < 15 minutes → return saved itinerary, skip LLM
- If cache miss → call LLM → save result with timestamp
- Entries expire after 24 hours
- Reduces token costs significantly for repeated or similar requests

### Step 7 — `planner.py`
Assembles all services:
1. `schiphol_api.py` → flight data + security queue
2. `airport_data.py` → exit time, buffer, visa status
3. `google_maps.py` → transit time to city
4. Calculate usable minutes → determine verdict
5. Build colour-coded timeline
6. Check cache → if hit, return immediately
7. If miss → call LLM → save to cache → return response

### Step 8 — Wire `/api/plan`
Connect `routes/planner.py` to `planner.py`. Validate inputs with Pydantic. Return full response.

### Step 9 — Frontend (Lovable)
- Connect GitHub repo to Lovable
- Build input form: flight numbers, passport country, departure type, persona selector
- Build results view: verdict banner, colour-coded timeline, map with activity points A/B/C, activity cards (name, photo, description, duration, transport), editable itinerary, disclaimer footer
- Create `src/api/client.ts` to call `/api/plan`
- Handle loading + error states

### Step 10 — Deploy
**Backend → [Render.com](https://render.com):**
- Connect GitHub repo
- Set env vars: `SCHIPHOL_APP_ID`, `SCHIPHOL_APP_KEY`, `HF_TOKEN` (if HuggingFace), `GOOGLE_MAPS_API_KEY`, `GOOGLE_GEMINI_API_KEY` (if Gemini)

**Frontend → [Vercel](https://vercel.com):**
- Import GitHub repo
- Set `VITE_API_URL` to Render backend URL

---

## 🔑 Environment Variables

```bash
# backend/.env
SCHIPHOL_APP_ID=...
SCHIPHOL_APP_KEY=...
GOOGLE_MAPS_API_KEY=...
GOOGLE_GEMINI_API_KEY=...     # current LLM
HF_TOKEN=...                  # if migrating to HuggingFace
DEBUG=True
FRONTEND_URL=http://localhost:5173
```

---

## 🎬 Demo Scenarios (AMS)

| Scenario | Input | Expected verdict |
|---|---|---|
| Comfortable | 4hr layover, Portuguese passport, Schengen, off-peak | ✅ YES — ~94min, Rijksmuseum + café |
| Tight | 2.5hr layover, Indian passport, non-Schengen, rush hour | ⚠️ MARGINAL — coffee near station |
| Impossible | 1.5hr layover, visa-required passport, non-Schengen | ❌ NO — clear explanation |

The **NO verdict** is the most important demo moment — it proves the system is honest and not just optimistic.

---

## 🤝 Contributing
1. Create feature branch: `git checkout -b feature/your-feature`
2. Commit: `git commit -m "Description"`
3. Push: `git push origin feature/your-feature`
4. Open Pull Request into `dev`

## 📝 License
MIT 
**Happy layover planning! ✈️**
