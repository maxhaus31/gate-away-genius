import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Server config
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Validation (optional for now - MVP uses hardcoded rules)
# if not GOOGLE_GEMINI_API_KEY:
#     raise ValueError("GOOGLE_GEMINI_API_KEY not set in .env")