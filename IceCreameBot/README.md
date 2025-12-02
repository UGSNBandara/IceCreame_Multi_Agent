Ice Cream Agent – MongoDB setup

Environment variables (use .env at repo root or PowerShell env vars):

- MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>/<params>
- MONGO_DB=icecream_agent

Collections expected:

- menu: documents with fields { id:int, name:str, description:str, price:float, updated_at:iso8601 }
- orders: minimal schema { id:int, customer_name:str, items:list, total:float, created_at:iso8601, updated_at:iso8601 }

Run (from repo root or IceCreameBot folder):

1) Create and activate venv, install requirements if needed
2) Set env vars or create .env, then

	uvicorn IceCreameBot.api:app --reload

Notes

- Menu and recent orders hydrate from Mongo on startup; SQLite is a cache.
- Use `/admin/sync-now` to flush outbox events to Mongo immediately.
