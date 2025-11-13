"""
MongoDB async client (Motor) singleton.

Env vars:
  - MONGODB_URI: full Mongo connection string
  - MONGODB_DB:  database name to use

Usage:
  db = await get_db()
  coll = db["orders"]
  await coll.insert_one({...})
"""
from __future__ import annotations

import os
from typing import Optional
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def get_db() -> AsyncIOMotorDatabase:
    """Return a singleton AsyncIOMotorDatabase based on env config."""
    global _client, _db
    if _db is not None:
        return _db

    load_dotenv()
    uri = os.getenv("MONGODB_URI")
    dbname = os.getenv("MONGODB_DB")
    if not uri or not dbname:
        raise RuntimeError("MONGODB_URI and MONGODB_DB must be set in environment")

    _client = AsyncIOMotorClient(uri)
    _db = _client[dbname]
    return _db


async def get_collection(name: str):
    db = await get_db()
    return db[name]
