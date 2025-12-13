from typing import List, Dict, Optional
import os
import time
import math
import asyncio
import http.client
import json
import threading
import contextvars


from .. import session_store as _session_store


class SessionContextReader:
    """Reads session-scoped attributes sent from the frontend.

    Expected payload per turn includes age_group, gender_guess, mood.
    No raw media handled here.
    """

    def read(self, session_id: str) -> Dict[str, Optional[str]]:
        # Read from in-memory session_store populated by API layer
        data = _session_store.user_sessions.get(session_id) or {}
        return {
            "age_group": data.get("age_group"),
            "gender_guess": data.get("gender_guess"),
            "mood": data.get("mood"),
        }


class GlobalContextReader:
    """Provides global context for all sessions: time_of_day and temperature_bucket.

    Backed by an in-memory cache refreshed periodically by a background job.
    """

    def __init__(self):
        self._last_fetch_ts: float = 0.0
        self._temp_c: Optional[float] = None
        self._cache_ttl_sec: int = int(os.getenv("WEATHER_CACHE_TTL_SEC", "600"))
        self._provider: str = os.getenv("WEATHER_PROVIDER", "open-meteo")
        self._latitude: Optional[str] = os.getenv("WEATHER_LAT")
        self._longitude: Optional[str] = os.getenv("WEATHER_LON")

    def time_of_day(self) -> str:
        # Use Colombo time (UTC+5:30)
        t = time.gmtime()
        # Add 5 hours 30 minutes (330 minutes) to UTC
        minutes = (t.tm_hour * 60 + t.tm_min + 330) % 1440
        
        # Morning: 05:00 to 11:30
        if 300 <= minutes < 690:
            return "morning"
        # Afternoon: 11:30 to 15:30 (3:30 PM)
        if 690 <= minutes < 930:
            return "afternoon"
        return "evening"

    def temperature_bucket(self) -> str:
        # Try refresh if stale; fall back to last known or 'normal'
        now = time.time()
        if (now - self._last_fetch_ts) > self._cache_ttl_sec:
            self._refresh_weather_safely()
        temp = self._temp_c if isinstance(self._temp_c, (int, float)) else None
        if temp is None:
            return "normal"
        if temp < 24:
            return "cool"
        if temp > 30:
            return "hot"
        return "normal"

    def _refresh_weather_safely(self) -> None:
        try:
            self._temp_c = self._fetch_temperature_c()
            self._last_fetch_ts = time.time()
        except Exception:
            # Keep previous cache; do not raise in agent path
            self._last_fetch_ts = time.time()

    def _fetch_temperature_c(self) -> Optional[float]:
        # Minimal, dependency-free fetcher. Defaults to Open-Meteo.
        # You can switch provider via env vars.
        if not (self._latitude and self._longitude):
            return None
        if self._provider == "open-meteo":
            # API: https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current_weather=true
            conn = http.client.HTTPSConnection("api.open-meteo.com", timeout=3)
            path = f"/v1/forecast?latitude={self._latitude}&longitude={self._longitude}&current_weather=true"
            conn.request("GET", path)
            resp = conn.getresponse()
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
            cw = data.get("current_weather") or {}
            temp = cw.get("temperature")
            try:
                return float(temp) if temp is not None else None
            except Exception:
                return None
        # Add other providers as needed (e.g., OpenWeatherMap) using env keys
        return None


def start_weather_warmup(reader: GlobalContextReader) -> None:
    """Start a lightweight daemon thread to periodically refresh weather cache.

    Refresh interval defaults to half of the TTL for smoother updates.
    """
    interval = max(60, int(os.getenv("WEATHER_WARMUP_INTERVAL_SEC", "0") or 0) or reader._cache_ttl_sec // 2)

    def _loop():
        while True:
            try:
                reader._refresh_weather_safely()
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=_loop, name="weather-warmup", daemon=True)
    t.start()


from ..CRUD import db as db
from .constants import CATEGORIES, FLAVORS


class CategoryPopularityStore:
    """Segment-level and global category popularity counters.

    Persist in SQLite and sync to MongoDB via existing background worker.
    """

    async def increment(self, segment_key: str, category: str) -> None:
        await db.pop_increment(segment_key, category)

    async def get_top_categories(self, segment_key: str, k: int = 3) -> List[str]:
        rows = await db.pop_top_categories(segment_key, k)
        return [r["category"] if isinstance(r, dict) else r[0] for r in rows]

    async def get_global_top_categories(self, k: int = 3) -> List[str]:
        rows = await db.pop_global_top_categories(k)
        return [r["category"] if isinstance(r, dict) else r[0] for r in rows]

    async def get_all_segments_top_categories(self, k: int = 3) -> Dict[str, List[str]]:
        rows = await db.pop_all_segments_top_categories(k)
        result = {}
        for r in rows:
            # Handle row factory (dict or tuple)
            seg = r["segment_key"] if isinstance(r, dict) else r[0]
            cat = r["category"] if isinstance(r, dict) else r[1]
            if seg not in result:
                result[seg] = []
            result[seg].append(cat)
        return result


class AnalyticsSink:
    """Asynchronous sink for manager analytics events.

    Events: selection, more_options_click, session_context_snapshot.
    """

    def emit(self, event_type: str, payload: Dict) -> None:
        # TODO: enqueue or persist event
        pass


def make_segment_key(age_group: Optional[str], gender_guess: Optional[str],
                     temperature_bucket: str, time_of_day: str) -> str:
    age = age_group or "unknown"
    gender = gender_guess or "unknown"
    return f"{age}_{gender}_{temperature_bucket}_{time_of_day}"


class CategoryFlavorCache:
    """In-memory cache of distinct categories and flavors from the catalog.

    Hydrated from SQLite for instant retrieval and refreshed on demand.
    """

    def __init__(self):
        self._categories: List[str] = []
        self._flavors: List[str] = []
        self._last_refresh_ts: float = 0.0

    async def refresh(self) -> None:
        # Load strict enums from constants (not dynamic at runtime)
        self._categories = list(CATEGORIES)
        self._flavors = list(FLAVORS)
        self._last_refresh_ts = time.time()

    def get_categories(self) -> List[str]:
        return list(self._categories)

    def get_flavors(self) -> List[str]:
        return list(self._flavors)


# ---- Session context (automatic injection) ----
CURRENT_SESSION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("CURRENT_SESSION_ID", default=None)

def set_current_session(session_id: str) -> None:
    """Set the current session id for downstream tools to consume automatically."""
    try:
        CURRENT_SESSION_ID.set(session_id)
    except Exception:
        pass

def get_current_session() -> Optional[str]:
    return CURRENT_SESSION_ID.get()
