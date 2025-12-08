# Static menu catalog - coded items for fast retrieval
from typing import List, Dict, Any

# Static menu items: 2 categories (Cup, Cone) × 3 flavors (Vanilla, Chocolate, Strawberry) × 3 items each = 18 items
STATIC_MENU: List[Dict[str, Any]] = [
    # CUP + VANILLA
    {"id": 1, "name": "Classic Vanilla Cup", "description": "Smooth vanilla ice cream in a cup", "price": 350.0, "category": "Cup", "flavor": "Vanilla", "available_count": 50},
    {"id": 2, "name": "Vanilla Delight Cup", "description": "Premium vanilla with cream swirls", "price": 450.0, "category": "Cup", "flavor": "Vanilla", "available_count": 40},
    {"id": 3, "name": "Vanilla Supreme Cup", "description": "Rich vanilla with cookie crumbs", "price": 550.0, "category": "Cup", "flavor": "Vanilla", "available_count": 30},
    
    # CUP + CHOCOLATE
    {"id": 4, "name": "Chocolate Bliss Cup", "description": "Rich chocolate ice cream in a cup", "price": 400.0, "category": "Cup", "flavor": "Chocolate", "available_count": 45},
    {"id": 5, "name": "Dark Chocolate Cup", "description": "Intense dark chocolate flavor", "price": 500.0, "category": "Cup", "flavor": "Chocolate", "available_count": 35},
    {"id": 6, "name": "Chocolate Fudge Cup", "description": "Chocolate with fudge chunks", "price": 600.0, "category": "Cup", "flavor": "Chocolate", "available_count": 25},
    
    # CUP + STRAWBERRY
    {"id": 7, "name": "Strawberry Fresh Cup", "description": "Fresh strawberry ice cream", "price": 380.0, "category": "Cup", "flavor": "Strawberry", "available_count": 40},
    {"id": 8, "name": "Strawberry Cream Cup", "description": "Creamy strawberry delight", "price": 480.0, "category": "Cup", "flavor": "Strawberry", "available_count": 30},
    {"id": 9, "name": "Wild Strawberry Cup", "description": "Wild strawberry with fruit bits", "price": 580.0, "category": "Cup", "flavor": "Strawberry", "available_count": 20},
    
    # CONE + VANILLA
    {"id": 10, "name": "Vanilla Classic Cone", "description": "Vanilla in a crispy cone", "price": 300.0, "category": "Cone", "flavor": "Vanilla", "available_count": 60},
    {"id": 11, "name": "Vanilla Swirl Cone", "description": "Vanilla with caramel swirl in cone", "price": 400.0, "category": "Cone", "flavor": "Vanilla", "available_count": 50},
    {"id": 12, "name": "Vanilla Crunch Cone", "description": "Vanilla with nut topping on cone", "price": 500.0, "category": "Cone", "flavor": "Vanilla", "available_count": 40},
    
    # CONE + CHOCOLATE
    {"id": 13, "name": "Chocolate Cone Classic", "description": "Chocolate ice cream in cone", "price": 350.0, "category": "Cone", "flavor": "Chocolate", "available_count": 55},
    {"id": 14, "name": "Double Chocolate Cone", "description": "Extra chocolate in chocolate cone", "price": 450.0, "category": "Cone", "flavor": "Chocolate", "available_count": 45},
    {"id": 15, "name": "Choco Chip Cone", "description": "Chocolate with chips in cone", "price": 550.0, "category": "Cone", "flavor": "Chocolate", "available_count": 35},
    
    # CONE + STRAWBERRY
    {"id": 16, "name": "Strawberry Cone Light", "description": "Light strawberry in cone", "price": 330.0, "category": "Cone", "flavor": "Strawberry", "available_count": 50},
    {"id": 17, "name": "Strawberry Dream Cone", "description": "Dreamy strawberry in waffle cone", "price": 430.0, "category": "Cone", "flavor": "Strawberry", "available_count": 40},
    {"id": 18, "name": "Berry Blast Cone", "description": "Strawberry with berry mix in cone", "price": 530.0, "category": "Cone", "flavor": "Strawberry", "available_count": 30},
]

# Active categories and flavors
CATEGORIES = ["Cup", "Cone"]
FLAVORS = ["Vanilla", "Chocolate", "Strawberry"]


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
