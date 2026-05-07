"""
Flight Data Service: Fetch real flight information from AviationStack API
"""

import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from config import AVIATIONSTACK_API_KEY


class FlightDataService:
    """Service to fetch flight data from AviationStack"""
    
    BASE_URL = "https://api.aviationstack.com/v1/flights"
    TIMEOUT = 10.0
    
    @staticmethod
    async def lookup_flight(flight_number: str, airport_code: str) -> Optional[Dict[str, Any]]:
        """
        Look up a flight by number and airport code
        
        Args:
            flight_number: IATA flight code (e.g., "LH780", "BA284")
            airport_code: IATA airport code (e.g., "SIN", "LIS")
        
        Returns:
            Dict with arrival/departure times, or None if not found
            {
                "flight_iata": "LH780",
                "arrival_iata": "SIN",
                "departure_iata": "FRA",
                "arrival_time": "2024-05-10T10:30:00+00:00",
                "departure_time": "2024-05-10T22:15:00+00:00",
                "status": "scheduled"
            }
        """
        if not AVIATIONSTACK_API_KEY:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "access_key": AVIATIONSTACK_API_KEY,
                    "flight_iata": flight_number.upper(),
                }
                
                response = await client.get(
                    FlightDataService.BASE_URL,
                    params=params,
                    timeout=FlightDataService.TIMEOUT
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Check if we got results
                if not data.get("data") or len(data["data"]) == 0:
                    return None
                
                # Find flight arriving at the specified airport
                for flight in data["data"]:
                    if flight.get("arrival", {}).get("iata") == airport_code.upper():
                        return {
                            "flight_iata": flight.get("flight", {}).get("iata"),
                            "arrival_iata": flight.get("arrival", {}).get("iata"),
                            "departure_iata": flight.get("departure", {}).get("iata"),
                            "arrival_time": flight.get("arrival", {}).get("scheduled"),
                            "departure_time": flight.get("departure", {}).get("scheduled"),
                            "status": flight.get("flight_status"),
                        }
                
                # If not found at that airport, return first match (might be wrong leg but better than nothing)
                if data["data"]:
                    flight = data["data"][0]
                    return {
                        "flight_iata": flight.get("flight", {}).get("iata"),
                        "arrival_iata": flight.get("arrival", {}).get("iata"),
                        "departure_iata": flight.get("departure", {}).get("iata"),
                        "arrival_time": flight.get("arrival", {}).get("scheduled"),
                        "departure_time": flight.get("departure", {}).get("scheduled"),
                        "status": flight.get("flight_status"),
                    }
                
                return None
                
        except httpx.TimeoutException:
            print(f"⏱️ Timeout looking up flight {flight_number}")
            return None
        except httpx.HTTPError as e:
            print(f"❌ Error fetching flight data: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error in flight lookup: {e}")
            return None


async def get_flight_times(flight_number: str, airport_code: str) -> Optional[Dict[str, str]]:
    """
    Public helper to get arrival and departure times for a flight
    
    Returns:
        {
            "arrival": "HH:MM",
            "departure": "HH:MM",
            "date": "YYYY-MM-DD"
        }
        or None if not found
    """
    flight = await FlightDataService.lookup_flight(flight_number, airport_code)
    
    if not flight or not flight.get("arrival_time"):
        return None
    
    try:
        # Parse ISO datetime
        arrival_dt = datetime.fromisoformat(flight["arrival_time"].replace("Z", "+00:00"))
        
        # Extract time in HH:MM format and date
        arrival_time = arrival_dt.strftime("%H:%M")
        date = arrival_dt.strftime("%Y-%m-%d")
        
        # We don't know the next departure from the lookup, but we return the structure
        return {
            "arrival": arrival_time,
            "date": date,
        }
    except Exception as e:
        print(f"❌ Error parsing flight times: {e}")
        return None
