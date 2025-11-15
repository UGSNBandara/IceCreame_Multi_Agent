# DB_Tools/orderTool.py
from typing import List, Dict, Any
from ..CRUD.OrderCrud import add_order as add_order_db, get_order_by_id as get_order_by_id_db


async def add_order(
    customer_name: str,
    items: List[Dict[str, Any]],
    total: float,
) -> Dict[str, Any]:
    """Create a minimal order for the exhibition.

    Args:
        customer_name: short display name (or provide "Guest").
        items: cart snapshot lines [{code,name,qty,price,amount}].
        total: subtotal from get_cart_with_total().

    Returns:
        Created order document with string id or error state.
    """
    try:
        row = await add_order_db(
            customer_name=customer_name,
            items=items,
            total=total,
        )
        return row
    except Exception:
        return {"state": "error_occured", "error": "db_error"}


async def get_order_by_id(order_id: str) -> Dict[str, Any]:
    """Get order by id (ObjectId string)."""
    try:
        row = await get_order_by_id_db(order_id)
        return row if row else {"state": "not_found"}
    except Exception:
        return {"state": "error_occured", "error": "db_error"}
