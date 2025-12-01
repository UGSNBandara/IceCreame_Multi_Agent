import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

try:
    from pymongo import MongoClient, UpdateOne
    from pymongo.errors import PyMongoError
except Exception:  # pragma: no cover
    MongoClient = None  # type: ignore
    PyMongoError = Exception  # type: ignore

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "icecream_agent")

_mongo_client: Optional[MongoClient] = None
_mongo_lock = asyncio.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_mongo():
    global _mongo_client
    if not MONGO_URI:
        return None
    async with _mongo_lock:
        if _mongo_client is None:
            if MongoClient is None:
                raise RuntimeError("pymongo not installed")
            _mongo_client = MongoClient(MONGO_URI)
        return _mongo_client[MONGO_DB]


# ---- Outbox Processing ----
async def process_outbox_once(fetch_outbox, mark_done, mark_error):
    """Process pending outbox rows once. Functions provided by SQLite layer.

    fetch_outbox: () -> List[Dict]
    mark_done: (id) -> None
    mark_error: (id, error:str) -> None
    """
    db = await get_mongo()
    if db is None:
        return  # Mongo not configured

    pending = await fetch_outbox(limit=50)
    if not pending:
        return

    for ev in pending:
        oid = ev["id"]
        entity = ev["entity"]
        op = ev["op"]
        try:
            payload = json.loads(ev["payload"]) if isinstance(ev["payload"], str) else ev["payload"]
        except Exception:
            payload = {}
        try:
            if entity == "menu":
                await _sync_menu_event(db, op, payload)
            elif entity == "order":
                await _sync_order_event(db, op, payload)
            await mark_done(oid)
        except Exception as e:  # noqa: BLE001
            await mark_error(oid, str(e))


async def _sync_menu_event(db, op: str, payload: Dict[str, Any]):
    col = db["menu"]
    if op in ("insert", "update"):
        # Upsert by id
        doc = dict(payload)
        doc["updated_at"] = _utc_now_iso()
        await asyncio.to_thread(
            lambda: col.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        )
    elif op == "delete":
        await asyncio.to_thread(lambda: col.delete_one({"id": payload["id"]}))


async def _sync_order_event(db, op: str, payload: Dict[str, Any]):
    col = db["orders"]
    if op in ("insert", "update"):
        doc = dict(payload)
        doc["updated_at"] = _utc_now_iso()
        await asyncio.to_thread(
            lambda: col.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        )
    # Orders usually not deleted; skip delete branch


# ---- Hydration (Startup cache rebuild) ----
async def hydrate_sqlite_from_mongo(
    upsert_menu,
    upsert_orders,
    is_sqlite_empty,
    recent_days: int = 14,
):
    db = await get_mongo()
    if db is None:
        return
    empty = await is_sqlite_empty()
    if not empty:
        return

    # Pull menu
    menu_docs: List[Dict[str, Any]] = await asyncio.to_thread(lambda: list(db["menu"].find({})))
    if menu_docs:
        await upsert_menu(menu_docs)

    # Pull recent orders
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=recent_days)
    orders: List[Dict[str, Any]] = await asyncio.to_thread(
        lambda: list(db["orders"].find({"created_at": {"$gte": since.isoformat()}}))
    )
    if orders:
        await upsert_orders(orders)


# ---- Helpers for direct sync triggers ----
async def direct_upsert_menu(docs: List[Dict[str, Any]]):
    db = await get_mongo()
    if db is None:
        return
    if not docs:
        return
    ops = [
        UpdateOne({"id": d["id"]}, {"$set": {**d, "updated_at": _utc_now_iso()}}, upsert=True)
        for d in docs
    ]
    await asyncio.to_thread(lambda: db["menu"].bulk_write(ops))


async def direct_upsert_orders(docs: List[Dict[str, Any]]):
    db = await get_mongo()
    if db is None or not docs:
        return
    ops = [
        UpdateOne({"id": d["id"]}, {"$set": {**d, "updated_at": _utc_now_iso()}}, upsert=True)
        for d in docs
    ]
    await asyncio.to_thread(lambda: db["orders"].bulk_write(ops))
