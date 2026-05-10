import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
SCHIPHOL_APP_ID = os.getenv("SCHIPHOL_APP_ID")
SCHIPHOL_APP_KEY = os.getenv("SCHIPHOL_APP_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# Server config
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")