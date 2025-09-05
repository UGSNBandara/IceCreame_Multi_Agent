# DB_Tools/cartTools.py
from typing import Any, Dict, List
from State.CartStore import cart_store 
from Cache.Cart import Cart, CatalogNotLoaded, ItemNotFound

async def add_item_to_cart(session_id: str, icecream_id: int, qty: int) -> Dict[str, Any]:
    """to add an ice cream item to the session cart

    Args:
        session_id (str): id of the session to store the cart
        icecream_id (int): id of the ice cream
        qty (int): quantity to add (default 1)

    Returns:
        dict: {"state":"success","cart":[...]} on success.
              {"state":"catalog_not_loaded"} if catalog not in RAM.
              {"state":"not_found"} if item id not in catalog.
    """
    lines = await cart_store.get(session_id)
    cart = Cart(lines)
    try:
        cart.add(icecream_id, qty)
    except CatalogNotLoaded:
        return {"state": "catalog_not_loaded"}
    except ItemNotFound:
        return {"state": "not_found"}

    snapshot = cart.to_lines()
    await cart_store.put(session_id, snapshot)
    return {"state": "success", "cart": snapshot}


async def remove_item_from_cart(session_id: str, icecream_id: int) -> Dict[str, Any]:
    """to remove an ice cream item from the session cart by id

    Args:
        session_id (str): id of the session
        icecream_id (int): id of the ice cream

    Returns:
        dict: {"state":"success","cart":[...]} (no-op if item not present)
    """
    lines = await cart_store.get(session_id)
    cart = Cart(lines)
    cart.remove(icecream_id)
    snapshot = cart.to_lines()
    await cart_store.put(session_id, snapshot)
    return {"state": "success", "cart": snapshot}


async def clear_cart(session_id: str) -> Dict[str, Any]:
    """to clear the session cart

    Args:
        session_id (str): id of the session

    Returns:
        dict: {"state":"cleared"}
    """
    await cart_store.clear(session_id)
    return {"state": "cleared"}



async def get_cart_with_total(session_id: str) -> Dict[str, Any]:
    """to get the current cart with the subtotal by session id

    Args:
        session_id (str): id of the session

    Returns:
        dict: {"cart": [...], "subtotal": ...}
    """
    snap = Cart(await cart_store.get(session_id)).to_lines()
    subtotal = round(sum(l["amount"] for l in snap), 2)
    return {"cart": snap, "subtotal": subtotal}