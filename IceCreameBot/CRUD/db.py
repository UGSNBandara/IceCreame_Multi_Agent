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

  # Facet tables for categories and flavors (many-to-many)
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS categories (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE
    )
    """
  )
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS flavors (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE
    )
    """
  )
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS item_category (
      item_id INTEGER NOT NULL,
      category_id INTEGER NOT NULL,
      PRIMARY KEY (item_id, category_id)
    )
    """
  )
  await conn.execute(
    """
    CREATE TABLE IF NOT EXISTS item_flavor (
      item_id INTEGER NOT NULL,
      flavor_id INTEGER NOT NULL,
      PRIMARY KEY (item_id, flavor_id)
    )
    """
  )
  await conn.commit()

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
async def list_categories() -> list[dict]:
  conn = await get_db()
  cur = await conn.execute("SELECT id, name FROM categories ORDER BY name ASC")
  return await cur.fetchall()

async def add_category(name: str) -> dict:
  conn = await get_db()
  await conn.execute("INSERT INTO categories(name) VALUES (?)", (name,))
  await conn.commit()
  cur = await conn.execute("SELECT id, name FROM categories WHERE name = ?", (name,))
  row = await cur.fetchone()
  doc = {"id": row["id"], "name": row["name"]}
  await outbox_enqueue("category", "upsert", doc)
  return doc

async def update_category(cat_id: int, name: str) -> dict:
  conn = await get_db()
  cur = await conn.execute("UPDATE categories SET name=? WHERE id=?", (name, int(cat_id)))
  await conn.commit()
  if cur.rowcount == 0:
    return {"state": "not_found"}
  cur = await conn.execute("SELECT id, name FROM categories WHERE id = ?", (int(cat_id),))
  row = await cur.fetchone()
  doc = {"id": row["id"], "name": row["name"]}
  await outbox_enqueue("category", "upsert", doc)
  return doc

async def delete_category(cat_id: int) -> dict:
  conn = await get_db()
  cur = await conn.execute("DELETE FROM categories WHERE id=?", (int(cat_id),))
  await conn.execute("DELETE FROM item_category WHERE category_id=?", (int(cat_id),))
  await conn.commit()
  if cur.rowcount == 0:
    return {"state": "not_found"}
  await outbox_enqueue("category", "delete", {"id": int(cat_id)})
  return {"state": "deleted", "id": int(cat_id)}

# ---- Catalog CRUD: Flavors ----
async def list_flavors() -> list[dict]:
  conn = await get_db()
  cur = await conn.execute("SELECT id, name FROM flavors ORDER BY name ASC")
  return await cur.fetchall()

async def add_flavor(name: str) -> dict:
  conn = await get_db()
  await conn.execute("INSERT INTO flavors(name) VALUES (?)", (name,))
  await conn.commit()
  cur = await conn.execute("SELECT id, name FROM flavors WHERE name = ?", (name,))
  row = await cur.fetchone()
  doc = {"id": row["id"], "name": row["name"]}
  await outbox_enqueue("flavor", "upsert", doc)
  return doc

async def update_flavor(flv_id: int, name: str) -> dict:
  conn = await get_db()
  cur = await conn.execute("UPDATE flavors SET name=? WHERE id=?", (name, int(flv_id)))
  await conn.commit()
  if cur.rowcount == 0:
    return {"state": "not_found"}
  cur = await conn.execute("SELECT id, name FROM flavors WHERE id = ?", (int(flv_id),))
  row = await cur.fetchone()
  doc = {"id": row["id"], "name": row["name"]}
  await outbox_enqueue("flavor", "upsert", doc)
  return doc

async def delete_flavor(flv_id: int) -> dict:
  conn = await get_db()
  cur = await conn.execute("DELETE FROM flavors WHERE id=?", (int(flv_id),))
  await conn.execute("DELETE FROM item_flavor WHERE flavor_id=?", (int(flv_id),))
  await conn.commit()
  if cur.rowcount == 0:
    return {"state": "not_found"}
  await outbox_enqueue("flavor", "delete", {"id": int(flv_id)})
  return {"state": "deleted", "id": int(flv_id)}

# ---- Item mappings ----
async def list_item_categories(item_id: int) -> list[dict]:
  conn = await get_db()
  cur = await conn.execute(
    "SELECT c.id, c.name FROM item_category ic JOIN categories c ON c.id = ic.category_id WHERE ic.item_id=? ORDER BY c.name ASC",
    (int(item_id),),
  )
  return await cur.fetchall()

async def add_item_category(item_id: int, category_id: int) -> dict:
  conn = await get_db()
  await conn.execute(
    "INSERT OR IGNORE INTO item_category(item_id, category_id) VALUES (?,?)",
    (int(item_id), int(category_id)),
  )
  await conn.commit()
  doc = {"item_id": int(item_id), "category_id": int(category_id)}
  await outbox_enqueue("item_category", "upsert", doc)
  return doc

async def remove_item_category(item_id: int, category_id: int) -> dict:
  conn = await get_db()
  cur = await conn.execute(
    "DELETE FROM item_category WHERE item_id=? AND category_id=?",
    (int(item_id), int(category_id)),
  )
  await conn.commit()
  if cur.rowcount == 0:
    return {"state": "not_found"}
  await outbox_enqueue("item_category", "delete", {"item_id": int(item_id), "category_id": int(category_id)})
  return {"state": "deleted"}

async def list_item_flavors(item_id: int) -> list[dict]:
  conn = await get_db()
  cur = await conn.execute(
    "SELECT f.id, f.name FROM item_flavor ifl JOIN flavors f ON f.id = ifl.flavor_id WHERE ifl.item_id=? ORDER BY f.name ASC",
    (int(item_id),),
  )
  return await cur.fetchall()

async def add_item_flavor(item_id: int, flavor_id: int) -> dict:
  conn = await get_db()
  await conn.execute(
    "INSERT OR IGNORE INTO item_flavor(item_id, flavor_id) VALUES (?,?)",
    (int(item_id), int(flavor_id)),
  )
  await conn.commit()
  doc = {"item_id": int(item_id), "flavor_id": int(flavor_id)}
  await outbox_enqueue("item_flavor", "upsert", doc)
  return doc

async def remove_item_flavor(item_id: int, flavor_id: int) -> dict:
  conn = await get_db()
  cur = await conn.execute(
    "DELETE FROM item_flavor WHERE item_id=? AND flavor_id=?",
    (int(item_id), int(flavor_id)),
  )
  await conn.commit()
  if cur.rowcount == 0:
    return {"state": "not_found"}
  await outbox_enqueue("item_flavor", "delete", {"item_id": int(item_id), "flavor_id": int(flavor_id)})
  return {"state": "deleted"}

# ---- Upserts for hydration ----
async def sqlite_upsert_categories(docs: list[dict]):
  conn = await get_db()
  for d in docs:
    cid = int(d.get("id")) if d.get("id") is not None else None
    if cid is None:
      await conn.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (d.get("name",""),))
    else:
      cur = await conn.execute("SELECT id FROM categories WHERE id=?", (cid,))
      row = await cur.fetchone()
      if row:
        await conn.execute("UPDATE categories SET name=? WHERE id=?", (d.get("name",""), cid))
      else:
        await conn.execute("INSERT INTO categories(id, name) VALUES (?,?)", (cid, d.get("name","")))
  await conn.commit()

async def sqlite_upsert_flavors(docs: list[dict]):
  conn = await get_db()
  for d in docs:
    fid = int(d.get("id")) if d.get("id") is not None else None
    if fid is None:
      await conn.execute("INSERT OR IGNORE INTO flavors(name) VALUES (?)", (d.get("name",""),))
    else:
      cur = await conn.execute("SELECT id FROM flavors WHERE id=?", (fid,))
      row = await cur.fetchone()
      if row:
        await conn.execute("UPDATE flavors SET name=? WHERE id=?", (d.get("name",""), fid))
      else:
        await conn.execute("INSERT INTO flavors(id, name) VALUES (?,?)", (fid, d.get("name","")))
  await conn.commit()

async def sqlite_upsert_item_category(docs: list[dict]):
  conn = await get_db()
  for d in docs:
    await conn.execute(
      "INSERT OR IGNORE INTO item_category(item_id, category_id) VALUES (?,?)",
      (int(d.get("item_id")), int(d.get("category_id"))),
    )
  await conn.commit()

async def sqlite_upsert_item_flavor(docs: list[dict]):
  conn = await get_db()
  for d in docs:
    await conn.execute(
      "INSERT OR IGNORE INTO item_flavor(item_id, flavor_id) VALUES (?,?)",
      (int(d.get("item_id")), int(d.get("flavor_id"))),
    )
  await conn.commit()
