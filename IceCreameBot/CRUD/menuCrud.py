from typing import List, Optional, Dict, Any
from CRUD.db import get_db
from Cache.MenuCache import MenuItemDTO, menu_cache

async def fetch_menu_items() -> List[MenuItemDTO]:
    db = await get_db()
    docs = await db["menu"].find({}, {"_id": 0}).to_list(length=2000)
    out: List[MenuItemDTO] = []
    for r in docs:
        try:
            out.append(
                MenuItemDTO(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    description=str(r.get("description", "")),
                    price=float(r.get("price", 0.0)),
                )
            )
        except Exception:
            continue
    return out

async def _refresh_cache() -> None:
    try:
        items = await fetch_menu_items()
        menu_cache.load(items)
    except Exception:
        pass

async def add_menu_item(name: str, description: str, price: float) -> Dict[str, Any]:
    db = await get_db()
    # Determine next id
    last = await db["menu"].find({}, {"id": 1, "_id": 0}).sort("id", -1).limit(1).to_list(length=1)
    next_id = (int(last[0]["id"]) + 1) if last else 1
    doc = {"id": next_id, "name": name, "description": description, "price": float(price)}
    await db["menu"].insert_one(doc)
    await _refresh_cache()
    return doc

async def update_menu_item(item_id: int, name: Optional[str] = None, description: Optional[str] = None, price: Optional[float] = None) -> Dict[str, Any]:
    db = await get_db()
    patch = {k: v for k, v in {"name": name, "description": description, "price": price}.items() if v is not None}
    if not patch:
        doc = await db["menu"].find_one({"id": int(item_id)}, {"_id": 0})
        return doc or {"state": "not_found"}
    res = await db["menu"].update_one({"id": int(item_id)}, {"$set": patch})
    if res.matched_count == 0:
        return {"state": "not_found"}
    doc = await db["menu"].find_one({"id": int(item_id)}, {"_id": 0})
    await _refresh_cache()
    return doc or {"state": "not_found"}

async def delete_menu_item(item_id: int) -> Dict[str, Any]:
    db = await get_db()
    res = await db["menu"].delete_one({"id": int(item_id)})
    if res.deleted_count == 0:
        return {"state": "not_found"}
    await _refresh_cache()
    return {"state": "deleted", "id": int(item_id)}
