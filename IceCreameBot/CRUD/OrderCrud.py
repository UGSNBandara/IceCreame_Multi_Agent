# CRUD for orders using MongoDB (Motor)
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from CRUD.db import get_db


def _stringify_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.pop("_id", None)
    if _id is not None:
        doc["id"] = str(_id)
    return doc


async def add_order(
    customer_name: str,
    items: List[Dict[str, Any]],
    total: float,
) -> Dict[str, Any]:
    """Create a minimal order document for exhibition use.

    Fields: customer_name, items, total, created_at
    """
    db = await get_db()
    payload = {
        "customer_name": (customer_name or "").strip() or "Guest",
        "items": items,
        "total": float(total),
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
