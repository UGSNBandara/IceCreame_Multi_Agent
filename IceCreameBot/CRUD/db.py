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
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "coffee.db")

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
      price REAL NOT NULL
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
      created_at TEXT NOT NULL
    )
    """
  )
  await conn.commit()

async def seed_menu_if_empty() -> None:
  conn = await get_db()
  cur = await conn.execute("SELECT COUNT(1) AS c FROM menu")
  row = await cur.fetchone()
  if row and row.get("c") == 0:
    sample = [
      ("Cappuccino", "Rich espresso with steamed milk", 650.0),
      ("Latte", "Espresso with milk", 550.0),
      ("Espresso", "Strong shot", 450.0),
      ("Iced Coffee", "Chilled brew", 600.0),
      ("Tea", "Hot brewed tea", 350.0),
    ]
    for name, desc, price in sample:
      await conn.execute(
        "INSERT INTO menu(name, description, price) VALUES (?,?,?)",
        (name, desc, price),
      )
    await conn.commit()
