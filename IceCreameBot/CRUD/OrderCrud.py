# Order CRUD using SQLite (formerly MongoDB version replaced)
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import json
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
    conn = await get_db()
    await conn.execute(
        "INSERT INTO orders(customer_name, items, total, status, created_at) VALUES (?,?,?,?,?)",
        (
            (customer_name or "").strip() or "Guest",
            json.dumps(items),
            float(total),
            OrderStatus.ADDED.value,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    await conn.commit()
    cur = await conn.execute(
        "SELECT id, customer_name, items, total, status, created_at FROM orders ORDER BY id DESC LIMIT 1"
    )
    row = await cur.fetchone()
    if not row:
        return {"state": "error_occured", "error": "db_error"}
    return {
        "id": str(row["id"]),
        "customer_name": row["customer_name"],
        "items": json.loads(row["items"]),
        "total": row["total"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    conn = await get_db()
    try:
        oid = int(order_id)
    except Exception:
        return None
    cur = await conn.execute(
        "SELECT id, customer_name, items, total, status, created_at FROM orders WHERE id = ?",
        (oid,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "customer_name": row["customer_name"],
        "items": json.loads(row["items"]),
        "total": row["total"],
        "status": row["status"],
        "created_at": row["created_at"],
    }

async def list_orders() -> List[Dict[str, Any]]:
    conn = await get_db()
    cur = await conn.execute(
        "SELECT id, customer_name, items, total, status, created_at FROM orders ORDER BY created_at DESC"
    )
    rows = await cur.fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": str(row["id"]),
                "customer_name": row["customer_name"],
                "items": json.loads(row["items"]),
                "total": row["total"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
        )
    return out

async def update_order_status(order_id: str, new_status: str) -> Dict[str, Any]:
    if new_status not in {s.value for s in OrderStatus}:
        return {"state": "invalid_status"}
    conn = await get_db()
    try:
        oid = int(order_id)
    except Exception:
        return {"state": "invalid_id"}
    cur = await conn.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, oid),
    )
    await conn.commit()
    if cur.rowcount == 0:
        return {"state": "not_found"}
    return await get_order_by_id(order_id)
