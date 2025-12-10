"""SQLite async DB layer (replaces previous Mongo layer).

Env vars (optional):
  SQLITE_DB_PATH: path to sqlite file (default: icecream.db)

Tables:
    menu(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price REAL,
      category TEXT, flavor TEXT, available_count INTEGER)
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
      category TEXT DEFAULT '',
      flavor TEXT DEFAULT '',
      available_count INTEGER NOT NULL DEFAULT 0,
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
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL,
      updated_at TEXT DEFAULT ''
    )
    """
  )
  # Map one order per session
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS session_orders (
      session_id TEXT PRIMARY KEY,
      order_id INTEGER NOT NULL,
      created_at TEXT NOT NULL
    )
    """
  )
  # Carts table (session-scoped, JSON snapshot)
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS carts (
      session_id TEXT PRIMARY KEY,
      items TEXT NOT NULL, -- JSON array of cart lines
      updated_at TEXT NOT NULL
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

  # Category popularity (segment-level and global)
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS category_popularity (
      segment_key TEXT NOT NULL,
      category TEXT NOT NULL,
      count INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (segment_key, category)
    )
    """
  )
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS global_category_popularity (
      category TEXT NOT NULL PRIMARY KEY,
      count INTEGER NOT NULL DEFAULT 0
    )
    """
  )
  # Weather logs
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS weather_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      temperature_bucket TEXT NOT NULL,
      time_of_day TEXT NOT NULL
    )
    """
  )
  # Facial expression logs
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS facial_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      timestamp TEXT NOT NULL,
      emotion TEXT NOT NULL,
      confidence REAL NOT NULL
    )
    """
  )
  await conn.commit()

# ---- Session→Order helpers ----
async def sqlite_set_session_order(session_id: str, order_id: int) -> None:
  conn = await get_db()
  await conn.execute(
    "REPLACE INTO session_orders(session_id, order_id, created_at) VALUES(?,?, datetime('now'))",
    (session_id, int(order_id)),
  )
  await conn.commit()

async def sqlite_get_session_order(session_id: str) -> int | None:
  conn = await get_db()
  cur = await conn.execute(
    "SELECT order_id FROM session_orders WHERE session_id = ?",
    (session_id,),
  )
  row = await cur.fetchone()
  await cur.close()
  if not row:
    return None
  # row can be dict or tuple depending on row_factory
  return int(row["order_id"]) if isinstance(row, dict) else int(row[0])

async def sqlite_clear_session_order(session_id: str) -> None:
  conn = await get_db()
  await conn.execute("DELETE FROM session_orders WHERE session_id = ?", (session_id,))
  await conn.commit()

# ---- Cart persistence helpers ----
async def sqlite_get_cart(session_id: str) -> list[dict]:
  conn = await get_db()
  cur = await conn.execute("SELECT items FROM carts WHERE session_id = ?", (session_id,))
  row = await cur.fetchone()
  await cur.close()
  if not row:
    return []
  try:
    return json.loads(row["items"]) if isinstance(row, dict) else json.loads(row[0])
  except Exception:
    return []

async def sqlite_put_cart(session_id: str, items: list[dict]) -> None:
  conn = await get_db()
  payload = json.dumps(items, ensure_ascii=False)
  now = datetime.now(timezone.utc).isoformat()
  await conn.execute(
    "REPLACE INTO carts(session_id, items, updated_at) VALUES(?, ?, ?)",
    (session_id, payload, now),
  )
  await conn.commit()

async def sqlite_clear_cart(session_id: str) -> None:
  conn = await get_db()
  await conn.execute("DELETE FROM carts WHERE session_id = ?", (session_id,))
  await conn.commit()

  # Removed facet tables: categories, flavors, item_category, item_flavor (using enum strings on menu instead)

  # Try to add columns if older DB exists
  try:
    await conn.execute("ALTER TABLE menu ADD COLUMN updated_at TEXT DEFAULT ''")
  except Exception:
    pass
  # Backfill new strict-enum columns if missing
  try:
    await conn.execute("ALTER TABLE menu ADD COLUMN category TEXT DEFAULT ''")
  except Exception:
    pass
  try:
    await conn.execute("ALTER TABLE menu ADD COLUMN flavor TEXT DEFAULT ''")
  except Exception:
    pass
  try:
    await conn.execute("ALTER TABLE menu ADD COLUMN available_count INTEGER NOT NULL DEFAULT 0")
  except Exception:
    pass
  try:
    await conn.execute("ALTER TABLE orders ADD COLUMN updated_at TEXT DEFAULT ''")
  except Exception:
    pass
  await conn.commit()

async def sqlite_clear_all():
  """Remove all rows from menu and orders (keeps schema)."""
  conn = await get_db()
  await conn.execute("DELETE FROM menu")
  await conn.execute("DELETE FROM orders")
  await conn.execute("DELETE FROM category_popularity")
  await conn.execute("DELETE FROM global_category_popularity")
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
          "UPDATE menu SET name=?, description=?, price=?, category=?, flavor=?, available_count=?, updated_at=? WHERE id=?",
          (
            d.get("name",""),
            d.get("description",""),
            float(d.get("price",0.0)),
            d.get("category",""),
            d.get("flavor",""),
            int(d.get("available_count", 0)),
            d.get("updated_at",""),
            int(d["id"]) 
          )
        )
      else:
        await conn.execute(
          "INSERT INTO menu(id, name, description, price, category, flavor, available_count, updated_at) VALUES (?,?,?,?,?,?,?,?)",
          (
            int(d["id"]),
            d.get("name",""),
            d.get("description",""),
            float(d.get("price",0.0)),
            d.get("category",""),
            d.get("flavor",""),
            int(d.get("available_count", 0)),
            d.get("updated_at","")
          )
        )
    else:
      await conn.execute(
        "INSERT INTO menu(name, description, price, category, flavor, available_count, updated_at) VALUES (?,?,?,?,?,?,?)",
        (
          d.get("name",""),
          d.get("description",""),
          float(d.get("price",0.0)),
          d.get("category",""),
          d.get("flavor",""),
          int(d.get("available_count", 0)),
          d.get("updated_at","")
        )
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

# ---- Catalog CRUD: Categories ----
# Categories/flavors CRUD removed (using enum fields in menu; no separate facet tables)

# ---- Catalog CRUD: Flavors ----
# Flavors CRUD removed

# Item mappings removed

# Upserts for categories/flavors/mappings removed

# ---- Category popularity helpers ----
async def pop_increment(segment_key: str, category: str) -> None:
  conn = await get_db()
  await conn.execute(
    "INSERT INTO category_popularity(segment_key, category, count) VALUES (?,?,1) ON CONFLICT(segment_key, category) DO UPDATE SET count = count + 1",
    (segment_key, category),
  )
  await conn.execute(
    "INSERT INTO global_category_popularity(category, count) VALUES (?,1) ON CONFLICT(category) DO UPDATE SET count = count + 1",
    (category,),
  )
  await conn.commit()

async def pop_top_categories(segment_key: str, k: int = 3) -> list[dict]:
  conn = await get_db()
  cur = await conn.execute(
    "SELECT category, count FROM category_popularity WHERE segment_key = ? ORDER BY count DESC, category ASC LIMIT ?",
    (segment_key, int(k)),
  )
  return await cur.fetchall()

async def pop_global_top_categories(k: int = 3) -> list[dict]:
  conn = await get_db()
  cur = await conn.execute(
    "SELECT category, count FROM global_category_popularity ORDER BY count DESC, category ASC LIMIT ?",
    (int(k),),
  )
  return await cur.fetchall()

async def pop_all_segments_top_categories(k: int = 3) -> list[dict]:
  conn = await get_db()
  # Use window function to get top k per segment
  cur = await conn.execute(
    """
    SELECT segment_key, category, count
    FROM (
        SELECT 
            segment_key, 
            category, 
            count,
            ROW_NUMBER() OVER (PARTITION BY segment_key ORDER BY count DESC) as rn
        FROM category_popularity
    )
    WHERE rn <= ?
    ORDER BY segment_key, rn
    """,
    (int(k),),
  )
  return await cur.fetchall()

# ---- Weather & Facial Logs ----
async def log_weather(timestamp: str, temperature_bucket: str, time_of_day: str) -> None:
  conn = await get_db()
  await conn.execute(
    "INSERT INTO weather_logs(timestamp, temperature_bucket, time_of_day) VALUES (?,?,?)",
    (timestamp, temperature_bucket, time_of_day),
  )
  await conn.commit()

async def log_facial_expression(session_id: str, timestamp: str, emotion: str, confidence: float) -> None:
  conn = await get_db()
  await conn.execute(
    "INSERT INTO facial_logs(session_id, timestamp, emotion, confidence) VALUES (?,?,?,?)",
    (session_id, timestamp, emotion, float(confidence)),
  )
  await conn.commit()
