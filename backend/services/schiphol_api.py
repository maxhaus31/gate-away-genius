"""
Schiphol API Service: Fetch real flight info and security queue times
from the Schiphol Public Flights API.
"""

import re
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from config import SCHIPHOL_APP_ID, SCHIPHOL_APP_KEY


# ── Mock data ──────────────────────────────────────────────────────────────────
# Returned whenever the API is unavailable, credentials are missing,
# or the requested flight is not found. Keeps the demo stable.
# Dates are generated at call-time so they always match today — a hardcoded date
# causes cross-day mismatches when one flight hits the API and the other falls back.

def _mock_flight_data() -> Dict[str, Any]:
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "flight_number":       "MOCK",
        "date":                today,
        "scheduled_arrival":   f"{today}T10:30:00+02:00",
        "scheduled_departure": f"{today}T14:00:00+02:00",
        "actual_arrival":      None,   # not available for scheduled/future flights
        "terminal":            "D",
        "pier":                "D",
        "gate":                "D7",
        "delay_minutes":       0,
        "status":              "scheduled",
        "is_mock":             True,
    }

MOCK_QUEUE_DATA: Dict[str, Any] = {
    "terminal": "D",
    "queue_minutes": 12,
    "is_mock": True,
}


# ── Service ────────────────────────────────────────────────────────────────────

class SchipholService:
    FLIGHTS_URL = "https://api.schiphol.nl/public-flights/flights"
    QUEUES_URL  = "https://api.schiphol.nl/public-flights/queues"
    TIMEOUT     = 10.0

    @staticmethod
    def _headers() -> Dict[str, str]:
        return {
            "app_id":          SCHIPHOL_APP_ID or "",
            "app_key":         SCHIPHOL_APP_KEY or "",
            "ResourceVersion": "v4",
            "Accept":          "application/json",
        }

    @staticmethod
    def _is_configured() -> bool:
        return bool(SCHIPHOL_APP_ID and SCHIPHOL_APP_KEY)

    @staticmethod
    def _delay_minutes(scheduled: str, actual: Optional[str]) -> int:
        """Return positive delay in whole minutes; 0 if on time or unknown."""
        if not actual:
            return 0
        try:
            sch = datetime.fromisoformat(scheduled)
            act = datetime.fromisoformat(actual)
            return max(0, int((act - sch).total_seconds() / 60))
        except Exception:
            return 0

    @staticmethod
    def _parse_flight(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the fields we need from a raw Schiphol flight record."""
        scheduled   = raw.get("scheduleDateTime", "")
        actual_land = raw.get("actualLandingTime") or raw.get("estimatedLandingTime")
        states      = raw.get("publicFlightState", {}).get("flightStates", [])
        status      = states[0].lower() if states else "scheduled"

        direction = raw.get("flightDirection", "")
        date      = scheduled[:10] if scheduled else ""  # "YYYY-MM-DD"

        return {
            "flight_number":       raw.get("flightName", ""),
            "date":                date,
            "scheduled_arrival":   scheduled if direction == "A" else "",
            "scheduled_departure": scheduled if direction == "D" else "",
            "actual_arrival":      actual_land if direction == "A" else None,
            "terminal":            str(raw.get("terminal", "")),
            "pier":                raw.get("pier", ""),
            "gate":                raw.get("gate", ""),
            "delay_minutes":       SchipholService._delay_minutes(scheduled, actual_land),
            "status":              status,
            "is_mock":             False,
        }

    @staticmethod
    async def get_flight(
        flight_name: str,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Look up a flight by IATA name (e.g. "KL1234").

        Uses the flightName query parameter as required by the Schiphol API —
        NOT flight_iata.

        Args:
            flight_name: IATA flight identifier, e.g. "KL1234"
            date:        Schedule date "YYYY-MM-DD"; defaults to today

        Returns:
            Parsed flight dict, or MOCK_FLIGHT_DATA if unavailable.
        """
        if not SchipholService._is_configured():
            print("WARNING:  Schiphol credentials not configured — using mock flight data")
            return _mock_flight_data()

        schedule_date = date or datetime.now().strftime("%Y-%m-%d")

        # Schiphol requires zero-padded 4-digit flight numbers (e.g. KL792 → KL0792)
        flight_clean = flight_name.upper().replace(" ", "")
        m = re.match(r"^([A-Z]{2})(\d+)$", flight_clean)
        if m:
            airline, number = m.groups()
            flight_clean = f"{airline}{int(number):04d}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    SchipholService.FLIGHTS_URL,
                    headers=SchipholService._headers(),
                    params={
                        "flightName":   flight_clean,
                        "scheduleDate": schedule_date,
                    },
                    timeout=SchipholService.TIMEOUT,
                )
                response.raise_for_status()
                if not response.content:
                    print(f"WARNING:  Empty response from Schiphol for {flight_name} — using mock data")
                    return _mock_flight_data()
                flights = response.json().get("flights", [])

        except httpx.TimeoutException:
            print(f"TIMEOUT:  Schiphol API timeout for {flight_name} — using mock data")
            return _mock_flight_data()
        except httpx.HTTPStatusError as e:
            print(f"ERROR:  Schiphol API {e.response.status_code} for {flight_name} — using mock data")
            return _mock_flight_data()
        except ValueError as e:
            print(f"WARNING:  Schiphol returned non-JSON for {flight_name} — using mock data")
            return _mock_flight_data()
        except Exception as e:
            print(f"ERROR:  Schiphol API error: {e} — using mock data")
            return _mock_flight_data()

        if not flights:
            print(f"WARNING:  Flight {flight_name} not found on {schedule_date} — using mock data")
            return _mock_flight_data()

        return SchipholService._parse_flight(flights[0])

    @staticmethod
    async def get_security_queue(terminal: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch real-time security queue wait times.

        Args:
            terminal: Optional terminal filter (e.g. "D").
                      Returns the first entry if omitted.

        Returns:
            Dict with terminal and queue_minutes, or MOCK_QUEUE_DATA if unavailable.
        """
        if not SchipholService._is_configured():
            print("WARNING:  Schiphol credentials not configured — using mock queue data")
            return MOCK_QUEUE_DATA

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    SchipholService.QUEUES_URL,
                    headers=SchipholService._headers(),
                    timeout=SchipholService.TIMEOUT,
                )
                response.raise_for_status()
                queues = response.json().get("queues", [])

        except httpx.TimeoutException:
            print("TIMEOUT:  Schiphol queue API timeout — using mock data")
            return MOCK_QUEUE_DATA
        except httpx.HTTPStatusError as e:
            print(f"ERROR:  Schiphol queue API {e.response.status_code} — using mock data")
            return MOCK_QUEUE_DATA
        except Exception as e:
            print(f"ERROR:  Schiphol queue API error: {e} — using mock data")
            return MOCK_QUEUE_DATA

        if not queues:
            return MOCK_QUEUE_DATA

        if terminal:
            match = next(
                (q for q in queues if str(q.get("terminal", "")) == str(terminal)),
                None,
            )
            if match:
                return {
                    "terminal":      str(match.get("terminal", terminal)),
                    "queue_minutes": int(match.get("waitingTime", 12)),
                    "is_mock":       False,
                }

        first = queues[0]
        return {
            "terminal":      str(first.get("terminal", "")),
            "queue_minutes": int(first.get("waitingTime", 12)),
            "is_mock":       False,
        }
