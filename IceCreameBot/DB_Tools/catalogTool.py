from typing import Any, Dict, List, Optional, Tuple
from ..CRUD.db import get_db

# Strict enums for simplicity (can be edited in code as needed)
CATEGORIES: List[str] = ["Cone", "Cup", "Sundae", "Stick"]
FLAVORS: List[str] = ["Vanilla", "Chocolate", "Strawberry", "Mint"]

async def catalog_facets() -> Dict[str, Any]:
    conn = await get_db()
    facets: Dict[str, Any] = {"categories": [], "flavors": [], "price_buckets": []}

    # Compute counts by scanning menu category/flavor strings
    cur = await conn.execute("SELECT category, flavor FROM menu")
    rows = await cur.fetchall()
    cat_counts: Dict[str, int] = {c: 0 for c in CATEGORIES}
    flv_counts: Dict[str, int] = {f: 0 for f in FLAVORS}
    for r in rows:
        c = str(r.get("category", ""))
        f = str(r.get("flavor", ""))
        if c in cat_counts:
            cat_counts[c] += 1
        if f in flv_counts:
            flv_counts[f] += 1
    facets["categories"] = [{"name": k, "count": v} for k, v in sorted(cat_counts.items())]
    facets["flavors"] = [{"name": k, "count": v} for k, v in sorted(flv_counts.items())]

    # Price buckets
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
    categories: Optional[List[str]] = None,
    flavors: Optional[List[str]] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    conn = await get_db()
    where = ["1=1"]
    params: List[Any] = []
    if price_min is not None:
        where.append("price >= ?")
        params.append(float(price_min))
    if price_max is not None:
        where.append("price <= ?")
        params.append(float(price_max))
    if categories:
        placeholders = ",".join(["?"] * len(categories))
        where.append(f"category IN ({placeholders})")
        params.extend([str(x) for x in categories])
    if flavors:
        placeholders = ",".join(["?"] * len(flavors))
        where.append(f"flavor IN ({placeholders})")
        params.extend([str(x) for x in flavors])
    # Unsorted instantaneous list (frontend sorts if needed)
    sql = "SELECT id, name, price, available_count FROM menu WHERE " + " AND ".join(where) + " LIMIT ?"
    params.append(int(limit))
    cur = await conn.execute(sql, tuple(params))
    items = await cur.fetchall()
    facets = await catalog_facets()
    return {"items": items, "facets": facets}
