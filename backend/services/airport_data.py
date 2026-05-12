"""
Airport Data: Step 1 buffer constants extracted from planner_service.AIRPORTS_CONFIG.

Exit times are pier-based for AMS only (Schiphol returns real pier data).
For LIS and SIN use EXIT_TIME_FALLBACK_MIN.

Checkin cutoff is inferred from passport_type as a proxy for departure zone:
  EU    → Schengen departure   → 45 min
  US    → non-Schengen         → 75 min
  OTHER → non-Schengen         → 75 min
"""

# AMS exit time per pier (minutes: disembark + walk + passport control + exit building)
# Source: AMS terminal layout knowledge base
AMS_EXIT_TIME_BY_PIER: dict[str, int] = {
    "B": 25,
    "C": 25,
    "D": 20,
    "E": 20,
    "F": 30,
    "G": 30,
    "H": 35,
    "M": 15,
}

# Used for LIS/SIN (no real pier data from API) and any unknown AMS pier
EXIT_TIME_FALLBACK_MIN = 25

# Per-airport Step 1 buffer constants.
# Extracted from planner_service.AIRPORTS_CONFIG — that dict retains city/transport/vibe
# fields needed for Step 3 activity planning.
AIRPORT_CONFIG: dict[str, dict] = {
    "AMS": {
        "walk_to_gate_min": 10,
        "security_reentry_min_fallback": 30,  # used if Schiphol queue API call fails
    },
    "LIS": {
        "walk_to_gate_min": 12,
        "security_reentry_min_fallback": 20,
    },
    "SIN": {
        "walk_to_gate_min": 15,
        "security_reentry_min_fallback": 25,
    },
}

# Checkin cutoff mapped from passport_type (proxy for departure zone).
# Replaces the flat checkin_cutoff_min=45 that was hardcoded in AIRPORTS_CONFIG.
CHECKIN_CUTOFF_BY_PASSPORT: dict[str, int] = {
    "EU":    45,   # Schengen departure
    "US":    75,   # non-Schengen departure
    "OTHER": 75,   # non-Schengen departure
}

# ACTIVITY PLANNING — domestic option (30 min cutoff) not needed until Step 3
# DOMESTIC_CUTOFF_MIN = 30
