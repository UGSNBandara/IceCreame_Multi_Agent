# app/state/cart_store.py
import time, asyncio
from typing import List, Dict, Any, Tuple
from ..CRUD.db import sqlite_get_cart, sqlite_put_cart, sqlite_clear_cart

DEFAULT_TTL_SEC = 60 * 60  # 1 hour

class CartStore:
    def __init__(self):
        self._carts: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, sid: str) -> List[Dict[str, Any]]:
        now = time.time()
        async with self._lock:
            lines, exp = self._carts.get(sid, ([], 0))
            if exp and exp < now:
                self._carts.pop(sid, None)
                lines = []
            if not lines:
                try:
                    lines = [dict(x) for x in await sqlite_get_cart(sid)]
                except Exception:
                    lines = []
            # refresh cache TTL
            self._carts[sid] = ([dict(x) for x in lines], now + DEFAULT_TTL_SEC)
            return [dict(x) for x in lines]

    async def put(self, sid: str, lines: List[Dict[str, Any]], ttl: int = DEFAULT_TTL_SEC) -> None:
        async with self._lock:
            snapshot = [dict(x) for x in lines]
            self._carts[sid] = (snapshot, time.time() + ttl)
            try:
                await sqlite_put_cart(sid, snapshot)
            except Exception:
                # keep cache even if DB write fails
                pass

    async def clear(self, sid: str) -> None:
        async with self._lock:
            self._carts.pop(sid, None)
            try:
                await sqlite_clear_cart(sid)
            except Exception:
                pass

# <- This is the exported singleton instance your tools import and use
cart_store = CartStore()
