# DB_Tools/menuTool.py
from typing import Any, Dict, List
from ..Cache.MenuCache import menu_cache, MenuItemDTO


def _to_dict(x: MenuItemDTO) -> Dict[str, Any]:
    return x.model_dump()


async def get_menu_items() -> List[Dict[str, Any]]:
    """Return the full menu list."""
    try:
        cat = menu_cache.get()
    except Exception:
        return []
    return [_to_dict(i) for i in cat.to_list()]


async def get_item_by_id(item_id: int) -> Dict[str, Any]:
    """Return a single menu item by id or not_found."""
    try:
        cat = menu_cache.get()
    except Exception:
        return {"state": "menu_not_loaded"}
    item = cat.by_item_id(int(item_id))
    return _to_dict(item) if item else {"state": "not_found"}
