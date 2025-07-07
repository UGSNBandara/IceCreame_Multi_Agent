# db.py
import asyncio
import mariadb
import sys
from contextlib import asynccontextmanager

DB_POOL_CONFIG = {
    'user': 'root',
    'password': 'Deshani613',
    'host': 'localhost',
    'port': 3300,
    'database': 'moodscoope',
    'pool_size': 5, 
    'pool_name': 'moodscoope_pool'
}
db_pool = None

@asynccontextmanager
def initialize_db_pool():
    """Initializes the database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = mariadb.ConnectionPool(**DB_POOL_CONFIG)
            print("MariaDB connection pool initialized successfully!")
        except mariadb.Error as e:
            print(f"Failed to initialize MariaDB connection pool: {e}", file=sys.stderr)
            sys.exit(1) 

@asynccontextmanager
def close_db_pool():
    """Closes all connections in the pool."""
    global db_pool
    if db_pool:
        db_pool.close()
        db_pool = None 
        print("MariaDB connection pool closed.")

@asynccontextmanager
async def get_db_connection():
    """Asynchronously gets a connection from the pool and yields it.
       Ensures connection is returned to the pool after use (async context manager).
    """
    conn = None
    try:
        conn = db_pool.get_connection() 
        yield conn
    finally:
        if conn:
            conn.close() 