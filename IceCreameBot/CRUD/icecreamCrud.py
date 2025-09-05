# app/crud_catalog_sb.py
from typing import List
from CRUD.db import get_supabase
from Cache.IceCreamCache import IceCreamDTO, CategoryDTO


async def fetch_ice_creams() -> List[IceCreamDTO]:
    sb = await get_supabase()
    # Ask for both price and price_cents so we can normalize either schema
    resp = await (
        sb.table("ice_cream")
        .select("id,name,category_id,description,price")
        .execute()
    )
    rows = resp.data or []
    out: List[IceCreamDTO] = []
    for r in rows:
        desc = r.get("description")
        price = r.get("price")
        out.append(
            IceCreamDTO(
                id=int(r["id"]),
                name=str(r["name"]),
                category_id=int(r["category_id"]),
                description=str(desc),
                price=float(price),
            )
        )
    return out


async def fetch_categories() -> List[CategoryDTO]:
    sb = await get_supabase()
    resp = await (
        sb.table("category")
        .select("id,name,description")
        .execute()
    )
    rows = resp.data or []
    return [
        CategoryDTO(
            id=int(r["id"]),
            name=str(r["name"]),
            description=str(r.get("description")),
        )
        for r in rows
    ]
