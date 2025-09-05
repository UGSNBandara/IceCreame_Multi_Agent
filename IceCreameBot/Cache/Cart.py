# app/state/cart_model.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from Cache.IceCreamCache import catalog_cache  # uses your RAM catalog

@dataclass
class CartLine:
    code: int
    name: str
    qty: int
    price: float
    amount: float = field(init=False)

    def __post_init__(self):
        self.qty = int(self.qty)
        self.price = float(self.price)
        self.amount = round(self.qty * self.price, 2)

class CatalogNotLoaded(Exception): ...
class ItemNotFound(Exception): ...

class Cart:
    """In-memory cart with authoritative prices from catalog_cache."""
    def __init__(self, lines: Optional[List[Dict[str, Any]]] = None):
        self._lines: List[CartLine] = []
        for it in lines or []:
            self._lines.append(
                CartLine(
                    code=int(it.get("code", 0)),
                    name=str(it.get("name", "")),
                    qty=int(it.get("qty", 0)),
                    price=float(it.get("price", 0.0)),
                )
            )

    # ----- helpers -----
    def _index(self, code: int) -> int:
        for i, it in enumerate(self._lines):
            if it.code == int(code):
                return i
        return -1

    @staticmethod
    def _resolve_from_catalog(icecream_id: int) -> Dict[str, Any]:
        # raises CatalogNotLoaded or ItemNotFound
        try:
            cat = catalog_cache.get()
        except Exception:
            raise CatalogNotLoaded()

        dto = cat.by_icecream_id(int(icecream_id))
        if not dto:
            raise ItemNotFound()

        return {
            "name": dto.name,
            "price": float(dto.price),
        }

    # ----- operations -----
    def add(self, icecream_id: int, qty: int = 1) -> None:
        """Add quantity; creates line if missing. qty<=0 is a no-op."""
        if qty <= 0:
            return
        prod = self._resolve_from_catalog(icecream_id)
        idx = self._index(icecream_id)
        if idx == -1:
            self._lines.append(CartLine(code=int(icecream_id), name=prod["name"], qty=int(qty), price=prod["price"]))
        else:
            line = self._lines[idx]
            line.qty = int(line.qty) + int(qty)
            line.price = prod["price"]  # authoritative
            line.amount = round(line.qty * line.price, 2)

    def remove(self, icecream_id: int) -> None:
        """Remove line if present (no error if absent)."""
        idx = self._index(icecream_id)
        if idx != -1:
            self._lines.pop(idx)

    def clear(self) -> None:
        self._lines.clear()

    # ----- serialization -----
    def to_lines(self) -> List[Dict[str, Any]]:
        return [
            {"code": it.code, "name": it.name, "qty": it.qty, "price": it.price, "amount": it.amount}
            for it in self._lines
        ]
