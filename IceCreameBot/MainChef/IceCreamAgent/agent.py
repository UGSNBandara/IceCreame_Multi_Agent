import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent

from ...DB_Tools.menuTool import (
    instruction = """
    You are Sofia, a friendly ice cream shop cashier of the Magic Ice Cream.

    Tone
    - Speak naturally, warm and conversational.
    - Use short, complete sentences (about 8–14 words).
    - Ask clear questions with natural phrasing.

    Pricing
    - Do not mention prices when exploring or listing menu items.
    - Only share prices if the user explicitly asks; format: 350 rupee (no decimals).

    Scope
    - Menu is static and category-first: categories = [Cup, Cone, Stick].
    - Flavors exist per item but are not proactively listed.
    - Budget bundles, cart, checkout. No complaints.

    Tools
    - get_items_by_category(category) -> returns list of items in that category with stock > 0
    - get_items_by_flavor(flavor) -> returns list of items with that flavor and stock > 0 (use only if user asks for a flavor)
    - get_items_by_category_flavor(category, flavor) -> returns items matching both (use sparingly)
    - get_item_details(item_id) -> get full details for specific item
    - plan_bundle_tool(payload) -> returns up to 2 plans: cheapest and variety
    - get_top_categories_for_session() -> returns top categories for this session's segment
    - add_item_to_cart, remove_item_from_cart, clear_cart
    - get_cart_with_total -> always use for totals
    - add_order(customer_name, items, total)

    Rules
    - Never invent items or prices; call tools first.
    - When asked "what do you have?":
        - Say we have Cup, Cone, and Stick.
        - Do not list flavors proactively.
    - When user asks for a category (cups, cones, sticks):
        - Call get_items_by_category(category).
        - List 2–3 item names only (no prices unless asked).
    - When user asks for a specific flavor (e.g., vanilla, chocolate):
        - Call get_items_by_flavor(flavor).
        - Present items grouped by category (Cup, Cone, Stick), names only.
    - When user asks for details:
        - Call get_item_details(item_id) for full description.
    - Before adding to cart:
        - Explicitly confirm the item and quantity.
        - If quantity > available_count, say "Sorry, we only have X left."
    - Checkout flow:
        - Call get_cart_with_total; give brief summary.
        - Ask for name; default "Guest".
        - Ask: "Would you like me to place the order now?"
        - On yes, call add_order and return order_id.

    Errors
    - If out of stock: suggest alternatives from the same category.
    - Never invent items; only suggest what tools return.
    """
- get_top_categories_for_session() -> returns top categories for this session's segment
- add_item_to_cart, remove_item_from_cart, clear_cart
- get_cart_with_total -> always use for totals
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- When asked "what do you have?":
    - Say we have Cup and Cone categories, with Vanilla, Chocolate, and Strawberry flavors.
- When user asks for cups/cones or a flavor:
    - Call get_items_by_category(category) or get_items_by_flavor(flavor) or both.
    - List 2–3 item names only (no prices unless asked).
- When user asks for details:
    - Call get_item_details(item_id) for full description.
- Before adding to cart:
    - Confirm the item and quantity.
    - If quantity > available_count, say "Sorry, we only have X left."
- Checkout flow:
    - Call get_cart_with_total; give brief summary.
    - Ask for name; default "Guest".
    - Ask: "Would you like me to place the order now?"
    - On yes, call add_order and return order_id.

Errors
- If out of stock: suggest alternatives from same category/flavor.
- Never invent items; only suggest what tools return.
"""

# Agent is constructed after tool functions are defined below

# ---- Context wiring (minimal, non-blocking) ----
_session_reader = SessionContextReader()
_global_reader = GlobalContextReader()
_pop_store = CategoryPopularityStore()
_analytics = AnalyticsSink()
start_weather_warmup(_global_reader)
_cf_cache = CategoryFlavorCache()

# Warm the category/flavor cache at startup
async def _warm_cf():
    await _cf_cache.refresh()
try:
    import asyncio as _aio
    _aio.run(_warm_cf())
except Exception:
    pass

async def get_top_categories_for_session():
    """Return top categories for the computed segment using session-scoped context."""
    session_id = get_current_session()
    ctx = _session_reader.read(session_id) if session_id else {"age_group": None, "gender_guess": None}
    age = ctx.get("age_group")
    gender = ctx.get("gender_guess")
    temp_bucket = _global_reader.temperature_bucket()
    tod = _global_reader.time_of_day()
    segment_key = make_segment_key(age, gender, temp_bucket, tod)
    tops = await _pop_store.get_top_categories(segment_key, k=3)
    if not tops:
        tops = await _pop_store.get_global_top_categories(k=3)
    _analytics.emit("session_context_snapshot", {
        "session_id": session_id,
        "segment_key": segment_key,
        "age_group": age,
        "gender_guess": gender,
        "time_of_day": tod,
        "temperature_bucket": temp_bucket,
    })
    return tops

async def increment_category_popularity(segment_key: str, category: str):
    await _pop_store.increment(segment_key, category)
    _analytics.emit("selection", {"segment_key": segment_key, "category": category})
    return {"ok": True}

def get_items_by_category(category: str):
    """Get all available items (stock > 0) in a category."""
    cache = get_static_cache()
    items = cache.get_by_category(category)
    return {"items": [{"id": i["id"], "name": i["name"], "price": i["price"], "flavor": i["flavor"], "available_count": i["available_count"]} for i in items]}

def get_items_by_flavor(flavor: str):
    """Get all available items (stock > 0) with a flavor."""
    cache = get_static_cache()
    items = cache.get_by_flavor(flavor)
    return {"items": [{"id": i["id"], "name": i["name"], "price": i["price"], "category": i["category"], "available_count": i["available_count"]} for i in items]}

def get_items_by_category_flavor(category: str, flavor: str):
    """Get items matching both category and flavor (stock > 0)."""
    cache = get_static_cache()
    items = cache.get_by_category_and_flavor(category, flavor)
    return {"items": [{"id": i["id"], "name": i["name"], "price": i["price"], "available_count": i["available_count"]} for i in items]}

def get_item_details(item_id: int):
    """Get full details for a specific item by ID."""
    cache = get_static_cache()
    item = cache.get_by_id(item_id)
    if not item:
        return {"state": "not_found"}
    return {"id": item["id"], "name": item["name"], "description": item["description"], 
            "price": item["price"], "category": item["category"], "flavor": item["flavor"], 
            "available_count": item["available_count"]}

async def plan_bundle_tool(payload: dict):
    try:
        budget_total = float(payload.get("budget_total") or 0.0)
        budget_per_person = float(payload.get("budget_per_person") or 0.0)
        people = int(payload.get("people") or 0)
        flavors = payload.get("flavors") or []
        categories = payload.get("categories") or []
    except Exception:
        budget_total, budget_per_person, people, flavors, categories = 0.0, 0.0, 0, [], []
    return await plan_bundle(budget_total, budget_per_person, people, flavors, categories)
IceCreamAgent = Agent(
    name="IceCreamAgent",
    model=GEMINI_MODEL_ID,
    description="Single agent for browsing, cart, and checkout for an ice cream shop.",
    instruction=instruction,
    tools=[
        get_items_by_category,
        get_items_by_flavor,
        get_items_by_category_flavor,
        get_item_details,
        plan_bundle_tool,
        # Context-aware helpers
        get_top_categories_for_session,
        increment_category_popularity,
        add_item_to_cart,
        remove_item_from_cart,
        clear_cart,
        get_cart_with_total,
        add_order,
    ],
)
