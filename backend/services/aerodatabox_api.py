"""
AeroDataBox API Service: Fetch flight info for LIS and SIN via RapidAPI.

AMS continues to use SchipholService. This service handles all other airports.
"""

import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from config import AERODATABOX_API_KEY


def _mock_flight_data() -> Dict[str, Any]:
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "flight_number":       "MOCK",
        "date":                today,
        "scheduled_arrival":   f"{today}T10:30:00+00:00",
        "scheduled_departure": f"{today}T14:00:00+00:00",
        "actual_arrival":      None,
        "terminal":            "1",
        "pier":                "",
        "gate":                "",
        "delay_minutes":       0,
        "status":              "scheduled",
        "is_mock":             True,
    }


class AeroDataBoxService:
    BASE_URL = "https://prod.api.market/api/v1/aedbx/aerodatabox"
    TIMEOUT  = 10.0

    @staticmethod
    def _headers() -> Dict[str, str]:
        return {
            "x-api-market-key": AERODATABOX_API_KEY or "",
            "Accept": "application/json",
        }

    @staticmethod
    def _is_configured() -> bool:
        return bool(AERODATABOX_API_KEY)

    @staticmethod
    def _delay_minutes(scheduled: str, actual: Optional[str]) -> int:
        if not actual:
            return 0
        try:
            sch = datetime.fromisoformat(scheduled)
            act = datetime.fromisoformat(actual)
            return max(0, int((act - sch).total_seconds() / 60))
        except Exception:
            return 0

    @staticmethod
    def _infer_pier(gate: str) -> str:
        """Return first alpha character of gate code as pier (e.g. 'D7' → 'D')."""
        if gate and gate[0].isalpha():
            return gate[0].upper()
        return ""

    @staticmethod
    def _normalize_iso(dt_str: Optional[str]) -> Optional[str]:
        """Replace space separator with T so fromisoformat works on Python < 3.11."""
        if dt_str:
            return dt_str.replace(" ", "T")
        return dt_str

    @staticmethod
    def _parse_flight(
        raw: Dict[str, Any],
        direction: str,  # "inbound" or "outbound"
    ) -> Dict[str, Any]:
        dep = raw.get("departure", {})
        arr = raw.get("arrival",   {})
        status = raw.get("status", "scheduled").lower()

        if direction == "inbound":
            sched_iso  = AeroDataBoxService._normalize_iso(
                arr.get("scheduledTime", {}).get("local", "")
            )
            actual_iso = AeroDataBoxService._normalize_iso(
                (arr.get("actualTime") or arr.get("revisedTime") or {}).get("local")
            )
            terminal = str(arr.get("terminal", ""))
            gate     = str(arr.get("gate", ""))
            sched_arr = sched_iso or ""
            sched_dep = ""
        else:  # outbound
            sched_iso  = AeroDataBoxService._normalize_iso(
                dep.get("scheduledTime", {}).get("local", "")
            )
            actual_iso = None  # outbound actual departure not used in layover calc
            terminal = str(dep.get("terminal", ""))
            gate     = str(dep.get("gate", ""))
            sched_arr = ""
            sched_dep = sched_iso or ""

        date = sched_iso[:10] if sched_iso else ""
        pier = AeroDataBoxService._infer_pier(gate)

        return {
            "flight_number":       raw.get("number", ""),
            "date":                date,
            "scheduled_arrival":   sched_arr,
            "scheduled_departure": sched_dep,
            "actual_arrival":      actual_iso if direction == "inbound" else None,
            "terminal":            terminal,
            "pier":                pier,
            "gate":                gate,
            "delay_minutes":       AeroDataBoxService._delay_minutes(sched_iso or "", actual_iso),
            "status":              status,
            "is_mock":             False,
        }

    @staticmethod
    async def get_flight(
        flight_number: str,
        date: Optional[str] = None,
        airport_code: str = "LIS",
        direction: str = "inbound",
    ) -> Dict[str, Any]:
        """
        Look up a flight by IATA number for non-AMS airports.

        AeroDataBox returns an array of legs for a flight number on a given date.
        We filter to the leg where the layover airport appears on the relevant side:
          - inbound:  arrival.airport.iata == airport_code
          - outbound: departure.airport.iata == airport_code

        Falls back to mock data on any error or if no matching leg is found.
        """
        if not AeroDataBoxService._is_configured():
            print("WARNING: AeroDataBox API key not configured — using mock flight data")
            return _mock_flight_data()

        schedule_date = date or datetime.now().strftime("%Y-%m-%d")
        flight_clean  = flight_number.upper().replace(" ", "")
        url = f"{AeroDataBoxService.BASE_URL}/flights/number/{flight_clean}/{schedule_date}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=AeroDataBoxService._headers(),
                    timeout=AeroDataBoxService.TIMEOUT,
                )
                response.raise_for_status()
                flights = response.json()

        except httpx.TimeoutException:
            print(f"TIMEOUT: AeroDataBox timeout for {flight_number} — using mock data")
            return _mock_flight_data()
        except httpx.HTTPStatusError as e:
            print(f"ERROR: AeroDataBox {e.response.status_code} for {flight_number} — using mock data")
            return _mock_flight_data()
        except Exception as e:
            print(f"ERROR: AeroDataBox error: {e} — using mock data")
            return _mock_flight_data()

        if not flights:
            print(f"WARNING: Flight {flight_number} not found on {schedule_date} — using mock data")
            return _mock_flight_data()

        # Filter to the leg that touches airport_code on the correct side
        iata_side = "arrival" if direction == "inbound" else "departure"
        match = next(
            (
                f for f in flights
                if f.get(iata_side, {}).get("airport", {}).get("iata", "").upper()
                   == airport_code.upper()
            ),
            None,
        )

        if match is None:
            print(
                f"WARNING: No {direction} leg for {flight_number} at {airport_code} "
                f"on {schedule_date} — using mock data"
            )
            return _mock_flight_data()

        return AeroDataBoxService._parse_flight(match, direction)
