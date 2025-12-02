from typing import Any, Dict, List, Optional, Tuple
from ..CRUD.db import get_db

async def catalog_facets() -> Dict[str, Any]:
    conn = await get_db()
    facets: Dict[str, Any] = {"categories": [], "flavors": [], "price_buckets": []}
    # Categories
    cur = await conn.execute("SELECT c.id, c.name, COUNT(ic.item_id) AS count FROM categories c LEFT JOIN item_category ic ON c.id = ic.category_id GROUP BY c.id, c.name ORDER BY c.name ASC")
    facets["categories"] = await cur.fetchall()
    # Flavors
    cur = await conn.execute("SELECT f.id, f.name, COUNT(ifl.item_id) AS count FROM flavors f LEFT JOIN item_flavor ifl ON f.id = ifl.flavor_id GROUP BY f.id, f.name ORDER BY f.name ASC")
    facets["flavors"] = await cur.fetchall()
    # Price buckets (0-100, 100-300, 300-600, 600+)
    buckets: List[Tuple[str, float, Optional[float]]] = [
        ("0-100", 0, 100),
        ("100-300", 100, 300),
        ("300-600", 300, 600),
        ("600+", 600, None),
    ]
    out_buckets: List[Dict[str, Any]] = []
    for label, lo, hi in buckets:
        if hi is None:
            cur = await conn.execute("SELECT COUNT(1) AS c FROM menu WHERE price >= ?", (lo,))
        else:
            cur = await conn.execute("SELECT COUNT(1) AS c FROM menu WHERE price >= ? AND price < ?", (lo, hi))
        row = await cur.fetchone()
        out_buckets.append({"label": label, "count": int(row.get("c", 0))})
    facets["price_buckets"] = out_buckets
    return facets

async def catalog_search(
    categories: Optional[List[int]] = None,
    flavors: Optional[List[int]] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    conn = await get_db()
    where = ["1=1"]
    params: List[Any] = []
    join_cat = False
    join_flv = False
    if price_min is not None:
        where.append("m.price >= ?")
        params.append(float(price_min))
    if price_max is not None:
        where.append("m.price <= ?")
        params.append(float(price_max))
    if categories:
        join_cat = True
        placeholders = ",".join(["?"] * len(categories))
        where.append(f"ic.category_id IN ({placeholders})")
        params.extend([int(x) for x in categories])
    if flavors:
        join_flv = True
        placeholders = ",".join(["?"] * len(flavors))
        where.append(f"ifl.flavor_id IN ({placeholders})")
        params.extend([int(x) for x in flavors])
    joins = []
    if join_cat:
        joins.append("LEFT JOIN item_category ic ON ic.item_id = m.id")
    if join_flv:
        joins.append("LEFT JOIN item_flavor ifl ON ifl.item_id = m.id")
    # Return lightweight fields only (exclude description for shortlist)
    sql = "SELECT DISTINCT m.id, m.name, m.price FROM menu m " + (" ".join(joins)) + " WHERE " + " AND ".join(where) + " ORDER BY m.price ASC, m.id ASC LIMIT ?"
    params.append(int(limit))
    cur = await conn.execute(sql, tuple(params))
    items = await cur.fetchall()
    facets = await catalog_facets()
    return {"items": items, "facets": facets}
