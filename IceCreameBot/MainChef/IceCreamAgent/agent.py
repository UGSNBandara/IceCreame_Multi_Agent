import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent

from ...DB_Tools.cartTool import (
    update_cart_item,
    remove_item_from_cart,
    clear_cart,
    get_cart_with_total,
)
from ...DB_Tools.orderTool import add_order
from ...DB_Tools.pricingTool import plan_bundle
from ..static_menu import get_static_cache, CATEGORIES, FLAVORS
from ..context_services import (
    SessionContextReader,
    GlobalContextReader,
    CategoryPopularityStore,
    AnalyticsSink,
    make_segment_key,
    start_weather_warmup,
    CategoryFlavorCache,
    get_current_session,
)

load_dotenv()
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite")

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

MENU KNOWLEDGE BASE (Use this to answer "Do you have X?" questions):
- Cones: Pani Kaju (Cashew), Vanilla, Chocolate, Fruit & Nut
- Cups: Chocolate, Vanilla, Fruit & Nut, Strawberry
- Sticks: Faluda, Chocolate, Mango

PHONETIC ALIASES (Common misheard names):
- "Pani Kaju" -> Panic, Panika, Honey Kaju, Cashew, Panika Jakon, Panika Juan
- "Cone" -> Corn, Con, Korn
- "Faluda" -> Falooda, Faloda

Tools
- get_items_by_category(category) -> returns list of items in that category with stock > 0
- get_items_by_flavor(flavor) -> returns list of items with that flavor and stock > 0 (use only if user asks for a flavor)
- get_item_details(item_id) -> get full details for specific item
- plan_bundle_tool(payload) -> returns up to 2 plans: cheapest and variety
- update_cart_item(item_id, qty, mode) -> Update cart. mode="add" (default) adds to existing; mode="set" sets exact quantity (use for corrections).
- remove_item_from_cart(item_id) -> Remove item completely.
- clear_cart -> Clear all items.
- get_cart_with_total -> always use for totals
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- TRUST YOUR KNOWLEDGE BASE FIRST. If a user asks for "Pani Kaju" (or any alias like "Panic"), check the Knowledge Base. You will see it exists in Cones. Do NOT assume it is out of stock just because a tool search for "Panic" returns nothing. Instead, ask: "Did you mean Pani Kaju Cone?" or search for "Cashew".
- If a tool returns "not_found" or empty results, do NOT say "out of stock". Say "I didn't find an item with that name." Only say "out of stock" if the tool explicitly returns "available_count: 0".
- You already know the menu items in your KNOWLEDGE BASE. If a user asks for a flavor (like 'Chocolate' or 'Pani Kaju'), check your Knowledge Base first. If it exists in multiple categories, tell the user options (e.g., 'We have Chocolate in Cups, Cones, and Sticks'). Do NOT say 'we don't have it' unless you are sure.
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
- Before adding/updating cart:
    - Explicitly confirm the item and quantity.
    - Use update_cart_item. For "add 2 more", use mode="add". For "change to 5", use mode="set".
    - If quantity > available_count, say "Sorry, we only have X left."
- Smart Suggestions (Marketer Mode):
    - If a user asks for something unavailable (or out of stock), NEVER just say "no".
    - Always suggest a similar alternative from the menu.
    - Example: "We don't have Tiramisu, but our Chocolate Cone is very rich and creamy!"
- Closing the Sale:
    - If the user says "No" (to "anything else?") or "That's all", DO NOT say "OK".
    - Immediately move to checkout: "Great! Let me get that ready for you."
    - Call get_cart_with_total, summarize, and ask: "Shall I place the order for you?"
    - Ask for name; default "Guest".
    - On yes, call add_order and return order_id.

Errors
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
        get_item_details,
        plan_bundle_tool,
        # Context-aware helpers
        update_cart_item,
        remove_item_from_cart,
        clear_cart,
        get_cart_with_total,
        add_order,
    ],
)
