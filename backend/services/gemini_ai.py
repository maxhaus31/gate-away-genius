"""
Gemini AI Service: Generate activity recommendations with coordinates using LangChain
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from config import GOOGLE_GEMINI_API_KEY
from typing import List
import json


class Activity(BaseModel):
    """Pydantic model for activity structure"""
    emoji: str = Field(..., description="Single emoji representing the activity")
    title: str = Field(..., description="Activity name")
    description: str = Field(..., description="What you'll do and why it's worth seeing")
    minTimeNeeded: int = Field(..., description="Time needed in minutes")
    latitude: float = Field(..., description="GPS latitude (-90 to 90)")
    longitude: float = Field(..., description="GPS longitude (-180 to 180)")


class GeminiActivityService:
    """Service to generate AI-powered activity recommendations using LangChain"""
    
    def __init__(self):
        """Initialize LangChain chat model"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=GOOGLE_GEMINI_API_KEY,
            temperature=0.7,
        )
        self.parser = PydanticOutputParser(pydantic_object=Activity)
    
    def generate_activities(
        self,
        airport_city: str,
        available_minutes: int,
        passport_region: str,
        airport_iata: str,
    ) -> List[dict]:
        """
        Ask Gemini for activity recommendations in the city using LangChain
        
        Args:
            airport_city: City name (e.g., "Lisbon", "Amsterdam")
            available_minutes: Time available for activities (after buffers)
            passport_region: Passport region (e.g., "EU", "US")
            airport_iata: Airport code (e.g., "AMS")
        
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
            prompt = PromptTemplate(
                template=prompt_text,
                input_variables=[],
            )
            
            # Generate content with LangChain
            response = self.llm.invoke(prompt_text)
            text = response.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            activities = json.loads(text)
            
            # Validate structure
            validated_activities = []
            for activity in activities:
                try:
                    # Validate using Pydantic model
                    validated = Activity(**activity)
                    validated_activities.append(validated.model_dump())
                except Exception as e:
                    print(f"⚠️ Activity validation failed: {e}")
                    continue
            
            return validated_activities[:3]  # Return max 3 activities
            
        except Exception as e:
            print(f"⚠️ Gemini activity generation failed: {e}")
            return self._fallback_activities(airport_city)
    
    def generate_verdict_copy(
        self,
        verdict: str,
        available_minutes: int,
        airport_city: str,
        activities: List[dict],
    ) -> str:
        """
        Generate witty, personalized copy for the verdict using LangChain
        
        Args:
            verdict: "safe", "tight", or "stay"
            available_minutes: City time available
            airport_city: City name
            activities: List of recommended activities
        
        Returns:
            1-sentence witty verdict
        """
        
        activity_names = [a.get("title", "activity") for a in activities[:2]]
        activity_str = " + ".join(activity_names) if activity_names else "exploration"
        
        if verdict == "safe":
            prompt_text = f"Write ONE witty, encouraging sentence telling someone they can absolutely do {activity_str} in {airport_city} with {available_minutes} minutes to spare. Be confident. Max 15 words. No markdown."
        elif verdict == "tight":
            prompt_text = f"Write ONE witty sentence about how someone can *squeeze in* {activity_str} in {airport_city} with {available_minutes} minutes, but they'll need to move. Max 15 words. No markdown."
        else:  # stay
            prompt_text = f"Write ONE witty sentence telling someone they should probably just stay in the airport and relax with a coffee. {airport_city} will still be there another time. Max 15 words. No markdown."
        
        try:
            response = self.llm.invoke(prompt_text)
            return response.content.strip()[:100]  # Cap at 100 chars for safety
        except Exception as e:
            print(f"⚠️ Gemini verdict generation failed: {e}")
            return self._fallback_copy(verdict, available_minutes, airport_city)
    
    def _fallback_activities(self, airport_city: str) -> List[dict]:
        """Return hardcoded activities if Gemini fails"""
        return [
            {
                "emoji": "☕",
                "title": "Airport Café",
                "description": f"Grab a coffee and relax before your next flight",
                "minTimeNeeded": 20,
                "latitude": 0.0,
                "longitude": 0.0,
            }
        ]
    
    def _fallback_copy(self, verdict: str, minutes: int, city: str) -> str:
        """Return hardcoded copy if Gemini fails"""
        if verdict == "safe":
            return f"You've got time! Quick {city} adventure incoming ✈️"
        elif verdict == "tight":
            return f"Tight timeline but doable—move fast! ⏰"
        else:
            return f"Stay cozy in the airport, {city} can wait 😊"
    
    def generate_place_description(
        self,
        place_name: str,
        place_types: List[str],
        rating: float,
        user_ratings_total: int,
    ) -> str:
        """
        Generate a witty description for a place based on its data
        
        Args:
            place_name: Name of the place
            place_types: Types/categories of the place
            rating: Google rating (1-5)
            user_ratings_total: Number of reviews
        
        Returns:
            Short witty description
        """
        place_type = place_types[0] if place_types else "attraction"
        
        prompt_text = f"Write ONE short, witty description (max 10 words) for '{place_name}', a {place_type} with {rating}/5 stars from {user_ratings_total} visitors. Make it compelling and fun."
        
        try:
            response = self.llm.invoke(prompt_text)
            return response.content.strip()[:80]  # Cap at 80 chars
        except Exception as e:
            print(f"⚠️ Place description generation failed: {e}")
            return f"{place_name} - {rating}/5 stars ({user_ratings_total} reviews)"
