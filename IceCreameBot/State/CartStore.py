# app/state/cart_store.py
import time, asyncio
from typing import List, Dict, Any, Optional, Tuple

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
                return []
            return [dict(x) for x in lines]

    async def put(self, sid: str, lines: List[Dict[str, Any]], ttl: int = DEFAULT_TTL_SEC) -> None:
        async with self._lock:
            self._carts[sid] = ([dict(x) for x in lines], time.time() + ttl)

    async def clear(self, sid: str) -> None:
        async with self._lock:
            self._carts.pop(sid, None)

# <- This is the exported singleton instance your tools import and use
cart_store = CartStore()
