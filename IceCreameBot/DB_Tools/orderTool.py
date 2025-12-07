# DB_Tools/orderTool.py
from typing import List, Dict, Any
from ..CRUD.OrderCrud import add_order as add_order_db, get_order_by_id as get_order_by_id_db
from .menuTool import get_item_by_id
from ..MainChef.context_services import (
    GlobalContextReader,
    SessionContextReader,
    CategoryPopularityStore,
    make_segment_key,
    get_current_session,
)
import asyncio
from ..CRUD.db import outbox_enqueue


async def _update_popularity_async(items: List[Dict[str, Any]]) -> None:
    """Background task to update category popularity from order items."""
    try:
        session_id = get_current_session()
        session_reader = SessionContextReader()
        global_reader = GlobalContextReader()
        pop_store = CategoryPopularityStore()
        ctx = session_reader.read(session_id) if session_id else {"age_group": None, "gender_guess": None}
        age = ctx.get("age_group")
        gender = ctx.get("gender_guess")
        temp_bucket = global_reader.temperature_bucket()
        tod = global_reader.time_of_day()
        segment_key = make_segment_key(age, gender, temp_bucket, tod)
        # Aggregate counts per category for this order to reduce DB ops and outbox events
        per_category: dict[str, int] = {}
        for it in items:
            code = it.get("code")
            qty = int(it.get("qty", 1)) if it.get("qty") is not None else 1
            if code is None:
                continue
            item = await get_item_by_id(int(code))
            category = item.get("category") if isinstance(item, dict) else None
            if not category:
                continue
            per_category[str(category)] = per_category.get(str(category), 0) + max(1, qty)

        # Apply popularity increments and enqueue compact sync events
        for category, count in per_category.items():
            for _ in range(count):
                await pop_store.increment(segment_key, category)
            # Enqueue a single outbox event per category for Mongo sync (compact)
            await outbox_enqueue(
                "popularity",
                "increment",
                {
                    "segment_key": segment_key,
                    "category": category,
                    "count": count,
                },
            )
    except Exception:
        # Popularity update is best-effort; ignore failures
        pass


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
        # Fire-and-forget popularity update in background
        asyncio.create_task(_update_popularity_async(items))
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
