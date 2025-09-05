# DB_Tools/catalogTools.py
from typing import Any, Dict, List
# adjust the import if your path differs
from Cache.IceCreamCache import catalog_cache, IceCreamDTO, CategoryDTO

def _icecream_to_dict(x: IceCreamDTO) -> Dict[str, Any]:
    return x.model_dump()

def _category_to_dict(x: CategoryDTO) -> Dict[str, Any]:
    return x.model_dump()


async def get_icecream_flavors() -> List[Dict[str, Any]]:
    """to get the ice cream flavors

    Args:
        None

    Returns:
        list[dict]: list of flavor dictionaries with keys id, name, description
    """
    try:
        cat = catalog_cache.get()
    except Exception:
        return []
    return [_category_to_dict(c) for c in cat.category_list()]


async def get_icecreams_by_flavor_id(category_id: int) -> List[Dict[str, Any]]:
    """to get the ice creams by flavor id

    Args:
        category_id (int): id of the flavor/category

    Returns:
        list[dict]: list of ice cream dictionaries under the given flavor. returns empty list if none found
    """
    try:
        cat = catalog_cache.get()
    except Exception:
        return []
    items = cat.by_category_id(category_id)
    return [_icecream_to_dict(i) for i in items]


async def get_icecream_by_id(icecream_id: int) -> Dict[str, Any]:
    """to get the ice cream details by ice cream id

    Args:
        icecream_id (int): id of the ice cream

    Returns:
        dict: ice cream dictionary if present, if not found return {"state": "not_found"}
    """
    try:
        cat = catalog_cache.get()
    except Exception:
        return {"state": "catalog_not_loaded"}
    item = cat.by_icecream_id(icecream_id)
    return _icecream_to_dict(item) if item else {"state": "not_found"}
