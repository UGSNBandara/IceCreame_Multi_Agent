# CRUD for orders using MongoDB (Motor)
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from CRUD.db import get_db


def _stringify_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.pop("_id", None)
    if _id is not None:
        doc["id"] = str(_id)
    return doc


class OrderStatus(str, Enum):
    ADDED = "added"
    PROCESSING = "processing"
    COMPLETED = "completed"

async def add_order(
    customer_name: str,
    items: List[Dict[str, Any]],
    total: float,
) -> Dict[str, Any]:
    """Create a minimal order document.

    Fields: customer_name, items, total, status(default=added), created_at
    """
    db = await get_db()
    payload = {
        "customer_name": (customer_name or "").strip() or "Guest",
        "items": items,
        "total": float(total),
        "status": OrderStatus.ADDED.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db["orders"].insert_one(payload)
    created = await db["orders"].find_one({"_id": res.inserted_id})
    return _stringify_id(created)


async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch order by Mongo ObjectId string."""
    db = await get_db()
    from bson import ObjectId  # local import to avoid lint issues if not installed yet
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None
    doc = await db["orders"].find_one({"_id": oid})
    return _stringify_id(doc) if doc else None

async def list_orders() -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = db["orders"].find({}).sort("created_at", -1)
    out: List[Dict[str, Any]] = []
    async for doc in cursor:
        out.append(_stringify_id(doc))
    return out

async def update_order_status(order_id: str, new_status: str) -> Dict[str, Any]:
    """Update order status if valid. Returns updated order or error state."""
    if new_status not in {s.value for s in OrderStatus}:
        return {"state": "invalid_status"}
    db = await get_db()
    from bson import ObjectId
    try:
        oid = ObjectId(order_id)
    except Exception:
        return {"state": "invalid_id"}
    res = await db["orders"].update_one({"_id": oid}, {"$set": {"status": new_status}})
    if res.matched_count == 0:
        return {"state": "not_found"}
    doc = await db["orders"].find_one({"_id": oid})
    return _stringify_id(doc) if doc else {"state": "not_found"}
