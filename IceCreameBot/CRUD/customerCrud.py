from typing import Optional, Dict, Any
from CRUD.db import get_db
from pymongo.errors import DuplicateKeyError


async def _ensure_indexes():
    db = await get_db()
    # Ensure unique index on phone
    await db["customer"].create_index("phone", unique=True, name="uniq_phone")


async def add_customer(name: str, phone: str) -> Dict[str, Any]:
    await _ensure_indexes()
    db = await get_db()
    doc = {"name": name, "phone": phone}
    try:
        res = await db["customer"].insert_one(doc)
    except DuplicateKeyError:
        # Signal to tool layer in a stable way
        raise ValueError("phone_already_exists")

    created = await db["customer"].find_one({"_id": res.inserted_id})
    # normalize id field for consumers
    out = {"id": str(created["_id"]), "name": created.get("name"), "phone": created.get("phone")}
    return out


async def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    doc = await db["customer"].find_one({"phone": phone})
    if not doc:
        return None
    return {"id": str(doc["_id"]), "name": doc.get("name"), "phone": doc.get("phone")}


async def update_customer(
    customer_id: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    from bson import ObjectId

    patch = {k: v for k, v in {"name": name, "phone": phone}.items() if v is not None}
    db = await get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return None
    if not patch:
        doc = await db["customer"].find_one({"_id": oid})
        return {"id": str(doc["_id"]), "name": doc.get("name"), "phone": doc.get("phone")} if doc else None

    try:
        await db["customer"].update_one({"_id": oid}, {"$set": patch})
    except DuplicateKeyError:
        raise ValueError("phone_already_exists")

    doc = await db["customer"].find_one({"_id": oid})
    return {"id": str(doc["_id"]), "name": doc.get("name"), "phone": doc.get("phone")} if doc else None
