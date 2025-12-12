# api.py
print("=== IMPORTING IceCreameBot.api (sentinel) ===")
import asyncio
import time
import os
from enum import Enum
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from .MainChef.IceCreamAgent.agent import IceCreamAgent, _global_reader
from .MainChef.context_services import set_current_session
from .MainChef.static_menu import get_static_cache
from . import session_store as _session_store
from .utils_for_api import call_agent_async

from .DB_Tools.menustateTool import get_menu_state
from .DB_Tools.catalogTool import catalog_facets
from .CRUD.OrderCrud import list_orders, update_order_status, OrderStatus, get_order_by_id
from .CRUD.db import (
    init_db,
    outbox_fetch,
    outbox_mark_done,
    outbox_mark_error,
    sqlite_upsert_orders,
    sqlite_get_session_order,
    upsert_session_analytics,
    log_weather,
)
from .MainChef.context_services import GlobalContextReader
from .Sync.mongo_sync import process_outbox_once, hydrate_orders_from_mongo

from .tts_stt_api.piper_loader import synthesize, synthesize_to_file
from .DB_Tools.cartTool import get_cart_with_total

load_dotenv()

APP_NAME = "Ice Cream Agent"

app = FastAPI(title=APP_NAME)

# (Optional) allow your frontend
app.add_middleware(
    CORSMiddleware,
    # Use regex to allow any origin; remove credentials so wildcard is safe
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# ---- ADK infra (singletons) ----
session_service = InMemorySessionService()
runner = Runner(agent=IceCreamAgent, app_name=APP_NAME, session_service=session_service)

# Session retention policy (env-configurable)
SESSION_TTL_SEC = int(os.getenv("SESSION_TTL_SEC", "900"))           # 15 minutes
SESSION_IDLE_RESET_SEC = int(os.getenv("SESSION_IDLE_RESET_SEC", "31536000"))  # ~1 year (effectively disabled)

# per-user map -> {"session_id": str, "created_at": float, "last_seen": float}
user_sessions = _session_store.user_sessions
_user_sessions_lock = asyncio.Lock()

# ---- Initial state ----
INITIAL_STATE = {
    "customer_name" : None,
    "customer_id": None,
    "phone_number" : None,
    "mood" : None,
    "age_group"  : None,
    "order_id" : None,
}

# ---- Models ----
class AgeGroup(str, Enum):
    CHILD = "child"
    TEEN = "teen"
    ADULT = "adult"
    SENIOR = "senior"

class GenderGroup(str, Enum):
    MALE = "male"
    FEMALE = "female"

class AgentRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    restart: bool = False
    session_id: Optional[str] = None
    speak: bool = False  # <-- only toggle
    voice: str = "en-US-JennyNeural"  # <-- voice selection
    age_group: Optional[AgeGroup] = None
    gender_guess: Optional[GenderGroup] = None

class AgentResponse(BaseModel):
    response: str
    session_id: str
    audio_base64: Optional[str] = None
    audio_mime: Optional[str] = None

class MenuCreateRequest(BaseModel):
    name: str
    description: str = ""
    price: float
    category: str
    flavor: str
    available_count: int = 0

class MenuUpdateRequest(BaseModel):
    available_count: Optional[int] = None

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderCancelRequest(BaseModel):
    session_id: Optional[str] = None
    order_id: Optional[str] = None

@app.post("/orders/cancel", response_class=JSONResponse)
async def cancel_order(payload: OrderCancelRequest):
    """Cancel an order by order_id or session_id."""
    oid = payload.order_id
    
    if not oid and payload.session_id:
        # Try to find order for session
        found_oid = await sqlite_get_session_order(payload.session_id)
        if found_oid:
            oid = str(found_oid)
            
    if not oid:
        raise HTTPException(status_code=400, detail="Must provide order_id or valid session_id with active order")
        
    try:
        # Use the shared update logic
        updated = await update_order_status(oid, OrderStatus.CANCELED.value)
        state = updated.get("state")
        
        if state == "invalid_status":
            raise HTTPException(status_code=400, detail="Invalid status")
        if state == "invalid_id":
            raise HTTPException(status_code=400, detail="Invalid order id")
        if state == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
            
        # Note: Stock is only deducted on 'done', so canceling 'pending' needs no stock action.
        # If canceling 'done', we technically should restock, but keeping it simple/safe for now.
        
        return JSONResponse(updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {e}")
    
# ---- Lifespan: init DB and sync orders only ----
@app.on_event("startup")
async def _startup():
    print("=== STARTUP BEGIN ===")
    await init_db()
    
    # Log initial weather
    try:
        from datetime import datetime, timezone
        reader = GlobalContextReader()
        # Force a refresh
        reader._refresh_weather_safely()
        timestamp = datetime.now(timezone.utc).isoformat()
        await log_weather(timestamp, reader.temperature_bucket(), reader.time_of_day())
        print(f"=== STARTUP: Logged weather {reader.temperature_bucket()} / {reader.time_of_day()} ===")
    except Exception as e:
        print(f"=== STARTUP: Weather log failed: {e} ===")
    
    # Static menu is hardcoded, no need to hydrate from Mongo
    print("Static menu: 18 items (Cup/Cone × Vanilla/Chocolate/Strawberry)")
    
    # Hydrate orders only from Mongo (menu is static)
    try:
        await hydrate_orders_from_mongo(
            upsert_orders=sqlite_upsert_orders,
        )
    except Exception as e:
        print(f"Order hydration skipped/failed: {e}")
    
    # Start background outbox worker (orders only)
    async def _worker():
        while True:
            try:
                await process_outbox_once(
                    fetch_outbox=outbox_fetch,
                    mark_done=outbox_mark_done,
                    mark_error=outbox_mark_error,
                )
            except Exception as e:  # noqa: BLE001
                print(f"Outbox worker error: {e}")
            await asyncio.sleep(5)
    asyncio.create_task(_worker())

    # Start background weather logger (every 10 mins)
    async def _weather_worker():
        while True:
            try:
                from datetime import datetime, timezone
                reader = GlobalContextReader()
                # Force refresh if needed (handled internally by reader, but we log current state)
                reader._refresh_weather_safely()
                timestamp = datetime.now(timezone.utc).isoformat()
                await log_weather(timestamp, reader.temperature_bucket(), reader.time_of_day())
                # print(f"=== WEATHER LOGGED: {reader.temperature_bucket()} / {reader.time_of_day()} ===")
            except Exception as e:
                print(f"Weather worker error: {e}")
            await asyncio.sleep(600) # 10 minutes
    asyncio.create_task(_weather_worker())

    print("=== STARTUP COMPLETE ===")

@app.get("/health")
async def health():
    from fastapi import Response
    return Response(content='{"ok": true}', media_type="application/json", headers={"X-App-Stamp": "custom123"})

# ---- Debug: Session Context ----
@app.get("/session/context/{session_id}", response_class=JSONResponse)
async def get_session_context(session_id: str):
    try:
        ctx = _session_store.user_sessions.get(session_id)
        if ctx is None:
            # Return empty defaults for clarity
            return JSONResponse({
                "session_id": session_id,
                "age_group": None,
                "gender_guess": None,
                "mood": None,
                "exists": False,
            })
        return JSONResponse({
            "session_id": session_id,
            "age_group": ctx.get("age_group"),
            "gender_guess": ctx.get("gender_guess"),
            "mood": ctx.get("mood"),
            "exists": True,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch session context: {e}")

# ---- Helpers ----
async def _get_or_create_session(user_id: str, session_id: Optional[str], restart: bool) -> str:
    now = time.time()
    async with _user_sessions_lock:
        def _create_new() -> str:
            new = session_service.create_session(
                app_name=APP_NAME, user_id=user_id, state=INITIAL_STATE.copy()
            )
            user_sessions[user_id] = {
                "session_id": new.id,
                "created_at": now,
                "last_seen": now,
            }
            return new.id

        # Explicit restart always creates a new session
        if restart or user_id not in user_sessions:
            return _create_new()

        meta = user_sessions[user_id]
        sid_current = meta.get("session_id")
        created_at = meta.get("created_at", now)
        last_seen = meta.get("last_seen", now)

        # TTL: new session after absolute age
        if (now - created_at) > SESSION_TTL_SEC:
            return _create_new()
        # Idle reset: new session after inactivity window
        if (now - last_seen) > SESSION_IDLE_RESET_SEC:
            return _create_new()

        # Keep server-side session; client-provided session_id is ignored if different
        meta["last_seen"] = now
        user_sessions[user_id] = meta
        return sid_current


# ---- Main endpoint ----
@app.post("/agent/", response_model=AgentResponse)
async def interact_with_agent(req: AgentRequest):
    sid = await _get_or_create_session(req.user_id, req.session_id, req.restart)
    # Update session-scoped context from frontend payload if provided
    try:
        set_current_session(sid)
    except Exception:
        pass
    try:
        ctx = _session_store.user_sessions.get(sid) or {}
        # Only override if provided; keep previous values otherwise
        if req.age_group is not None:
            ctx["age_group"] = req.age_group.value
        if req.gender_guess is not None:
            ctx["gender_guess"] = req.gender_guess.value
        # mood can be added later similarly
        _session_store.user_sessions[sid] = ctx
    except Exception:
        pass

    try:
        reply_text = await call_agent_async(runner, req.user_id, sid, req.text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"agent_error: {e!s}"})


    result = {"response": reply_text or "", "session_id": sid}

    if req.speak:
        try:
            audio_b64, mime = await synthesize(reply_text or "")
            result.update({"audio_base64": audio_b64, "audio_mime": mime})
        except Exception as e:
            print(f"Piper TTS failed: {e}")
            result.update({"audio_base64": None, "audio_mime": None})

    return JSONResponse(result)
    
# ---- Cart Endpoint (Session-scoped) ----
@app.get("/cart/{session_id}", response_class=JSONResponse)
async def get_cart(session_id: str):
    """Return the current cart for a given session_id with totals."""
    from .Context.SessionContext import CURRENT_SID
    token = CURRENT_SID.set(session_id)
    try:
        cart = await get_cart_with_total()
        return JSONResponse({"session_id": session_id, "cart": cart})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cart: {e}")
    finally:
        CURRENT_SID.reset(token)

# ---- Unified Session Summary Endpoint ----
@app.get("/session/{session_id}/summary", response_class=JSONResponse)
async def get_session_summary(session_id: str):
    """Return either the active order for the session or the current cart.
    Shapes:
    - {"kind":"order","order":{...}}
    - {"kind":"cart","cart":{...}}
    - {"kind":"empty","cart":{...}}
    """
    from .Context.SessionContext import CURRENT_SID
    token = CURRENT_SID.set(session_id)
    try:
        oid = await sqlite_get_session_order(session_id)
        if oid is not None:
            order = await get_order_by_id(str(oid))
            if order:
                return JSONResponse({"kind": "order", "order": order})
        cart = await get_cart_with_total()
        kind = "cart" if (cart and cart.get("cart")) else "empty"
        return JSONResponse({"kind": kind, "cart": cart})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch session summary: {e}")
    finally:
        CURRENT_SID.reset(token)
# ---- Admin Sync Endpoints ----
# Removed: automatic sync every ~5 seconds handles it; no manual triggers needed

# ---- Public Catalog Endpoints ----
@app.get("/catalog/facets", response_class=JSONResponse)
async def public_facets():
    try:
        facets = await catalog_facets()
        return JSONResponse({"facets": facets})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"facets_failed: {e}")

# Removed: /catalog/search (frontend will organize via /menu/items)

# Catalog categories/flavors and mapping endpoints removed for strict-enum mode



# ---- Text-only endpoint (no TTS) ----
@app.post("/agent/text", response_model=AgentResponse)
async def interact_with_agent_text_only(req: AgentRequest):
    print("\n" + "="*80)
    print(f"🎯 API ENDPOINT HIT: /agent/text (TEXT ONLY)")
    print(f"   User: {req.user_id}")
    print(f"   Text: {req.text}")
    print(f"   Restart: {req.restart}")
    print("="*80 + "\n")
    
    sid = await _get_or_create_session(req.user_id, req.session_id, req.restart)
    try:
        set_current_session(sid)
    except Exception:
        pass
    try:
        ctx = _session_store.user_sessions.get(sid) or {}
        if req.age_group is not None:
            ctx["age_group"] = req.age_group
        if req.gender_guess is not None:
            ctx["gender_guess"] = req.gender_guess
        _session_store.user_sessions[sid] = ctx
    except Exception:
        pass
    
    print(f"📌 Session ID: {sid}\n")

    try:
        print("🔄 Calling agent...")
        reply_text = await call_agent_async(runner, req.user_id, sid, req.text)
        print(f"✅ Agent returned: {reply_text}\n")
    except Exception as e:
        print(f"❌ Agent error: {e}\n")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"agent_error: {e!s}"})

    # Return only text, no TTS
    result = {"response": reply_text or "", "session_id": sid}
    return JSONResponse(result)


