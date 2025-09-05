# api_test.py
import os
from typing import Any, Optional, List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, constr

# ---- Your Supabase-backed CRUD wrappers ----
# Adjust import paths if your files are in different packages.
from CRUD.icecreamCrud import fetch_ice_creams, fetch_categories
from CRUD.customerCrud import add_customer, get_customer_by_phone, update_customer
from CRUD.OrderCrud import add_order, get_order_by_id
from CRUD.complainCrud import add_complain

app = FastAPI(title="MoodScoop Test API", version="1.0")

# CORS (optional, helpful while testing from anywhere)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic request models ----------
class CustomerCreate(BaseModel):
    name: str
    phone: str
    address: Optional[str] = None

class CustomerUpdateIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class OrderCreate(BaseModel):
    customer_id: int
    items: Any               # dict or list -> stored as JSON in DB
    dine_in: bool            # True = Dine-in, False = Take-away
    address: Optional[str] = None
    phone: Optional[str] = None
    table_number: Optional[int] = Field(default=None, ge=0)

class ComplainCreate(BaseModel):
    description: str

# ---------- Health ----------
@app.get("/health")
async def health():
    # Quick check that required env vars exist; doesn’t call DB
    return {
        "ok": True,
        "has_SUPABASE_URL": "SUPABASE_URL" in os.environ,
        "has_SUPABASE_KEY": "SUPABASE_KEY" in os.environ,
    }

# ---------- Catalog ----------
@app.get("/catalog/ice-creams")
async def api_ice_creams():
    try:
        data = await fetch_ice_creams()
        return data  # list of IceCreamDTO dicts
    except Exception as e:
        raise HTTPException(500, f"catalog_error: {e}")

@app.get("/catalog/categories")
async def api_categories():
    try:
        data = await fetch_categories()
        return data  # list of CategoryDTO dicts
    except Exception as e:
        raise HTTPException(500, f"catalog_error: {e}")

# ---------- Customers ----------
@app.post("/customers")
async def api_customer_create(payload: CustomerCreate):
    try:
        row = await add_customer(payload.name, payload.phone, payload.address)
        return row  # {id,name,phone,address}
    except Exception as e:
        # If you enforce UNIQUE(phone), consider mapping to 409 here
        detail = str(e)
        if "duplicate key" in detail.lower() or "unique" in detail.lower():
            raise HTTPException(409, "phone_already_exists")
        raise HTTPException(500, f"db_error: {e}")

@app.get("/customers/by-phone/{phone}")
async def api_customer_by_phone(phone: str):
    try:
        row = await get_customer_by_phone(phone)
        if not row:
            raise HTTPException(404, "not_found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"db_error: {e}")

@app.patch("/customers/{customer_id}")
async def api_customer_update(customer_id: int, payload: CustomerUpdateIn):
    try:
        row = await update_customer(
            customer_id=customer_id,
            name=payload.name,
            phone=payload.phone,
            address=payload.address,
        )
        if not row:
            raise HTTPException(404, "customer_not_found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        detail = str(e)
        if "duplicate key" in detail.lower() or "unique" in detail.lower():
            raise HTTPException(409, "phone_already_exists")
        raise HTTPException(500, f"db_error: {e}")

# ---------- Orders ----------
@app.post("/orders")
async def api_order_create(payload: OrderCreate):
    try:
        row = await add_order(
            customer_id=payload.customer_id,
            items=payload.items,
            dine_in=payload.dine_in,
            address=payload.address,
            phone=payload.phone,
            table_number=payload.table_number,
        )
        return row
    except Exception as e:
        raise HTTPException(500, f"db_error: {e}")

@app.get("/orders/{order_id}")
async def api_order_get(order_id: int):
    try:
        row = await get_order_by_id(order_id)
        if not row:
            raise HTTPException(404, "not_found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"db_error: {e}")

# ---------- Complains ----------
@app.post("/complains")
async def api_complain_create(payload: ComplainCreate):
    try:
        new_id = await add_complain(payload.description)
        return {"id": new_id}
    except ValueError as ve:
        raise HTTPException(400, str(ve))
    except Exception as e:
        raise HTTPException(500, f"db_error: {e}")
