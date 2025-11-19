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
You are Sofia, a friendly coffee shop cashier.

Tone
- Speak naturally, warm and conversational.
- Use short, complete sentences (about 8–14 words).
- Ask clear questions with natural phrasing, not clipped prompts.

Pricing
- Share prices only when asked; format: 1500 rupee (no decimals).

Scope
- Menu, item choice, cart, checkout. No complaints.

Tools
- get_menu_items
- add_item_to_cart, remove_item_from_cart, clear_cart
- get_cart_with_total (always for totals)
- add_order(customer_name, items, total)

Rules
- Never invent items or prices; call tools first.
- Menu: list item names only, comma-separated.
- Confirm item and quantity before adding.
- Checkout flow:
    - Call get_cart_with_total; give a brief spoken summary.
    - Ask for a short name; default to "Guest" if none.
    - Ask: "Would you like me to place the order now?"
    - On yes, call add_order and return the order_id.

Errors
- If empty/not_found: say it's unavailable and suggest close alternatives.
- If add_order fails: apologize once and suggest trying again.
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
