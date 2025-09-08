# app/state/menu_state_store.py
import asyncio
from typing import Dict

DEFAULT_STATE = 0  # what get() returns if the session wasn't set yet

class MenuStateStore:
    def __init__(self):
        self._states: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get(self, sid: str) -> int:
        """Return the current menu state for this session.
        If not set yet, returns DEFAULT_STATE (does not create an entry)."""
        async with self._lock:
            return self._states.get(sid, DEFAULT_STATE)

    async def set(self, sid: str, value: int) -> int:
        """Set the menu state for this session. Creates it if missing."""
        async with self._lock:
            self._states[sid] = int(value)
            return self._states[sid]

# <- exported singleton instance your tools can import
menu_state_store = MenuStateStore()
