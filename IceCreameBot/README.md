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

---

Design addendum: Context, Popularity, Analytics, and ML roadmap

Objectives
- Context-aware suggestions using session vision attributes and global weather/time.
- Popularity counters per segment with global fallback.
- Decoupled analytics for manager insights and forecasting.
- ML layering: lightweight clustering and next-slot/next-day predictions.

Key Concepts
- Segment fields: `age_group`, `gender_guess`, `time_of_day`, `temperature_bucket`.
- Segment key: `"<age>_<gender>_<temp>_<time>"` with bounded vocabularies.
- Emotion usage: secondary signal only; average over 2–3 seconds; never surface directly to users.

Services (decoupled from agent)
1) Context Cache Service
- Fetch weather via API every 5–10 minutes; compute `temperature_bucket ∈ {cool, normal, hot}`.
- Provide `time_of_day ∈ {morning, afternoon, evening}` on read.
- Expose fast reads (in-memory or local cache) for the agent.

2) Popularity Store (Category-level)
- Counters: `popularity[segment_key][category] = int`, `global_popularity[category] = int`.
- Increment on confirmed selection events (use chosen category).
- Optional: light time decay for responsiveness (not required for expo).

3) Analytics Pipeline (Managers)
- Event stream: `selection`, `more_options_click`, `session_context_snapshot`.
- Aggregations:
	- Top 5 flavours overall (daily).
	- Top flavours by segment (age, gender, hot/cool, time).
	- Time slots with highest sales.
	- Optional: trend “Mood vs Sales” (aggregate only).
- Dashboard reads aggregates periodically (15–30 min). Agent never waits on analytics.

Agent Flow (single-agent, modular)
- Each turn: frontend sends `{session_id, age_group, gender_guess, mood}`; no raw media.
- Backend reads global `{time_of_day, temperature_bucket}` from Context Cache.
- Build segment key, fetch top 2–3 flavours; fallback to global top.
- Emotion reorders or offers “More options” after ~2–3s stable neutral/confusion.

Interfaces (no implementation yet)
- `SessionContextReader(session_id) -> {age_group, gender_guess, mood}`
- `GlobalContextReader() -> {time_of_day, temperature_bucket}`
- `CategoryPopularityStore`
	- `get_top_categories(segment_key, k=3) -> [category]`
	- `get_global_top_categories(k=3) -> [category]`
	- `increment(segment_key, category)`
- `AnalyticsSink.emit(event_type, payload)`

ML Roadmap
- Clustering: K-Modes/K-Prototypes or Mini-Batch K-Means on one-hot features; refresh every 1–2 hours; store `cluster_id` and top categories; use as optional bias.
- Prediction: Poisson/Negative Binomial or GBT for top categories per `time_of_day × temperature_bucket`; rolling windows; next-slot/next-day outputs.
- Satisfaction: 0–1 score from affect trend, hesitation, explicit confirmations; report averages by segment/cluster/time; suggestion funnel.

Privacy & UX
- Derived attributes only; aggregate affect; never state emotion explicitly.
- Agent path remains fast and independent of analytics/ML refreshes.

Rollout Order
1. Define and wire `SessionContextReader`, `GlobalContextReader`, `PopularityStore`.
2. Agent uses them for suggestions and emits `selection` events to `AnalyticsSink`.
3. Build basic aggregates and dashboard.
4. Add clustering refresh and satisfaction aggregation.
5. Add forecasting for next-slot/next-day and use for merchandising and early suggestions.
