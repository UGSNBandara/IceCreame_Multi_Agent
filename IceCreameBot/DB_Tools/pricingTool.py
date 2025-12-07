from typing import Any, Dict, List
from ..CRUD.db import get_db

async def plan_bundle(
    budget_total: float,
    budget_per_person: float,
    people: int,
    flavors: List[str],
    categories: List[str],
) -> Dict[str, Any]:
    """Suggest a simple bundle given budget and preferences.
    Strategy: choose cheapest items matching filters, fill quantities to meet people or budget.
    """
    conn = await get_db()
    where = ["1=1"]
    params: List[Any] = []
    if categories:
        placeholders = ",".join(["?"] * len(categories))
        where.append(f"category IN ({placeholders})")
        params.extend([str(x) for x in categories])
    if flavors:
        placeholders = ",".join(["?"] * len(flavors))
        where.append(f"flavor IN ({placeholders})")
        params.extend([str(x) for x in flavors])
    sql = "SELECT id, name, description, price, available_count FROM menu WHERE " + " AND ".join(where) + " ORDER BY price ASC"
    cur = await conn.execute(sql, tuple(params))
    items = await cur.fetchall()

    if not items:
        return {"state": "no_matches", "bundle": [], "total": 0.0}

    # Helper to compute quantities given items sorted by price
    def _make_bundle(items_sorted: List[Dict[str, Any]], spread: bool = False) -> Dict[str, Any]:
        bundle: List[Dict[str, Any]] = []
        total = 0.0
        remaining_people = int(people or 0)
        remaining_budget = float(budget_total or 0.0)
        picks = items_sorted if spread else items_sorted[:1]  # spread uses multiple cheapest, else single cheapest
        idx = 0
        while True:
            if not picks:
                break
            it = picks[idx % len(picks)]
            price = float(it.get("price") or 0.0)
            stock = int(it.get("available_count", 0))
            if price <= 0 or stock <= 0:
                idx += 1
                if idx >= len(picks):
                    break
                continue
            qty = 0
            if (people or 0) > 0 and (budget_total or 0.0) > 0.0:
                qty_by_people = max(0, remaining_people)
                qty_by_budget = int(remaining_budget // price)
                qty = min(qty_by_people, qty_by_budget)
            elif (people or 0) > 0:
                qty = max(0, remaining_people)
            elif (budget_total or 0.0) > 0.0:
                qty = int(remaining_budget // price)
            else:
                qty = 1
            if qty <= 0:
                break
            take = min(qty, 10, stock)
            if take <= 0:
                break
            bundle.append({"id": it["id"], "name": it["name"], "unit_price": price, "qty": take, "line_total": round(price * take, 2)})
            total += price * take
            remaining_people = max(0, remaining_people - take)
            remaining_budget = max(0.0, remaining_budget - price * take)
            if remaining_people == 0 and ((budget_total or 0.0) <= 0.01):
                break
            idx += 1
            if idx >= len(picks):
                idx = 0
        return {"bundle": bundle, "total": round(total, 2), "remaining_budget": round(remaining_budget, 2), "remaining_people": remaining_people}

    # Build up to two plans: (1) cheapest focus, (2) spread across top-3 cheapest
    items_sorted = items
    plan_a = _make_bundle(items_sorted, spread=False)
    plan_b = _make_bundle(items_sorted[:3], spread=True)
    plans_out = []
    if plan_a["bundle"]:
        plans_out.append({"name": "cheapest", **plan_a})
    if plan_b["bundle"]:
        plans_out.append({"name": "variety", **plan_b})
    if not plans_out:
        return {"state": "no_matches"}
    return {"state": "ok", "plans": plans_out[:2]}
