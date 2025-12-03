from typing import List, Optional, Dict, Any
from .db import get_db, outbox_enqueue
from ..Cache.MenuCache import MenuItemDTO, menu_cache

async def fetch_menu_items() -> List[MenuItemDTO]:
    conn = await get_db()
    cur = await conn.execute("SELECT id, name, description, price, category, flavor, available_count FROM menu ORDER BY id ASC")
    rows = await cur.fetchall()
    out: List[MenuItemDTO] = []
    for r in rows:
        try:
            out.append(
                MenuItemDTO(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    description=str(r.get("description", "")),
                    price=float(r.get("price") or 0.0),
                    category=str(r.get("category", "")),
                    flavor=str(r.get("flavor", "")),
                    available_count=int(r.get("available_count", 0)),
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

async def add_menu_item(name: str, description: str, price: float, category: str, flavor: str, available_count: int) -> Dict[str, Any]:
    conn = await get_db()
    await conn.execute(
        "INSERT INTO menu(name, description, price, category, flavor, available_count, updated_at) VALUES (?,?,?,?,?, ?, datetime('now'))",
        (name, description, float(price), category, flavor, int(available_count)),
    )
    await conn.commit()
    cur = await conn.execute("SELECT id, name, description, price, category, flavor, available_count FROM menu ORDER BY id DESC LIMIT 1")
    r = await cur.fetchone()
    doc = {
        "id": r["id"],
        "name": r["name"],
        "description": r.get("description", ""),
        "price": r["price"],
        "category": r.get("category", ""),
        "flavor": r.get("flavor", ""),
        "available_count": int(r.get("available_count", 0)),
    }
    # Queue outbox event for Mongo
    await outbox_enqueue("menu", "insert", doc)
    await _refresh_cache()
    return doc

async def update_menu_item(item_id: int, available_count: Optional[int] = None) -> Dict[str, Any]:
    conn = await get_db()
    patch_pairs = []
    params = []
    if available_count is not None:
        patch_pairs.append("available_count = ?")
        params.append(int(available_count))
    if not patch_pairs:
        cur = await conn.execute("SELECT id, name, description, price, category, flavor, available_count FROM menu WHERE id = ?", (int(item_id),))
        r = await cur.fetchone()
        return ({"id": r["id"], "name": r["name"], "description": r.get("description", ""), "price": r["price"], "category": r.get("category", ""), "flavor": r.get("flavor", ""), "available_count": int(r.get("available_count", 0))}
                if r else {"state": "not_found"})
    patch_pairs.append("updated_at = datetime('now')")
    sql = "UPDATE menu SET " + ", ".join(patch_pairs) + " WHERE id = ?"
    params.append(int(item_id))
    cur2 = await conn.execute(sql, tuple(params))
    await conn.commit()
    if cur2.rowcount == 0:
        return {"state": "not_found"}
    cur = await conn.execute("SELECT id, name, description, price, category, flavor, available_count FROM menu WHERE id = ?", (int(item_id),))
    r = await cur.fetchone()
    await outbox_enqueue("menu", "update", {"id": int(item_id), "name": r["name"], "description": r.get("description",""), "price": r["price"], "category": r.get("category",""), "flavor": r.get("flavor",""), "available_count": int(r.get("available_count",0))})
    await _refresh_cache()
    return ({"id": r["id"], "name": r["name"], "description": r.get("description", ""), "price": r["price"], "category": r.get("category", ""), "flavor": r.get("flavor", ""), "available_count": int(r.get("available_count",0))}
            if r else {"state": "not_found"})

async def delete_menu_item(item_id: int) -> Dict[str, Any]:
    conn = await get_db()
    cur = await conn.execute("DELETE FROM menu WHERE id = ?", (int(item_id),))
    await conn.commit()
    if cur.rowcount == 0:
        return {"state": "not_found"}
    await outbox_enqueue("menu", "delete", {"id": int(item_id)})
    await _refresh_cache()
    return {"state": "deleted", "id": int(item_id)}
