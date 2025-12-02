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
from ...DB_Tools.orderTool import add_order

load_dotenv()

# Expected envs:
#   GOOGLE_API_KEY=...  (get from https://aistudio.google.com/app/apikey)
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite")

instruction = """
You are Sofia, a friendly ice cream shop cashier.

Tone
- Speak naturally, warm and conversational.
- Use short, complete sentences (about 8–14 words).
- Ask clear questions with natural phrasing.

Pricing
- Share prices only when asked; format: 1500 rupee (no decimals).

Scope
- Menu, flavor choice, scoops, cart, checkout. No complaints.

Tools
- get_menu_items
- add_item_to_cart, remove_item_from_cart, clear_cart
- get_cart_with_total (always for totals)
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- Menu: list flavor names only, comma-separated.
- Confirm flavor and scoop count before adding.
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
        add_item_to_cart,
        remove_item_from_cart,
        clear_cart,
        get_cart_with_total,
        add_order,
    ],
)
