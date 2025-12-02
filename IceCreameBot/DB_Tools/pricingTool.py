from typing import Any, Dict, List, Optional
from ..CRUD.db import get_db

async def plan_bundle(
    budget_total: Optional[float] = None,
    budget_per_person: Optional[float] = None,
    people: Optional[int] = None,
    flavor_ids: Optional[List[int]] = None,
    category_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Suggest a simple bundle given budget and preferences.
    Strategy: choose cheapest items matching filters, fill quantities to meet people or budget.
    """
    conn = await get_db()
    where = ["1=1"]
    params: List[Any] = []
    joins: List[str] = []
    if category_ids:
        joins.append("LEFT JOIN item_category ic ON ic.item_id = m.id")
        placeholders = ",".join(["?"] * len(category_ids))
        where.append(f"ic.category_id IN ({placeholders})")
        params.extend([int(x) for x in category_ids])
    if flavor_ids:
        joins.append("LEFT JOIN item_flavor ifl ON ifl.item_id = m.id")
        placeholders = ",".join(["?"] * len(flavor_ids))
        where.append(f"ifl.flavor_id IN ({placeholders})")
        params.extend([int(x) for x in flavor_ids])
    sql = "SELECT DISTINCT m.id, m.name, m.description, m.price FROM menu m " + (" ".join(joins)) + " WHERE " + " AND ".join(where) + " ORDER BY m.price ASC"
    cur = await conn.execute(sql, tuple(params))
    items = await cur.fetchall()

    if not items:
        return {"state": "no_matches", "bundle": [], "total": 0.0}

    bundle: List[Dict[str, Any]] = []
    total = 0.0
    remaining_people = int(people or 0)
    remaining_budget = float(budget_total or 0.0)

    # Simple fill: pick cheapest item repeatedly until constraints met
    for it in items:
        price = float(it.get("price") or 0.0)
        if price <= 0:
            continue
        qty = 0
        if people and budget_total:
            # choose qty bounded by both
            qty_by_people = max(0, remaining_people)
            qty_by_budget = int(remaining_budget // price)
            qty = min(qty_by_people, qty_by_budget)
        elif people:
            qty = max(0, remaining_people)
        elif budget_total:
            qty = int(remaining_budget // price)
        else:
            # No constraints; suggest 1 of cheapest three
            qty = 1
        if qty <= 0:
            continue
        take = min(qty, 10)  # cap per item for variety
        bundle.append({"id": it["id"], "name": it["name"], "unit_price": price, "qty": take, "line_total": round(price * take, 2)})
        total += price * take
        remaining_people = max(0, remaining_people - take)
        remaining_budget = max(0.0, remaining_budget - price * take)
        if remaining_people == 0 and (budget_total is None or remaining_budget <= 0.01):
            break

    return {"state": "ok", "bundle": bundle, "total": round(total, 2), "remaining_budget": round(remaining_budget, 2), "remaining_people": remaining_people}
