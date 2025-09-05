# app/crud_orders_sb.py
from typing import List, Dict, Optional, Any
from CRUD.db import get_supabase

async def add_order(
    customer_id: Optional[int],
    items: List[Dict[str, Any]],
    dine_in: bool,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    table_number: Optional[int] = None,
) -> Dict[str, Any]:
    sb = await get_supabase()
    payload = {
        "customer_id": customer_id,
        "items": items,
        "dine-in": dine_in,   # True=Dine-in, False=Take-away
        "address": address,
        "phone": phone,
        "table_number": table_number,
        "done": False,
    }
    resp = await (
        sb.table("orders")
        .insert(payload)
        .execute()
    )
    return resp.data

async def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    sb = await get_supabase()
    resp = await (
        sb.table("orders")
        .select("id,customer_id,created_at,items,done,dine-in,address,phone,table_number")
        .eq("id", order_id)
        .limit(1)
        .single()
        .execute()
    )
    return resp.data
