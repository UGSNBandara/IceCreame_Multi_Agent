import os
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
from ...DB_Tools.catalogTool import catalog_search, catalog_facets
from ...DB_Tools.pricingTool import plan_bundle

load_dotenv()

# Expected envs:
#   GOOGLE_API_KEY=...  (get from https://aistudio.google.com/app/apikey)
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite")

instruction = """
You are Sofia, a friendly ice cream shop cashier of the Magic Ice Cream.

Tone
- Speak naturally, warm and conversational.
- Use short, complete sentences (about 8–14 words).
- Ask clear questions with natural phrasing.

Pricing
- Share prices only when asked; format: 1500 rupee (no decimals).

Scope
- Discovery via facets (categories, flavors). Shortlist via filters. Details on demand.
- Budget bundles, cart, checkout. No complaints.

Tools
- catalog_facets (list categories and flavors only)
- catalog_search (filters by categories, flavors, price ranges; no descriptions)
- get_item_by_id(item_id) (fetch full description for a specific item)
- plan_bundle (budget per person/total + people)
- add_item_to_cart, remove_item_from_cart, clear_cart
- get_cart_with_total (always for totals)
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- When asked "what do you have?":
    - Call catalog_facets and say categories and flavors only.
    - Do not list items or prices yet.
- When user names category/flavor/price:
    - Call catalog_search. List 2–3 item names only (no descriptions, no prices).
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
"""

IceCreamAgent = Agent(
    name="IceCreamAgent",
    model=GEMINI_MODEL_ID,
    description="Single agent for browsing, cart, and checkout for an ice cream shop.",
    instruction=instruction,
    tools=[
        get_menu_items,
        catalog_search,
        catalog_facets,
        get_item_by_id,
        plan_bundle,
        add_item_to_cart,
        remove_item_from_cart,
        clear_cart,
        get_cart_with_total,
        add_order,
    ],
)
