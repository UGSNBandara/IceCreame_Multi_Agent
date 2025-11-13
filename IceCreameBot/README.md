Coffee Shop Agent – MongoDB setup

Environment variables (use .env at repo root or PowerShell env vars):

- MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/<params>
- MONGODB_DB=coffee_shop

Collections expected:

- menu: documents with fields { id:int, name:str, description:str, price:float }
- customer: unique index on phone, fields { name, phone, address }
- orders: inserted by API with fields { customer_id?, items:list, dine_in:bool, address?, phone?, table_number?, done:bool }
 - orders: minimal schema { customer_name:str, items:list, total:float, created_at:iso8601 }
- complains: { description }

Run (from IceCreameBot folder):

1) Create and activate venv, install requirements if needed
2) Set env vars or create .env, then

	uvicorn api:app --reload

Notes

- IDs returned from Mongo are ObjectId strings (e.g., order id, customer id, complain id).
- Menu is loaded on startup from Mongo (menu collection). Seed this first.
