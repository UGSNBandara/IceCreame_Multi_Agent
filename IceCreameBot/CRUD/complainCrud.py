# app/crud_complains_sb.py
from CRUD.db import get_supabase

async def add_complain(description: str) -> int:
    desc = (description or "").strip()
    if not desc:
        raise ValueError("description cannot be empty")
    sb = await get_supabase()
    resp = await (
        sb.table("complains")
        .insert({"description": desc})
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise RuntimeError("insert returned no data")

    return int(rows[0]["id"])
