# Ice Cream Agent

A FastAPI-based assistant for an ice cream shop with text-to-speech (TTS) and Mongo-backed persistence.

## Features
- Menu browsing and ordering
- Cart management
- Order tracking with status updates
- Offline TTS using pyttsx3 (Windows-friendly)
- SQLite cache with MongoDB as the source of truth

## Setup Locally
1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your `GOOGLE_API_KEY` (from [Google AI Studio](https://aistudio.google.com))

4. Run the app:
   ```bash
   uvicorn IceCreameBot.api:app --reload
   ```
   - Access at `http://127.0.0.1:8000`
   - API docs at `http://127.0.0.1:8000/docs`

## Deploy to Railway
1. Push your code to GitHub (includes `Procfile` for start command).

2. Go to [Railway.app](https://railway.app) and sign up/login.

3. Click "New Project" > "Deploy from GitHub repo" > Select your repo.

4. Railway auto-detects Python and installs from `requirements.txt`.

5. In Railway dashboard > Variables tab, add:
   - `GOOGLE_API_KEY`: Your Gemini API key
   - `MONGO_URI`: Connection string to your MongoDB/Atlas
   - `MONGO_DB`: `icecream_agent` (optional; default used by app)
   - `SQLITE_DB_PATH`: `icecream.db` (optional; default used by app)

6. Deploy! Railway uses the `Procfile` for the start command.

7. On pushes to the connected branch, Railway auto-redeploys.

## API Endpoints
- `GET /health`: Health check
- `POST /agent/`: Chat with the agent
- `POST /agent/text`: Chat (text-only, no TTS)
- `GET /menu/items`: List menu items
- `POST /menu/items`: Add menu item
- `PUT /menu/items/{id}`: Update menu item
- `DELETE /menu/items/{id}`: Delete menu item
- `GET /orders`: List orders
- `PUT /orders/{id}/status`: Update order status
- `GET /orders/{id}`: Get single order
- `POST /generate-voice/`: Generate TTS audio

## Notes
- TTS uses pyttsx3 on Windows and Piper where available.
- Persistence: MongoDB is the source of truth; SQLite (`icecream.db`) is a local cache hydrated from Mongo on startup.
- Free Railway tier: 512MB RAM, sleeps after inactivity.

## Contributing
- Use branches for features.
- Add tests in `tests/`.