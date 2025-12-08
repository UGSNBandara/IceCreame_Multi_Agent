# DB_Tools/cartTools.py
from typing import Any, Dict, List
from ..State.CartStore import cart_store 
from ..Cache.Cart import Cart, CatalogNotLoaded, ItemNotFound
from ..Context.SessionContext import CURRENT_SID
from ..MainChef.static_menu import get_static_cache

async def add_item_to_cart(item_id: int, qty: int) -> Dict[str, Any]:
    """Add a menu item to the session cart.

    Args:
        item_id (int): id of the item
        qty (int): quantity to add

    Returns:
        dict: {"state":"success","cart":[...]} on success.
              {"state":"insufficient_stock", "available": N} if not enough stock.
              {"state":"not_found"} if item id not in menu.
    """
    # Check stock availability first
    cache = get_static_cache()
    item = cache.get_by_id(item_id)
    if not item:
        return {"state": "not_found"}
    
    available = item["available_count"]
    if available < qty:
        return {"state": "insufficient_stock", "available": available, "requested": qty}
    
    session_id = CURRENT_SID.get()
    lines = await cart_store.get(session_id)
    cart = Cart(lines)
    try:
        cart.add(item_id, qty)
    except CatalogNotLoaded:
        return {"state": "catalog_not_loaded"}
    except ItemNotFound:
        return {"state": "not_found"}

    snapshot = cart.to_lines()
    await cart_store.put(session_id, snapshot)
    return {"state": "success", "cart": snapshot}


async def remove_item_from_cart(item_id: int) -> Dict[str, Any]:
    """Remove a menu item from the session cart by id.

    Returns:
        dict: {"state":"success","cart":[...]} (no-op if item not present)
    """
    session_id = CURRENT_SID.get()
    lines = await cart_store.get(session_id)
    cart = Cart(lines)
    cart.remove(item_id)
    snapshot = cart.to_lines()
    await cart_store.put(session_id, snapshot)
    return {"state": "success", "cart": snapshot}


async def clear_cart() -> Dict[str, Any]:
    """Clear the session cart."""
    session_id = CURRENT_SID.get()
    await cart_store.clear(session_id)
    return {"state": "cleared"}


async def get_cart_with_total() -> Dict[str, Any]:
    """Get the current cart with subtotal for the session."""
    session_id = CURRENT_SID.get()
    snap = Cart(await cart_store.get(session_id)).to_lines()
    subtotal = round(sum(l["amount"] for l in snap), 2)
    return {"cart": snap, "subtotal": subtotal}