"""SQLite async DB layer (replaces previous Mongo layer).

Env vars (optional):
  SQLITE_DB_PATH: path to sqlite file (default: icecream.db)

Tables:
  menu(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price REAL)
  orders(id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, items TEXT, total REAL,
     status TEXT, created_at TEXT)

Note: WAL mode enabled for better concurrent read/write behavior.
"""
import os
import json
from datetime import datetime, timezone
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "icecream.db")

_conn: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
  global _conn
  if _conn is None:
    _conn = await aiosqlite.connect(DB_PATH)
    await _conn.execute("PRAGMA journal_mode=WAL;")
    _conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
  return _conn

async def init_db() -> None:
  conn = await get_db()
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS menu (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      price REAL NOT NULL,
      updated_at TEXT DEFAULT ''
    )
    """
  )
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_name TEXT NOT NULL,
      items TEXT NOT NULL, -- JSON
      total REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'added',
      created_at TEXT NOT NULL,
      updated_at TEXT DEFAULT ''
    )
    """
  )
  # Outbox for Mongo sync
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS outbox (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entity TEXT NOT NULL,          -- 'menu' | 'order'
      op TEXT NOT NULL,              -- 'insert' | 'update' | 'delete'
      payload TEXT NOT NULL,         -- JSON document with stable 'id'
      attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT DEFAULT NULL,
      created_at TEXT NOT NULL,
      processed_at TEXT DEFAULT NULL
    )
    """
  )
  await conn.commit()

  # Try to add columns if older DB exists
  try:
    await conn.execute("ALTER TABLE menu ADD COLUMN updated_at TEXT DEFAULT ''")
  except Exception:
    pass
  try:
    await conn.execute("ALTER TABLE orders ADD COLUMN updated_at TEXT DEFAULT ''")
  except Exception:
    pass
  await conn.commit()

async def seed_menu_if_empty() -> None:
  conn = await get_db()
  cur = await conn.execute("SELECT COUNT(1) AS c FROM menu")
  row = await cur.fetchone()
  if row and row.get("c") == 0:
    # Ice cream sample menu (names & prices illustrative)
    sample = [
      ("Vanilla", "Classic vanilla ice cream", 500.0),
      ("Chocolate", "Rich chocolate scoop", 550.0),
      ("Strawberry", "Fresh strawberry scoop", 550.0),
      ("Mint Chip", "Mint with chocolate chips", 600.0),
      ("Cookie Dough", "Chunks of cookie dough", 650.0),
    ]
    for name, desc, price in sample:
      await conn.execute(
        "INSERT INTO menu(name, description, price, updated_at) VALUES (?,?,?,?)",
        (name, desc, price, datetime.now(timezone.utc).isoformat()),
      )
    await conn.commit()

async def outbox_enqueue(entity: str, op: str, payload: dict) -> None:
  conn = await get_db()
  await conn.execute(
    "INSERT INTO outbox(entity, op, payload, created_at) VALUES (?,?,?,?)",
    (entity, op, json.dumps(payload), datetime.utcnow().isoformat()+"Z"),
  )
  await conn.commit()

async def outbox_fetch(limit: int = 50):
  conn = await get_db()
  cur = await conn.execute(
    "SELECT id, entity, op, payload FROM outbox WHERE processed_at IS NULL ORDER BY id ASC LIMIT ?",
    (limit,),
  )
  return await cur.fetchall()

async def outbox_mark_done(oid: int):
  conn = await get_db()
  await conn.execute(
    "UPDATE outbox SET processed_at = ?, last_error = NULL WHERE id = ?",
    (datetime.utcnow().isoformat()+"Z", oid),
  )
  await conn.commit()

async def outbox_mark_error(oid: int, err: str):
  conn = await get_db()
  await conn.execute(
    "UPDATE outbox SET attempts = attempts + 1, last_error = ? WHERE id = ?",
    (err[:500], oid),
  )
  await conn.commit()

async def sqlite_is_empty():
  conn = await get_db()
  cur = await conn.execute("SELECT COUNT(1) AS c FROM menu")
  r1 = await cur.fetchone()
  cur = await conn.execute("SELECT COUNT(1) AS c FROM orders")
  r2 = await cur.fetchone()
  return (r1.get("c", 0) == 0) and (r2.get("c", 0) == 0)

async def sqlite_upsert_menu(docs: list[dict]):
  conn = await get_db()
  for d in docs:
    # Upsert by id if provided, else insert
    if "id" in d:
      cur = await conn.execute("SELECT id FROM menu WHERE id = ?", (int(d["id"]),))
      row = await cur.fetchone()
      if row:
        await conn.execute(
          "UPDATE menu SET name=?, description=?, price=?, updated_at=? WHERE id=?",
          (d.get("name",""), d.get("description",""), float(d.get("price",0.0)), d.get("updated_at",""), int(d["id"]))
        )
      else:
        await conn.execute(
          "INSERT INTO menu(id, name, description, price, updated_at) VALUES (?,?,?,?,?)",
          (int(d["id"]), d.get("name",""), d.get("description",""), float(d.get("price",0.0)), d.get("updated_at",""))
        )
    else:
      await conn.execute(
        "INSERT INTO menu(name, description, price, updated_at) VALUES (?,?,?,?)",
        (d.get("name",""), d.get("description",""), float(d.get("price",0.0)), d.get("updated_at",""))
      )
  await conn.commit()

async def sqlite_upsert_orders(docs: list[dict]):
  conn = await get_db()
  for d in docs:
    oid = int(d.get("id")) if d.get("id") is not None else None
    if oid is not None:
      cur = await conn.execute("SELECT id FROM orders WHERE id=?", (oid,))
      row = await cur.fetchone()
      if row:
        await conn.execute(
          "UPDATE orders SET customer_name=?, items=?, total=?, status=?, created_at=?, updated_at=? WHERE id=?",
          (
            d.get("customer_name","Guest"), json.dumps(d.get("items",[])), float(d.get("total",0.0)),
            d.get("status","added"), d.get("created_at",""), d.get("updated_at",""), oid
          )
        )
      else:
        await conn.execute(
          "INSERT INTO orders(id, customer_name, items, total, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
          (
            oid, d.get("customer_name","Guest"), json.dumps(d.get("items",[])), float(d.get("total",0.0)),
            d.get("status","added"), d.get("created_at",""), d.get("updated_at","")
          )
        )
    else:
      await conn.execute(
        "INSERT INTO orders(customer_name, items, total, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (
          d.get("customer_name","Guest"), json.dumps(d.get("items",[])), float(d.get("total",0.0)),
          d.get("status","added"), d.get("created_at",""), d.get("updated_at","")
        )
      )
  await conn.commit()
