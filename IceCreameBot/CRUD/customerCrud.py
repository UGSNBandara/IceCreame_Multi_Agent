# app/crud_customers_sb.py
from typing import Optional, Dict, Any
from  CRUD.db import get_supabase

async def add_customer(name: str, phone: str, address: Optional[str] = None) -> Dict[str, Any]:
    sb = await get_supabase()
    resp = await (
        sb.table("customer")
        .insert({"name": name, "phone": phone, "address": address})  
        .execute()
    )
    return resp.data  # {"id", "name", "phone", "address"}
    # Use UNIQUE(phone) to catch duplicates at DB level

async def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    sb = await get_supabase()
    resp = await (
        sb.table("customer")
        .select("id,name,phone,address")
        .eq("phone", phone)
        .limit(1)
        .single()        # or .maybe_single() if you want None when not found
        .execute()
    )
    return resp.data  # None or dict
    # note: .single() / .maybe_single() are documented helpers. :contentReference[oaicite:2]{index=2}

async def update_customer(
    customer_id: int,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    patch = {k: v for k, v in {"name": name, "phone": phone, "address": address}.items() if v is not None}
    if not patch:
        # Fetch current row
        sb = await get_supabase()
        resp = await sb.table("customer").select("id,name,phone,address").eq("id", customer_id).single().execute()
        return resp.data

    sb = await get_supabase()
    resp = await (
        sb.table("customer")
        .update(patch)
        .eq("id", customer_id)
        .execute()
    )
    return resp.data  # None if not found (depending on version/config)
