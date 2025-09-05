from dataclasses import dataclass
from typing import Dict, List, Optional
from pydantic import BaseModel

# Keep a light DTO so UI/agent payloads are clean
class IceCreamDTO(BaseModel):
    id: int
    name: str
    category_id: int
    description: str
    price: float

class CategoryDTO(BaseModel):
    id: int
    name: str
    description: str


@dataclass
class Catalog:
    # your custom data structure (fast lookups)
    by_id: Dict[int, IceCreamDTO]
    by_category: Dict[int, List[IceCreamDTO]]
    categories: Dict[int, CategoryDTO]

    def to_list(self) -> List[IceCreamDTO]:
        # full list, if ever needed
        return list(self.by_id.values())

    def category_list(self) -> List[CategoryDTO]:
        return list(self.categories.values())
    
    def by_category_id(self, category_id: int) -> List[IceCreamDTO]:
        return self.by_category.get(category_id, [])
    
    def by_icecream_id(self, icecream_id: int) -> Optional[IceCreamDTO]:
        return self.by_id.get(icecream_id)
    
    

class CatalogCache:
    _catalog: Optional[Catalog] = None

    def load(self, ice_creams: List[IceCreamDTO], categories: List[CategoryDTO]) -> None:
        by_id: Dict[int, IceCreamDTO] = {i.id: i for i in ice_creams}
        cats: Dict[int, CategoryDTO] = {c.id: c for c in categories}

        by_category: Dict[int, List[IceCreamDTO]] = {}

        for it in ice_creams:
            by_category.setdefault(it.category_id, []).append(it)

        self._catalog = Catalog(
            by_id=by_id,
            by_category=by_category,
            categories=cats,
        )       

    def get(self) -> Catalog:
        if not self._catalog:
            raise RuntimeError("Catalog not loaded yet")
        return self._catalog

catalog_cache = CatalogCache()
