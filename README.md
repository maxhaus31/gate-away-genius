# GateAway Genius

**Your AI-powered layover planner.** Get instant, personalized recommendations on whether you have time to safely leave the airport during your connection.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [Running the App](#running-the-app)
- [Project Status](#project-status)
- [API Documentation](#api-documentation)

---

## 🚀 Quick Start

**Prerequisites:** Node.js, Python 3.10+, Bun (or npm)

### Setup & Run (Two Terminals)

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs at: `http://localhost:8000`

**Terminal 2 — Frontend (from root):**
```bash
npm install
npm run dev
```

**Then open in browser:**
```
http://localhost:8080
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Frontend (React + TypeScript)              │
│              http://localhost:8080                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Input: Flight Info + Passport + Desired Activity     │
│  ↓                                                           │
│  [Calls POST /api/plan]                                     │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                Backend (Python FastAPI)                     │
│              http://localhost:8000                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Fetch flight data (AviationStack API)                   │
│  2. Calculate transit times (Google Maps API)               │
│  3. Apply airport rules + safety logic                      │
│  4. Call Gemini AI for personalized verdict                 │
│  ↓                                                           │
│  Response: Safe/Tight/Stay + Timeline + Suggestions        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠 Setup Instructions

### Prerequisites
- **Node.js** (for frontend)
- **Python 3.10+** (for backend)
- **Git** (to clone repo)

### Step 1: Clone Repository

```bash
git clone https://github.com/maxhaus31/gate-away-genius.git
cd gate-away-genius
```

### Step 2: Frontend Setup

```bash
npm install  # or: bun install
```

### Step 3: Backend Setup

```bash
cd backend

# Create Python virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Return to project root
cd ..
```

### Step 4: Configure API Keys

```bash
# Copy example file
cp backend/.env.example backend/.env

# Edit backend/.env with your API keys:
```

Edit `backend/.env`:
```
GOOGLE_GEMINI_API_KEY=sk-proj-...
AVIATIONSTACK_API_KEY=...
GOOGLE_MAPS_API_KEY=...
DEBUG=True
FRONTEND_URL=http://localhost:8080
```

Get keys from:
- **Gemini:** [Google AI Studio](https://aistudio.google.com/app/apikey)
- **AviationStack:** [aviationstack.com](https://aviationstack.com)
- **Google Maps:** [Google Cloud Console](https://console.cloud.google.com/)

---

## ▶️ Running the App

### Option 1: Two Terminal Windows (Recommended)

**Terminal 1:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Terminal 2:**
```bash
npm run dev
```

**Open:** `http://localhost:8080`

### Option 2: Manual One-by-One

```bash
# Install dependencies
npm install
cd backend && pip install -r requirements.txt && cd ..

# Backend
cd backend && source venv/bin/activate && python main.py

# Frontend (in new terminal)
npm run dev
```

---

## 📊 Project Status

### ✅ Phase 1: Backend Skeleton (Completed)

- [x] FastAPI app setup (`main.py`, `config.py`, `models.py`)
- [x] CORS configuration for frontend communication
- [x] Mock `/api/plan` endpoint
- [x] `/api/airports` endpoint
- [x] Environment variables & API key management
- [x] Health check endpoint (`/health`)

### 🚧 Phase 2: External API Integration (Next)

- [ ] AviationStack service — fetch real flight data
- [ ] Google Maps Distance Matrix — calculate transit times
- [ ] Airport data service — re-entry rules, activities per airport
- [ ] Mock data for testing (since free tier has limitations)

### ⏳ Phase 3: Gemini AI Integration

- [ ] Create `services/gemini_ai.py`
- [ ] Design system prompt with airport rules
- [ ] Implement verdict logic: "Safe" / "Tight" / "Stay"
- [ ] Implement suggestion ranking

### 📱 Phase 4: Frontend Integration

- [ ] Create `src/api/client.ts` — API client
- [ ] Update `PlannerForm.tsx` to call backend
- [ ] Update `Index.tsx` to handle API responses
- [ ] Loading & error states
- [ ] Graceful fallback if backend unavailable

### 🧪 Phase 5: Testing & Deployment

- [ ] Unit tests (backend services)
- [ ] Integration tests (full API flow)
- [ ] Frontend tests (form submission)
- [ ] Deploy backend to Render.com
- [ ] Deploy frontend to Vercel
- [ ] Set up CI/CD with GitHub Actions

---

## 🔌 API Endpoints

### Health Check
```
GET /health
```
Returns: `{"status":"ok"}`

### List Airports
```
GET /api/airports
```

### Get Airport Details
```
GET /api/airports/{airport_code}
```
Example: `GET /api/airports/LIS`

### Create Layover Plan (Main)
```
POST /api/plan
Content-Type: application/json

{
  "arrival_time": "2024-05-01T10:00:00",
  "departure_time": "2024-05-01T14:00:00",
  "airport_code": "LIS",
  "passport_region": "EU"
}
```

**Response:**
```json
{
  "verdict": "safe",
  "verdict_description": "You have enough time...",
  "available_time_minutes": 180,
  "timeline": [
    {"label": "Security", "duration_minutes": 15, "color": "red"}
  ],
  "suggestions": [
    {"emoji": "🍷", "name": "Wine Tasting", "duration_minutes": 60}
  ]
}
```

### Interactive API Docs
```
http://localhost:8000/docs
```
Visit this URL to test endpoints in Swagger UI (auto-generated by FastAPI).

---

## 🧪 Testing

### Test AviationStack Connection
```bash
cd backend
source venv/bin/activate
python test_aviationstack.py
```

### Test Backend Locally
```bash
# Backend is running on http://localhost:8000
# Try these URLs:
http://localhost:8000/health
http://localhost:8000/api/airports
http://localhost:8000/docs
```

---

## 📁 Project Structure

```
gate-away-genius/
├── src/                           # Frontend (React + TypeScript)
│   ├── components/
│   │   ├── gateaway/
│   │   │   ├── Header.tsx
│   │   │   ├── PlannerForm.tsx    # User input form
│   │   │   ├── Verdict.tsx        # Safe/Tight/Stay verdict
│   │   │   ├── Timeline.tsx       # Visual timeline
│   │   │   └── Suggestions.tsx    # Activity recommendations
│   │   └── ui/                    # shadcn UI components
│   ├── lib/
│   │   ├── gateaway-data.ts      # Static data (moving to backend)
│   │   └── utils.ts
│   └── pages/
│       ├── Index.tsx              # Main page
│       └── NotFound.tsx
│
├── backend/                       # Backend (Python FastAPI)
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # Environment config
│   ├── models.py                 # Pydantic schemas
│   ├── requirements.txt          # Python deps
│   ├── .env                      # API keys (git-ignored)
│   ├── .env.example              # Template
│   │
│   ├── services/                 # Business logic
│   │   ├── flight_data.py        # Flight info (Phase 2)
│   │   ├── google_maps.py        # Transit times (Phase 2)
│   │   ├── airport_data.py       # Airport rules (Phase 2)
│   │   ├── gemini_ai.py          # AI reasoning (Phase 3)
│   │   └── planner.py            # Core logic (Phase 3)
│   │
│   └── routes/                   # API routes
│       └── planner.py            # /api/plan endpoint
│
├── package.json                  # Frontend deps
├── vite.config.ts                # Vite config
├── tsconfig.json                 # TypeScript config
├── tailwind.config.ts            # Tailwind CSS
└── README.md                      # This file
```

---

## 🚀 Deployment

### Backend → Render.com

1. Push code to GitHub
2. Create account at [render.com](https://render.com)
3. Connect GitHub repo
4. Set environment variables in Render dashboard
5. Deploy!

Backend URL: `https://gate-away-genius-backend.onrender.com`

### Frontend → Vercel

1. Create account at [vercel.com](https://vercel.com)
2. Import GitHub repo
3. Set `VITE_API_URL=https://gate-away-genius-backend.onrender.com`
4. Deploy!

Frontend URL: `https://gate-away-genius.vercel.app`

---

## 📚 Resources

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Google Gemini API](https://ai.google.dev/)
- [React Docs](https://react.dev)
- [Vite Guide](https://vitejs.dev)
- [shadcn/ui](https://ui.shadcn.com)
- [Tailwind CSS](https://tailwindcss.com)

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Commit: `git commit -m "Add description"`
4. Push: `git push origin feature/your-feature`
5. Open Pull Request

---

## 📝 License

MIT License

---

**Happy layover planning! ✈️**