@app.post("/generate-voice/")
async def generate_voice(text: str, filename: str, voice: str = "en_US-lessac-medium"):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if not filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty")
    try:
        path = await synthesize_to_file(text, filename)
        return JSONResponse({
            "success": True,
            "message": "Voice generated",
            "filepath": path,
            "filename": f"{filename}.wav",
            "voice": voice
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Piper generation failed: {e}")


@app.get("/menu/index/{session_id}", response_class=JSONResponse)
async def get_menu_index(session_id: str):
    indexx = await get_menu_state(session_id)
    
    return JSONResponse({"index": indexx})

# ---- Menu Endpoints (Static Cache) ----
@app.get("/menu/items", response_class=JSONResponse)
async def list_menu_items():
    """Get all menu items with stock > 0 (for customers) or all items (for admin)."""
    try:
        cache = get_static_cache()
        items = cache.get_all_available()
        return JSONResponse({"items": items, "count": len(items)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch menu items: {e}")

@app.get("/menu/items/all", response_class=JSONResponse)
async def list_all_menu_items():
    """Get ALL menu items including zero stock (admin only)."""
    try:
        cache = get_static_cache()
        # Access internal items dict to get all items
        items = list(cache._items.values())
        return JSONResponse({"items": items, "count": len(items)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch all menu items: {e}")

@app.get("/menu/items/{item_id}", response_class=JSONResponse)
async def get_menu_item(item_id: int):
    """Get single item by ID."""
    try:
        cache = get_static_cache()
        item = cache.get_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return JSONResponse(item)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch item: {e}")

@app.put("/menu/items/{item_id}/stock", response_class=JSONResponse)
async def update_stock(item_id: int, quantity: int):
    """Update stock for an item (admin operation). Positive to add, negative to reduce."""
    try:
        cache = get_static_cache()
        if quantity >= 0:
            success = cache.increase_stock(item_id, quantity)
        else:
            success = cache.decrease_stock(item_id, abs(quantity))
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid operation or insufficient stock")
        
        item = cache.get_by_id(item_id)
        return JSONResponse({"success": True, "item": item})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update stock: {e}")

# ---- Order Endpoints ----
@app.get("/orders", response_class=JSONResponse)
async def get_orders():
    try:
        orders = await list_orders()
        return JSONResponse({"orders": orders})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {e}")

@app.put("/orders/{order_id}/status", response_class=JSONResponse)
async def update_order_status_endpoint(order_id: str, payload: OrderStatusUpdate):
    try:
        updated = await update_order_status(order_id, payload.status.value)
        state = updated.get("state")
        if state == "invalid_status":
            raise HTTPException(status_code=400, detail="Invalid status")
        if state == "invalid_id":
            raise HTTPException(status_code=400, detail="Invalid order id")
        if state == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Decrease stock when order is marked as done
        if payload.status.value == "done":
            cache = get_static_cache()
            items = updated.get("items", [])
            for item_line in items:
                item_id = item_line.get("code")
                qty = int(item_line.get("qty", 1))
                if item_id:
                    cache.decrease_stock(int(item_id), qty)
        
        return JSONResponse(updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update order status: {e}")

@app.get("/orders/{order_id}", response_class=JSONResponse)
async def get_order(order_id: str):
    try:
        order = await get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return JSONResponse(order)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch order: {e}")

class Emotion(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"

class FacialData(BaseModel):
    emotion: Emotion
    age_group: Optional[AgeGroup] = None
    gender_guess: Optional[GenderGroup] = None

@app.post("/session/{session_id}/facial", response_class=JSONResponse)
async def log_facial(session_id: str, data: FacialData):
    """Log facial expression data for a session and update session context."""
    try:
        # 1. Update session context (in-memory) with age/gender/emotion if provided
        if data.age_group or data.gender_guess or data.emotion:
            async with _user_sessions_lock:
                session_data = user_sessions.get(session_id, {})
                if data.age_group:
                    session_data["age_group"] = data.age_group.value
                if data.gender_guess:
                    session_data["gender_guess"] = data.gender_guess.value
                if data.emotion:
                    session_data["emotion"] = data.emotion.value
                # Ensure session exists in map
                if session_id not in user_sessions:
                    session_data["created_at"] = time.time()
                session_data["last_seen"] = time.time()
                user_sessions[session_id] = session_data
        
        # 2. Log to Session Analytics (DB)
        # Get current weather context
        temp = _global_reader.temperature_bucket()
        tod = _global_reader.time_of_day()
        
        await upsert_session_analytics(
            session_id=session_id,
            age_group=data.age_group.value if data.age_group else None,
            gender=data.gender_guess.value if data.gender_guess else None,
            weather_temp=temp,
            weather_tod=tod,
            new_emotion=data.emotion.value
        )
                
        return JSONResponse({"status": "logged", "context_updated": bool(data.age_group or data.gender_guess)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log facial data: {e}")

# ---- Analytics Endpoints for Admin Panel ----

@app.get("/analytics/dashboard-stats", response_class=JSONResponse)
async def get_dashboard_stats(days: int = 7):
    """
    Get aggregated stats for dashboard charts.
    
    Frontend Implementation Guide:
    1. Demographics (Pie Charts): Use 'age_distribution' and 'gender_distribution'.
    2. Emotion Frequency (Bar Charts): Use 'emotion_frequency'.
    3. Trends (Line Charts): Use 'daily_sessions' (x=day, y=count).
    4. Correlations (Heatmap/Grouped Bar): Use 'emotion_by_weather' (rows=weather, cols=emotion).
    """
    try:
        from .CRUD.db import get_db
        conn = await get_db()
        
        stats = {}

        # 1. Demographics
        cur = await conn.execute("SELECT age_group, COUNT(*) as count FROM session_analytics WHERE age_group IS NOT NULL GROUP BY age_group")
        stats["age_distribution"] = {row["age_group"]: row["count"] for row in await cur.fetchall()}
        
        cur = await conn.execute("SELECT gender, COUNT(*) as count FROM session_analytics WHERE gender IS NOT NULL GROUP BY gender")
        stats["gender_distribution"] = {row["gender"]: row["count"] for row in await cur.fetchall()}

        # 2. Emotion Frequency
        cur = await conn.execute("SELECT dominant_emotion, COUNT(*) as count FROM session_analytics WHERE dominant_emotion IS NOT NULL GROUP BY dominant_emotion")
        stats["emotion_frequency"] = {row["dominant_emotion"]: row["count"] for row in await cur.fetchall()}

        # 3. Trends (Daily Sessions)
        cur = await conn.execute(
            f"SELECT date(updated_at) as day, COUNT(*) as count FROM session_analytics GROUP BY day ORDER BY day DESC LIMIT {days}"
        )
        stats["daily_sessions"] = (await cur.fetchall())[::-1] # Chronological order
        
        # 4. Emotion vs Weather
        cur = await conn.execute(
            "SELECT weather_temp, dominant_emotion, COUNT(*) as count FROM session_analytics WHERE dominant_emotion IS NOT NULL AND weather_temp IS NOT NULL GROUP BY weather_temp, dominant_emotion"
        )
        weather_stats = {}
        for row in await cur.fetchall():
            w = row["weather_temp"]
            e = row["dominant_emotion"]
            c = row["count"]
            if w not in weather_stats: weather_stats[w] = {}
            weather_stats[w][e] = c
        stats["emotion_by_weather"] = weather_stats

        await cur.close()
        return JSONResponse(stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard stats: {e}")

@app.get("/analytics/facial-logs", response_class=JSONResponse)
async def get_facial_logs(
    session_id: Optional[str] = None, 
    age_group: Optional[str] = None,
    gender: Optional[str] = None,
    dominant_emotion: Optional[str] = None,
    limit: int = 50
):
    """
    Get raw session facial analytics for Tables/Grids. 
    
    Frontend Implementation Guide:
    - Use for 'Tables: Raw/aggregated data with sorting'.
    - Support filtering by passing query params (e.g., ?dominant_emotion=happy).
    """
    try:
        from .CRUD.db import get_db
        conn = await get_db()
        query = "SELECT session_id, age_group, gender, weather_temp, weather_tod, dominant_emotion, emotion_counts, updated_at FROM session_analytics WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if age_group:
            query += " AND age_group = ?"
            params.append(age_group)
        if gender:
            query += " AND gender = ?"
            params.append(gender)
        if dominant_emotion:
            query += " AND dominant_emotion = ?"
            params.append(dominant_emotion)
            
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        cur = await conn.execute(query, params)
        rows = await cur.fetchall()
        await cur.close()
        return JSONResponse({"facial_logs": rows})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch facial logs: {e}")

@app.get("/analytics/weather-logs", response_class=JSONResponse)
async def get_weather_logs(limit: int = 10):
    """Get recent weather logs."""
    try:
        from .CRUD.db import get_db
        conn = await get_db()
        cur = await conn.execute(
            "SELECT timestamp, temperature_bucket, time_of_day FROM weather_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return JSONResponse({"weather_logs": rows})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather logs: {e}")
