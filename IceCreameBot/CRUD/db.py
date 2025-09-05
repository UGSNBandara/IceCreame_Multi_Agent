# app/supabase_client.py
import os
from supabase import acreate_client, AsyncClient

_supabase: AsyncClient | None = None
SUPABASE_URL = "https://wicdvohhcwmhwlfahofy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndpY2R2b2hoY3dtaHdsZmFob2Z5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5ODU2NTYsImV4cCI6MjA3MjU2MTY1Nn0.oWDDpNgWzxUmWA4kmksqGInhWkqzoJv_BO1cjLreP5A"



async def get_supabase() -> AsyncClient:
    """Singleton async client (uses env SUPABASE_URL / SUPABASE_KEY)."""
    global _supabase
    if _supabase is None:
        _supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)  # async client
    return _supabase
