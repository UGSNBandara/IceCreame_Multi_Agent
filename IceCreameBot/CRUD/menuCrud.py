from typing import List, Optional, Dict, Any
from .db import get_db
from ..Cache.MenuCache import MenuItemDTO, menu_cache

async def fetch_menu_items() -> List[MenuItemDTO]:
    conn = await get_db()
    cur = await conn.execute("SELECT id, name, description, price FROM menu ORDER BY id ASC")
    rows = await cur.fetchall()
    out: List[MenuItemDTO] = []
    for r in rows:
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
    conn = await get_db()
    await conn.execute(
        "INSERT INTO menu(name, description, price) VALUES (?,?,?)",
        (name, description, float(price)),
    )
    await conn.commit()
    cur = await conn.execute("SELECT id, name, description, price FROM menu ORDER BY id DESC LIMIT 1")
    r = await cur.fetchone()
    doc = {"id": r["id"], "name": r["name"], "description": r.get("description", ""), "price": r["price"]}
    await _refresh_cache()
    return doc

async def update_menu_item(item_id: int, name: Optional[str] = None, description: Optional[str] = None, price: Optional[float] = None) -> Dict[str, Any]:
    conn = await get_db()
    patch_pairs = []
    params = []
    if name is not None:
        patch_pairs.append("name = ?")
        params.append(name)
    if description is not None:
        patch_pairs.append("description = ?")
        params.append(description)
    if price is not None:
        patch_pairs.append("price = ?")
        params.append(float(price))
    if not patch_pairs:
        cur = await conn.execute("SELECT id, name, description, price FROM menu WHERE id = ?", (int(item_id),))
        r = await cur.fetchone()
        return ({"id": r["id"], "name": r["name"], "description": r.get("description", ""), "price": r["price"]}
                if r else {"state": "not_found"})
    sql = "UPDATE menu SET " + ", ".join(patch_pairs) + " WHERE id = ?"
    params.append(int(item_id))
    cur2 = await conn.execute(sql, tuple(params))
    await conn.commit()
    if cur2.rowcount == 0:
        return {"state": "not_found"}
    cur = await conn.execute("SELECT id, name, description, price FROM menu WHERE id = ?", (int(item_id),))
    r = await cur.fetchone()
    await _refresh_cache()
    return ({"id": r["id"], "name": r["name"], "description": r.get("description", ""), "price": r["price"]}
            if r else {"state": "not_found"})

async def delete_menu_item(item_id: int) -> Dict[str, Any]:
    conn = await get_db()
    cur = await conn.execute("DELETE FROM menu WHERE id = ?", (int(item_id),))
    await conn.commit()
    if cur.rowcount == 0:
        return {"state": "not_found"}
    await _refresh_cache()
    return {"state": "deleted", "id": int(item_id)}
