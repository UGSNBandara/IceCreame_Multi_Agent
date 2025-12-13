# Static menu catalog - coded items for fast retrieval
from typing import List, Dict, Any

STATIC_MENU: List[Dict[str, Any]] = [
    # Cones
    {"id": 101, "name": "Chocolate Cone", "description": "Rich chocolate ice cream in a crispy cone.", "price": 150.0, "category": "Cone", "flavor": "Chocolate", "available_count": 50},
    {"id": 102, "name": "Vanilla Cone", "description": "Classic creamy vanilla ice cream cone.", "price": 150.0, "category": "Cone", "flavor": "Vanilla", "available_count": 50},
    {"id": 103, "name": "Crunch Cone", "description": "Crunchy cone with a special topping.", "price": 170.0, "category": "Cone", "flavor": "Crunch", "available_count": 50},
    {"id": 104, "name": "Cappuccino Cone", "description": "Coffee flavored cappuccino ice cream cone.", "price": 190.0, "category": "Cone", "flavor": "Cappuccino", "available_count": 50},
    {"id": 105, "name": "Blueberry Cone", "description": "Sweet and tangy blueberry ice cream cone.", "price": 190.0, "category": "Cone", "flavor": "Blueberry", "available_count": 50},

    # Sticks
    {"id": 301, "name": "Diul Stick", "description": "Traditional woodapple (Diul) flavored stick.", "price": 60.0, "category": "Stick", "flavor": "Diul", "available_count": 40},
    {"id": 302, "name": "Traffic Light Stick", "description": "Colorful 3-flavor fruit ice stick.", "price": 60.0, "category": "Stick", "flavor": "Fruit", "available_count": 40},
    {"id": 303, "name": "Faluda Stick", "description": "Rose and milk faluda flavored stick.", "price": 60.0, "category": "Stick", "flavor": "Faluda", "available_count": 40},
    {"id": 304, "name": "Magic Choc Vanilla", "description": "Vanilla ice cream coated in chocolate shell.", "price": 150.0, "category": "Stick", "flavor": "Vanilla", "available_count": 40},
    {"id": 305, "name": "Magic Choc Chocolate", "description": "Double chocolate delight on a stick.", "price": 150.0, "category": "Stick", "flavor": "Chocolate", "available_count": 40},
    {"id": 306, "name": "Mango Stick", "description": "Refreshing mango fruit ice stick.", "price": 50.0, "category": "Stick", "flavor": "Mango", "available_count": 40},
    {"id": 307, "name": "Berry Stick", "description": "Mixed berry fruit ice stick.", "price": 50.0, "category": "Stick", "flavor": "Berry", "available_count": 40},
    {"id": 308, "name": "Fantastic Stick", "description": "Premium multi-layered ice cream stick.", "price": 150.0, "category": "Stick", "flavor": "Fantastic", "available_count": 40},
]

# Active categories and flavors
CATEGORIES = ["Cone", "Stick"]
FLAVORS = ["Vanilla", "Chocolate", "Crunch", "Cappuccino", "Blueberry", "Diul", "Fruit", "Faluda", "Mango", "Berry", "Fantastic"]


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
