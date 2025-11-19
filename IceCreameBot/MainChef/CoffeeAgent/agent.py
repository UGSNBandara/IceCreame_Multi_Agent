import os
from dotenv import load_dotenv
from google.adk.agents import Agent

from ...DB_Tools.menuTool import (
    get_menu_items,
)
from ...DB_Tools.cartTool import (
    add_item_to_cart,
    remove_item_from_cart,
    clear_cart,
    get_cart_with_total,
)
# Use the existing order tool
from ...DB_Tools.orderTool import add_order

load_dotenv()

# Expected envs:
#   GOOGLE_API_KEY=...  (get from https://aistudio.google.com/app/apikey)
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")

instruction = """
You are Sofia, a coffee shop cashier bot.

Scope
- Menu, item choice, cart, checkout. No complaints.

Style
- Friendly, concise, ≤12 words per reply.
- Prices only when asked; format: 1500 rupee (no decimals).
- Keep moving toward placing the order.

Tools
- get_menu_items
- add_item_to_cart, remove_item_from_cart, clear_cart
- get_cart_with_total (use for totals only; never compute)
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- Menu: list item names only, comma-separated.
- Confirm item and quantity before adding.
- Checkout: call get_cart_with_total; brief summary; ask short name (default "Guest"); ask "Place order?"; on yes call add_order; return order_id.

Errors
- If empty/not_found: say unavailable and suggest alternatives.
- If add_order fails: apologize once; suggest retry.
"""

CoffeeShopAgent = Agent(
    name="CoffeeShopAgent",
    model=GEMINI_MODEL_ID,
    description="Single agent for browsing, cart, and checkout for a coffee shop.",
    instruction=instruction,
    tools=[
        get_menu_items,
        add_item_to_cart,
        remove_item_from_cart,
        clear_cart,
        get_cart_with_total,
        add_order,
    ],
)
