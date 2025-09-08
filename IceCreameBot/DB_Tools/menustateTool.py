# DB_Tools/menuStateTools.py
from typing import Any, Dict
from Context.SessionContext import CURRENT_SID

# Match your existing import style (adjust path/case if you use snake_case dirs)
from State.MenuStateStore import menu_state_store

async def set_menu_state(menu_state: int):
    """Set (or create) the integer menu state for a session.

    Returns:
        {"state":"success","session_id":..., "value": <int>}
    """
    sid = CURRENT_SID.get()
    value = await menu_state_store.set(sid, menu_state)
    print(f"Menu state for session {sid} set to {value}")


async def get_menu_state(session_id: str) -> int:
    """Get the integer menu state for a session.
       If none exists yet, returns DEFAULT_STATE (0)."""
    value = await menu_state_store.get(session_id)
    return value or 0