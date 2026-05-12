"""
Cache Service: Disk-backed JSON cache for layover plans.

Key is built from airport, passport, transport mode, and flight times rounded to
the nearest 15-minute bucket — so a 12-minute delay still hits the same entry.
Entries expire after 24 hours. Expired entries are evicted on every write.
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

CACHE_FILE = Path(__file__).parent.parent / "cache" / "itineraries.json"
TTL_HOURS = 24


def _round_to_15(iso_str: str) -> str:
    """Snap ISO timestamp to the nearest 15-minute bucket."""
    dt = datetime.fromisoformat(iso_str)
    minutes = (dt.minute // 15) * 15
    return dt.replace(minute=minutes, second=0, microsecond=0).isoformat()


def make_key(
    airport_code: str,
    passport_region: str,
    transport_mode: str,   # ACTIVITY PLANNING — not user-supplied in Step 1; revisit in Step 3
    arrival_time: str,
    departure_time: str,
) -> str:
    raw = ":".join([
        airport_code,
        passport_region,
        transport_mode,
        _round_to_15(arrival_time),
        _round_to_15(departure_time),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _load() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2))


def get(key: str) -> Optional[dict]:
    """Return cached plan dict if present and not expired."""
    store = _load()
    entry = store.get(key)
    if not entry:
        return None
    saved_at = datetime.fromisoformat(entry["saved_at"])
    if saved_at.tzinfo is None:
        saved_at = saved_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - saved_at > timedelta(hours=TTL_HOURS):
        return None
    return entry["data"]


def set(key: str, data: dict) -> None:
    """Write plan to cache, evicting any expired entries."""
    store = _load()
    store[key] = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    cutoff = datetime.now(timezone.utc) - timedelta(hours=TTL_HOURS)
    store = {
        k: v for k, v in store.items()
        if datetime.fromisoformat(v["saved_at"]).replace(tzinfo=timezone.utc) > cutoff
    }
    _save(store)
