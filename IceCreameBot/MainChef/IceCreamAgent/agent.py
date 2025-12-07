import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent

from ...DB_Tools.menuTool import (
    get_menu_items,
    get_item_by_id,
)
from ...DB_Tools.cartTool import (
    add_item_to_cart,
    remove_item_from_cart,
    clear_cart,
    get_cart_with_total,
)
from ...DB_Tools.orderTool import add_order
from ...DB_Tools.catalogTool import catalog_search
from ...DB_Tools.pricingTool import plan_bundle
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

- Tools
- catalog_search_tool(filters) (filters by categories, flavors, price ranges; returns lightweight list)
- Use short, complete sentences (about 8–14 words).
- plan_bundle_tool(payload) (returns up to 2 plans: cheapest and variety)

Pricing
- Share prices only when asked; format: 1500 rupee (no decimals).

Scope
- Discovery uses fixed enums in code (strict lists, not dynamic): categories = [Cone, Cup, Sundae, Stick], flavors = [Vanilla, Chocolate, Strawberry, Mint]. Shortlist via filters (no server facets). Details on demand. Never reference categories or flavors outside these lists.
- Budget bundles, cart, checkout. No complaints.

Tools
- catalog_search_tool(filters) (filters by categories, flavors, price ranges; returns lightweight list)
- get_item_by_id(item_id) (fetch full description for a specific item)
- plan_bundle (returns up to 2 plans: cheapest and variety)
- get_top_categories_for_session() -> returns top categories for this session's segment (session_id auto-injected)
- increment_category_popularity(segment_key, category) -> increments category counters for segment and global
- get_cached_categories() -> returns distinct categories from cache
- get_cached_flavors() -> returns distinct flavors from cache
- add_item_to_cart, remove_item_from_cart, clear_cart
- get_cart_with_total (always for totals)
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- When asked "what do you have?":
    - Say available categories and flavors from the fixed list.
    - Do not list items or prices yet.
- When user names category/flavor/price:
    - First call get_top_categories_for_session to bias toward top categories for this customer segment.
    - Then call catalog_search_tool with filters (validation ensures only allowed enums). List 2–3 item names (no descriptions, no prices). Only suggest items returned by catalog_search_tool.
- When user asks for details of an item:
    - Call get_item_by_id and read a short description.
- Confirm flavor and scoop count before adding to cart.
- Checkout flow:
    - Call get_cart_with_total; give a brief spoken summary.
    - Ask for a short name; default to "Guest" if none.
    - Ask: "Would you like me to place the order now?"
    - On yes, call add_order and return the order_id.

Errors
- If empty/not_found: say it's unavailable and suggest close alternatives.
- If add_order fails: apologize once and suggest trying again.
- Never invent items: always verify with catalog_search or get_item_by_id before adding to cart.
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

def get_cached_categories():
    return _cf_cache.get_categories()

def get_cached_flavors():
    return _cf_cache.get_flavors()

async def catalog_search_tool(filters: dict):
    try:
        categories = filters.get("categories") or []
        flavors = filters.get("flavors") or []
        price_min = float(filters.get("price_min") or 0.0)
        price_max = float(filters.get("price_max") or 0.0)
        limit = int(filters.get("limit") or 20)
    except Exception:
        categories, flavors, price_min, price_max, limit = [], [], 0.0, 0.0, 20
    return await catalog_search(categories, flavors, price_min, price_max, limit)

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
async def catalog_search_tool(filters: dict):
    """ADK-friendly wrapper for catalog_search.

    Accepts a single object 'filters' with keys:
      - categories: List[str] (optional)
      - flavors: List[str] (optional)
      - price_min: float (optional)
      - price_max: float (optional)
      - limit: int (optional)
    Missing or zero/empty values are treated as no filter.
    """
    try:
        categories = filters.get("categories") or []
        flavors = filters.get("flavors") or []
        price_min = float(filters.get("price_min") or 0.0)
        price_max = float(filters.get("price_max") or 0.0)
        limit = int(filters.get("limit") or 20)
    except Exception:
        categories, flavors, price_min, price_max, limit = [], [], 0.0, 0.0, 20
    return await catalog_search(categories, flavors, price_min, price_max, limit)
IceCreamAgent = Agent(
    name="IceCreamAgent",
    model=GEMINI_MODEL_ID,
    description="Single agent for browsing, cart, and checkout for an ice cream shop.",
    instruction=instruction,
    tools=[
        get_menu_items,
        catalog_search_tool,
        get_item_by_id,
        plan_bundle_tool,
        # Context-aware helpers
        get_top_categories_for_session,
        increment_category_popularity,
        get_cached_categories,
        get_cached_flavors,
        add_item_to_cart,
        remove_item_from_cart,
        clear_cart,
        get_cart_with_total,
        add_order,
    ],
)
