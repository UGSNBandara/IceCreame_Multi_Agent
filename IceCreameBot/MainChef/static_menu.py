# Static menu catalog - coded items for fast retrieval
from typing import List, Dict, Any

STATIC_MENU: List[Dict[str, Any]] = [
    # Cones
    {"id": 101, "name": "Pani Kaju Cone", "description": "Cashew mixed ice cream cone.", "price": 300.0, "category": "Cone", "flavor": "Cashew", "available_count": 50},
    {"id": 102, "name": "Vanilla Cone", "description": "Classic vanilla cone.", "price": 300.0, "category": "Cone", "flavor": "Vanilla", "available_count": 50},
    {"id": 103, "name": "Chocolate Cone", "description": "Rich chocolate cone.", "price": 300.0, "category": "Cone", "flavor": "Chocolate", "available_count": 50},
    {"id": 104, "name": "Fruit & Nut Cone", "description": "Fruit and nut cone.", "price": 320.0, "category": "Cone", "flavor": "Fruit & Nut", "available_count": 50},

    # Cups (60 ml)
    {"id": 201, "name": "Chocolate Cup", "description": "60 ml chocolate ice cream cup.", "price": 280.0, "category": "Cup", "flavor": "Chocolate", "available_count": 60},
    {"id": 202, "name": "Vanilla Cup", "description": "60 ml vanilla ice cream cup.", "price": 280.0, "category": "Cup", "flavor": "Vanilla", "available_count": 60},
    {"id": 203, "name": "Fruit & Nut Cup", "description": "60 ml fruit and nut ice cream cup.", "price": 300.0, "category": "Cup", "flavor": "Fruit & Nut", "available_count": 60},
    {"id": 204, "name": "Strawberry Cup", "description": "60 ml strawberry ice cream cup.", "price": 300.0, "category": "Cup", "flavor": "Strawberry", "available_count": 60},

    # Sticks
    {"id": 301, "name": "Faluda Stick", "description": "Faluda-flavored ice cream stick.", "price": 300.0, "category": "Stick", "flavor": "Faluda", "available_count": 40},
    {"id": 302, "name": "Chocolate Stick", "description": "Chocolate ice cream stick.", "price": 300.0, "category": "Stick", "flavor": "Chocolate", "available_count": 40},
    {"id": 303, "name": "Mango Stick", "description": "Mango ice cream stick.", "price": 300.0, "category": "Stick", "flavor": "Mango", "available_count": 40},
]

# Active categories and flavors
CATEGORIES = ["Cup", "Cone", "Stick"]
FLAVORS = ["Vanilla", "Chocolate", "Strawberry", "Cashew", "Fruit & Nut", "Faluda", "Mango"]


class StaticMenuCache:
    """Fast in-memory cache for static menu with stock awareness."""
    
    def __init__(self):
        self._items = {item["id"]: dict(item) for item in STATIC_MENU}
    
    def get_all_available(self) -> List[Dict[str, Any]]:
        """Get all items with stock > 0."""
        return [item for item in self._items.values() if item["available_count"] > 0]
    
    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get items by category (stock > 0 only)."""
        return [item for item in self._items.values() 
                if item["category"] == category and item["available_count"] > 0]
    
    def get_by_flavor(self, flavor: str) -> List[Dict[str, Any]]:
        """Get items by flavor (stock > 0 only)."""
        return [item for item in self._items.values() 
                if item["flavor"] == flavor and item["available_count"] > 0]
    
    def get_by_category_and_flavor(self, category: str, flavor: str) -> List[Dict[str, Any]]:
        """Get items by category and flavor (stock > 0 only)."""
        return [item for item in self._items.values() 
                if item["category"] == category and item["flavor"] == flavor and item["available_count"] > 0]
    
    def get_by_id(self, item_id: int) -> Dict[str, Any] | None:
        """Get single item by ID (includes zero stock for admin)."""
        return self._items.get(item_id)
    
    def decrease_stock(self, item_id: int, quantity: int) -> bool:
        """Decrease stock for an item. Returns True if successful."""
        if item_id not in self._items:
            return False
        item = self._items[item_id]
        if item["available_count"] < quantity:
            return False
        item["available_count"] -= quantity
        return True
    
    def increase_stock(self, item_id: int, quantity: int) -> bool:
        """Increase stock for an item (admin operation)."""
        if item_id not in self._items:
            return False
        self._items[item_id]["available_count"] += quantity
        return True
    
    def get_stock(self, item_id: int) -> int:
        """Get current stock for an item."""
        item = self._items.get(item_id)
        return item["available_count"] if item else 0


# Global cache instance
_static_cache = StaticMenuCache()

def get_static_cache() -> StaticMenuCache:
    """Get the global static menu cache."""
    return _static_cache
