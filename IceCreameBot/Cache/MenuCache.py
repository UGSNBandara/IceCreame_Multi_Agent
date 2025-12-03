from dataclasses import dataclass
from typing import Dict, List, Optional
from pydantic import BaseModel

class MenuItemDTO(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    flavor: str
    available_count: int

@dataclass
class MenuCatalog:
    by_id: Dict[int, MenuItemDTO]

    def to_list(self) -> List[MenuItemDTO]:
        return list(self.by_id.values())

    def by_item_id(self, item_id: int) -> Optional[MenuItemDTO]:
        return self.by_id.get(int(item_id))

class MenuCache:
    _catalog: Optional[MenuCatalog] = None

    def load(self, items: List[MenuItemDTO]) -> None:
        by_id: Dict[int, MenuItemDTO] = {int(i.id): i for i in items}
        self._catalog = MenuCatalog(by_id=by_id)

    def get(self) -> MenuCatalog:
        if not self._catalog:
            raise RuntimeError("Menu not loaded yet")
        return self._catalog

menu_cache = MenuCache()
