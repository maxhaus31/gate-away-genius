"""
Gemini AI Service: Generate personalized layover verdicts and recommendations
"""

import google.generativeai as genai
from config import GOOGLE_GEMINI_API_KEY
from typing import Literal


class GeminiVerdictService:
    """Service to generate AI-powered layover verdicts"""
    
    def __init__(self):
        if GOOGLE_GEMINI_API_KEY:
            genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
        # Use gemini-2.0-flash or gemini-1.5-pro if available
        try:
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        except:
            self.model = genai.GenerativeModel("gemini-1.5-pro")
    
    def generate_verdict(
        self,
        airport_city: str,
        available_minutes: int,
        passport_region: str,
        airport_vibe: str,
        activity_suggestions: list,
    ) -> dict:
        """
        Generate a personalized verdict and enhanced description using Gemini
        
        Args:
            airport_city: City name (e.g., "Lisbon")
            available_minutes: Total time available (e.g., 180)
            passport_region: Passport region (e.g., "EU")
            airport_vibe: Airport vibe description
            activity_suggestions: List of activity dicts with emoji, title, min_time_needed
        
        Returns:
            {
                "verdict": "safe|tight|stay",
                "verdict_description": "...",
                "enhanced_message": "..."
            }
        """
        
        # Determine verdict based on time
        if available_minutes >= 180:
            verdict = "safe"
            time_assessment = "you have plenty of time"
        elif available_minutes >= 120:
            verdict = "tight"
            time_assessment = "you're cutting it close"
        else:
            verdict = "stay"
            time_assessment = "you should really stay at the airport"
        
        # Build prompt for Gemini
        activities_str = "\n".join([
            f"  • {s['emoji']} {s['title']} ({s['min_time_needed']} min)"
            for s in activity_suggestions[:3]
        ])
        
        prompt = f"""You are a witty travel advisor. Give a SHORT, punchy 1-sentence verdict about whether someone should leave the airport during a {available_minutes}-minute layover in {airport_city}.

Context:
- Passport: {passport_region}
- Available time: {available_minutes} minutes
- Airport vibe: {airport_vibe}
- Possible activities:
{activities_str}

Your verdict style:
- If {available_minutes} >= 180: They can definitely go out ("You have {available_minutes - 60} glorious minutes...")
- If {available_minutes} >= 120: It's risky but possible ("You *could* rush into the city...")
- If {available_minutes} < 120: Stay put ("Better to grab a drink at the airport...")

Keep it to ONE sentence max, be encouraging but honest."""

        try:
            response = self.model.generate_content(prompt)
            enhanced_message = response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            enhanced_message = self._fallback_message(verdict, available_minutes, airport_city)
        
        # Create verdict description based on verdict type
        if verdict == "safe":
            verdict_description = f"You have {available_minutes} minutes to leave {airport_city}'s airport and return. That's plenty of time!"
        elif verdict == "tight":
            verdict_description = f"With {available_minutes} minutes, you could technically explore {airport_city}, but you'd need to move fast."
        else:  # stay
            verdict_description = f"With only {available_minutes} minutes, it's safest to stay at the airport. Grab food and relax!"
        
        return {
            "verdict": verdict,
            "verdict_description": verdict_description,
            "enhanced_message": enhanced_message,
        }
    
    @staticmethod
    def _fallback_message(verdict: str, minutes: int, city: str) -> str:
        """Fallback message if Gemini fails"""
        if verdict == "safe":
            return f"You've got {minutes} solid minutes in {city}. Time to explore!"
        elif verdict == "tight":
            return f"Possible to leave, but you'll need to hustle in {city}. Go quick."
        else:
            return f"Play it safe and stay at the airport. Next time, {city} awaits!"
