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
            elif entity == "analytics":
                await _sync_analytics_event(db, op, payload)
            elif entity == "category":
                await _sync_category_event(db, op, payload)
            elif entity == "flavor":
                await _sync_flavor_event(db, op, payload)
            elif entity == "item_category":
                await _sync_item_category_event(db, op, payload)
            elif entity == "item_flavor":
                await _sync_item_flavor_event(db, op, payload)
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

async def _sync_analytics_event(db, op: str, payload: Dict[str, Any]):
    col = db["session_analytics"]
    if op in ("insert", "update", "session_update"):
        doc = dict(payload)
        doc["updated_at"] = _utc_now_iso()
        await asyncio.to_thread(
            lambda: col.update_one({"session_id": doc["session_id"]}, {"$set": doc}, upsert=True)
        )
    # Analytics usually not deleted; skip delete branch

async def _sync_category_event(db, op: str, payload: Dict[str, Any]):
    col = db["categories"]
    if op in ("insert", "update", "upsert"):
        doc = dict(payload)
        doc["updated_at"] = _utc_now_iso()
        await asyncio.to_thread(
            lambda: col.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        )
    elif op == "delete":
        await asyncio.to_thread(lambda: col.delete_one({"id": payload["id"]}))

async def _sync_flavor_event(db, op: str, payload: Dict[str, Any]):
    col = db["flavors"]
    if op in ("insert", "update", "upsert"):
        doc = dict(payload)
        doc["updated_at"] = _utc_now_iso()
        await asyncio.to_thread(
            lambda: col.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        )
    elif op == "delete":
        await asyncio.to_thread(lambda: col.delete_one({"id": payload["id"]}))

async def _sync_item_category_event(db, op: str, payload: Dict[str, Any]):
    col = db["item_category"]
    key = {"item_id": int(payload["item_id"]), "category_id": int(payload["category_id"])}
    if op in ("insert", "update", "upsert"):
        doc = {**key, "updated_at": _utc_now_iso()}
        await asyncio.to_thread(lambda: col.update_one(key, {"$set": doc}, upsert=True))
    elif op == "delete":
        await asyncio.to_thread(lambda: col.delete_one(key))

async def _sync_item_flavor_event(db, op: str, payload: Dict[str, Any]):
    col = db["item_flavor"]
    key = {"item_id": int(payload["item_id"]), "flavor_id": int(payload["flavor_id"])}
    if op in ("insert", "update", "upsert"):
        doc = {**key, "updated_at": _utc_now_iso()}
        await asyncio.to_thread(lambda: col.update_one(key, {"$set": doc}, upsert=True))
    elif op == "delete":
        await asyncio.to_thread(lambda: col.delete_one(key))


# ---- Hydration (Startup cache rebuild) ----
async def hydrate_sqlite_from_mongo(
    upsert_menu,
    upsert_orders,
    is_sqlite_empty,
    recent_days: int = 14,
    upsert_categories=None,
    upsert_flavors=None,
    upsert_item_category=None,
    upsert_item_flavor=None,
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

    # Pull categories/flavors and mappings if handlers provided
    if upsert_categories is not None:
        cats = await asyncio.to_thread(lambda: list(db["categories"].find({})))
        if cats:
            await upsert_categories(cats)
    if upsert_flavors is not None:
        flvs = await asyncio.to_thread(lambda: list(db["flavors"].find({})))
        if flvs:
            await upsert_flavors(flvs)
    if upsert_item_category is not None:
        ic = await asyncio.to_thread(lambda: list(db["item_category"].find({})))
        if ic:
            await upsert_item_category(ic)
    if upsert_item_flavor is not None:
        ifl = await asyncio.to_thread(lambda: list(db["item_flavor"].find({})))
        if ifl:
            await upsert_item_flavor(ifl)


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


async def hydrate_orders_from_mongo(upsert_orders, recent_days: int = 14):
    """Hydrate orders only from MongoDB. Menu is now static/hardcoded."""
    db = await get_mongo()
    if db is None:
        return
    
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=recent_days)
    orders: List[Dict[str, Any]] = await asyncio.to_thread(
        lambda: list(db["orders"].find({"created_at": {"$gte": since.isoformat()}}))
    )
    if orders:
        await upsert_orders(orders)


async def hydrate_sessions_from_mongo(recent_hours: int = 24) -> List[Dict[str, Any]]:
    """Hydrate session analytics (mood, gender, age) from MongoDB."""
    db = await get_mongo()
    if db is None:
        return []
    
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
    
    # Fetch sessions updated recently
    sessions: List[Dict[str, Any]] = await asyncio.to_thread(
        lambda: list(db["session_analytics"].find({"updated_at": {"$gte": since.isoformat()}}))
    )
    return sessions


async def direct_upsert_orders(docs: List[Dict[str, Any]]):
    db = await get_mongo()
    if db is None or not docs:
        return
    ops = [
        UpdateOne({"id": d["id"]}, {"$set": {**d, "updated_at": _utc_now_iso()}}, upsert=True)
        for d in docs
    ]
    await asyncio.to_thread(lambda: db["orders"].bulk_write(ops))
